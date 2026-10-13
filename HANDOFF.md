# HANDOFF · 01-SEO内容站（自动运营机器人）

> 本文件用于「接力」项目：任何接手或下次打开会话的人，先读这个，再动手。
> 最后更新：2026-10-13

---

## 0. 一句话背景

用 AI 批量生成「小而实用」的中文内容页（计算器 / 单位换算 / 攻略 / FAQ），构建成**零成本静态站**，靠 AdSense / 国内联盟的广告点击与展示分成赚钱。全流程已搭好：选题 → 生成 → 构建 → 部署 → 提交收录。

目标（README）：单站先发到 100 篇优质页面，日 UV 500~2000，月广告收入 ¥300~1500；跑通后复制成站群。

---

## 1. 当前进度（截至 2026-10-12）

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 项目脚手架 / 代码 | ✅ 完成 | `seo_article_bot/` 核心包 + `main.py` + `build_site.py` 均可用 |
| 配置 config.yaml | ✅ 已填 | AI 已切 **DeepSeek 官方**接口（base_url `https://api.deepseek.com/v1`，model `deepseek-chat`），Key 明文在本地、已被 .gitignore 忽略 |
| 主题池 topics.csv | 🟡 58 个 | 8 大垂直：理财7/装修6/母婴5/工具4/健康7/饮食4/出行5/教育4/数码4/职场4/居家4/政务4 |
| 已生成文章 | ✅ 59 篇 | output/ + site/ 已构建（2026-10-12 全量补齐；含 1 篇历史非 csv 文章） |
| 已用主题 | ✅ 58 个 | `topics_used.json` 记录（csv 58 个选题全部生成完毕，剩余 0） |
| **剩余未生成主题** | ✅ **0 个** | csv 选题已全部生成 |
| 站点部署 | 🟢 已部署待解析 | 仓库 `itoves/liulianggu-site`（公开）已推送 `main`；GitHub Pages 已开启（Actions 模式）；自定义域名 `liulianggu.site` 已绑定；**仅差腾讯云 DNSPod 加 A 记录** |
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

## 4. 部署到 GitHub Pages（已接入域名 liulianggu.site，腾讯云 DNSPod）

> 项目已本地提交到 `main` 分支，但 **git 还没有远程仓库**，需你建库后推送。部署链路：
> push `main` → Actions 用 `SITE_URL`（兜底 `https://liulianggu.site`）构建 → 部署到 GitHub Pages → 自定义域名 liulianggu.site。

1. **建 GitHub 仓库**（Public/Private 均可；不要勾选初始化文件），记下仓库 URL。
2. 本地关联并推送（当前分支已是 `main`）：
   ```bash
   git remote add origin https://github.com/<用户名>/<仓库名>.git
   git push -u origin main
   ```
   首次推送用 GitHub 个人访问令牌（PAT，勾 `repo` 权限）代替密码。
3. 仓库 **Settings → Pages → Source 选 GitHub Actions**；等首次部署成功（Actions 标签页可见）。
4. **Settings → Secrets and Variables → Actions → Variables** 加 `SITE_URL = https://liulianggu.site`
   （不配也能跑，`deploy.yml` 已兜底真实域名）。
5. **Settings → Pages → Custom domain** 填 `liulianggu.site` → Save；DNS 生效后勾选 **Enforce HTTPS**
   （GitHub 自动签发证书，约 15~30 分钟）。
6. **腾讯云 DNSPod 解析**（域名控制台 → 解析 → 添加记录）：
   | 主机记录 | 类型 | 记录值 | 说明 |
   | --- | --- | --- | --- |
   | `@` | A | `185.199.108.153` | GitHub Pages |
   | `@` | A | `185.199.109.153` | GitHub Pages |
   | `@` | A | `185.199.110.153` | GitHub Pages |
   | `@` | A | `185.199.111.153` | GitHub Pages |
   | `www`（可选）| CNAME | `<用户名>.github.io` | 如需 www 访问 |
   改完等 DNS 生效（几分钟~几小时），再回 GitHub 开 Enforce HTTPS。
