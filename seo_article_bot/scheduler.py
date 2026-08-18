"""定时发布调度：schedule 库循环运行；也支持系统 cron / 计划任务调用 --once。"""

from __future__ import annotations

import json
import logging
import time
from datetime import date
from pathlib import Path

import schedule

from .config import PROJECT_ROOT

logger = logging.getLogger("seo_bot.scheduler")


class DailyLimit:
    """记录当天已发布数量，跨天自动重置。"""

    def __init__(self, state_file: Path | None = None):
        self.state_file = state_file or (PROJECT_ROOT / "scheduler_state.json")
        self.data: dict = {}
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            try:
                self.data = json.loads(self.state_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.data = {}

    def _save(self) -> None:
        self.state_file.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def published_today(self) -> int:
        today = date.today().isoformat()
        if self.data.get("date") != today:
            self.data = {"date": today, "count": 0}
        return int(self.data.get("count", 0))

    def add(self, n: int = 1) -> None:
        today = date.today().isoformat()
        if self.data.get("date") != today:
            self.data = {"date": today, "count": 0}
        self.data["count"] = int(self.data.get("count", 0)) + n
        self._save()


def run_once(
    config: dict,
    mock: bool = False,
    count: int | None = None,
    dry_run: bool = False,
    category: str | None = None,
) -> int:
    """生成并发布一批文章，返回发布数量。尊重 max_daily 上限。"""
    from .generator import ArticleGenerator
    from .publisher import make_publisher
    from .topics import TopicPool

    sched = config.get("schedule", {})
    posts_per_run = count or sched.get("posts_per_run", 1)
    max_daily = sched.get("max_daily", 10)

    limit = DailyLimit()
    remaining = max_daily - limit.published_today()
    if remaining <= 0:
        logger.info("今日已达发布上限 %s 篇，跳过。", max_daily)
        return 0
    posts_per_run = min(posts_per_run, remaining)

    pool = TopicPool(config)
    topics = pool.next_topics(posts_per_run, category=category)
    if not topics:
        logger.info("主题池已用尽，请扩充 topics.csv。")
        return 0

    generator = ArticleGenerator(config)
    publisher = make_publisher(config)
    published = 0
    for topic in topics:
        logger.info("生成文章：%s（类别 %s）", topic.keyword, topic.category)
        article = generator.generate(topic, mock=mock)
        if dry_run:
            logger.info("[dry-run] 跳过发布：%s", article.title)
        else:
            publisher.publish(article)
        published += 1
    if not dry_run:
        pool.mark_used(topics)
        limit.add(published)
    logger.info("本批完成：%s 篇（今日已发布 %s/%s）", published, limit.published_today(), max_daily)
    return published


def run_scheduler(config: dict, mock: bool = False) -> None:
    """常驻循环：按 config.schedule.interval_minutes 定时发布。"""
    sched = config.get("schedule", {})
    interval = max(1, int(sched.get("interval_minutes", 60)))
    at_time = sched.get("at_time")
    logger.info("定时任务启动：每 %s 分钟发布一批（mock=%s）", interval, mock)

    if at_time:
        schedule.every().day.at(at_time).do(run_once, config, mock)
    else:
        schedule.every(interval).minutes.do(run_once, config, mock)

    run_once(config, mock=mock)  # 启动后立即跑一批
    while True:
        schedule.run_pending()
        time.sleep(10)
