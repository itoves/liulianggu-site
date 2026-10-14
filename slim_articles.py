"""内容瘦身：对 output/*/index.md 做确定性清洗，不调用任何 API。

清洗项：
1. 修正 json_ld 里的错误域名 example.com -> 真实域名（SEO 正确性）。
2. 统一署名：frontmatter 中 "我的工具站" -> 站点真实名称。
3. 删除与 FAQPage 结构化数据完全重复的「可见 FAQ 小节」（去重瘦身，schema 仍保留供搜索富媒体）。
4. 剔除营销注水句（收藏 CTA、弄晕/被坑、干货、最后提醒等整行或短语）。

全部为确定性强替换，可用 git 还原。运行：python slim_articles.py [--dry]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"

REAL_DOMAIN = "https://liulianggu.site"
SITE_NAME = "流量谷"
OLD_NAME = "我的工具站"

# 可见 FAQ 小节的 H2 标题（命中即视为待删除区块）
FAQ_HEADING = re.compile(r"^##\s*(?!.*\bQ[:：]).*(常见问题|FAQ|常见疑问).*$", re.M | re.I)
# 任意 H2 标题（用于定位 FAQ 区块结束）
H2 = re.compile(r"^##\s+\S", re.M)
# frontmatter 边界
FM = re.compile(r"^---\n(.*?)\n---\n", re.S)

# 内联注水短语（直接删除，不留残句）
FILLER_PHRASES = [
    r"建议直接收藏", r"欢迎收藏", r"收藏备用", r"收藏本页", r"收藏使用",
    r"建议收藏", r"可以收藏", r"直接收藏", r"值得收藏", r"建议收藏本页",
    r"弄晕", r"不被坑", r"被坑到", r"坑到", r"踩坑", r"避坑指南",
    r"干货", r"最后提醒", r"最后总结", r"总而言之",
    r"既不会被复杂计算", r"也不会被.*?坑",
    r"下面先放一张.*?收藏", r"如果你经常需要.*?收藏",
]
FILLER_RE = re.compile("|".join(FILLER_PHRASES))


def slim_frontmatter(fm: str) -> tuple[str, int]:
    n = 0
    if "example.com" in fm:
        fm = fm.replace("https://example.com", REAL_DOMAIN)
        n += 1
    if OLD_NAME in fm:
        fm = fm.replace(OLD_NAME, SITE_NAME)
        n += 1
    return fm, n


def remove_duplicate_faq(body: str, has_schema_faq: bool) -> tuple[str, bool]:
    """若文件已含 FAQPage 结构化数据，则删除正文里重复的可见 FAQ 小节。"""
    if not has_schema_faq:
        return body, False
    m = FAQ_HEADING.search(body)
    if not m:
        return body, False
    start = m.start()
    # 区块结束：下一个 H2 标题（不含）或文件末尾
    rest = body[start:]
    nxt = H2.search(rest[1:])  # 跳过自身
    if nxt:
        end = start + 1 + nxt.end()
        new_body = body[:start].rstrip() + "\n\n" + body[end:].lstrip("\n")
    else:
        new_body = body[:start].rstrip() + "\n"
    return new_body, True


def strip_filler(body: str) -> tuple[str, int]:
    """含注水短语的行整行删除（不破坏句子、不留空标题）。"""
    lines = body.split("\n")
    out = []
    removed = 0
    for line in lines:
        if FILLER_RE.search(line):
            removed += 1
            continue
        out.append(line)
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)  # 合并多余空行
    return text, removed


# 正文额外清洗：修品牌名 + 去掉指向 example.com 的死链（保留锚文本）
BRAND_FIX = ("我的工具站", SITE_NAME)
DEAD_LINK_RE = re.compile(r"\[([^\]]+)\]\(https?://example\.com[^)]*\)")
BARE_EXAMPLE_RE = re.compile(r"https?://example\.com\S*")


def clean_body(body: str) -> str:
    if BRAND_FIX[0] in body:
        body = body.replace(BRAND_FIX[0], BRAND_FIX[1])
    body = DEAD_LINK_RE.sub(r"\1", body)  # [文字](example.com/...) -> 文字
    body = BARE_EXAMPLE_RE.sub(REAL_DOMAIN, body)  # 裸 example.com -> 真实域名
    return body


def process_file(md_path: Path, dry: bool) -> dict:
    raw = md_path.read_text(encoding="utf-8")
    m = FM.match(raw)
    if not m:
        return {"file": md_path.name, "skip": "no frontmatter"}
    fm = m.group(1)
    body = raw[m.end():]

    fm_new, fm_fixed = slim_frontmatter(fm)
    has_schema_faq = "FAQPage" in fm_new
    body, faq_removed = remove_duplicate_faq(body, has_schema_faq)
    body = clean_body(body)
    body, filler_removed = strip_filler(body)

    before = len(raw)
    new_raw = f"---\n{fm_new}\n---\n{body}" if fm_new == fm else f"---\n{fm_new}\n---\n{body}"
    # 统一组装
    new_raw = f"---\n{fm_new}\n---\n{body}"
    after = len(new_raw)

    if not dry:
        md_path.write_text(new_raw, encoding="utf-8")

    return {
        "file": md_path.name,
        "domain_fix": fm_fixed > 0,
        "faq_removed": faq_removed,
        "filler_lines": filler_removed,
        "chars_before": before,
        "chars_after": after,
        "chars_cut": before - after,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只预览不写回")
    args = ap.parse_args()

    files = sorted(OUTPUT_DIR.glob("*/index.md"))
    total = 0
    faq_n = 0
    domain_n = 0
    filler_n = 0
    chars_cut = 0
    for f in files:
        r = process_file(f, args.dry)
        if "skip" in r:
            print(f"[skip] {r['file']}: {r['skip']}")
            continue
        total += 1
        if r["domain_fix"]:
            domain_n += 1
        if r["faq_removed"]:
            faq_n += 1
        filler_n += r["filler_lines"]
        chars_cut += r["chars_cut"]
        if args.dry:
            print(f"[dry] {r['file'][:34]:34} cut={r['chars_cut']:5} faq={int(r['faq_removed'])} filler={r['filler_lines']} domain={int(r['domain_fix'])}")
    print("\n=== 内容瘦身汇总 ===")
    print(f"处理文章: {total}")
    print(f"修正域名 example.com -> {REAL_DOMAIN}: {domain_n} 篇")
    print(f"删除重复可见 FAQ 小节: {faq_n} 篇")
    print(f"剔除注水句(整行): {filler_n} 行")
    print(f"累计减少字符: {chars_cut} (~{chars_cut//2} 中文字)")
    if args.dry:
        print("(dry-run 完成，未写回文件)")


if __name__ == "__main__":
    raise SystemExit(main())
