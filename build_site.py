"""静态站生成器：把 output/*/index.md 渲染成可直接部署的静态 HTML 站点。

用法:
  python build_site.py                 # 用 config.yaml 里的 site.url 构建
  python build_site.py --domain https://你的域名.com   # 覆盖域名（部署时用真实域名）

产出: site/ 目录，包含 index.html、文章页、style.css、robots.txt、sitemap.xml。
本地预览: python -m http.server 8000 -d site
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from html import escape
from pathlib import Path

import markdown as md_lib
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
SITE_DIR = PROJECT_ROOT / "site"

MD = md_lib.Markdown(extensions=["tables", "fenced_code", "toc"])


# ---------------- 数据读取 ----------------

def read_config() -> dict:
    """读取 config.yaml；CI/无配置环境下回退默认站点配置（域名用 --domain 覆盖）。"""
    cfg_path = PROJECT_ROOT / "config.yaml"
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        if cfg.get("site"):
            return cfg
    return {
        "site": {
            "name": "我的工具站",
            "url": "https://example.com",
            "language": "zh-CN",
            "tagline": "小而实用的在线工具与知识指南，全部免费使用。",
        }
    }


def read_articles() -> list[dict]:
    articles = []
    for md_file in sorted(OUTPUT_DIR.glob("*/index.md")):
        text = md_file.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        if end == -1:
            continue
        meta = yaml.safe_load(text[3:end]) or {}
        body = text[end + 4 :].strip()
        if not meta.get("slug"):
            continue
        articles.append({"meta": meta, "body_md": body})
    # 按日期倒序
    articles.sort(key=lambda a: a["meta"].get("date", ""), reverse=True)
    return articles


# ---------------- 渲染 ----------------

def render_article_html(article: dict) -> str:
    """Markdown 正文转 HTML，并给 h2/h3 加锚点。"""
    MD.reset()
    html = MD.convert(article["body_md"])
    # 给标题加锚点 id（toc 扩展已生成 id，只需包一层）
    for level in (2, 3):
        pattern = re.compile(rf"<h{level}>(.*?)</h{level}>", re.S)
        html = pattern.sub(
            lambda m: f'<h{level} id="{_slug_id(m.group(1))}">{m.group(1)}</h{level}>', html
        )
    return html


def _slug_id(text: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text).strip("-").lower()
    return s[:60] or "sec"


def page_wrap(title: str, content_html: str, site: dict, canonical: str = "", description: str = "",
              extra_head: str = "", active: str = "") -> str:
    site_url = site["url"].rstrip("/")
    return f"""<!DOCTYPE html>
<html lang="{site.get('language', 'zh-CN')}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
{('<meta name="description" content="' + escape(description) + '">') if description else ""}
{('<link rel="canonical" href="' + escape(canonical) + '">') if canonical else ""}
<meta property="og:title" content="{escape(title)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{escape(canonical or site_url)}">
<meta property="og:site_name" content="{escape(site.get('name', ''))}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/style.css">
{extra_head}
</head>
<body>
<header class="site-header">
  <div class="container header-inner">
    <a class="logo" href="/">{escape(site.get('name', '我的工具站'))}</a>
    <nav>
      <a href="/" class="{('active' if active == 'home' else '')}">首页</a>
      <a href="/#articles">全部文章</a>
    </nav>
  </div>
</header>
<main class="container">{content_html}</main>
<footer class="site-footer">
  <div class="container">
    <p>&copy; {datetime.now().year} {escape(site.get('name', '我的工具站'))} · 内容均为原创，仅供学习参考</p>
    <p><a href="/sitemap.xml">sitemap</a> · <a href="/robots.txt">robots</a></p>
  </div>
</footer>
</body>
</html>"""


def render_home(articles: list[dict], site: dict) -> str:
    cards = []
    for a in articles:
        meta = a["meta"]
        summary = (meta.get("summary") or "")[:90]
        date = meta.get("date", "")
        cards.append(f"""
<article class="card">
  <a class="card-link" href="/{meta['slug']}/">
    <span class="badge">{escape(meta.get('category', '文章'))}</span>
    <h3>{escape(meta['title'])}</h3>
    <p>{escape(summary)}…</p>
    <time>{date}</time>
  </a>
</article>""")
    grid = "\n".join(cards) if cards else '<p class="empty">还没有文章。先运行 <code>python main.py generate --count 5</code> 生成内容。</p>'
    return f"""
<section class="hero">
  <h1>{escape(site.get('name', '我的工具站'))}</h1>
  <p>{escape(site.get('tagline', '小而实用的在线工具与知识指南，全部免费使用。'))}</p>
  <p class="stat">已收录 <strong>{len(articles)}</strong> 篇实用内容</p>
</section>
<section id="articles">
  <h2>全部文章</h2>
  <div class="grid">{grid}</div>
</section>"""


def render_article_page(article: dict, site: dict) -> str:
    meta = article["meta"]
    body_html = render_article_html(article)
    site_url = site["url"].rstrip("/")
    canonical = f"{site_url}/{meta['slug']}/"
    json_ld = meta.get("json_ld") or {}
    if not json_ld:
        json_ld = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": meta["title"],
            "description": meta.get("summary", ""),
            "datePublished": meta.get("date", ""),
            "author": {"@type": "Organization", "name": site.get("name", "")},
        }
    script = '<script type="application/ld+json">' + json.dumps(json_ld, ensure_ascii=False) + "</script>"
    tags = "".join(f'<span class="tag">{escape(t)}</span>' for t in (meta.get("tags") or []))
    content = f"""
<nav class="breadcrumb"><a href="/">首页</a> <span>/</span> <span>{escape(meta.get('category', '文章'))}</span></nav>
<article class="post">
  <header>
    <h1>{escape(meta['title'])}</h1>
    <div class="post-meta"><time>{meta.get('date', '')}</time>{tags}</div>
  </header>
  <div class="post-body">{body_html}</div>
