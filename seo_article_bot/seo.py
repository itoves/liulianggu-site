"""SEO 工具：slug 生成、JSON-LD 结构化数据、Markdown 转 HTML、sitemap 生成。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import markdown as md_lib
from slugify import slugify


def make_slug(text: str, fallback: str = "page") -> str:
    """生成 URL slug；中文经拼音转写，失败时用 md5 短哈希兜底。"""
    s = slugify(text, max_length=60, word_boundary=True)
    if not s:
        s = fallback + "-" + hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    return s


def build_json_ld(article: Any, site_url: str, site_name: str, language: str) -> dict:
    """构造 Article + FAQPage 结构化数据。"""
    url = f"{site_url.rstrip('/')}/{article.slug}/"
    base = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article.title,
        "description": article.summary,
        "datePublished": article.created_at,
        "dateModified": article.created_at,
        "author": {"@type": "Organization", "name": site_name},
        "publisher": {"@type": "Organization", "name": site_name},
        "mainEntityOfPage": url,
        "inLanguage": language,
        "keywords": ",".join(article.tags),
    }
    faq_items = [
        {"@type": "Question", "name": it["q"], "acceptedAnswer": {"@type": "Answer", "text": it["a"]}}
        for it in article.faq
    ]
    if faq_items:
        base["mainEntity"] = [{"@type": "FAQPage", "mainEntity": faq_items}]
    return base


def html_from_markdown(md_text: str) -> str:
    return md_lib.markdown(md_text, extensions=["tables", "fenced_code", "toc"])


def render_article_html(article: Any, site_url: str, site_name: str, language: str) -> str:
    """WordPress 正文 HTML：Markdown 转 HTML + 注入 JSON-LD。"""
    body = html_from_markdown(article.markdown)
    schema = build_json_ld(article, site_url, site_name, language)
    script = '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False) + "</script>"
    return body + "\n" + script


def write_sitemap(output_dir, site_url: str, language: str) -> None:
    """扫描本地 output 目录，生成 sitemap.xml。"""
    from .frontmatter import parse_frontmatter

    urls: list[tuple[str, str]] = []
    if output_dir.exists():
        for md_file in sorted(output_dir.glob("*/index.md")):
            meta = parse_frontmatter(md_file)
            slug = meta.get("slug")
            if not slug:
                continue
            lastmod = meta.get("date", datetime.now(timezone.utc).date().isoformat())
            urls.append((f"{site_url.rstrip('/')}/{slug}/", lastmod))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url, lastmod in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{url}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("  </url>")
    lines.append("</urlset>")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
