# cn2kr 项目状态快照（跨频道上下文）

> 本文件用于跨会话/跨频道保留项目上下文。切到新频道后，先读这个文件即可接上进度。

## 项目是什么

**cn2kr** —— 面向韩国人的"中国综合门户"网站。三大板块：**科技(중국 테크) / 美景旅行(중국 여행) / 电商(중국 직구)**。

## 最终架构（已抛弃 WordPress）

```
中文信息源(百度热搜/今日头条/什么值得买)
  ↓ Python pipeline 抓取
DeepSeek API 加工（翻译+本土化+随机切入角度）
  ↓ 存 Markdown（带 frontmatter + 真实照片配图）
Nuxt 4 + @nuxt/content 读取
  ↓ nuxt generate 静态生成
Cloudflare Pages（静态托管，$0）+ Supabase（点赞/评论/未来登录）
```

- **无 WordPress、无主题**；内容就是 Markdown 文件，点赞/评论/用户走 Supabase（免费 Postgres）
- 技术栈：Vue 3 + Nuxt 4（用户只会 Vue，不会 React/Next）
- 部署：`cn2kr.net` → Cloudflare Pages（首尔 CDN），详见 `SETUP_DEPLOY.md`

## 关键路径

| 东西 | 路径 |
|------|------|
| pipeline 脚本 | `D:\Application\cn2kr\pipeline.py` |
| pipeline 配置 | `D:\Application\cn2kr\config.json`（含 DeepSeek key） |
| 配图脚本 | `D:\Application\cn2kr\fetch_images.py`（Wikimedia Commons 真实照片） |
| 前端项目 | `D:\Application\cn2kr-frontend\` |
| 内容目录 | `D:\Application\cn2kr-frontend\content\articles\`（30 篇 md） |
| 配图目录 | `D:\Application\cn2kr-frontend\public\images\`（30 张 jpg/png 真实照片 + 旧 svg） |
| 前端设计 | `app\assets\css\main.css` + `app\pages\` + `app\components\` |
| 数据库 schema | `D:\Application\cn2kr\supabase\schema.sql`（likes/comments 表 + RLS） |
| 部署文档 | `D:\Application\cn2kr\SETUP_DEPLOY.md`（Supabase + Cloudflare Pages） |
| 环境变量模板 | `cn2kr-frontend\.env.example`（SUPABASE_URL + ANON_KEY） |

## 当前进度

1. ✅ pipeline 已跑通，30 篇内容（科技10+旅行10+电商10，均衡）
2. ✅ 前端已改成 Nuxt 4 + @nuxt/content，从 Markdown 读取
3. ✅ 解决过的坑：@nuxt/content 需要 better-sqlite3；字段是 `path`/`meta.category`（不是 `_path`/`category`）；内容目录在根 `content/`（不是 `app/content/`）
4. ✅ 修掉 bug：分类页用了不存在的 `.grid`/`.section-title` 类 → 抽了共用 `PostGrid.vue`，首页/分类页统一杂志混排
5. ✅ 配图升级：30 篇全部换成 Wikimedia Commons 真实照片（前端 `image` 字段已从 .svg 改为 .jpg/.png）
6. ✅ 首页加了「头条焦点区」Hero（大图 + 渐变压暗 + 分类色块 + 大标题 + 导语，跟随分类页签切换，与网格去重）
7. ✅ 点赞功能 + 访客评论（先做了 SQLite + Nitro 版，后因托管需求迁移）
8. ✅ 点赞/评论加固：匿名 client_id 幂等去重、IP 滑动窗口限流、honeypot 蜜罐、`approved` 审核字段
9. ✅ **迁移到 Supabase + 静态托管**：删掉 `server/`（SQLite/Nitro），点赞/评论改走 Supabase 客户端直连；`nuxt generate` 静态生成（71 路由，`.output/public`）；写好 `schema.sql` + `SETUP_DEPLOY.md` + `.env.example`
10. 🔄 **待办**：用户在 Supabase 建项目跑 schema + Cloudflare Pages 绑定 `cn2kr.net`；之后加 Google 登录（表已预留 user_id）、评论审核后台、排版精修

## UI 方向（用户明确要的）

- 用户喜欢 **Naver 新闻那种"看似非规则但正规"的杂志式布局**
- 已经实现：**CSS Grid 杂志混排**（`card--large` 2×2 大卡、`card--wide` 2×1 横排、`card--tall` 1×2 高卡 + 普通卡，`grid-auto-flow: dense`）+ 顶部分类标签页签（전체/테크/여행/직구，可点击筛选）
- 配色：科技蓝 #2563eb / 旅行绿 #10b981 / 电商橙 #f97316（分类专属色，定义在 `app/composables/useCategories.js`）
- 用户刚说"不喜欢"之前那版，要更明显的大小混排 → 已改成 Grid 杂志式，待用户确认

## 配图说明

- 已从 SVG 渐变占位图升级为 **Wikimedia Commons 真实照片**（30 张 jpg/png，免费、无需 key）
- 配图脚本：`fetch_images.py`（文件名 → 英文检索词 → 搜图 → 下载 → 更新 frontmatter，带 `--dry-run` 预览 + 429 重试限速）
- 旧 svg 仍留在 `public/images/` 但已无引用（可安全删除）
- 之后若嫌 Commons 图源不够精致，可换 Pexels/Unsplash 免费 API（需注册 key）

## 启动命令

```bash
# 前端 dev server（当前已在后台运行）
cd D:\Application\cn2kr-frontend && npm run dev   # → localhost:3000

# 生成更多内容
cd D:\Application\cn2kr && python pipeline.py --category tech --count 10
# 分类：tech / travel / direct

# 查看 Hermes 频道配置
hermes config get discord.allowed_channels
```

## 用户偏好/雷区（重要）

- 极度反感：付费主题/订阅制、卖课/知识付费、"教人赚钱的课"
- 用户是开发者，只熟 Vue（不熟 React/Next）
- 讨厌被说"这不现实"，要"一定能做成"的前提
- 参考过 Morningstar Korea 那种干净专业的企业站风格
- 之前反复强调设计的重要性，别轻视 UI
