# 流量谷 · 项目交接文档（AGENT HANDOFF）

> **给接手的人/Agent：先读这一份，再动手。** 这份文档取代此前的所有版本（旧版归档在 `.workbuddy/archive/HANDOFF-2026-10-14.md`）。
> 最后更新：**2026-11-05** ｜ 代码基线提交：`bcab4cd` ｜ 站点：https://liulianggu.site

---

## 0. 30 秒速览

| 项 | 内容 |
| --- | --- |
| 这是什么 | 中文「在线工具 + 说明文」站，59 篇文章里 58 个页面顶部嵌了**真能算的 JS 工具**，另有导航页/隐私页，共 62 页 |
| 技术形态 | 纯静态站。Markdown → Python 构建器 → HTML/CSS/JS → GitHub Pages（无服务器、无数据库、无框架） |
| 代码仓库 | `github.com/itoves/liulianggu-site`（public），分支 `main`，push 即自动部署 |
| 业务目标 | 靠搜索流量变现（AdSense / 联盟 / CPA 线索），当前**尚未有任何收入，也尚未被收录** |
| 最大卡点 | Google 侧 sitemap 一直「无法抓取」；Bing/百度未验证；AdSense 未申请 |
| 代码健康度 | 构建链路稳定，工具单测 27/27 绿，页面全部 200、无 noindex、canonical 齐全 |

**接手前必须知道的 3 件事：**

1. **`config.yaml` 不入库**（含 API Key，被 `.gitignore` 排除）。所有**影响线上渲染**的站点信息都必须同时写在已入库的 `site.yaml` 里，否则 CI 构建会退回默认值——这曾经导致全站显示「我的工具站」（见坑 H1）。
2. **工具挂载靠 `data-tool-keyword` 这个属性三段对齐**：文章 frontmatter 的 `keyword` == `registry.json` 的键 == `build_site.py` 注入的属性值。任何一环改名，页面上工具就是**空白框**（见坑 H2）。
3. **推送需要 fine-grained PAT 的 `Contents: Read and write`**。只给 Read 会 403，而 GitHub REST API 返回的 `permissions.push=true` 反映的是账号权限、**不是** token 权限（见坑 H7）。

---

## 1. 项目演变（理解现状的必要背景）

| 时间 | 阶段 | 关键动作 | 遗留影响 |
| --- | --- | --- | --- |
| 2026-10-12 | **AI 内容站** | 用 DeepSeek 批量生成 59 篇「教你怎么算」的文章；搭静态构建 + GitHub Pages | 这些文章构成今天 59 个页面的正文底稿 |
| 2026-10-13 | 上线 | 域名 `liulianggu.site`、DNSPod 解析、HTTPS、CI 自动部署 | DNSPod 免费版**只有 2 条记录名额**，已被 A 记录占满 → 验证只能用 HTML 标记法 |
| 2026-10-14 上午 | **转工具站（决定性转折）** | 原文章写「输入身高点击计算」却**没有输入框**，搜索意图严重错配。改为混合模式：真工具 + 精简说明 + FAQ | 新增 `tools/` 引擎、`registry.json`、27 个单测；`build_site.py` 注入 widget |
| 2026-10-14 晚 | 内容瘦身 | `slim_articles.py` 批量清洗：删重复 FAQ 段、去营销注水、修死链、统一品牌名；收紧生成 prompt 防回归 | 正文从「AI 水文」变成「工具陪衬」；FAQ 改由 `FAQPage` schema 承载 |
| 2026-10-14 深夜 | 真人点测 | 用 `agent-browser` 实测，发现工具**全站未挂载**（选择器不匹配），修复并复测通过 | 这是唯一一次「真人在浏览器里点」的验证，单测发现不了这类问题 |
| 2026-10-16 | 首页改版 | 59 篇从一个大网格 → 13 分类分区 + 渐变 hero + 站内搜索 + 每类配色 | 首页从「列表页」变成「门户页」 |
| 2026-10-19 | 收录排障 | GSC 选错资源类型（网域→只能用 DNS）、sitemap「无法抓取」、新增 `/all/` 兜底索引页 | 收录至今仍未成功，是当前第一阻塞 |
| 2026-11-03 | 巡检 + 品牌名修复 | 上线 `patrol.py` + 每周自动化；发现并修复全站品牌名回退 bug | 站点侧工作基本收尾，进入「等收录」阶段 |

---

## 2. 当前状态快照（2026-11-05）

### 2.1 内容与工具

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 文章数 | **59** | `output/<slug>/index.md` |
| 工具数 | **58** | `tools/registry.json`；calculator 50 + converter 8；24 个带免责声明 |
| 分类（frontmatter 原始值） | 14 个 | 健康 7、理财 7、装修 6、母婴 5、出行 5、教育 4、政务 4、居家 4、饮食 4、职场 4、数码 4、工具 3、`converter` 1、`guide` 1 |
| 分类（页面展示） | **13 个** | `CAT_FIX` 在渲染时把 `converter→工具`、`guide→站长`、`faq→工具` 归一化。**frontmatter 未改**，别以为数据一致 |
| 页面总数 | **62** | 首页 + 59 文章 + `/all/` + `/privacy/` |
| sitemap 条目 | **62** | 首页(daily) + `/all/`(daily) + `/privacy/`(monthly) + 59 文章 |
| 工具单测 | **27 个，全绿** | `node --test tools/tests/tools.test.mjs` |

### 2.2 线上可用性（实测）

```
https://liulianggu.site/                   200
https://liulianggu.site/all/               200（58 个 ⚡工具 标记）
https://liulianggu.site/privacy/           200
https://liulianggu.site/sitemap.xml        200  application/xml  62 条
https://liulianggu.site/robots.txt         200  Allow: / + Sitemap 声明
https://liulianggu.site/style.css          200（有 CDN 缓存，改动后用 ?v=xxx 穿透验证）
```

首页 `<title>` = `流量谷 · 免费在线计算工具与实用指南`，`og:site_name` = `流量谷`，全站 62 页零「我的工具站」残留。

### 2.3 收录与变现状态 ⚠️ 核心阻塞区

