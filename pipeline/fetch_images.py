#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cn2kr 配图脚本：为内容自动配真实照片（Wikimedia Commons）。

逻辑：扫描 content/articles/ 下所有 .md，只要配图还是 .svg（说明是 pipeline 刚生成、
还没配真实照片的新文章），就用 DeepSeek 把标题翻译成英文检索词 → 搜图 → 下载 → 更新 frontmatter。
已经是 .jpg/.png 的文章自动跳过。

用法：
  python fetch_images.py --dry-run   # 只预览，不下载
  python fetch_images.py             # 真正下载
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

# 强制 UTF-8 输出（Windows 计划任务 cp949 环境会崩溃）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# repo 根目录（pipeline 的上一级），路径相对化以便本地/云端都能跑
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(REPO_ROOT, "frontend", "content", "articles")
IMAGE_DIR = os.path.join(REPO_ROOT, "frontend", "public", "images")
CONFIG_PATH = os.path.join(REPO_ROOT, "pipeline", "config.json")
UA = {"User-Agent": "cn2kr-image-fetcher/1.0 (personal project)"}

GOOD_MIME = {"image/jpeg", "image/png"}

# 分类兜底检索词（多个，逐个尝试；都用「和分类相关」的词）
CATEGORY_FALLBACK = {
    "중국 테크": ["China technology", "smartphone"],
    "중국 여행": ["Great Wall of China", "China travel"],
    "중국 직구": ["online shopping", "Taobao"],
    "중국사회": ["China", "Chinese culture"],
}

# 韩国语城市名 → 英文检索词（从标题提取城市，作为兜底；用「标志性景点」而非城市名，避免配到地铁图/铁路等无关图）
CITY_MAP = {
    "청두": "Chengdu panda", "충칭": "Chongqing skyline", "베이징": "Forbidden City", "상하이": "Shanghai skyline",
    "시안": "Terracotta Army", "항저우": "Hangzhou West Lake", "쑤저우": "Suzhou garden", "리장": "Lijiang old town",
    "다리": "Dali Yunnan", "하이난": "Hainan beach", "장가계": "Zhangjiajie", "구이린": "Guilin karst",
    "쿤밍": "Kunming", "윈난": "Yunnan", "광저우": "Guangzhou skyline", "선전": "Shenzhen skyline",
    "톈진": "Tianjin", "난징": "Nanjing", "우한": "Wuhan", "샤먼": "Xiamen Gulangyu",
    "칭다오": "Qingdao", "다롄": "Dalian", "하얼빈": "Harbin ice festival", "창사": "Changsha",
    "정저우": "Zhengzhou", "둥관": "Dongguan",
}


def extract_city(title):
    """从韩文标题里提取城市名，返回英文检索词（找不到返回 None）"""
    for ko, en in CITY_MAP.items():
        if ko in title:
            return en
    return None


def load_config():
    cfg = {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        pass

    # 环境变量优先（GitHub Actions 用 secret 注入）
    if os.environ.get("DEEPSEEK_API_KEY"):
        cfg["deepseek_api_key"] = os.environ["DEEPSEEK_API_KEY"]
    if os.environ.get("DEEPSEEK_BASE_URL"):
        cfg["deepseek_base_url"] = os.environ["DEEPSEEK_BASE_URL"]
    if os.environ.get("DEEPSEEK_MODEL"):
        cfg["model"] = os.environ["DEEPSEEK_MODEL"]

    cfg.setdefault("deepseek_base_url", "https://api.deepseek.com/v1")
    cfg.setdefault("model", "deepseek-chat")
    if not cfg.get("deepseek_api_key"):
        print("❌ 找不到 DeepSeek API key（需要 config.json 或 DEEPSEEK_API_KEY 环境变量）")
        sys.exit(1)
    return cfg


def call_deepseek(prompt):
    cfg = load_config()
    body = json.dumps({
        "model": cfg.get("model", "deepseek-chat"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }).encode("utf-8")
    url = cfg["deepseek_base_url"].rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + cfg["deepseek_api_key"],
    })
    resp = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
    return resp["choices"][0]["message"]["content"].strip()


