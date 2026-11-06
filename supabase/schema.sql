-- ============================================================
-- cn2kr 数据库 schema（点赞 + 评论）
-- 用法：登录 Supabase → SQL Editor → 粘贴本文件全部内容 → Run
-- ============================================================

-- ---------- 点赞表（一条点赞 = 一行，支持未来关联登录用户） ----------
create table if not exists public.likes (
  id bigint generated always as identity primary key,
  path text not null,
  client_id text,                          -- 匿名去重（未来登录后可用 user_id）
  user_id uuid references auth.users(id),  -- 预留：登录用户
  created_at timestamptz not null default now()
);
create index if not exists idx_likes_path on public.likes (path);

-- ---------- 评论表 ----------
create table if not exists public.comments (
  id bigint generated always as identity primary key,
  path text not null,
  author text not null default '익명',
  content text not null,
  user_id uuid references auth.users(id),  -- 预留：登录用户
  approved boolean not null default true,  -- 审核开关（默认放行）
  created_at timestamptz not null default now()
);
create index if not exists idx_comments_path on public.comments (path);
create index if not exists idx_comments_path_created on public.comments (path, created_at desc);

-- ============================================================
-- Row Level Security（关键：保护数据，只允许合法操作）
-- ============================================================
alter table public.likes enable row level security;
alter table public.comments enable row level security;

-- 任何人可读（点赞计数 / 评论展示，评论只显示已审核的）
create policy "likes_public_read"    on public.likes    for select using (true);
create policy "comments_public_read" on public.comments for select using (approved = true);

-- 匿名可插入（点赞 / 评论），但只能写自己的 user_id（匿名则为 null，防伪造）
create policy "likes_public_insert" on public.likes for insert
  with check (user_id is null or user_id = auth.uid());

create policy "comments_public_insert" on public.comments for insert
  with check (user_id is null or user_id = auth.uid());

-- 不创建 update/delete policy = 默认拒绝删改（安全）

-- ============================================================
-- 说明：
-- 1. 现在匿名即可点赞/评论（client_id 幂等去重由前端 localStorage 实现）
-- 2. 之后加 Google 登录：直接在 Supabase Auth 开启 Google provider，
--    登录后 user_id 自动填充，点赞/评论自然挂到用户账号上
-- 3. 想开审核：把 comments 的 approved 默认值改成 false + 建审核后台即可
-- ============================================================