| 平台 | 状态 | 卡在哪 |
| --- | --- | --- |
| Google Search Console | ✅ 资源已验证（网址前缀类型） | sitemap 提交后显示**「无法抓取」**，`上次读取时间` 一直为空 —— Google 至今**一次都没成功读过** |
| Bing Webmaster | ❌ 未验证 | 从 GSC 导入报 "we didn't find any sites"；需手动 HTML Meta 验证 |
| 百度搜索资源平台 | ❌ 未验证 | 需 HTML 标签验证；且 GitHub Pages 对百度抓取本就慢 |
| Google AdSense | ❌ 未申请 | 建议等有实际收录后再申请（中文站审核通过率低） |

**对 sitemap「无法抓取」的已排查结论（服务端全部正常，别再重复查）：**
`curl` 200 / `application/xml` / 11159→12100 字节 / 0 跳转 / Googlebot UA 200 / robots 放行 / XML 可解析且 59(现 62) 条 URL 全部匹配前缀 / DNS 指向 GitHub Pages 官方 IP / 无 BOM。

**已做的兜底**：新增 `/all/` 索引页并在**每页页脚**链过去，这样即使 sitemap 永远抓不到，爬虫抓到任意一页也能走遍全站。这是当前最该依赖的发现路径。

### 2.4 已知技术债

| # | 问题 | 影响 | 建议 |
| --- | --- | --- | --- |
| D1 | `registry.json` 58 条但只有 **49 个唯一 `id`** | 无（挂载按 keyword，不按 id）；若将来按 id 索引会冲突 | 新增工具时保证 id 唯一 |
| D2 | frontmatter 分类与展示分类不一致（14 vs 13） | 无 | 如需彻底统一，改 2 篇文章的 `category` |
| D3 | 文章页无「相关阅读」真实内链（只有「返回首页」） | 内链权重传递弱 | 可按同分类生成 3 条内链，改动点在 `render_article_page` |
| D4 | `ads.txt` 尚未生成 | AdSense 通过后必须有 | 拿到 `ca-pub` 后加进 `write_static_files()` |
| D5 | 本地 git 的 `origin/main` 引用过期（显示 ahead 3） | 无，只是本地引用没更新 | `git fetch` 一次即同步；**不要**误以为没推上去（远端确认为 `bcab4cd`） |

---

## 3. 系统架构

```
   topics.csv ──┐                                    ┌─→ GitHub Pages（自动）
                ├→ main.py generate → output/<slug>/index.md ─┐
 config.yaml ───┘   （DeepSeek API，可选 --mock）             │
                                                              ▼
 tools/registry.json ──────────────────────────────→ build_site.py
 tools/tools.js      ──────────────────────────────→      │
 site.yaml（站点信息，入库）                          │      ▼
 verification.json（验证码/AdSense）                  │   site/  （静态产物，gitignore）
                                                      │      │
                                                      └──────┴→ git push main → GitHub Actions → Pages
```

**关键设计原则（别破坏）：**

1. **公式不靠 AI、不做 `eval`**。所有计算逻辑手写在 `tools/tools.js` 的 `COMPUTE` 表里，配套单测；AI 只写"陪衬文字"。
2. **正文服务端渲染**，工具是渐进增强。JS 挂不出来时页面仍有完整可读内容（对 SEO 友好）。
3. **工具按 keyword 挂载**，不写死在文章里；文章只留一个空容器。
4. **站点信息单一来源**：`site.yaml`（入库）+ `config.yaml`（本地，含密钥，覆盖前者）。
5. **不加数据库、不加框架**。这是刻意的：静态站零成本、零运维、GitHub Pages 免费。

---

## 4. 目录与文件职责

```
01-SEO内容站/
├── build_site.py           ★ 核心：Markdown → 静态站。改样式/模板/结构都在这里
├── patrol.py               ★ 站点健康巡检（只读，异常才报警）
├── slim_articles.py          内容瘦身脚本（确定性、可重跑、可 git 回滚）
├── main.py                   极薄入口，转发到 seo_article_bot/main.py
├── site.yaml               ★ 入库的站点信息（name/url/tagline）—— CI 构建依赖它
├── config.yaml            ★ 本地配置，含 DeepSeek API Key，**已被 gitignore**
├── config.example.yaml       配置模板（入库，给人看结构）
├── verification.json      ★ 搜索引擎验证码 + AdSense client ID（入库，空值=不注入）
├── monetization.json      ★ 广告位 / CPA 线索位配置（入库，空值=不渲染，见 10.4）
├── topics.csv                选题池（keyword,category,target_url）
├── topics.example.csv        选题池模板
├── topics_used.json          已用选题记录（生成器维护，防重复）
├── scheduler_state.json      定时发布计数（当前未启用 schedule）
├── requirements.txt          pyyaml / requests / schedule / python-slugify / markdown
│
├── seo_article_bot/          内容生成包
│   ├── main.py               CLI 子命令：init/generate/publish/schedule/sitemap
│   ├── generator.py        ★ OpenAI 兼容调用 + SYSTEM_PROMPT 硬规则 + 重试
│   ├── publisher.py          local 模式写 output/；wordpress 模式（未使用）
│   ├── topics.py             选题池读写与去重
│   ├── seo.py                slug 生成 / JSON-LD / sitemap
│   ├── scheduler.py          定时发布
│   ├── config.py             配置加载
│   └── frontmatter.py        frontmatter 解析
│
├── tools/                    工具引擎（浏览器/Node 共用）
│   ├── registry.json       ★ 58 个工具的定义（keyword → 配置）
│   ├── tools.js            ★ 计算引擎 + 表单渲染 + DOM 挂载（543 行）
│   ├── package.json          {"type":"module"}
│   └── tests/tools.test.mjs  27 个单测
│
├── output/<slug>/index.md    59 篇源文章（Markdown + YAML frontmatter）——**内容源头**
├── site/                     构建产物（**gitignore，不要手改**）
└── .github/workflows/deploy.yml  push main → 构建 → 部署 Pages
```

