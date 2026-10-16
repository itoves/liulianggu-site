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


def load_registry() -> dict:
    """读取 tools/registry.json（工具站配置）。缺失时返回空字典。"""
    reg_path = PROJECT_ROOT / "tools" / "registry.json"
    if reg_path.exists():
        try:
            return json.loads(reg_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def copy_tool_assets(site_dir: Path) -> None:
    """把工具引擎与配置复制到 site/assets，供浏览器加载。"""
    assets = site_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    src = PROJECT_ROOT / "tools" / "tools.js"
    if src.exists():
        shutil.copyfile(src, assets / "tools.js")
    reg = PROJECT_ROOT / "tools" / "registry.json"
    if reg.exists():
        shutil.copyfile(reg, assets / "registry.json")


def load_verification_head() -> str:
    """读取 verification.json，生成搜索引擎验证 meta 与 AdSense 脚本，注入每个页面 <head>。

    字段（留空则不注入）：
      google  - Google Search Console 的 content（meta google-site-verification）
      bing    - Bing Webmaster 的 content（meta msvalidate.01）
      baidu   - 百度搜索资源平台的 content（meta baidu-site-verification）
      adsense - AdSense 客户端 ID，如 ca-pub-XXXXXXXXXXXXXX（注入广告脚本）
    """
    vp = PROJECT_ROOT / "verification.json"
    if not vp.exists():
        return ""
    try:
        v = json.loads(vp.read_text(encoding="utf-8"))
    except Exception:
        return ""
    tags = []
    if v.get("google"):
        tags.append(f'<meta name="google-site-verification" content="{escape(str(v["google"]))}">')
    if v.get("bing"):
        tags.append(f'<meta name="msvalidate.01" content="{escape(str(v["bing"]))}">')
    if v.get("baidu"):
        tags.append(f'<meta name="baidu-site-verification" content="{escape(str(v["baidu"]))}">')
    if v.get("adsense"):
        tags.append(
            '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
            f'?client={escape(str(v["adsense"]))}" crossorigin="anonymous"></script>'
        )
    return "\n".join(tags)


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
{load_verification_head()}
{extra_head}
</head>
<body>
<header class="site-header">
  <div class="container header-inner">
    <a class="logo" href="/">{escape(site.get('name', '我的工具站'))}</a>
    <nav>
      <a href="/" class="{('active' if active == 'home' else '')}">首页</a>
      <a href="/#categories">分类</a>
    </nav>
  </div>
</header>
<main class="container">{content_html}</main>
<footer class="site-footer">
  <div class="container">
    <p>&copy; {datetime.now().year} {escape(site.get('name', '我的工具站'))} · 内容均为原创，仅供学习参考</p>
    <p><a href="/sitemap.xml">sitemap</a> · <a href="/robots.txt">robots</a> · <a href="/privacy/">隐私政策</a></p>
  </div>
</footer>
</body>
</html>"""


# 分类归一化（历史遗留的英文分类 -> 中文）与配色
CAT_FIX = {"converter": "工具", "guide": "站长", "faq": "工具"}
CAT_COLORS = [
    "#2563eb", "#0891b2", "#059669", "#d97706", "#dc2626", "#7c3aed",
    "#db2777", "#0d9488", "#65a30d", "#ea580c", "#4f46e5", "#b45309",
    "#0369a1", "#9333ea",
]


def _norm_cat(name: str) -> str:
    raw = (name or "").strip()
    return CAT_FIX.get(raw.lower(), raw or "未分类")


HOME_SEARCH_JS = """<script>(function(){
var q=document.getElementById('q'),nr=document.getElementById('nores');if(!q)return;
q.addEventListener('input',function(){
var v=q.value.trim().toLowerCase(),total=0;
document.querySelectorAll('.cat-section').forEach(function(s){var n=0;
s.querySelectorAll('.card').forEach(function(c){
var ok=!v||(c.getAttribute('data-search')||'').toLowerCase().indexOf(v)>=0;
c.style.display=ok?'':'none';if(ok)n++;});
s.style.display=n?'':'none';total+=n;});
if(nr){nr.style.display=total?'none':'block';}
});
})();</script>"""


def render_home(articles: list[dict], site: dict, registry: dict | None = None) -> str:
    """首页：渐变 hero + 搜索 + 分类快捷跳转 + 按分类分组的卡片网格。"""
    registry = registry or {}

    groups: dict[str, list[dict]] = {}
    for a in articles:
        groups.setdefault(_norm_cat(a["meta"].get("category")), []).append(a)
    order = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    color_of = {c: CAT_COLORS[i % len(CAT_COLORS)] for i, (c, _) in enumerate(order)}

    tool_n = sum(
        1 for a in articles if registry.get((a["meta"].get("keyword") or "").strip())
    )

    if not order:
        return (
            '<section class="hero"><h1>' + escape(site.get("name", "我的工具站")) + "</h1>"
            '<p class="tagline">' + escape(site.get("tagline", "")) + "</p></section>"
            '<p class="empty">还没有文章。先运行 <code>python main.py generate --count 5</code> 生成内容。</p>'
        )

    chips = "\n".join(
        f'<a class="chip" href="#cat-{i}">{escape(c)}<span>{len(items)}</span></a>'
        for i, (c, items) in enumerate(order)
    )

    sections = []
    for i, (cat, items) in enumerate(order):
        cards = []
        for a in items:
            m = a["meta"]
            kw = (m.get("keyword") or "").strip()
            has_tool = bool(registry.get(kw))
            summary = (m.get("summary") or "")[:62]
            search = " ".join(
                [str(m.get("title", "")), str(m.get("summary", "")), kw, cat]
            )
            flag = '<span class="tool-flag">⚡ 可在线计算</span>' if has_tool else ""
            cards.append(
                f'<article class="card" data-search="{escape(search)}">'
                f'<a class="card-link" href="/{m["slug"]}/">'
                f'<div class="card-top">'
                f'<span class="badge" style="background:{color_of[cat]}">{escape(cat)}</span>'
                f"{flag}</div>"
                f"<h3>{escape(m['title'])}</h3>"
                f"<p>{escape(summary)}…</p>"
                f"<time>{escape(str(m.get('date', '')))}</time>"
                "</a></article>"
            )
        sections.append(
            f'<section class="cat-section" id="cat-{i}">'
            f'<div class="cat-head" style="--c:{color_of[cat]}"><h2>{escape(cat)}</h2>'
            f'<span class="cat-count">{len(items)} 篇</span></div>'
            f'<div class="grid">{"".join(cards)}</div></section>'
        )

    stats = (
        f'<div class="stats">'
        f'<span><b>{len(articles)}</b>篇内容</span>'
        f'<span><b>{tool_n}</b>个在线工具</span>'
        f'<span><b>{len(order)}</b>个分类</span>'
        f"</div>"
    )

    return (
        f'<section class="hero">'
        f'<h1>{escape(site.get("name", "我的工具站"))}</h1>'
        f'<p class="tagline">{escape(site.get("tagline", "小而实用的在线工具与实用指南，全部免费使用。"))}</p>'
        f"{stats}"
        f'<input id="q" class="search" type="search" autocomplete="off" '
        f'placeholder="搜索工具或文章，如 BMI、房贷、单位换算…" aria-label="搜索站内内容">'
        f"</section>"
        f'<nav class="chips" id="categories" aria-label="分类快捷跳转">{chips}</nav>'
        + "".join(sections)
        + '<p class="no-result" id="nores" style="display:none">没有找到匹配的内容，换个关键词试试。</p>'
        + HOME_SEARCH_JS
    )


def render_article_page(article: dict, site: dict, registry: dict | None = None) -> str:
    meta = article["meta"]
    body_html = render_article_html(article)
    site_url = site["url"].rstrip("/")
    canonical = f"{site_url}/{meta['slug']}/"

    # 工具注入：若本页 keyword 在 registry 中，则在正文顶部放置可交互工具
    tool_cfg = (registry or {}).get(meta.get("keyword"))
    widget_html = ""
    tool_script = ""
    if tool_cfg:
        widget_html = f'<div class="tool-widget" data-tool-keyword="{escape(meta["keyword"])}"></div>'
        tool_script = (
            '<script type="module">'
            "import {autoMount} from '/assets/tools.js';"
            "fetch('/assets/registry.json').then(r=>r.json()).then(reg=>autoMount(reg)).catch(()=>{});"
            "</script>"
        )

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
    # 有工具的页面补充 SoftwareApplication 结构化数据（增强富媒体机会）
    if tool_cfg:
        app_ld = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": meta["title"],
            "applicationCategory": "UtilityApplication",
            "operatingSystem": "Web",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "CNY"},
        }
        json_ld = [json_ld, app_ld] if not isinstance(json_ld, list) else json_ld + [app_ld]
    ld_block = "".join(
        '<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False) + "</script>"
        for x in (json_ld if isinstance(json_ld, list) else [json_ld])
    )

    tags = "".join(f'<span class="tag">{escape(t)}</span>' for t in (meta.get("tags") or []))
    content = f"""
<nav class="breadcrumb"><a href="/">首页</a> <span>/</span> <span>{escape(meta.get('category', '文章'))}</span></nav>
<article class="post">
  <header>
    <h1>{escape(meta['title'])}</h1>
    <div class="post-meta"><time>{meta.get('date', '')}</time>{tags}</div>
  </header>
  <div class="post-body">{widget_html}{body_html}</div>
</article>
<section class="related">
  <h2>相关阅读</h2>
  <p><a href="/">返回首页查看其他文章</a></p>
</section>"""
    return page_wrap(meta["title"], content, site, canonical=canonical,
                     description=meta.get("summary", ""), extra_head=ld_block + tool_script)


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
/* ---- 首页 hero / 搜索 / 分类导航 ---- */
.hero{text-align:center;padding:44px 24px 30px;margin:26px 0 6px;border-radius:18px;border:1px solid #e6ecff;
background:
radial-gradient(900px 280px at 18% -25%,rgba(37,99,235,.12),transparent 62%),
radial-gradient(760px 280px at 86% -10%,rgba(217,119,6,.12),transparent 62%),
linear-gradient(135deg,#eef4ff 0%,#f7f8ff 45%,#fff7ed 100%)}
.hero h1{font-size:34px;margin:0 0 8px;letter-spacing:.5px}
.hero .tagline{margin:6px 0 18px;color:var(--muted);font-size:15px}
.stats{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;margin-bottom:18px}
.stats span{background:rgba(255,255,255,.92);border:1px solid #e3e9f7;border-radius:999px;
padding:6px 16px;font-size:13px;color:var(--muted);box-shadow:0 1px 2px rgba(16,24,40,.04)}
.stats b{color:var(--accent);font-size:16px;margin-right:4px}
.search{display:block;width:100%;max-width:460px;margin:0 auto;padding:12px 18px;font-size:15px;
font-family:inherit;border:1px solid #dbe3f5;border-radius:999px;background:#fff;color:var(--ink);
outline:none;box-shadow:0 2px 10px rgba(37,99,235,.06)}
.search:focus{border-color:var(--accent);box-shadow:0 3px 14px rgba(37,99,235,.18)}
.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:20px 0 4px}
.chip{display:inline-flex;align-items:center;gap:6px;margin:0;padding:6px 8px 6px 14px;border-radius:999px;
background:#fff;border:1px solid var(--line);color:#374151;text-decoration:none;font-size:13px;
transition:transform .15s,border-color .15s,color .15s}
.chip:hover{border-color:var(--accent);color:var(--accent);transform:translateY(-1px)}
.chip span{background:#f1f5f9;border-radius:999px;padding:0 6px;font-size:11px;color:var(--muted)}
.no-result{text-align:center;color:var(--muted);padding:40px 0 60px}
/* ---- 分类区块与卡片 ---- */
.cat-section{margin:32px 0 0;scroll-margin-top:78px}
.cat-head{display:flex;align-items:center;gap:10px;margin:0 0 14px}
.cat-head h2{font-size:20px;margin:0;padding-left:12px;position:relative}
.cat-head h2::before{content:"";position:absolute;left:0;top:5px;bottom:5px;width:4px;border-radius:4px;background:var(--c,var(--accent))}
.cat-count{font-size:12px;color:var(--muted);background:#f3f4f6;border-radius:999px;padding:2px 9px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-bottom:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.07);border-color:#cfdcf5}
.card-link{display:block;padding:18px;text-decoration:none;color:inherit}
.card-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px}
.card h3{margin:6px 0;font-size:17px;color:var(--ink);line-height:1.45}
.card p{margin:0 0 10px;color:var(--muted);font-size:14px;min-height:44px}
.card time{color:var(--muted);font-size:13px}
.badge{display:inline-block;background:var(--accent);color:#fff;font-size:12px;padding:2px 9px;border-radius:999px}
.tool-flag{display:inline-block;font-size:11px;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:999px;padding:2px 8px}
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
.tool-widget{background:linear-gradient(135deg,#eff6ff,#f9fafb);border:1px solid var(--line);border-radius:14px;padding:22px 24px;margin:8px 0 26px}
.tool-head strong{display:block;font-size:18px;color:var(--ink);margin-bottom:4px}
.tool-head p{margin:0 0 14px;color:var(--muted);font-size:14px}
.tool-form{display:flex;flex-wrap:wrap;gap:14px 18px;align-items:flex-end}
.field{display:flex;flex-direction:column;gap:5px;min-width:130px;flex:1 1 130px}
.field label{font-size:13px;color:var(--muted)}
.field input,.field select{padding:9px 10px;border:1px solid var(--line);border-radius:8px;font-size:15px;background:#fff;color:var(--ink)}
.tool-btn{background:var(--accent);color:#fff;border:none;border-radius:8px;padding:10px 22px;font-size:15px;cursor:pointer;height:40px}
.tool-btn:hover{filter:brightness(1.05)}
.tool-result{display:none;margin-top:18px;padding-top:16px;border-top:1px dashed var(--line)}
.tool-primary{font-size:30px;font-weight:700;color:var(--accent);line-height:1.2}
.tool-primary .u{font-size:15px;color:var(--muted);font-weight:400;margin-left:6px}
.tool-rows{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;margin:12px 0 0;font-size:14px}
.tool-rows dt{color:var(--muted)}
.tool-rows dd{margin:0;color:var(--ink)}
.tool-table{border-collapse:collapse;width:100%;margin:6px 0;font-size:14px}
.tool-table th,.tool-table td{border:1px solid var(--line);padding:7px 10px;text-align:left}
.tool-table th{background:#f9fafb}
.tool-note{color:var(--muted);font-size:13px;margin:10px 0 0}
.tool-disclaimer{margin-top:14px;font-size:13px;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:8px 12px}
@media(max-width:640px){
.post{padding:20px}
.hero{padding:32px 16px 24px;border-radius:14px;margin-top:16px}
.hero h1{font-size:26px}
.grid{grid-template-columns:1fr}
.card p{min-height:auto}
.tool-primary{font-size:24px}
}"""


def render_privacy_page(site: dict) -> str:
    """生成隐私政策页（AdSense / 百度联盟 审核硬性要求）。"""
    name = escape(site.get("name", "我的工具站"))
    content = f"""
<article class="post">
  <header><h1>隐私政策</h1></header>
  <div class="post-body">
    <p>本页说明 <strong>{name}</strong>（以下简称"本站"）如何收集、使用与保护您的信息。访问或使用本站即表示您同意本政策。</p>

    <h2>一、我们收集的信息</h2>
    <p>本站为静态内容站点，<strong>不主动收集您的姓名、电话、邮箱等个人身份信息</strong>。服务器仅会记录标准的匿名访问日志（如访问时间、来源页、浏览器类型），用于排查故障与了解整体流量趋势，无法定位到具体个人。</p>

    <h2>二、第三方广告与 Cookie</h2>
    <p>为维持站点运营，本站可能投放 <strong>Google AdSense</strong> 等第三方广告。这些广告联盟会通过 Cookie 或类似技术，依据您的浏览行为投放个性化或一般性广告。您可随时在浏览器设置中清除或禁用 Cookie；禁用后页面仍可正常浏览，但广告相关性可能下降。关于 Google 广告的隐私控制，详见 <a href="https://policies.google.com/technologies/ads" target="_blank" rel="noopener">Google 广告政策</a>。</p>

    <h2>三、外部链接</h2>
    <p>本站可能包含指向第三方网站的链接。这些站点有独立的隐私政策，本站对其内容或数据处理方式不承担责任。</p>

    <h2>四、未成年人保护</h2>
    <p>本站内容面向一般成年读者，不含针对未成年人的定向广告。若您为未成年人，请在监护人指导下使用。</p>

    <h2>五、政策变更</h2>
    <p>本站可能不时更新本隐私政策，更新后将以本页最新版本为准。</p>

    <h2>六、联系我们</h2>
    <p>如对本政策有疑问，可通过站点首页提供的渠道与我们联系。</p>
  </div>
</article>"""
    return page_wrap(f"{name} · 隐私政策", content, site,
                     canonical=f"{site['url'].rstrip('/')}/privacy/",
                     description="了解本站如何收集与使用信息、第三方广告与 Cookie 的说明。")


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

    registry = load_registry()
    articles = read_articles()
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    # 清理站点里已不存在的文章目录，避免旧页面残留（单个失败不阻塞构建）
    # 跳过 privacy/assets：二者每次构建都会重新生成，无需先删
    current_slugs = {a["meta"]["slug"] for a in articles} | {"privacy"}
    for child in SITE_DIR.iterdir():
        if (
            child.is_dir()
            and (child / "index.html").exists()
            and child.name not in current_slugs
        ):
            try:
                shutil.rmtree(child)
            except OSError:
                pass  # 目录被占用/权限受限时跳过，不影响本次生成

    (SITE_DIR / "index.html").write_text(
        page_wrap(site.get("name", "我的工具站"), render_home(articles, site, registry), site,
                  canonical=f"{site_url}/", description=site.get("tagline", ""), active="home"),
        encoding="utf-8",
    )
    for a in articles:
        meta = a["meta"]
        page_dir = SITE_DIR / meta["slug"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(render_article_page(a, site, registry), encoding="utf-8")

    write_static_files(site, site_url)
    write_sitemap(articles, site_url)
    copy_tool_assets(SITE_DIR)

    # 隐私政策页（AdSense / 百度联盟 审核硬性要求）
    (SITE_DIR / "privacy").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "privacy" / "index.html").write_text(render_privacy_page(site), encoding="utf-8")
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