7. 浏览器打开 `https://liulianggu.site` 应看到首页；随后在 GSC / Bing / 百度 提交 `sitemap.xml`。
   - 搜索引擎验证文件（`google*.html` / `baidu_verify_*.html`）放到**仓库根目录**，CI 会自动复制到站点。
   - 国内（百度）抓取 GitHub Pages 偏慢，必要时后续换 Cloudflare Pages + 已备案域名提速。

---

## 5. 已知问题 / 坑（接手请留意）

0. **✅ API 接口已切换（原 tokenrhythm Key 过期）**：原 `sk_tr_...` Key 在 2026-10-12 返回
   `401 UNAUTHORIZED`。用户已改用 **DeepSeek 官方接口**（`base_url: https://api.deepseek.com/v1`，
   `model: deepseek-chat`，填入官方 Key），冒烟+全量生成均通过。
   - 附带修复：原 `generator.py` 仅在网络/空内容时重试，遇到**模型返回非法 JSON 会直接整批崩溃**；
     已改为「JSON 解析失败/字段缺失/空内容」都自动重试（最多 3 次），并先剥离 ```` ```json ```` 代码围栏；
     同时 `cmd_generate` 改为单篇失败跳过、不中断整批。一轮 46 篇曾因该 bug 中途失败，加固后补跑剩余 6 篇全过。
1. **占位域名已解决**：`site.url` 已改为 `https://liulianggu.site`，本地构建与 CI（兜底 `SITE_URL`）都用真实域名。
   剩余阻塞：本地 git 此前无远程仓库、分支为 `master`，已把分支改名为 `main` 对齐 `deploy.yml`；
   还需你**建 GitHub 仓库并 push**，详见第 4 节。
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

- [x] **AI Key 已换（DeepSeek 官方）**：`config.yaml` 已填官方 Key，`generate` 全量通过。
- [x] **内容已补齐**：58 个选题全部生成（59 篇），`topics.csv` 剩余 0。
- [x] **域名与构建已就绪**：`site.url=https://liulianggu.site`，`deploy.yml` 含 `SITE_URL` 兜底，分支已改 `main`，已本地提交。
- [x] **建 GitHub 仓库并推送**：仓库 `itoves/liulianggu-site`（公开）已建，`main` 已推送，Actions 自动构建部署成功（run 已 completed）。
- [x] **GitHub Pages 设置**：Source=GitHub Actions、`SITE_URL` 变量、自定义域名 `liulianggu.site` 均已在 API 层完成；HTTPS 证书将在 DNS 生效后自动签发，随后在 Settings → Pages 勾选 Enforce HTTPS。
- [ ] **腾讯云 DNSPod 解析**（见第 4 节记录表）：`@` 加 4 条 A 记录指向 GitHub Pages IP；可选 `www` CNAME。
- [ ] 部署后在 GSC / Bing / 百度 提交 `sitemap.xml`，请求索引（验证文件放仓库根，CI 自动复制）。
- [ ] 内容稳定后申请 AdSense（建议先有真实流量与隐私页）。
- [ ] 第 30 天复盘：收录率（>80%）、搜索点击，淘汰零流量方向；要冲 100 篇把 `topics.csv` 扩到 100+ 再 `generate`。
- [ ] （可选）修复 mock 标签 bug；开启 `schedule` 定时发布。

---

## 7. 关键命令速查

| 想做 | 命令 |
| --- | --- |
| 看还剩多少主题 | 打开 `topics_used.json` 比对 `topics.csv` |
| 生成全部剩余 | `python main.py generate --count 11` |
| 只看不生成 | `python main.py publish --count 3 --dry-run` |
| 重建站点 | `python build_site.py --domain 真实域名` |
| 本地预览 | `python -m http.server 8000 -d site` |
