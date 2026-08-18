"""Markdown YAML frontmatter 读写。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def parse_frontmatter(path: str | Path) -> dict[str, Any]:
    """读取 Markdown 文件的 YAML frontmatter；没有则返回空 dict。"""
    text = Path(path).read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    try:
        meta = yaml.safe_load(block) or {}
    except yaml.YAMLError:
        return {}
    return meta if isinstance(meta, dict) else {}


def dump_markdown(meta: dict[str, Any], body: str) -> str:
    """把 meta 渲染成 YAML frontmatter，并与正文拼成 Markdown 文件。"""
    header = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{header}\n---\n\n{body}\n"