**文档职责**：`HANDOFF.md`（本文，唯一权威交接）｜`README.md`（最初的商业模式设想，已部分过时）｜`工具站改造方案.md`（改造设计决策，历史参考）｜`提交操作清单.md`（收录/AdSense 操作步骤 + 直达链接）｜`变现操作清单.md`（早期三步变现，部分过时）｜`运行说明.md`（命令手册）。

> ⚠️ 除 `HANDOFF.md` 外，其余 md 都**保留着历史时间点的状态**，别把里面的「未做」当成现在的事实。以本文第 2 节为准。

---

## 5. 构建系统 `build_site.py` 详解

### 5.1 配置加载 `read_config()`

三层合并，**后者覆盖前者**：

```
DEFAULT_SITE（硬编码真值：流量谷 / https://liulianggu.site / tagline）
      ← site.yaml（入库，CI 唯一可用来源）
      ← config.yaml（本地，含 api_key，优先级最高）
```

返回 `{"site": {...}, "ai": {...}, ...}`。`site` 段会被 `--domain` 覆盖 `url`。

**改站点名/域名/tagline 时，`site.yaml` 和 `config.yaml` 必须同步改**，否则本地预览和线上会不一致。

### 5.2 页面骨架 `page_wrap(title, content, site, canonical, description, extra_head, active)`

所有页面共用的 HTML 外壳，输出：`<title>`、description、canonical、`og:title/type/url/site_name`、favicon、`/style.css`、**`load_verification_head()` 注入点**、`extra_head`（放 JSON-LD 与工具脚本）、header（logo + 首页/分类）、`<main>`、footer（版权 + 全部内容/sitemap/robots/隐私政策）。

**改动注意**：这是全站模板，改一次影响 62 页；改完必须全站扫描验证（见第 13 节命令）。

### 5.3 首页 `render_home(articles, site, registry)`

结构（自上而下）：

```
<section class="hero">
    <h1>流量谷</h1>
    <p class="tagline">
    <div class="stats">  59 篇内容 / 58 个在线工具 / 13 个分类
    <input id="q" class="search">     ← 站内搜索
</section>
<nav class="chips" id="categories">    ← 13 个分类锚点 #cat-0..#cat-12
<section class="cat-section" id="cat-i">
    <div class="cat-head" style="--c:#2563eb"><h2>健康</h2><span class="cat-count">7 篇</span></div>
    <div class="grid">
        <article class="card" data-search="标题 摘要 关键词 分类">
            <a class="card-link">
                <div class="card-top"><span class="badge" style="background:#2563eb">健康</span>
                                    <span class="tool-flag">⚡ 可在线计算</span></div>
                <h3>标题</h3><p>摘要…</p><time>2026-10-12</time>
</section>
<p class="no-result" id="nores">     ← 搜索无结果空态
<script> ...HOME_SEARCH_JS... </script>
```

- 分类排序：按文章数降序，同数量按名称；配色取 `CAT_COLORS[i % 14]`（14 色调色板）。
- 搜索是**纯前端过滤**：`HOME_SEARCH_JS` 读 `#q`，逐个 `.cat-section` / `.card` 比对 `data-search`，无结果时显示 `#nores`。**不支持拼音/模糊匹配**，只做 `indexOf`。
- `registry` 用来判断「这一页有没有工具」→ 渲染 `⚡ 可在线计算` 角标与统计数。

### 5.4 文章页 `render_article_page(article, site, registry, articles)`

关键逻辑：

```python
tool_cfg = registry.get(meta["keyword"])     # ① 按 keyword 查工具
if tool_cfg:
    widget_html = f'<div class="tool-widget" data-tool-keyword="{keyword}"></div>'
    tool_script = <script type="module"> import {autoMount} from '/assets/tools.js';
                  fetch('/assets/registry.json').then(...).then(autoMount)</script>
```

- **工具容器插在正文最前面**（`<div class="post-body">{widget_html}{body_html}</div>`），即「先给工具，再给解释」。
- **正文结构（2026-11-09 起）**：`{widget}{cpa}{ad_in_article}{body}{ad_bottom}` —— CPA 贴近工具、广告分两处，全部留空则不渲染（见 10.4）。
- **相关阅读（2026-11-09 新增）**：`pick_related()` 取同分类前 4 篇，不足用最新文章补齐，生成 4 条同簇内链（59 页共 236 条）；末尾链到 `/all/`。**此前每篇只链回首页，爬虫深度=2、无法形成主题簇**，改动后全站站内出链约 965 条。新增文章无需额外操作，自动进簇。
- JSON-LD：frontmatter 有 `json_ld` 就用它（`Article`），否则按字段兜底生成；**有工具的页面再追加一条 `SoftwareApplication`**（`applicationCategory: UtilityApplication`、免费）。
- FAQ 的 `FAQPage` schema 来自 frontmatter 的 `json_ld`（部分文章是 list），正文**不再重复写 FAQ 小节**。

### 5.5 两个附属页

- `render_privacy_page()` → `/privacy/`：AdSense / 百度联盟审核硬性要求。含「不收集个人信息 / 第三方广告与 Cookie / 外链免责 / 未成年人 / 政策变更 / 联系方式」六节。**别删**。
- `render_all_page()` → `/all/`：按分类列出全部 59 篇链接（带 ⚡工具 标记）。这是 sitemap 抓取失败时的兜底发现路径，**每页页脚都链过来**。别删。

### 5.6 静态资源

| 产出 | 生成函数 | 说明 |
| --- | --- | --- |
| `style.css` | `STYLE_CSS` 常量 | 全站唯一样式表，无构建、无预处理器 |
| `favicon.svg` | 内联 SVG | 蓝底 + 字母 S（历史遗留，可改成「流」） |
| `robots.txt` | `write_static_files()` | `User-agent: * / Allow: / / Sitemap: ...` |
| `sitemap.xml` | `write_sitemap()` | 首页+`/all/`+`/privacy/`+59 篇，共 62 条 |
| `assets/tools.js`、`assets/registry.json` | `copy_tool_assets()` | 从 `tools/` 复制，浏览器从 `/assets/` 加载 |

