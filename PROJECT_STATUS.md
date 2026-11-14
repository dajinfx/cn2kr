# cn2kr 项目状态快照（跨频道上下文）

> 本文件用于跨会话/跨频道保留项目上下文。切到新频道后，先读这个文件即可接上进度。

## 项目是什么

**cn2kr** —— 面向韩国人的"中国综合门户"网站。四大板块：**科技(중국 테크) / 美景旅行(중국 여행) / 电商(중국 직구) / 社会(중국사회)**。

## 最终架构（已抛弃 WordPress）

```
中文信息源(百度热搜/今日头条/什么值得买/简书/少数派)
  ↓ Python pipeline 抓取
DeepSeek API 加工（翻译+本土化+从热搜自由选题）
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
| pipeline 脚本 | `D:\Git\cn2kr\pipeline\pipeline.py` |
| pipeline 配置 | `D:\Git\cn2kr\pipeline\config.json`（含 DeepSeek key） |
| 配图脚本 | `D:\Git\cn2kr\pipeline\fetch_images.py`（Wikimedia 真实照片，多层兜底+去重+城市映射） |
| 前端项目 | `D:\Git\cn2kr\frontend\` |
| 内容目录 | `D:\Git\cn2kr\frontend\content\articles\`（34 篇 md） |
| 配图目录 | `D:\Git\cn2kr\frontend\public\images\`（jpg/png 真实照片 + 旧 svg） |
| 前端设计 | `app\assets\css\main.css` + `app\pages\` + `app\components\` |
| 数据库 schema | `D:\Git\cn2kr\supabase\schema.sql`（likes/comments 表 + RLS） |
| 部署文档 | `D:\Git\cn2kr\SETUP_DEPLOY.md`（Supabase + Cloudflare Pages） |
| 环境变量模板 | `D:\Git\cn2kr\frontend\.env.example`（SUPABASE_URL + ANON_KEY） |
| 自动化 | `.github/workflows/daily.yml`（GitHub Actions 云端，每天 8:00 KST，1篇/天） |

## 当前进度

1. ✅ pipeline 已跑通，30 篇内容（科技10+旅行10+电商10，均衡）
2. ✅ 前端已改成 Nuxt 4 + @nuxt/content，从 Markdown 读取
3. ✅ 解决过的坑：@nuxt/content 需要 better-sqlite3；字段是 `path`/`meta.category`（不是 `_path`/`category`）；内容目录在根 `content/`（不是 `app/content/`）
4. ✅ 修掉 bug：分类页用了不存在的 `.grid`/`.section-title` 类 → 抽了共用 `PostGrid.vue`，首页/分类页统一杂志混排
5. ✅ 配图升级：30 篇全部换成 Wikimedia Commons 真实照片（前端 `image` 字段已从 .svg 改为 .jpg/.png）
6. ✅ 首页加了「头条焦点区」Hero（大图 + 渐变压暗 + 分类色块 + 大标题 + 导语，跟随分类页签切换，与网格去重）
7. ✅ 点赞功能 + 访客评论（先做了 SQLite + Nitro 版，后因托管需求迁移）
8. ✅ 点赞/评论加固：匿名 client_id 幂等去重、IP 滑动窗口限流、honeypot 蜜罐、`approved` 审核字段
9. ✅ **迁移到 Supabase + 静态托管**：删掉 `server/`（SQLite/Nitro），点赞/评论改走 Supabase 客户端直连；`nuxt generate` 静态生成；写好 `schema.sql` + `SETUP_DEPLOY.md` + `.env.example`
10. ✅ **正式上线**：Cloudflare Pages 部署 + 域名 `cn2kr.net` + DNS + SSL；Supabase 建项目跑 schema（likes/comments 表 + RLS，publishable key 可用）
11. ✅ **去 AI 味儿提示词**：具体细节 + 禁套话（총정리/안녕하세요/오늘은 等）+ 温度 0.7
12. ✅ **敬语规则**：允许 합니다체(-ㅂ니다) 和 해요체(-요)，只禁 반말
13. ✅ **字体优化**：Pretendard（jsdelivr CDN）+ 字间距微调
14. ✅ **SEO/AEO**：@nuxtjs/sitemap 自动 sitemap.xml + robots.txt + 每页 meta + Article/WebSite JSON-LD + lang=ko
15. ✅ **首页版面优化**：卡片去边框改柔和阴影 + 栏目标题
16. ✅ **UAT/PRD 双环境**：`cn2kr.net`(main) + `uat.cn2kr.net`(uat)，两个独立 Pages 项目
17. ✅ **每日自动更新**：先 Windows 计划任务，后迁移到 GitHub Actions 云端（见 21）
18. ✅ **URL 关键词 slug**：pipeline 让 DeepSeek 生成英文 slug，`migrate_slugs.py` 迁移全部文章（`/articles/china-high-speed-rail-korean-tips` 这种，不再是时间戳）
19. ✅ **搜索引擎收录**：Naver（등록+검증+sitemap）、Google（验证+sitemap）、Bing（验证）全部完成，验证文件在 `frontend/public/`
20. ✅ **配图多层兜底**：搜索词简化（去尾巴词）+ 图片去重 + 城市标志景点映射（청두→Chengdu panda 等），修掉重复图/错城市/无关图
21. ✅ **迁移 GitHub Actions**：自动更新搬到云端（DeepSeek key 存 GitHub Secret，pipeline 支持环境变量+相对路径），不依赖本地电脑开机
22. ✅ **卡片悬浮样式**：缩略图 16:9 固定比例 + 图片四角圆角 + flex-shrink（修 70px 窄条 + 标题被裁）
23. ✅ **合并/删除重复文章**：删 17 篇重复（50 → 33 篇）
24. ✅ **About 页**：E-E-A-T 信任（站点使命/内容制作/编辑原则/免责声明/联系），导航+页脚入口
25. ✅ **文章语气改客观**：去掉「저는/제가/직접」第一人称编造，改「整理·指南」客观语气
26. ✅ **降发布频率**：每天 3 篇 → 1 篇（三个分类按日期轮流）
27. ✅ **相关文章推荐**（同分类内链）+ **分享按钮**（카카오톡/X/페이스북/링크복사）
28. ✅ **站内搜索**（搜索页 + 头部搜索图标）+ **首页加载更多**（初始 12 篇，点「더 보기」逐步显示）
29. ✅ **首页改 Yahoo 式三栏门户布局**：左 widgets + 主新闻流（大头图头条+排名小卡片+图文新闻流）+ 右 widgets，浅灰背景，白色卡片浮起
30. ✅ **配图精确化**：搜索词改成「具体产品/场景」（非泛分类词），DeepSeek 失败时先按标题提取城市（항저우→西湖），分类兜底词也改成相关词（직구→online shopping）
31. ✅ **全站封面图重配**：37 篇全部重配（精确搜索词 + 城市兜底），修掉了테무配上海全景、청두配长城等错图
32. ✅ **canonical 补上**（之前漏了）+ **删 4 篇最新重复文章**（로봇·드론/청두충칭고속철/AI앱/알리）+ `_redirects` 301 重定向
33. ✅ **pipeline 去重检查**：生成后跟已有标题比对主题（TOPIC_KEYWORDS），重复则换题重试（最多 5 次）
34. ✅ **方案 B 自由选题**：取消固定 10 个角度，让 DeepSeek 每天从当天热搜自己挑具体主题（主题跟着新鲜内容走，不再重复）
35. ✅ **新增「중국사회」分类**：4 分类（테크/여행/직구/사회），每日轮换，配图兜底+关键词都加了
36. ✅ **新增信息源**：简书（泛生活/社会话题，归入중국사회）+ 少数派（数码/科技 RSS）。知乎要登录(401)、36氪feed空、虎嗅超时，暂不加
37. ✅ **旧文章改第三人称**：31 篇的「저는/제가/직접 써보니/다녀와 보니」全部改写为客观指南语气（已验证 0 残留）
38. ✅ **prompt 加 H2 小标题 + 官方出处**：新文章带 2~4 个 `## H2 小标题`，涉及法规时附官方机构链接
39. 🔄 **待办**：Google 登录（表已预留 user_id）、评论审核后台、上广告、二级分类/标签、图片 alt 韩文化、变现（AdSense/联盟）、Kakao App Key（原生分享卡片）、知乎/36氪/虎嗅信息源（需解决反爬）

