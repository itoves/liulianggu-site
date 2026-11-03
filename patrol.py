"""流量谷站健康巡检（只读）。

每周自动运行：抓取 sitemap 全量 URL，逐一检查 HTTP 状态、noindex、canonical，
并与上次基线对比。只在异常时报警——「没变化就不吵我」。

用法：
    python patrol.py            # 正常巡检（会读取/更新基线）
    python patrol.py --dry      # 只看结果，不写基线与日志

输出：JSON（stdout）+ 追加日志到 .workbuddy/patrol_log.md
基线：.workbuddy/patrol_baseline.json
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

SITE = "https://liulianggu.site"
ROOT = Path(__file__).resolve().parent
WORK = ROOT / ".workbuddy"
BASELINE = WORK / "patrol_baseline.json"
LOG = WORK / "patrol_log.md"
UA = "Mozilla/5.0 (compatible; SitePatrol/1.0; +https://liulianggu.site)"
TIMEOUT = 25


def fetch(url: str) -> tuple[int, str, dict]:
    """返回 (状态码, 正文前 20KB, 响应头)。异常时状态码为 0。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(20480).decode("utf-8", "ignore")
            return r.status, body, dict(r.headers)
    except Exception as e:  # 网络/超时/DNS
        return 0, f"{type(e).__name__}: {e}", {}


def sitemap_urls() -> tuple[list[str], str]:
    status, body, _ = fetch(f"{SITE}/sitemap.xml")
    if status != 200:
        return [], f"sitemap.xml 无法获取（HTTP {status}）"
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        return [], f"sitemap.xml 解析失败（{e}）"
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    return [e.find(ns + "loc").text.strip() for e in root.findall(ns + "url")], ""


def check_page(url: str) -> dict:
    status, body, headers = fetch(url)
    issues, warns = [], []

    if status != 200:
        issues.append(f"HTTP {status or '无响应'}")
    else:
        meta_robots = re.search(
            r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']*)', body, re.I
        )
        if meta_robots and "noindex" in meta_robots.group(1).lower():
            issues.append("页面被 meta robots 设为 noindex")
        if "noindex" in headers.get("X-Robots-Tag", "").lower():
            issues.append("响应头 X-Robots-Tag 含 noindex")
        if not re.search(r'rel=["\']canonical["\']', body, re.I):
            warns.append("缺少 canonical")
        if url.rstrip("/") == SITE and 'name="google-site-verification"' not in body:
            warns.append("首页缺少 Google 验证 meta")

    return {"url": url, "status": status, "issues": issues, "warns": warns}


def main() -> int:
    dry = "--dry" in sys.argv
    today = datetime.now().strftime("%Y-%m-%d")
    alerts: list[dict] = []
    notes: list[str] = []

    # 1. robots.txt
    status, robots, _ = fetch(f"{SITE}/robots.txt")
    if status != 200:
        alerts.append({"url": f"{SITE}/robots.txt", "issue": f"HTTP {status}",
                       "suggestion": "检查部署是否成功，robots.txt 由 build_site.py 生成"})
    else:
        if f"Sitemap: {SITE}/sitemap.xml" not in robots:
            alerts.append({"url": f"{SITE}/robots.txt", "issue": "缺少 Sitemap 声明",
                           "suggestion": "检查 write_static_files() 的 robots 模板"})
        if "Allow: /" not in robots:
            alerts.append({"url": f"{SITE}/robots.txt", "issue": "未放行全站",
                           "suggestion": "检查 User-agent 规则"})

    # 2. sitemap
    urls, err = sitemap_urls()
    if err:
        alerts.append({"url": f"{SITE}/sitemap.xml", "issue": err,
                       "suggestion": "检查 write_sitemap() 与最近一次 CI 部署"})
    elif len(urls) < 50:
        alerts.append({"url": f"{SITE}/sitemap.xml", "issue": f"URL 数骤降到 {len(urls)}（预期 ≥60）",
                       "suggestion": "检查 output/ 文章是否被误删或构建失败"})

    # 3. 逐页检查
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(check_page, urls))
    for r in results:
        for i in r["issues"]:
            alerts.append({"url": r["url"], "issue": i,
                           "suggestion": "查看对应页面的构建输出与部署日志"})

    # 4. 与基线对比
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else None
    if baseline:
        old = set(baseline.get("urls", []))
        cur = set(urls)
        gone, added = sorted(old - cur), sorted(cur - old)
        if gone:
            notes.append(f"较基线减少 {len(gone)} 页: {', '.join(gone[:5])}")
        if added:
            notes.append(f"较基线新增 {len(added)} 页: {', '.join(added[:5])}")
        if not gone and not added:
            notes.append(f"与基线一致（{len(urls)} 页）")
    else:
        notes.append("首次巡检，已建立基线")

    summary = {
        "date": today,
        "checked": len(urls),
        "alerts": alerts,
        "warnings": [
            {"url": r["url"], "issue": w}
            for r in results for w in r["warns"]
        ],
        "notes": notes,
        "ok": not alerts,
    }

    # 5. 落盘（基线只记录成功轮次）
    if not dry and not alerts and urls:
        WORK.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(
            json.dumps({"date": today, "urls": urls}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )

    if not dry:
        WORK.mkdir(parents=True, exist_ok=True)
        line = (
            f"\n## {today}\n"
            f"- 巡检 {len(urls)} 页，异常 {len(alerts)}，提醒 {len(summary['warnings'])}\n"
            + ("".join(f"- ⚠ {a['url']} — {a['issue']}\n" for a in alerts)
               or "- 无异常\n")
            + ("".join(f"- ℹ {n}\n" for n in notes))
        )
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line)

    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