`STYLE_CSS` 里的主要类：`.hero/.stats/.search/.chips/.chip/.cat-section/.cat-head/.cat-count/.card/.card-top/.badge/.tool-flag/.tool-widget/.tool-form/.field/.tool-btn/.tool-primary/.tool-rows/.tool-table/.tool-disclaimer/.all-list/.all-flag/.post/.related`。移动端在 `@media(max-width:640px)` 里收成单列。

### 5.7 `build()` 执行顺序（别随意调整）

1. 读配置 → 合并 `--domain`
2. `load_registry()` + `read_articles()`
3. **清理**：删掉 `site/` 下已不存在的文章目录（跳过 `privacy`/`all`，`rmtree` 包 `try/except` 防 Windows 卡死）
4. 首页 → 逐篇文章
5. `write_static_files()`（css/favicon/robots）→ `write_sitemap()` → `copy_tool_assets()`
6. `/privacy/` → `/all/`

### 5.8 改样式/模板的正确姿势

1. 改 `build_site.py`（**不要改 `site/` 里的产物**，会被下次构建覆盖）
2. 重新构建 → 本地起服务看效果
3. 跑全站校验（第 13 节）
4. commit → push → 等 CI → 用 `?v=随机数` 验证线上（`style.css` 有 CDN 缓存）

---

## 6. 内容生产链路

### 6.1 选题池

- `topics.csv` 列：`keyword,category,target_url` —— **58 个选题已全部生成，剩余 0**。
- `topics_used.json` 记录已用选题，生成器据此跳过。
- 现在**没有新内容需求**时不要瞎扩；要扩就先扩 `topics.csv` 再 `generate`。

### 6.2 `generator.py`（AI 生成）

- 接口：OpenAI 兼容 Chat Completions，`config.yaml` 的 `ai` 段（base_url `https://api.deepseek.com/v1`，model `deepseek-chat`）。
- **SYSTEM_PROMPT 硬规则**（2026-10-14 收紧过，防注水回归）：
  1. 标题含核心关键词，15–30 字
  2. 正文 **2–3 个 H2**，含要点列表 + **至少 1 张表格**，禁空洞套话
  3. 全文 **500–900 字**，口语自然、信息密度高，无营销腔
  4. **正文不写 FAQ 小节**（FAQ 由 schema 承载）
  5. **正文不写「输入X点击计算」**（顶部已有真工具）
  6. 禁词：收藏 / 干货 / 避坑 / 弄晕 / 不被坑 / 建议收藏本页
- 只输出 JSON：`{title, summary, tags, content, faq[]}`。
- 重试：JSON 解析失败 / 字段缺失 / 空内容 / 网络错误都重试（最多 3 次）；单篇失败跳过不中断整批。

### 6.3 文章 frontmatter 字段（`output/<slug>/index.md`）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `title` | ✅ | 页面 H1 与 `<title>` |
| `slug` | ✅ | URL 路径（`/<slug>/`）、目录名 |
| `keyword` | ✅ | **与 `registry.json` 的键严格一致**，决定是否注入工具 |
| `category` | ✅ | 展示分类（渲染时经 `CAT_FIX` 归一化） |
| `summary` | ✅ | meta description + 首页卡片摘要（截 62 字） |
| `tags` | | 页面标签 |
| `date` | ✅ | 展示与 sitemap `lastmod` |
| `json_ld` | ✅ | `Article` 或 `[Article, FAQPage]`，构建时原样输出 |

### 6.4 `slim_articles.py`（内容瘦身，幂等）

**已执行完毕，一般不需要再跑。** 若重跑，先确认规则仍适用：

- 统一品牌名（`我的工具站` → `流量谷`）、把 `example.com` 换成真实域名
- 删除与 `FAQPage` schema **完全重复**的可见 FAQ 小节（无 schema 的保留）
- **整行删除**含营销注水词的句子（不是行内替换——初版做过行内替换，把标题掏空成 `## `）
- 死链处理：`[文字](https://example.com/...)` → 保留文字去掉链接

用法：`python slim_articles.py --dry`（只看）→ 去掉 `--dry` 执行。改动在 `output/`，可 `git checkout -- output` 回滚。

### 6.5 新增一篇内容的完整流程

```
1. echo "关键词,分类,目标URL" >> topics.csv
2. python main.py generate --count 1 --category 分类
3. 检查 output/<slug>/index.md：keyword 是否与 registry 键一致、字数、有无注水
4. 若该关键词需要工具：在 tools/registry.json 加配置 + tools.js 加 COMPUTE 函数 + 单测
5. node --test tools/tests/tools.test.mjs          # 必须全绿
6. python build_site.py --domain https://liulianggu.site
7. 本地校验（第 13 节）→ git add output/ tools/ → commit → push
```

---

## 7. 工具引擎

### 7.1 `registry.json` schema

顶层是「关键词 → 工具配置」的映射（**键必须是文章 frontmatter 的 `keyword` 原值**）。

**calculator 示例（房贷）：**

```json
"房贷利率计算器": {
  "id": "mortgage",
  "type": "calculator",
  "title": "房贷利率计算器",
  "intro": "输入贷款金额、年利率与年限，计算每月还款额与总利息。",
  "disclaimer": true,
  "inputs": [
    {"key":"amount","label":"贷款总额","unit":"万元","default":100,"min":1,"max":5000,"step":1},
    {"key":"rate","label":"年利率","unit":"%","default":3.95,"min":0.1,"max":15,"step":0.01},
    {"key":"years","label":"贷款年限","unit":"年","default":30,"min":1,"max":40,"step":1},
    {"key":"method","label":"还款方式","type":"select","options":["等额本息","等额本金"],"default":"等额本息"}
  ],
  "note": "等额本息：每月还款额固定；等额本金：每月本金固定、利息递减。"
}
```

**converter 额外字段**：`units: [{name, factor}]`、`defaultFrom`、`defaultTo`（`type: "converter"` 时表单自动变成「数值 + 从 + 到」三个控件）。

支持 `input.type`：默认 number ｜ `select`（要 `options`）｜ `date`。

