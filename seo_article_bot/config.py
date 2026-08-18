"""配置加载：读取项目根目录 config.yaml，校验必填项。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """加载 YAML 配置。path 缺省时读取项目根目录 config.yaml。"""
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        example = PROJECT_ROOT / "config.example.yaml"
        raise FileNotFoundError(
            f"未找到配置文件 {cfg_path}。\n"
            f"请先执行: Copy-Item {example.name} config.yaml"
            f"（Linux/Mac 用 cp config.example.yaml config.yaml），然后按注释填写。"
        )
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    _validate(raw)
    return raw


def _validate(cfg: dict[str, Any]) -> None:
    if "site" not in cfg or not cfg["site"].get("url"):
        raise ValueError("配置缺少 site.url（网站域名，如 https://example.com）")
    if "ai" not in cfg:
        raise ValueError("配置缺少 ai 段（AI 生成参数）")
    publish_type = cfg.get("publish", {}).get("type", "local")
    if publish_type not in ("local", "wordpress"):
        raise ValueError('publish.type 仅支持 "local" 或 "wordpress"')
    if publish_type == "wordpress":
        wp = cfg["publish"].get("wordpress", {})
        if not wp.get("base_url"):
            raise ValueError("wordpress 发布模式缺少 publish.wordpress.base_url")
        if not wp.get("username"):
            raise ValueError("wordpress 发布模式缺少 publish.wordpress.username")
