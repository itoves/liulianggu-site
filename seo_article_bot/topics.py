"""主题池管理：内置种子主题 + 可选 topics.csv 自定义池，记录已用主题避免重复。"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path

from .config import PROJECT_ROOT

# 内置种子主题（可被 topics.csv 覆盖）。类别：calculator/converter/faq/guide
BUILTIN_TOPICS: list[tuple[str, str]] = [
    ("房贷计算器", "calculator"),
    ("个人所得税计算器", "calculator"),
    ("BMI 体重指数计算器", "calculator"),
    ("贷款利息计算器", "calculator"),
    ("存款利息计算器", "calculator"),
    ("温度单位换算", "converter"),
    ("人民币大写转换", "converter"),
    ("二进制/十六进制换算", "converter"),
    ("尺寸单位换算(厘米/英寸)", "converter"),
    ("面积单位换算", "converter"),
    ("网站收录多久生效", "faq"),
    ("AdSense 过审需要什么条件", "faq"),
    ("SSL 证书过期怎么处理", "faq"),
    ("WordPress 提速优化清单", "guide"),
    ("新手建站完整攻略", "guide"),
    ("SEO 外链建设方法清单", "guide"),
    ("网站关键词布局技巧", "guide"),
]


@dataclass
class Topic:
    keyword: str
    category: str = "faq"
    target_url: str = ""


class TopicPool:
    def __init__(self, config: dict, project_root: Path | None = None):
        self.config = config
        self.project_root = project_root or PROJECT_ROOT
        self.used_file = self.project_root / "topics_used.json"
        self.used: set[str] = self._load_used()
        self.pool: list[Topic] = self._load_pool()

    def _load_used(self) -> set[str]:
        if self.used_file.exists():
            try:
                data = json.loads(self.used_file.read_text(encoding="utf-8"))
                return set(data.get("used", []))
            except (json.JSONDecodeError, OSError):
                return set()
        return set()

    def _load_pool(self) -> list[Topic]:
        pool_file = self.project_root / "topics.csv"
        if pool_file.exists():
            topics: list[Topic] = []
            with pool_file.open(encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    keyword = (row.get("keyword") or "").strip()
                    if not keyword:
                        continue
                    topics.append(
                        Topic(
                            keyword=keyword,
                            category=(row.get("category") or "faq").strip(),
                            target_url=(row.get("target_url") or "").strip(),
                        )
                    )
            if topics:
                return topics
        return [Topic(k, c) for k, c in BUILTIN_TOPICS]

    def next_topics(self, count: int, category: str | None = None) -> list[Topic]:
        """取 count 个未用过的主题；category 指定时优先该方向，不足则退回全池。"""
        unused = [t for t in self.pool if t.keyword not in self.used]
        if category:
            cat_unused = [t for t in unused if t.category == category]
            if cat_unused:
                unused = cat_unused
        if not unused:
            unused = list(self.pool)
        random.shuffle(unused)
        return unused[:count]

    def mark_used(self, topics: list[Topic]) -> None:
        for t in topics:
            self.used.add(t.keyword)
        self.used_file.write_text(
            json.dumps({"used": sorted(self.used)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def remaining(self) -> int:
        return len([t for t in self.pool if t.keyword not in self.used])