### 7.2 `tools.js` 结构

| 位置 | 作用 |
| --- | --- |
| 顶部工具函数 | `fmt/pct/parseDate/addDays/fmtDate/daysBetween/taxTable` |
| `const COMPUTE = { id: (inputs, config) => {...} }` | **全部计算逻辑**，键是 registry 的 `id` |
| `convert(config, value, from, to)` | 单位换算（按 `factor` 归一化再折算） |
| `computeTool(config, inputs)` | 统一出口：converter 走 `convert`，其余查 `COMPUTE[config.id]`；异常返回友好提示，不抛到页面 |
| `buildForm(config)` | 按配置动态生成表单；`select/date/number` 三类控件；**输入即自动重算**，首次渲染也会算一次 |
| `renderResult(res)` | `kind: "table"` 渲染表格，否则渲染大数字 `primary` + `rows` 键值对 + `note` |
| `mountTool(container, config)` | 把标题/intro/表单/结果/免责声明拼进容器 |
| `autoMount(registry)` | **扫描 `[data-tool-keyword]`**，逐个 `mountTool` |

返回值约定：`{kind:"value"|"table", primary, unit, rows, headers, note}`。

### 7.3 挂载链路（最容易踩的地方）

```
文章 frontmatter.keyword
        ↓ 构建时比对
registry.json 的键  ──匹配──> build_site.py 注入 <div data-tool-keyword="同一字符串">
                                        ↓ 浏览器
                           autoMount() 用这个字符串去 registry 里取配置
```

**三者必须逐字一致**（含空格、全半角）。不一致的表现是：`<div class="tool-widget">` 空着，页面只剩文字，控制台**没有报错**（因为 `if (config) mountTool(...)` 静默跳过）。

### 7.4 测试

```bash
cd 项目根目录
node --test tools/tests/tools.test.mjs          # 27 个用例，全绿
```

覆盖：BMI、房贷（等额本息/本金）、复利、个税、体脂、单位换算等已知答案 + 「58 个工具均可调用」。

> ⚠️ **必须传文件路径，不能传目录**。Node 22 在 Windows 下执行 `node --test tools/tests/` 会报
> `Cannot find module '...\tools\tests'`（把目录当模块解析），看起来像"测试全挂了"，实际是命令写法问题。

**测试的盲区（务必知道）**：单测直接调用 `mountTool`，**绕过了 DOM 选择器**，所以 H2 那种"选择器写错"的 bug 单测抓不到。涉及前端挂载的改动，必须真开浏览器看一次。

### 7.5 新增一个工具

1. `registry.json` 加一条（键 = 文章 keyword，`id` 唯一）
2. `tools.js` 的 `COMPUTE` 加函数（或配 converter 的 `units`）
3. `tools/tests/tools.test.mjs` 加 2–3 组权威已知答案
4. `node --test tools/tests/tools.test.mjs` 全绿
5. 重建 + 浏览器实测一次

---

## 8. SEO 与结构化数据

| 项 | 现状 | 位置 |
| --- | --- | --- |
| canonical | 每页都有，绝对 URL，带尾斜杠 | `page_wrap` / 各 render 函数 |
| meta description | 首页用 tagline；文章用 summary | 同上 |
| Open Graph | `og:title/type/url/site_name`（无 og:image） | `page_wrap` |
| Article schema | frontmatter `json_ld` | 文章页 |
| FAQPage schema | frontmatter `json_ld`（list 时两条） | 文章页 |
| SoftwareApplication | 有工具的页面自动追加 | `render_article_page` |
| sitemap | 62 条，首页/`/all/` daily，隐私页 monthly | `write_sitemap` |
| robots | 放行全站 + 声明 sitemap | `write_static_files` |
| 内链 | 首页分类 + `/all/` + 页脚；文章间**无**相关阅读 | 待优化（D3） |

**没有的东西（别找）**：`og:image`、`twitter:card`、hreflang、AMP、RSS。

---

## 9. 部署与发布

### 9.1 CI 流程（`.github/workflows/deploy.yml`）

```
push main → job build（ubuntu / python 3.12）
            ├ pip install -r requirements.txt
            ├ python build_site.py --domain "${SITE_URL:-https://liulianggu.site}"
            ├ cp google*.html / baidu_verify_*.html / BingSiteAuth.xml / yandex_*.html → site/
            └ upload-pages-artifact
         → job deploy（actions/deploy-pages@v4，environment: github-pages）
```

`SITE_URL` 是仓库 Variables（已有值 `https://liulianggu.site`），不配也有兜底。

### 9.2 推送凭据（血泪）

用户给的是 **fine-grained PAT**。要求：

- Repository access：包含 `itoves/liulianggu-site`
- **Contents: Read and write**（只给 Read → `403 Permission denied`）
- 建议同时给 Workflows: Read and write（以后改 CI 不用再换）

推送用一次性 URL，**不要**写进 `.git/config`：

```bash
git push "https://x-access-token:<TOKEN>@github.com/itoves/liulianggu-site.git" main
```

**诊断技巧**：`git ls-remote` 能成功但 `git push` 403 → 一定是写权限问题；`curl -H "Authorization: Bearer <TOKEN>" https://api.github.com/repos/itoves/liulianggu-site` 返回的 `permissions.push=true` **不代表 token 有写权限**（那是账号权限）。

### 9.3 常见部署故障

| 现象 | 处理 |
| --- | --- |
| deploy job 卡 `in_progress` 后 `failure` | 用 API 重跑失败 job：`POST /repos/itoves/liulianggu-site/actions/runs/{id}/rerun-failed-jobs`（build 产物还在，不用重跑 build） |
| 线上看到旧页面 | CDN 缓存。HTML 加 `?v=随机数`；`style.css` 同理 |
| 本地构建卡住 / `OSError: SHFileOperationW 0x2` | Windows 的 `sitecustomize.py` 把 `rmtree` 路由到回收站。现已 `try/except` 兜住；必要时 `rm -rf site` 再构建 |
| `git push` 报 `could not read Username` | 凭据管理器里是失效 token。用 9.2 的一次性 URL 推送 |