def derive_query(title, category):
    """韩文标题 → 英文图片检索词（DeepSeek，失败则用分类兜底）"""
    prompt = (
        "下面是一篇韩文文章标题。请从中提取「具体的人/产品/地点/场景/物体」，翻译成 3~6 个英文单词的图片搜索词，"
        "要具体到能搜到和文章内容直接相关的照片（比如具体产品名、具体地名、具体场景），"
        "不要只给「online shopping」「China travel」这种泛泛的分类词。\n"
        "只输出搜索词本身，不要解释、不要标点、不要引号。\n\n"
        f"标题：{title}\n分类：{category}\n\n搜索词："
    )
    try:
        q = call_deepseek(prompt)
        q = q.strip().strip('"').strip("'").strip()
        if q and len(q) <= 60:
            return q
    except Exception as e:
        print(f"    [DeepSeek 翻译失败，尝试城市/分类兜底] {e}")
    # 先按标题提取城市（항저우→Hangzhou West Lake），提不到才用分类兜底
    city = extract_city(title)
    if city:
        return city
    fb = CATEGORY_FALLBACK.get(category, ["China"])
    return fb[0] if isinstance(fb, list) else fb


def wm_search(query, limit=6, retries=4):
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": 1280,
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise
    return {}


def pick_candidate(query, skip_titles=None):
    """返回 (thumb_url, title, mime, width) 或 None；跳过 skip_titles 里已用过的图"""
    skip = skip_titles or set()
    try:
        data = wm_search(query)
    except Exception as e:
        print(f"    [SEARCH ERROR] {e}")
        return None
    pages = (data.get("query") or {}).get("pages", {})
    if not pages:
        return None
    items = sorted(pages.values(), key=lambda p: p.get("index", 99))
    for p in items:
        title = p.get("title", "")
        if title in skip:
            continue
        ii = (p.get("imageinfo") or [{}])[0]
        mime = ii.get("mime", "")
        w = ii.get("width", 0)
        if mime in GOOD_MIME and w >= 800:
            thumb = ii.get("thumburl") or ii.get("url")
            return thumb, title, mime, w
    for p in items:
        title = p.get("title", "")
        if title in skip:
            continue
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime", "") in GOOD_MIME:
            thumb = ii.get("thumburl") or ii.get("url")
            return thumb, title, ii.get("mime", ""), ii.get("width", 0)
    return None


def simplify_query(query):
    """把查询词逐步缩短（去掉末尾词），返回简化版本列表"""
    words = query.split()
    return [" ".join(words[:i]) for i in range(len(words) - 1, 1, -1)]


def pick_with_fallback(query, cat, indent="   ", skip_titles=None, title=None):
    """多层兜底：完整词 → 城市标志景点 → 简化词 → 分类词 → 通用 China，尽量找到且不重复"""
    skip = skip_titles or set()
    cand = pick_candidate(query, skip)
    if cand:
        return cand
    # 优先用标题里的城市标志性景点（比简化泛词更精准，避免配到地铁图/铁路等无关图）
    city = extract_city(title or "")
    if city and city.lower() != query.lower():
        print(f"{indent}-> 城市标志景点: {city}")
        time.sleep(1.2)
        cand = pick_candidate(city, skip)
        if cand:
            return cand
    # 逐步简化查询词（去掉末尾的多余词，如 alley/cable car）
    for short in simplify_query(query):
        print(f"{indent}-> 简化查询: {short}")
        time.sleep(1.2)
        cand = pick_candidate(short, skip)
        if cand:
            return cand
    # 分类兜底
    for fb in CATEGORY_FALLBACK.get(cat, []):
        if fb.lower() != query.lower():
            print(f"{indent}-> 兜底词: {fb}")
            time.sleep(1.2)
            cand = pick_candidate(fb, skip)
            if cand:
                return cand
    # 最终 China
    if query.lower() != "china":
        print(f"{indent}-> 最终兜底: China")
        time.sleep(1.2)
        cand = pick_candidate("China", skip)
        if cand:
            return cand
    return None


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def process_inline_images(slug, body, cat, dry, used_titles=None, title=None):
    """把正文里的 [이미지: 검색어] 标记替换成真实照片，返回 (新正文, 成功数)"""
    used = used_titles if used_titles is not None else set()
    pattern = re.compile(r"\[이미지:\s*[^\]]+\]")
    markers = re.findall(r"\[이미지:\s*([^\]]+)\]", body)
    if not markers:
        return body, 0
    new_body = body
    ok = 0
    for i, marker in enumerate(markers):
        # 标记格式: "English query | Korean alt"（兼容只有 English 的旧格式）
        parts = [p.strip() for p in marker.split("|")]
        query = parts[0]
        alt = parts[1] if len(parts) > 1 and parts[1] else (title or "이미지")
        if not query:
            continue
        print(f"    [插图 {i + 1}] query: {query} / alt: {alt}")
        time.sleep(1.2)
        cand = pick_with_fallback(query, cat, indent="    ", skip_titles=used, title=title)
        if not cand:
            print("    -> 插图无匹配，跳过")
            continue
        thumb, wm_title, mime, w = cand
        used.add(wm_title)
        print(f"    -> {wm_title} ({mime}, {w}px)")
        if dry:
            ok += 1
            continue
        ext = ".jpg" if mime == "image/jpeg" else ".png"
        dest_name = f"{slug}-{i + 1}{ext}"
        dest = os.path.join(IMAGE_DIR, dest_name)
        try:
            nbytes = download(thumb, dest)
            new_body = pattern.sub(
                f"![{alt}](/images/{dest_name})", new_body, count=1
            )
            print(f"    ✅ 插图已下载 {nbytes // 1024}KB -> /images/{dest_name}")
            ok += 1
        except Exception as e:
            print(f"    [插图下载失败] {e}")
    return new_body, ok


