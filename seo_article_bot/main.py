"""CLI 入口实现（供 python -m seo_article_bot 与根目录 main.py 调用）。

命令：
  init        从示例生成 config.yaml（已存在则跳过）
  generate    仅生成文章到本地 output/（不发布）
  publish     生成并发布（按配置 local/wordpress）
  schedule    常驻定时发布
  sitemap     重新生成本地 sitemap.xml
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import PROJECT_ROOT, load_config
from .generator import ArticleGenerator
from .publisher import LocalPublisher
from .seo import write_sitemap
from .topics import TopicPool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def cmd_init(_args) -> int:
    example = PROJECT_ROOT / "config.example.yaml"
    target = PROJECT_ROOT / "config.yaml"
    if target.exists():
        print(f"config.yaml 已存在：{target}")
        return 0
    if not example.exists():
        print(f"缺少模板文件：{example}", file=sys.stderr)
        return 1
    target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"已生成 {target}，请打开并按注释填写配置。")
    return 0


def cmd_generate(args) -> int:
    """只生成到本地 output/，无论发布模式配置是什么。"""
    config = load_config(args.config)
    pool = TopicPool(config)
    topics = pool.next_topics(args.count, category=args.category)
    generator = ArticleGenerator(config)
    publisher = LocalPublisher(config)
    for topic in topics:
        article = generator.generate(topic, mock=args.mock)
        path = publisher.publish(article)
        pool.mark_used([topic])
        print(f"[生成] {article.title}\n       -> {path}")
    return 0


def cmd_publish(args) -> int:
    from .scheduler import run_once

    published = run_once(
        config=load_config(args.config),
        mock=args.mock,
        count=args.count,
        dry_run=args.dry_run,
        category=args.category,
    )
    verb = "生成(dry-run)" if args.dry_run else "发布"
    print(f"本次{verb} {published} 篇。")
    return 0


def cmd_schedule(args) -> int:
    from .scheduler import run_scheduler

    run_scheduler(load_config(args.config), mock=args.mock)
    return 0


def cmd_sitemap(args) -> int:
    config = load_config(args.config)
    publish = config["publish"]
    if publish.get("type") == "wordpress":
        print("wordpress 模式下 sitemap 由 WordPress 插件管理，跳过本地生成。")
        return 0
    output_dir = Path(publish["local"].get("output_dir", "output"))
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    write_sitemap(output_dir, config["site"]["url"], config["site"].get("language", "zh-CN"))
    print(f"已更新 sitemap：{output_dir / 'sitemap.xml'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="SEO 内容站：AI 生成文章并定时发布",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="从示例生成 config.yaml")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("generate", help="仅生成文章到本地 output/")
    p.add_argument("--count", type=int, default=1, help="生成篇数（默认 1）")
    p.add_argument("--category", default=None, help="只取指定方向主题（如 理财/装修/母婴/工具）")
    p.add_argument("--mock", action="store_true", help="本地模板模式，不调用 AI API")
    p.add_argument("--config", default=str(PROJECT_ROOT / "config.yaml"), help="配置文件路径")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("publish", help="生成并发布文章")
    p.add_argument("--count", type=int, default=None, help="本次发布篇数（默认取配置 posts_per_run）")
    p.add_argument("--category", default=None, help="只取指定方向主题（如 理财/装修/母婴/工具）")
    p.add_argument("--mock", action="store_true", help="本地模板模式，不调用 AI API")
    p.add_argument("--dry-run", action="store_true", help="只生成不发布，不消耗主题")
    p.add_argument("--config", default=str(PROJECT_ROOT / "config.yaml"), help="配置文件路径")
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser("schedule", help="常驻定时发布（Ctrl+C 退出）")
    p.add_argument("--mock", action="store_true", help="本地模板模式")
    p.add_argument("--config", default=str(PROJECT_ROOT / "config.yaml"), help="配置文件路径")
    p.set_defaults(func=cmd_schedule)

    p = sub.add_parser("sitemap", help="重新生成本地 sitemap.xml")
    p.add_argument("--config", default=str(PROJECT_ROOT / "config.yaml"), help="配置文件路径")
    p.set_defaults(func=cmd_sitemap)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
