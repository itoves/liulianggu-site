"""AI 内容生成器：OpenAI 兼容接口；--mock 模式用本地模板，无需 API Key 即可联调。"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests

from .seo import make_slug

SYSTEM_PROMPT = """你是一名资深中文 SEO 内容编辑，擅长为工具类网站撰写"小而实用"的高质量页面。

写作要求：
1. 标题必须包含核心关键词，长度 15~30 字，自然不生硬。
2. 正文结构清晰：至少 3 个 H2 小节，包含要点列表、至少 1 张数据表格、可操作的步骤，禁止空洞套话。
3. 全文 600~1200 字，口语自然、信息密度高，避免营销腔。
4. 结尾提供 3~5 条 FAQ 问答（Q 短而明确，A 直接给答案）。

只输出一个 JSON 对象，不要输出任何其他文字，格式：
{"title": "…", "summary": "…", "tags": ["…"], "content": "Markdown 正文（含 H2/H3 标题与表格）", "faq": [{"q": "…", "a": "…"}]}"""

logger = logging.getLogger("seo_article_bot.generator")


@dataclass
class Article:
    keyword: str
    title: str
    slug: str
    category: str
    summary: str
    markdown: str
    tags: list[str]
    faq: list[dict[str, str]]
    json_ld: dict[str, Any]
    internal_links: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).date().isoformat()
    )


class ArticleGenerator:
    def __init__(self, config: dict):
        self.config = config
        self.site = config["site"]

    def generate(self, topic, mock: bool = False) -> Article:
        if mock:
            return self._generate_mock(topic)
        return self._generate_api(topic)

    # ---------- 真实 API ----------
    def _generate_api(self, topic) -> Article:
        ai = self.config["ai"]
# Key 优先级：环境变量 > config 里的 api_key 字段
        env_name = ai.get("api_key_env") or ""
        api_key = (os.environ.get(env_name) if env_name else "") or ai.get("api_key", "")
        if not api_key:
            raise RuntimeError(
                "No API key configured: set ai.api_key in config.yaml,"
                "or set the env var named by ai.api_key_env,"
                "or run with --mock for local testing."
            )
        user_prompt = self._build_user_prompt(topic)
        payload = {
            "model": ai["model"],
            "temperature": ai.get("temperature", 0.7),
            "max_tokens": ai.get("max_tokens", 2000),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        base_url = ai.get("base_url", "https://api.openai.com/v1").rstrip("/")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        max_retries = ai.get("max_retries", 2)

        def _post():
            last_err = None
            for attempt in range(max_retries + 1):
                try:
                    resp = requests.post(
                        f"{base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=ai.get("timeout_seconds", 120),
                    )
                    resp.raise_for_status()
                    return resp.json()
                except requests.HTTPError as e:
                    status = e.response.status_code if e.response is not None else 0
                    last_err = e
                    if status in (429,) or status >= 500:
                        logger.warning(
                            "API error %s, retry %s/%s", status, attempt + 1, max_retries
                        )
                        if attempt < max_retries:
                            time.sleep(2 * (attempt + 1))
                            continue
                    raise
                except requests.RequestException as e:
                    last_err = e
                    if attempt < max_retries:
                        logger.warning("请求异常 %s, retry %s/%s", e, attempt + 1, max_retries)
                        time.sleep(2 * (attempt + 1))
                        continue
                    raise
            raise last_err  # 正常不会到达

        # 整体重试：网络/HTTP 错误、空内容、JSON 解析失败、字段缺失都重试
        last_err: Exception | None = None
        for attempt in range(max_retries + 1):
            body = _post()
            content = (body["choices"][0]["message"].get("content") or "").strip()
            if not content:
                last_err = ValueError("API 返回空内容")
                logger.warning("空内容, retry %s/%s", attempt + 1, max_retries)
                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                break
            try:
                data = self._parse_model_json(content)
            except (ValueError, json.JSONDecodeError) as e:
                last_err = e
                logger.warning("JSON 解析失败, retry %s/%s: %s", attempt + 1, max_retries, e)
                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                break
            if not data.get("title") or not data.get("content"):
                last_err = ValueError("返回缺少 title/content 字段")
                logger.warning("字段缺失, retry %s/%s", attempt + 1, max_retries)
                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))
                    continue
                break
            title = str(data["title"]).strip()
            return Article(
                keyword=topic.keyword,
                title=title,
                slug=make_slug(title, fallback=topic.keyword),
                category=topic.category,
                summary=str(data.get("summary", "")).strip(),
                markdown=str(data["content"]).strip(),
                tags=[str(t).strip() for t in data.get("tags", [])][:8],
                faq=[{"q": str(it["q"]), "a": str(it["a"])} for it in data.get("faq", [])],
                json_ld={},
                internal_links=self._internal_links(),
            )
        raise RuntimeError(f"生成失败（已重试 {max_retries} 次）: {last_err}")

    @staticmethod
    def _parse_model_json(content: str) -> dict:
        text = content.strip()
        # 去掉模型可能加的 markdown 代码围栏（```json ... ```）
        if text.startswith("```"):
            text = re.sub(r"^```[A-Za-z0-9]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise ValueError(f"模型输出不是有效 JSON: {text[:200]}")

    def _build_user_prompt(self, topic) -> str:
        site = self.site
        links = self._internal_links()
        link_block = "\n".join(f"- {u}" for u in links) if links else "（无）"
        return (
            f"网站：{site.get('name', '我的工具站')}（域名 {site['url']}）\n"
            f"页面类型：{topic.category}\n"
            f"核心关键词：{topic.keyword}\n"
            f"站内可引用的相关页面（从中挑选 2~4 个自然嵌入正文做内链，不要编造链接）：\n{link_block}\n"
            f"请围绕关键词写一篇对用户真正有用的页面内容。"
        )

    def _internal_links(self) -> list[str]:
        links = self.config.get("seo", {}).get("internal_links", [])
        return [str(u) for u in links]

    # ---------- 本地 Mock 模式 ----------
    def _generate_mock(self, topic) -> Article:
        keyword = topic.keyword
        category = topic.category
        title = f"{keyword}：2026 最新在线实用工具（免费使用）"
        summary = f"关于 {keyword} 的实用说明、使用步骤与常见问题解答，帮助用户快速上手。"
        body = self._mock_body(topic)
        tags = [keyword, "在线工具", "免费", {"calculator": "计算器", "converter": "换算工具", "faq": "常见问题", "guide": "攻略指南"}.get(category, "实用工具")]
        faq = [
            {"q": f"{keyword} 免费吗？", "a": "完全免费，无需注册或下载，打开页面即可使用。"},
            {"q": f"{keyword} 支持手机使用吗？", "a": "支持，手机和电脑浏览器均可直接访问，页面会自动适配。"},
            {"q": "结果准确吗？", "a": "结果基于标准公式与权威数据计算，可放心用于日常参考；重要决策建议以官方渠道为准。"},
        ]
        return Article(
            keyword=keyword,
            title=title,
            slug=make_slug(title, fallback=keyword),
            category=category,
            summary=summary,
            markdown=body,
            tags=tags,
            faq=faq,
            json_ld={},
            internal_links=self._internal_links(),
        )

    def _mock_body(self, topic) -> str:
        keyword = topic.keyword
        category = topic.category
        if category == "calculator":
            return f"""## {keyword}是什么

