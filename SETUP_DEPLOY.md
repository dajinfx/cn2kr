# cn2kr 部署指南（Supabase + Cloudflare Pages）

目标架构：**静态站点 + Supabase（数据库/未来 Google 登录）**，$0 托管，韩国访问走首尔 CDN。

```
文章(Markdown) → nuxt generate → 静态 HTML → Cloudflare Pages（无限免费）
浏览器 → 直连 Supabase（点赞 / 评论 / 未来 Google 登录）
```

---

## 一、Supabase（数据库 + 未来登录）

### 1. 建项目
1. 打开 https://supabase.com → Sign up（可用 GitHub 登录）
2. New Project → 起个名字（如 `cn2kr`）→ 设数据库密码 → 选 **ap-northeast-1（东京）** 或 **ap-northeast-2（首尔）** 区域
3. 等 1~2 分钟项目初始化完成

### 2. 建表（执行 schema）
1. 左侧 **SQL Editor** → New query
2. 把 `D:\Git\cn2kr\supabase\schema.sql` 的**全部内容**粘贴进去
3. 点 **Run**

> 这一步会创建 `likes`、`comments` 两张表 + 开启 RLS（行级安全）。

### 3. 拿 key
1. **Project Settings → API**
2. 复制两个值：
   - **Project URL**（形如 `https://xxxx.supabase.co`）
   - **anon public** key（以 `eyJ...` 开头的长字符串）

---

## 二、本地运行（可选）

```bash
cd D:\Git\cn2kr\frontend
# 复制 .env.example 成 .env，填入上面拿到的两个值
npm run dev
```

> 不填 key 也能跑（点赞/评论会静默降级为不可用），但填了才能测完整功能。

---

## 三、Cloudflare Pages（托管）

### 方式 A：Git 集成（推荐，自动部署）

1. 把 `cn2kr-frontend` 推到 GitHub（Cloudflare 也能连 GitLab）：
   ```bash
   cd D:\Git\cn2kr\frontend
   git init
   git add .
   git commit -m "cn2kr initial"
   # 在 GitHub 建仓库后：
   git remote add origin https://github.com/你的用户名/cn2kr-frontend.git
   git push -u origin main
   ```
2. 打开 https://dash.cloudflare.com → **Workers & Pages** → Create → **Pages** → **Connect to Git** → 选仓库
3. 构建配置：
   - **Framework preset**: `Nuxt.js`
   - **Build command**: `npm run generate`
   - **Build output directory**: `.output/public`
4. 环境变量（**Settings → Environment variables**，添加两个）：
   - `NUXT_PUBLIC_SUPABASE_URL` = 你的 Project URL
   - `NUXT_PUBLIC_SUPABASE_ANON_KEY` = 你的 anon key
5. Save & Deploy → 等构建完成

### 方式 B：直接上传（不用 Git）

```bash
cd D:\Git\cn2kr\frontend
# 构建时带上 Supabase key
export NUXT_PUBLIC_SUPABASE_URL="https://xxxx.supabase.co"
export NUXT_PUBLIC_SUPABASE_ANON_KEY="eyJ..."
npm run generate
npx wrangler pages deploy dist
```

---

## 四、绑定域名 cn2kr.net

1. Cloudflare 后台：**Add a site** → 输入 `cn2kr.net` → 选 Free 计划
2. 它会给你两个 Cloudflare 的 nameserver（如 `xxx.ns.cloudflare.com`）
3. 去你买域名的注册商（或 Cloudflare 自己）把 nameserver 改成这两个
4. 等 DNS 生效（几分钟到几小时）
5. 回到 Pages 项目 → **Custom domains** → 添加 `cn2kr.net`（和 `www.cn2kr.net`）
6. Cloudflare 自动签发 SSL 证书

---

## 五、以后加 Google 登录（已预留）

代码和表结构都预留了 `user_id` 字段。到时候只需：

1. Supabase 后台 → **Authentication → Providers** → 开启 **Google**（填 OAuth client id/secret）
2. 前端加登录按钮（`supabase.auth.signInWithOAuth({ provider: 'google' })`）
3. 点赞/评论自动从 `client_id` 升级成 `user_id`（表结构不用改）

---

## 常见问题

- **点赞/评论没反应**：检查 Cloudflare Pages 环境变量是否填对，以及 Supabase SQL Editor 里是否已执行 `schema.sql`
- **构建失败**：确认 build command 是 `npm run generate`，output 是 `.output/public`（`dist` 是指向它的符号链接，两者等价）
- **改文章不生效**：静态站需要重新构建部署（push 到 git 自动触发，或手动 Redeploy）
