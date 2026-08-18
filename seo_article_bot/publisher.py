"""发布器：本地 Markdown 输出（含 frontmatter 与 sitemap），或 WordPress REST API 发布。"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import requests

from .config import PROJECT_ROOT
from .frontmatter import dump_markdown
from .seo import build_json_ld, render_article_html, write_sitemap


class LocalPublisher:
    """把文章写成 output/<slug>/index.md，并维护 sitemap.xml。"""

    def __init__(self, config: dict):
        self.config = config
        site = config["site"]
        publish = config["publish"]
        self.site_url = site["url"]
        self.site_name = site.get("name", "我的工具站")
        self.language = site.get("language", "zh-CN")
        self.output_dir = Path(publish.get("local", {}).get("output_dir", "output"))
        if not self.output_dir.is_absolute():
            self.output_dir = PROJECT_ROOT / self.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def publish(self, article) -> Path:
        article_dir = self.output_dir / article.slug
        article_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "title": article.title,
            "slug": article.slug,
            "keyword": article.keyword,
            "category": article.category,
            "summary": article.summary,
            "tags": article.tags,
            "date": article.created_at,
            "json_ld": build_json_ld(article, self.site_url, self.site_name, self.language),
        }
        md_file = article_dir / "index.md"
        md_file.write_text(dump_markdown(meta, article.markdown), encoding="utf-8")
        write_sitemap(self.output_dir, self.site_url, self.language)
        return md_file


class WordPressPublisher:
    """通过 WordPress REST API 发布文章（Basic Auth + 应用密码）。"""

    def __init__(self, config: dict):
        self.config = config
        site = config["site"]
        wp = config["publish"]["wordpress"]
        self.site_url = site["url"]
        self.site_name = site.get("name", "我的工具站")
        self.language = site.get("language", "zh-CN")
        self.base_url = wp["base_url"].rstrip("/")
        self.username = wp["username"]
        app_password = wp.get("app_password") or os.environ.get(
            wp.get("app_password_env", "WORDPRESS_APP_PASSWORD"), ""
        )
        if not app_password:
            raise RuntimeError(
                "未配置 WordPress 应用密码：请在 config.yaml 的 app_password 或 "
                f"环境变量 {wp.get('app_password_env', 'WORDPRESS_APP_PASSWORD')} 中提供。"
            )
        token = base64.b64encode(f"{self.username}:{app_password}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }
        self.status = wp.get("post_status", "draft")
        # WordPress 分类是数字 ID，需在配置里按实际后台 ID 填写
        self.category_ids = [int(c) for c in wp.get("category_ids", []) if str(c).isdigit()]

    def publish(self, article) -> int:
        html = render_article_html(article, self.site_url, self.site_name, self.language)
        payload: dict[str, Any] = {
            "title": article.title,
            "slug": article.slug,
            "content": html,
            "status": self.status,
            "tags": article.tags,
        }
        if self.category_ids:
            payload["categories"] = self.category_ids
        resp = requests.post(f"{self.base_url}/posts", json=payload, headers=self.headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        post_id = data.get("id")
        if not post_id:
            raise RuntimeError(f"WordPress 返回异常：{data}")
        return post_id


def make_publisher(config: dict):
    if config["publish"]["type"] == "wordpress":
        return WordPressPublisher(config)
    return LocalPublisher(config)