### 9.4 查看部署状态

```bash
curl -s "https://api.github.com/repos/itoves/liulianggu-site/actions/runs?per_page=1" \
 | python -c "import json,sys;r=json.load(sys.stdin)['workflow_runs'][0];print(r['head_sha'][:7],r['status'],r['conclusion'])"
```

---

## 10. 收录与站点验证

### 10.1 `verification.json`（一键注入机制）

```json
{"google": "t2MPIT6...", "bing": "", "baidu": "", "adsense": ""}
```

`build_site.py` 的 `load_verification_head()` 读取并注入**每个页面** `<head>`：

| 字段 | 注入内容 |
| --- | --- |
| `google` | `<meta name="google-site-verification" content="...">` |
| `bing` | `<meta name="msvalidate.01" content="...">` |
| `baidu` | `<meta name="baidu-site-verification" content="...">` |
| `adsense` | `<script async src=".../adsbygoogle.js?client=ca-pub-xxx" crossorigin="anonymous">` |

留空则不注入。**改完必须重建 + 推送才生效**（CI 会重新构建）。

### 10.2 各平台踩坑记录

- **GSC 资源类型选错（H5）**：选「网域/Domain」→ 只能用 DNS TXT 验证，而 DNSPod 免费版记录数已满 → 走不通。**必须选「网址前缀 / URL prefix」**，然后用 HTML 标记验证（meta 已全站注入）。
- **GSC 没点「验证」时**：左侧菜单不完整，看不到「索引编制 → 站点地图」；Bing 的 "Import from GSC" 也会拉不到任何资源。这两个报错是同一个根因。
- **Bing 备选**：手动 Add site → HTML Meta Tag（把 content 填进 `verification.json.bing`），或下载 `BingSiteAuth.xml` 放仓库根目录（CI 会自动复制到站点根）。
- **百度**：`ziyuan.baidu.com` → 添加网站 → HTML 标签验证（把 content 填进 `verification.json.baidu`）。百度对 GitHub Pages 抓取慢，短期收录少属正常。

### 10.3 sitemap 现状

- 已提交到 GSC，状态「无法抓取」，`上次读取时间` 空 —— **Google 从未成功读取**。
- 服务端已全项排查正常（见 2.3），结论是 Google 侧时机/新域名问题，**不是配置错误**。
- 已做的兜底：`/all/` 索引页 + 每页页脚入口。**下一步建议**：GSC 里移除后重新提交**完整 URL**（`https://liulianggu.site/sitemap.xml`），间隔 24–48 小时；同时用「网址检查 → 请求编入索引」手动催首页与 5–10 个重点工具页。

---

### 10.4 变现位 `monetization.json`（2026-11-06 新增）

广告与 CPA 的插入点已经写好，**全部"留空即不渲染"**——默认配置下生成的 HTML 与没有变现位时完全一致，不会有空盒子。

```json
{
  "adsense": {"slot_in_article": "", "slot_bottom": ""},
  "cpa": {"理财": {"title": "", "text": "", "cta": "", "url": ""}}
}
```

| 位置 | 由谁控制 | 插入点（`render_article_page`） |
| --- | --- | --- |
| 广告客户端 ID | `verification.json.adsense`（`ca-pub-xxx`） | 每页 `<head>` + 自动生成 `site/ads.txt` |
| 文内广告 | `monetization.json.adsense.slot_in_article` | 工具下方、正文之前 |
| 文末广告 | `monetization.json.adsense.slot_bottom` | 正文之后 |
| CPA/线索卡 | `monetization.json.cpa.<分类>` | 工具下方（用户刚算完，意图最强） |

要点：
- `render_ad_slot()` / `render_cpa_block()` / `adsense_client()` 在 `build_site.py` 第 105 行之后的「变现位」段。
- CPA 块的 key 必须与 frontmatter 的 `category` **完全一致**；`url` 为空整块不渲染。
- CPA 块自动带「推广」标识与 `rel="sponsored nofollow"`，**别去掉**（合规）。
- `ads.txt` 随 `verification.json.adsense` 自动生成/删除，不要手工维护。
- `_MONETIZATION` 是进程级缓存，**改完 `monetization.json` 必须重新构建**才生效。

> 变现策略与阶段判断写在 `变现操作清单.md`（2026-11-06 重写版），交接时可直接给业务方看。

## 11. 巡检系统（`patrol.py` + 每周自动化）

**设计原则：没变化就不吵我。** 只读，不改任何文件。

```bash
python patrol.py          # 正常巡检：读/写基线，追加日志
python patrol.py --dry    # 只看结果，不落盘
```

检查项：

1. `robots.txt`：HTTP 200、含 `Sitemap:` 声明、含 `Allow: /`
2. `sitemap.xml`：可获取、可解析、URL 数 ≥ 50（防文章被误删）
3. 逐个 URL（并发 8）：HTTP 状态、`meta robots` / `X-Robots-Tag` 的 `noindex`、canonical 是否存在、首页是否有 Google 验证 meta
4. 与基线 `.workbuddy/patrol_baseline.json` 对比：新增/减少页面
5. 输出 JSON（`date/checked/alerts/warnings/notes/ok`）+ 追加 `.workbuddy/patrol_log.md`

**自动化**：`流量谷站健康周巡检`，id `d17935b2-4d45-4fd2-92ca-caf914ac2c10`，每周一 09:00，ACTIVE。
汇报规则：无异常只回一行；有异常逐条列 URL + 问题 + 建议，按严重程度排序。

**最近一轮**：2026-11-03，59 页全 200、0 异常 0 警告，基线已建立（当时 `/all/` 尚未上线，基线为 59 页；下次巡检会记为「新增 3 页」，属正常）。

---

## 12. 已踩的坑（按重要性排序）

### H1 · 全站品牌名回退成「我的工具站」（2026-11-03 修复，影响最大）

