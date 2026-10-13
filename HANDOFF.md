# HANDOFF · 01-SEO内容站（自动运营机器人）

> 本文件用于「接力」项目：任何接手或下次打开会话的人，先读这个，再动手。
> 最后更新：2026-10-12

---

## 0. 一句话背景

用 AI 批量生成「小而实用」的中文内容页（计算器 / 单位换算 / 攻略 / FAQ），构建成**零成本静态站**，靠 AdSense / 国内联盟的广告点击与展示分成赚钱。全流程已搭好：选题 → 生成 → 构建 → 部署 → 提交收录。

目标（README）：单站先发到 100 篇优质页面，日 UV 500~2000，月广告收入 ¥300~1500；跑通后复制成站群。

---

## 1. 当前进度（截至 2026-10-12）

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 项目脚手架 / 代码 | ✅ 完成 | `seo_article_bot/` 核心包 + `main.py` + `build_site.py` 均可用 |
| 配置 config.yaml | ✅ 已填 | AI 用 tokenrhythm（DeepSeek 上游）接口，Key 已写入明文 |
| 主题池 topics.csv | 🟡 58 个 | 8 大垂直：理财7/装修6/母婴5/工具4/健康7/饮食4/出行5/教育4/数码4/职场4/居家4/政务4 |
| 已生成文章 | ✅ 59 篇 | output/ + site/ 已构建（2026-10-12 全量补齐；含 1 篇历史非 csv 文章） |
| 已用主题 | ✅ 58 个 | `topics_used.json` 记录（csv 58 个选题全部生成完毕，剩余 0） |
| **剩余未生成主题** | ✅ **0 个** | csv 选题已全部生成 |
| 站点部署 | ❌ 未做 | `site.url` 仍是占位 `https://example.com` |
| 搜索引擎提交 | ❌ 未做 | 未提交 GSC / Bing / 百度 |
| AdSense 申请 | ❌ 未做 | 需先有可访问站点 + 一定内容量 |
| 定时发布 | ⚪ 配置关闭 | `schedule.enabled: false`，目前靠手动 `generate` |

**结论**：代码与生成链路健康，**内容生成已完成首批 59 篇（csv 58 个选题全部生成完毕，0 剩余）**。生成器已加固——模型返回非法 JSON 时自动重试、单篇失败不再中断整批（详见第 5 节）。下一步重点是**部署上线 + 提交搜索引擎 + 申请 AdSense**；要冲 README 的「100 篇」目标，把 `topics.csv` 扩到 100+ 再跑一轮 `generate` 即可。

---

## 2. 目录结构（接手必读）

```
01-SEO内容站/
├── main.py                 # 入口：python main.py <init|generate|publish|schedule|sitemap>
├── build_site.py           # 静态站构建器：output/*/index.md → site/
├── config.yaml             # ⚠️ 含明文 API Key，已被 .gitignore 忽略，勿提交
├── config.example.yaml     # 配置模板
├── topics.csv              # 主题池（keyword,category,target_url），可随意扩充
├── topics.example.csv      # 主题池模板
├── topics_used.json        # 已用主题记录（生成器自动维护）
├── scheduler_state.json    # 每日发布计数（publish/schedule 模式用）
├── requirements.txt        # 依赖：pyyaml/requests/schedule/python-slugify/markdown
├── seo_article_bot/        # 核心代码包
│   ├── main.py             # CLI 子命令实现
│   ├── generator.py        # AI 生成器（OpenAI 兼容，--mock 走本地模板）
│   ├── publisher.py        # 发布器（local 写 output/；wordpress 发 WP）
│   ├── topics.py           # 主题池管理 + 去重
│   ├── seo.py              # slug / JSON-LD / sitemap
│   ├── scheduler.py        # 定时发布 + 每日上限
│   ├── config.py           # 配置加载
│   └── frontmatter.py      # Markdown frontmatter 解析
├── output/                 # 生成文章（Markdown + YAML frontmatter）
├── site/                   # 构建出的静态站（可直接部署；已 .gitignore）
├── .github/workflows/deploy.yml  # 推送 main 后自动构建并部署到 GitHub Pages
├── 运行说明.md / 站长提交清单.md / README.md  # 操作手册
```

---

## 3. 怎么跑（常用命令）

```bash
# 0) 安装依赖（首次）
pip install -r requirements.txt

# 1) 本地模板联调（不耗 API，先验证管道）
python main.py generate --count 2 --mock

# 2) 真实生成（自动取未用主题，每篇消耗 1 个额度）
python main.py generate --count 5

# 3) 指定方向批量生成（如先把装修/母婴补齐）
python main.py generate --count 6 --category 装修

# 4) 构建静态站（默认域名取 config.yaml 的 site.url）
python build_site.py
#    上线时覆盖真实域名：
python build_site.py --domain https://你的域名.com

# 5) 本地预览
python -m http.server 8000 -d site

# 6) 重新生成本地 sitemap（local 模式）
python main.py sitemap
```

定时发布（可选，目前关闭）：
```bash
python main.py schedule          # 常驻进程，按 config.schedule 节奏发布
# 或系统计划任务每 N 分钟：python main.py publish --count 1
```