## UI 方向（用户明确要的）

- 用户要 **Yahoo 式「门户」布局**（反复强调不要 WordPress 博客味、不要纯文字列表）
- 已实现：**三栏门户布局**（左 widgets 300px + 主新闻流 + 右 widgets 300px），主新闻流 = 大头图头条(21:9) + 排名小卡片(4列) + 图文新闻流(240px图)，浅灰背景 #f0f3f5 + 白色卡片浮起
- 配色：科技蓝 #2563eb / 旅行绿 #10b981 / 电商橙 #f97316 / 社会紫 #8b5cf6（分类专属色，在 `app/composables/useCategories.js`）
- 响应式：窄屏自动变两栏/单栏，侧栏隐藏
- 注：Yahoo 真实 CSS 已抓取分析过（bg #f0f3f5、三栏 grid、feed 图 260px）

## 配图说明

- 已从 SVG 渐变占位图升级为 **Wikimedia Commons 真实照片**（30 张 jpg/png，免费、无需 key）
- 配图脚本：`fetch_images.py`（文件名 → 英文检索词 → 搜图 → 下载 → 更新 frontmatter，带 `--dry-run` 预览 + 429 重试限速）
- 旧 svg 仍留在 `public/images/` 但已无引用（可安全删除）
- 之后若嫌 Commons 图源不够精致，可换 Pexels/Unsplash 免费 API（需注册 key）

## 启动命令

```bash
# 前端 dev server（当前已在后台运行）
cd D:\Git\cn2kr\frontend && npm run dev   # → localhost:3000

# 生成更多内容
cd D:\Git\cn2kr\pipeline && python pipeline.py --category tech --count 10
# 分类：tech / travel / direct / society

# 查看 Hermes 频道配置
hermes config get discord.allowed_channels
```

## 用户偏好/雷区（重要）

- 极度反感：付费主题/订阅制、卖课/知识付费、"教人赚钱的课"
- 用户是开发者，只熟 Vue（不熟 React/Next）
- 讨厌被说"这不现实"，要"一定能做成"的前提
- 参考过 Morningstar Korea 那种干净专业的企业站风格
- 之前反复强调设计的重要性，别轻视 UI