- **现象**：线上每页 header logo、页脚版权、`og:site_name`、首页/`all`/隐私页的 `<title>` 全是「我的工具站」。
- **根因**：`config.yaml` 含 API Key 被 `.gitignore` 排除 → CI 里不存在 → `read_config()` 回退到硬编码默认 `{"name":"我的工具站","url":"https://example.com"}`。这个问题**从建站起就存在**。
- **修复**：新增入库 `site.yaml`；`read_config()` 改三层合并；默认值统一为「流量谷」；首页 title 优化为带副标题。
- **教训**：任何被 gitignore 的配置，只要字段影响线上渲染，就必须在仓库里留非敏感副本。**验证方法：把该文件临时移走再构建，看产物是否正确。**

### H2 · 所有工具页空白（2026-10-14 修复，唯一靠真人点测发现）

- **现象**：`.tool-widget` 容器存在但内容为空，无 JS 报错。
- **根因**：`autoMount()` 选 `[data-tool-id]`，而构建注入的是 `data-tool-keyword`。
- **修复**：选择器对齐；复测 BMI 180/80→24.7、1cm→0.393701in。
- **教训**：单测直调 `mountTool` 绕过了选择器；**前端挂载改动必须真开浏览器验证**。

### H3 · 瘦身脚本把标题掏空（2026-10-14）

- **现象**：正文出现空的 `## ` 标题和「到。」这种断句。
- **根因**：用正则做**行内**替换营销词，把整句/整行结构破坏。
- **修复**：改为**整行删除**（命中词则删掉所在行）；`git checkout -- output` 回滚后重跑。
- **教训**：批量文本清洗优先"整行粒度"，且必须先 `--dry` 看 diff。

### H4 · GSC 选了「网域」资源 → 无解

见 10.2。用户当时卡在"DNS 记录验证"，因为免费 DNSPod 只有 2 条记录且被 A 记录占用。**正确路径是「网址前缀」+ HTML 标记**。

### H5 · 本地构建 `OSError: SHFileOperationW 失败: 0x2`

- **根因**：Windows 环境的 `sitecustomize.py` 把 `shutil.rmtree` 重定向到回收站，遇到被占用目录会失败/挂死。
- **修复**：`rmtree` 包 `try/except OSError`，并跳过每次都会重建的 `privacy`/`all`。CI 是全新 checkout，不受影响。

### H6 · GitHub Pages deploy job 卡住

已 `build` 成功后 `deploy` 偶发 `failure`。用 `rerun-failed-jobs` 重跑即可，不要重新提交代码。

### H7 · fine-grained PAT 403

见 9.2。核心误区：把 API 的 `permissions.push=true` 当成 token 权限。

### H8 · `agent-browser` 使用坑（做浏览器实测时）

- `batch` 多命令会挂死 → 用 `&&` 串成一条命令
- 没有 `resize` → 用 `set viewport 1280 1000`
- `screenshot --full-page` 会卡住 → 只截视口
- `type` 是追加不是覆盖 → 用 `fill`（先清空）
- `snapshot` 常返回 "(empty page)" → 改用 `screenshot` + 从源码推 CSS 选择器（如 `[data-key="heightCm"]`、`.tool-btn`）
- 页面与后台进程在**分次命令间会丢** → 整个流程放同一条命令里跑

### H9 · Python 环境

系统 `python3` 缺 `yaml` / `markdown`。用托管 venv：

```
C:/Users/60585/.workbuddy/binaries/python/envs/default/Scripts/python.exe
```

Node：`C:/Users/60585/.workbuddy/binaries/node/versions/22.22.2-6/node.exe`（`node --test tools/tests/tools.test.mjs` 用 PATH 里的 node 即可）。

### H10 · 首页搜索只做 `indexOf`

没有拼音、没有同义、没有分词。搜「房贷」命中，「fangdai」不命中。要升级就改 `HOME_SEARCH_JS`（注意它是内联在 HTML 里的，改完用 `node --check` 验语法）。

### H11 · `git push` 后显示 `ahead 3` 的假象

- **现象**：推送明明成功、CI 也跑成功了，但 `git status -sb` 仍显示 `## main...origin/main [ahead 3]`。
- **根因**：推送时用的是**一次性完整 URL**（`https://x-access-token:...@github.com/...`），git 只更新了 `FETCH_HEAD` 逻辑，没有更新 `refs/remotes/origin/main`。
- **确认方法**：不要信本地 ref，直接查远端 —— `curl -s https://api.github.com/repos/itoves/liulianggu-site/commits/main`，比 `head_sha`。
- **修复**：`git fetch "<带 token 的 URL>" main:refs/remotes/origin/main`（本机代理偶发 502，可重试或用 API 确认）。

### H12 · 把「sitemap 无法抓取」当成配置错误反复排查

- **现象**：GSC 显示「无法抓取」「上次读取时间空」，于是反复检查 sitemap 格式、DNS、robots、UA。
- **结论**：服务端**全部正常**（见 2.3 的逐项清单），根因在 Google 侧的抓取时机/新域名信任度，属于「只能等 + 加发现路径」的问题。
- **正确动作**：确认一次服务端正常 → 保留 `/all/` 兜底 → 24–48 小时内不要反复重提 → 用「网址检查 → 请求编入索引」手动催重点页。
- **教训**：把排查结论写进文档（本文 2.3），避免下一个 agent 从头再查一遍。

---

## 13. 常用命令速查

> 所有命令在项目根目录 `D:/ClaudeWorkSpace/兼职/01-SEO内容站` 执行。
> 下文的 `PY` 指托管 venv（系统 `python3` 缺 `yaml`/`markdown`，见坑 H9）：
> `C:/Users/60585/.workbuddy/binaries/python/envs/default/Scripts/python.exe`