</article>
<section class="related">
  <h2>相关阅读</h2>
  <p><a href="/">返回首页查看其他文章</a></p>
</section>"""
    return page_wrap(meta["title"], content, site, canonical=canonical,
                     description=meta.get("summary", ""), extra_head=script)


# ---------------- 站点文件 ----------------

STYLE_CSS = """:root{--bg:#f6f7f9;--card:#fff;--ink:#1f2937;--muted:#6b7280;--accent:#2563eb;--line:#e5e7eb}
*{box-sizing:border-box}
body{margin:0;font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.7}
.container{max-width:960px;margin:0 auto;padding:0 20px}
.site-header{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}
.header-inner{display:flex;align-items:center;justify-content:space-between;height:60px}
.logo{font-size:19px;font-weight:700;color:var(--ink);text-decoration:none}
nav a{margin-left:18px;color:var(--muted);text-decoration:none}
nav a:hover,nav a.active{color:var(--accent)}
.hero{text-align:center;padding:56px 0 30px}
.hero h1{font-size:32px;margin:0 0 10px}
.hero p{margin:6px 0;color:var(--muted)}
.stat strong{color:var(--accent);font-size:22px}
#articles h2,.related h2{font-size:22px;margin:34px 0 14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-bottom:40px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.07)}
.card-link{display:block;padding:18px;text-decoration:none;color:inherit}
.card h3{margin:8px 0;font-size:17px;color:var(--ink)}
.card p{margin:0 0 8px;color:var(--muted);font-size:14px}
.card time{color:var(--muted);font-size:13px}
.badge{display:inline-block;background:#eef2ff;color:var(--accent);font-size:12px;padding:2px 8px;border-radius:999px}
.empty{color:var(--muted)}
.breadcrumb{font-size:13px;color:var(--muted);margin:24px 0 8px}
.breadcrumb a{color:var(--accent);text-decoration:none}
.post{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:28px 32px;margin-bottom:24px}
.post h1{font-size:26px;margin:0 0 10px}
.post-meta{color:var(--muted);font-size:13px;margin-bottom:16px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.tag{background:#f3f4f6;padding:2px 8px;border-radius:999px}
.post-body h2{font-size:21px;margin:26px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.post-body h3{font-size:17px;margin:20px 0 8px}
.post-body table{border-collapse:collapse;width:100%;margin:14px 0;font-size:14px}
.post-body th,.post-body td{border:1px solid var(--line);padding:8px 10px;text-align:left}
.post-body th{background:#f9fafb}
.post-body blockquote{margin:14px 0;padding:10px 16px;border-left:4px solid var(--accent);background:#eff6ff;color:#374151}
.post-body code{background:#f3f4f6;padding:2px 5px;border-radius:4px;font-size:13px}
.post-body a{color:var(--accent)}
.related{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px 28px;margin-bottom:40px}
.site-footer{border-top:1px solid var(--line);background:#fff;color:var(--muted);font-size:13px;padding:26px 0;margin-top:40px}
.site-footer p{margin:4px 0}
.site-footer a{color:var(--accent);text-decoration:none}
@media(max-width:640px){.post{padding:20px}.hero h1{font-size:26px}}"""


def write_static_files(site: dict, site_url: str) -> None:
    (SITE_DIR / "style.css").write_text(STYLE_CSS, encoding="utf-8")
    favicon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="#2563eb"/><text x="50" y="68" font-size="52" text-anchor="middle" fill="#fff" font-family="Arial">S</text></svg>'
    (SITE_DIR / "favicon.svg").write_text(favicon, encoding="utf-8")
    (SITE_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site_url.rstrip('/')}/sitemap.xml\n", encoding="utf-8"
    )


def write_sitemap(articles: list[dict], site_url: str) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for a in articles:
        meta = a["meta"]
        lines.append("  <url>")
        lines.append(f"    <loc>{site_url.rstrip('/')}/{meta['slug']}/</loc>")
        lines.append(f"    <lastmod>{meta.get('date', datetime.now().date().isoformat())}</lastmod>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("  </url>")
    lines.append("</urlset>")
    (SITE_DIR / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------- 构建 ----------------

def build(domain: str | None = None) -> Path:
    config = read_config()
    site = config.get("site", {})
    site_url = (domain or site.get("url", "https://example.com")).rstrip("/")
    site = dict(site, url=site_url)

    articles = read_articles()
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    # 清理站点里已不存在的文章目录，避免旧页面残留
    current_slugs = {a["meta"]["slug"] for a in articles}
    for child in SITE_DIR.iterdir():
        if child.is_dir() and (child / "index.html").exists() and child.name not in current_slugs:
            shutil.rmtree(child)

    (SITE_DIR / "index.html").write_text(
        page_wrap(site.get("name", "我的工具站"), render_home(articles, site), site,
                  canonical=f"{site_url}/", description=site.get("tagline", ""), active="home"),
        encoding="utf-8",
    )
    for a in articles:
        meta = a["meta"]
        page_dir = SITE_DIR / meta["slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(render_article_page(a, site), encoding="utf-8")

    write_static_files(site, site_url)
    write_sitemap(articles, site_url)
    return SITE_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="构建静态 SEO 站点")
    parser.add_argument("--domain", help="覆盖站点域名，如 https://mytools.example.com")
    args = parser.parse_args()
    site_dir = build(args.domain or None)
    n = len(read_articles())
    print(f"构建完成: {site_dir}")
    print(f"页面数: 首页 + {n} 篇文章")
    print("本地预览: python -m http.server 8000 -d site")


if __name__ == "__main__":
    raise SystemExit(main())