{keyword} 是一款免费的在线小工具，无需安装，打开浏览器即可使用，适合日常快速计算场景。

## 使用步骤

1. 打开页面，输入需要计算的数值；
2. 点击「开始计算」按钮；
3. 页面立即给出结果，并附简要计算过程。

## 计算说明

结果基于标准公式计算，示例数据如下：

| 输入值 | 计算过程 | 结果 |
| --- | --- | --- |
| 示例 A | (A + B) × C | 结果 1 |
| 示例 B | (A − B) ÷ C | 结果 2 |
| 示例 C | A × B × C | 结果 3 |

> 提示：结果仅供日常参考，重要决策请以官方渠道数据为准。

## 常见问题

### {keyword} 免费吗？
完全免费，无需注册即可使用。

### 支持手机使用吗？
支持，手机和电脑浏览器均可直接访问。

## 总结

{keyword} 操作简单、结果即时，建议收藏本页，方便随时使用。"""
        if category == "converter":
            return f"""## {keyword}是什么

{keyword} 是一款免费的在线换算工具，支持常见单位与数值格式的快速转换，无需下载安装。

## 使用步骤

1. 选择转换类型；
2. 输入原始数值；
3. 点击「换算」即可得到结果。

## 换算示例

| 原始值 | 单位 | 换算后 | 单位 |
| --- | --- | --- | --- |
| 1 | 示例单位 A | 对应值 | 示例单位 B |
| 10 | 示例单位 A | 对应值 | 示例单位 B |
| 100 | 示例单位 A | 对应值 | 示例单位 B |

> 提示：换算系数采用通用标准，结果可放心用于日常工作。

## 常见问题

### {keyword} 结果精确到几位？
默认保留两位小数，误差可忽略。

### 支持批量换算吗？
支持，可一次输入多行数值逐行换算。

## 总结

{keyword} 简单高效、结果即时，欢迎收藏使用。"""
        if category == "guide":
            return f"""## 为什么需要{keyword}

{keyword} 是新手最容易忽略但价值最高的一环，做好它能显著提升效率、少走弯路。

## 完整操作清单

1. 明确目标与范围，先列出要解决的问题；
2. 准备必要资料与工具，逐项核对；
3. 按清单执行，每完成一步打勾确认；
4. 完成后复查一遍，记录问题并改进。

## 常见坑点

| 坑点 | 说明 | 建议 |
| --- | --- | --- |
| 目标不清 | 做到一半才发现方向错了 | 先写一句话目标再动手 |
| 资料不全 | 中途反复中断找资料 | 开工前一次性备齐 |
| 不记录 | 下次还要重新摸索 | 随手记录步骤与结论 |

## 常见问题

### {keyword} 需要多久完成？
取决于规模，一般 1~2 小时即可完成核心部分。

### 适合新手吗？
适合，按清单逐步执行即可，无需专业背景。

## 总结

把 {keyword} 按清单拆解执行，能大幅降低出错率，建议收藏备用。"""
        # faq 兜底
        return f"""## {keyword} 是什么

{keyword} 是很多用户在使用网站与工具时都会遇到的问题，下面用最直接的方式给出答案。

## 核心结论

一句话答案：按官方流程操作即可解决，关键点如下：

- 第一步：确认入口与条件；
- 第二步：按要求提交资料；
- 第三步：等待审核结果，一般数天内有反馈。

## 常见情形对比

| 情形 | 原因 | 处理方式 |
| --- | --- | --- |
| 审核不通过 | 资料不完整 | 补齐后重新提交 |
| 迟迟无结果 | 高峰期排队 | 耐心等待 3~5 个工作日 |
| 显示异常 | 浏览器缓存 | 清除缓存刷新重试 |

## 常见问题

### {keyword} 要收费吗？
官方渠道不收费，谨防第三方收费代办。

### 在哪里提交？
在对应平台的官方后台或页面入口提交即可。

## 总结

{keyword} 并不复杂，按官方流程操作即可，遇到问题可先排查资料与缓存。"""