def main():
    dry = "--dry-run" in sys.argv
    mode = "DRY-RUN (预览)" if dry else "DOWNLOAD (下载)"
    print(f"=== 配图脚本 {mode} ===\n")

    # 扫描所有 .md，找出配图还是 .svg 的
    todo = []
    for f in sorted(os.listdir(CONTENT_DIR)):
        if not f.endswith(".md"):
            continue
        md_path = os.path.join(CONTENT_DIR, f)
        with open(md_path, encoding="utf-8") as fh:
            txt = fh.read()
        m_img = re.search(r'image:\s*"([^"]+)"', txt)
        img = m_img.group(1) if m_img else ""
        if not img.lower().endswith(".svg"):
            continue
        m_title = re.search(r'title:\s*"([^"]+)"', txt)
        m_cat = re.search(r'category:\s*"([^"]+)"', txt)
        todo.append((
            f[:-3],
            m_title.group(1) if m_title else "",
            m_cat.group(1) if m_cat else "",
        ))

    if not todo:
        print("所有文章都已有真实配图，无需处理。")
        return

    print(f"待处理 {len(todo)} 篇（配图还是 SVG）\n")
    ok = fail = 0
    used = set()  # 全局已用图片标题（跨文章去重，避免不同文章配同一张图）
    for name, title, cat in todo:
        query = derive_query(title, cat)
        print(f"{name}\n  标题: {title[:40]}\n  query: {query}")
        time.sleep(2.5)  # 放慢节奏，避免 DeepSeek/Wikimedia 限流
        cand = pick_with_fallback(query, cat, skip_titles=used, title=title)
        if not cand:
            print("   -> 无匹配结果，保留 SVG ❌")
            fail += 1
            continue
        thumb, wm_title, mime, w = cand
        used.add(wm_title)
        print(f"   -> {wm_title} ({mime}, {w}px)")
        if dry:
            ok += 1
            continue
        ext = ".jpg" if mime == "image/jpeg" else ".png"
        dest = os.path.join(IMAGE_DIR, name + ext)
        try:
            nbytes = download(thumb, dest)
            md_path = os.path.join(CONTENT_DIR, name + ".md")
            with open(md_path, encoding="utf-8") as fh:
                txt = fh.read()
            new_img = f"/images/{name}{ext}"
            txt2, cnt = re.subn(
                r'image:\s*"/images/[^"]+"', f'image: "{new_img}"', txt
            )
            # 处理正文插图（[이미지: ...] 标记 → 真实照片），复用 used 去重
            txt3, inline_ok = process_inline_images(name, txt2, cat, dry, used, title)
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write(txt3)
            print(f"   ✅ 封面已下载 {nbytes // 1024}KB -> {new_img}")
            if inline_ok:
                print(f"   ✅ 正文插图 {inline_ok} 张")
            ok += 1
        except Exception as e:
            print(f"   [DOWNLOAD ERROR] {e}")
            fail += 1

    print(f"\n=== 完成: {ok} 成功 / {fail} 失败 ===")


if __name__ == "__main__":
    main()