> AI 接口在 `config.yaml` 的 `ai` 段：base_url `https://tokenrhythm.studio/v1`，model `deepseek-v4-flash-0731`。
> Key 是明文；若要提交到公开仓库，改用 `api_key_env` 环境变量方式。

---

## 4. 部署到 GitHub Pages（必做，见 站长提交清单.md）

1. 建 GitHub 仓库（不要勾选初始化文件）；
2. `git remote add origin ... && git push -u origin master`（用 PAT 代替密码）；
3. 仓库 Settings → Pages → Source 选 **GitHub Actions**；
4. （可选）Settings → Variables 加 `SITE_URL`；
5. 推送后 Actions 自动构建并部署；浏览器打开 `https://用户名.github.io/仓库名/` 应看到首页。
6. 部署后在 GSC / Bing / 百度 提交 `sitemap.xml`，请求编入索引。
   - 国内流量（百度）建议再买已备案域名 + Cloudflare，GitHub Pages 国内抓取差。

---

## 5. 已知问题 / 坑（接手请留意）

0. **✅ API 接口已切换（原 tokenrhythm Key 过期）**：原 `sk_tr_...` Key 在 2026-10-12 返回
   `401 UNAUTHORIZED`。用户已改用 **DeepSeek 官方接口**（`base_url: https://api.deepseek.com/v1`，
   `model: deepseek-chat`，填入官方 Key），冒烟+全量生成均通过。
   - 附带修复：原 `generator.py` 仅在网络/空内容时重试，遇到**模型返回非法 JSON 会直接整批崩溃**；
     已改为「JSON 解析失败/字段缺失/空内容」都自动重试（最多 3 次），并先剥离 ```` ```json ```` 代码围栏；
     同时 `cmd_generate` 改为单篇失败跳过、不中断整批。一轮 46 篇曾因该 bug 中途失败，加固后补跑剩余 6 篇全过。
1. **未部署 + 占位域名**：`site.url` 仍为 `https://example.com`。部署前用
   `python build_site.py --domain 真实域名` 重建，否则 sitemap/canonical 全是 example.com。
2. **明文 API Key**：`config.yaml` 含 Key，已 gitignore。换机器 / 公开仓库前改环境变量方式。
3. **Mock 标签 bug（仅 --mock 测试受影响，真实生成无碍）**：`generator.py:_generate_mock`
   里用 `{"calculator":...,"converter":...,"faq":...,"guide":...}.get(category)` 映射标签，
   但 topics.csv 的 category 是中文（理财/装修/母婴/工具），永远落到兜底 `"实用工具"`。
   修复：把那行 `category` 标签直接换成 `topic.category` 即可。
4. **主题池与 used 列表不一致**：`网站关键词布局技巧` 在 `topics_used.json` 里、却不在 `topics.csv`
   （历史残留）。不影响生成（生成只从 csv 取未用项），但下次清理 csv 时注意别误删逻辑。
5. **真实生成质量需抽检**：README 要求首次真实生成后人工抽检 1~2 篇（数据表格/FAQ 准确性），
   再放开定时任务，避免 AI 低质内容被搜索引擎惩罚。
6. **内容量远未达标**：目标 100 篇，当前 12 篇。需持续 `generate` 扩充主题池并生成。

---

## 6. 待办 / 下一步（接手直接照做）

> ⚠️ 前置条件：先解决第 5 节「API Key 过期」问题（换有效 Key），否则以下生成步骤全部卡住。

- [ ] **换上有效 AI Key**：更新 `config.yaml` 的 `ai.api_key`（或改 `api_key_env` 环境变量）。
      验证：`python main.py generate --count 1` 能产出 1 篇即说明通了。
- [ ] **生成剩余 47 个主题**（池已扩到 58，已用 11，剩 47）：
      - 早期未做 11 个：装修6（装修预算/墙砖数量/乳胶漆用量/窗帘尺寸/装修工期/瓷砖美缝）+ 母婴5（预产期/宝宝身高体重/疫苗接种/辅食添加/孕期体重）
      - 新增 36 个：健康7 / 饮食4 / 出行5 / 教育4 / 数码4 / 职场4 / 居家4 / 政务4
      - 建议分批：`python main.py generate --count 10 --category 装修` 等，避免一次超时。
- [ ] 真实域名 + `build_site.py --domain` 重建并部署到 GitHub Pages / Cloudflare。
- [ ] 提交 GSC / Bing / 百度 sitemap，请求索引。
- [ ] 内容到 ~20 篇后申请 AdSense（英文站单价更高，可后续测）。
- [ ] 第 30 天复盘：看收录率（>80%）、有无搜索点击，淘汰零流量方向。
- [ ] （可选）修复第 5 节 mock 标签 bug；开启 `schedule` 定时发布。

---

## 7. 关键命令速查

| 想做 | 命令 |
| --- | --- |
| 看还剩多少主题 | 打开 `topics_used.json` 比对 `topics.csv` |
| 生成全部剩余 | `python main.py generate --count 11` |
| 只看不生成 | `python main.py publish --count 3 --dry-run` |
| 重建站点 | `python build_site.py --domain 真实域名` |
| 本地预览 | `python -m http.server 8000 -d site` |