```bash
# ---- 构建与预览 ----
PY build_site.py --domain https://liulianggu.site
PY -m http.server 8123 --bind 127.0.0.1 -d site      # 本地预览 http://127.0.0.1:8123/

# ---- 工具单测（改公式必跑）----
node --test tools/tests/tools.test.mjs

# ---- 全站校验（改模板后必跑）----
PY -c "
import glob,re
pages=glob.glob('site/**/index.html',recursive=True)
bad=sum(open(p,encoding='utf-8').read().count('我的工具站') for p in pages)
print('页面数',len(pages),'旧名残留',bad)
print('sitemap',open('site/sitemap.xml',encoding='utf-8').read().count('<loc>'))
"

# ---- 线上全量扫描（62 页并发）----
PY -c "
import urllib.request,re
from concurrent.futures import ThreadPoolExecutor
sm=urllib.request.urlopen('https://liulianggu.site/sitemap.xml').read().decode()
urls=re.findall(r'<loc>(.*?)</loc>',sm)
def chk(u):
    try:
        h=urllib.request.urlopen(u+'?v=1',timeout=20).read().decode()
        return (u,h.count('我的工具站'),h.count('example.com'))
    except Exception as e: return (u,-1,str(e)[:30])
with ThreadPoolExecutor(max_workers=12) as ex:
    r=list(ex.map(chk,urls))
print('扫描',len(r),'异常页',len([x for x in r if x[1]!=0 or x[2]!=0]))
"

# ---- 巡检 ----
PY patrol.py --dry

# ---- 内容 ----
PY main.py generate --count 3 --category 理财
PY main.py generate --count 2 --mock          # 不耗 API，验管道

# ---- Git ----
git add -A && git commit -m "说明"
git push "https://x-access-token:<TOKEN>@github.com/itoves/liulianggu-site.git" main
```

---

## 14. 待办清单（按优先级）

### P0 · 只有用户能做（账号侧）

| # | 事项 | 具体动作 | 完成后 |
| --- | --- | --- | --- |
| 1 | GSC 重提交 sitemap | 移除旧条目 → 提交**完整 URL** `https://liulianggu.site/sitemap.xml`；再用「网址检查」催首页 + 5–10 个重点工具页 | 等 24–48h 看「上次读取时间」 |
| 2 | Bing 验证 | webmasters → Add site → HTML Meta Tag，把 32 位 content 发来 | 填 `verification.json.bing` |
| 3 | 百度验证 | ziyuan.baidu.com → 添加网站 → HTML 标签验证 | 填 `verification.json.baidu` |
| 4 | AdSense 申请 | 等有实际收录后申请；需真实手机号 + 可收快递地址（国家选定不可改） | 拿到 `ca-pub-xxx` 填 `verification.json.adsense` |
| 5 | 吊销旧 PAT | 之前贴到对话里的 token 建议撤销 | — |

### P1 · Agent 可做（拿到验证码后）

- 填 `verification.json` → 重建 → 推送 → 线上抽查注入生效
- 生成 `ads.txt`（拿到 `ca-pub` 后）：`google.com, pub-XXXX, DIRECT, f08c47fec0942fa0`
- 文章页加同分类「相关阅读」（D3，改 `render_article_page`）

### P2 · 有流量后再做

- 扩内容到 100 篇（先扩 `topics.csv`）
- 计算器结果区加 CPA 位（装修线索 / 贷款，见第 15 节）
- AdSense 广告位布局（自动广告优先）
- 英文站复制（同一个引擎换语言，RPM 高 5–8 倍）

---

## 15. 变现路线（结论摘要，供决策参考）

**现状：0 收入，0 收录。** 现在谈变现方式没有意义，但有两条判断值得记住：

1. **AdSense 只是零花钱**。中文站 RPM 实测约 ¥10–30/千 PV（工具站停留短，偏下限），月入 ¥1,000 需要 5 万 PV/月。而英文站 RPM 是 $8–12（约 ¥60–85）。
2. **这个站的分类天生适合 CPA/线索，不适合纯广告**：理财（房贷计算器 → 贷款 CPA ¥50–300）、装修（预算计算器 → 装修公司线索 ¥100–500/条）、母婴/教育（保险、课程分销）。一个转化的价值 ≈ 几千次广告展示。工具结果区预留「推荐位」是将来最值钱的位置。

**阶段性结论**：先用中文站验证"工具 + SEO"这条流水线能否出流量；跑通后把同一套引擎复制到英文细分市场，那才是收入规模化的路径。

---

## 16. 交接红线（Do / Don't）

### Do

- 改任何模板/样式后，跑第 13 节的**全站校验**，并真开浏览器看一次工具页
- 改公式先跑 `node --test tools/tests/tools.test.mjs`
- 改站点名/域名时，`site.yaml` 与 `config.yaml` **同步改**
- 提交前确认 `git status` 里没有 `config.yaml`、`site/`、`.workbuddy/`
- 服务端排查结论优先信任本文第 2.3 节，别重复 curl 半小时

### Don't

- **不要**把 API Key、PAT 写进任何入库文件或文档
- **不要**手改 `site/` 里的产物（会被重建覆盖）
- **不要**删 `/privacy/`（AdSense/联盟审核硬性要求）或 `/all/`（收录兜底）
- **不要**用 `rm -rf` 清理 `output/`、`site/`；要回滚用 `git checkout -- output`
- **不要**在没跑测试的情况下改 `COMPUTE` 里的公式（健康/金融类算错有实际风险）
- **不要**把 `category` 字段直接改名成展示名（`CAT_FIX` 只做渲染归一化，frontmatter 保持原样）
- **不要**假设 API 返回的 `permissions.push=true` 等于 token 可写（H7）

---

## 17. 术语表

| 词 | 含义 |
| --- | --- |
| **工具 / widget** | 页面顶部的可交互计算表单，由 `tools.js` 动态挂载 |
| **registry** | `tools/registry.json`，58 个工具的配置表，键是文章 keyword |
| **keyword 三段对齐** | frontmatter.keyword == registry 键 == `data-tool-keyword` |
| **slug** | 文章 URL 路径与 `output/` 目录名 |
| **兜底发现路径** | `/all/` 索引页，用于 sitemap 抓取失败时让爬虫走遍全站 |
| **基线** | `patrol_baseline.json`，巡检对比用的上一轮 URL 集合 |
| **CAT_FIX** | 渲染时把遗留英文分类映射成中文的字典 |

---

*本文档由 2026-11-05 的会话生成，数据均为当日实测。下次大改动后请更新第 2 节的快照与第 12 节的坑表。*
