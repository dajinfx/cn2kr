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

CONTENT_DIR = "D:/Git/cn2kr/frontend/content/articles"
IMAGE_DIR = "D:/Git/cn2kr/frontend/public/images"
CONFIG_PATH = "D:/Git/cn2kr/pipeline/config.json"
UA = {"User-Agent": "cn2kr-image-fetcher/1.0 (personal project)"}

GOOD_MIME = {"image/jpeg", "image/png"}

# DeepSeek 失败时的分类兜底检索词
CATEGORY_FALLBACK = {
    "중국 테크": "China technology",
    "중국 여행": "China travel landmark",
    "중국 직구": "online shopping parcel",
}


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


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
        "把下面这个韩文文章标题翻译成一个简短的英文图片搜索关键词（3~6 个英文单词，"
        "适合在图片库搜相关照片）。只输出关键词本身，不要解释、不要标点、不要引号。\n\n"
        f"标题：{title}\n分类：{category}\n\n关键词："
    )
    try:
        q = call_deepseek(prompt)
        q = q.strip().strip('"').strip("'").strip()
        if q and len(q) <= 60:
            return q
    except Exception as e:
        print(f"    [DeepSeek 翻译失败，用分类兜底] {e}")
    return CATEGORY_FALLBACK.get(category, "China")


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


def pick_candidate(query):
    """返回 (thumb_url, title, mime, width) 或 None"""
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
        ii = (p.get("imageinfo") or [{}])[0]
        mime = ii.get("mime", "")
        w = ii.get("width", 0)
        if mime in GOOD_MIME and w >= 800:
            thumb = ii.get("thumburl") or ii.get("url")
            return thumb, p.get("title", ""), mime, w
    for p in items:
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime", "") in GOOD_MIME:
            thumb = ii.get("thumburl") or ii.get("url")
            return thumb, p.get("title", ""), ii.get("mime", ""), ii.get("width", 0)
    return None


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def process_inline_images(slug, body, cat, dry):
    """把正文里的 [이미지: 검색어] 标记替换成真实照片，返回 (新正文, 成功数)"""
    pattern = re.compile(r"\[이미지:\s*[^\]]+\]")
    markers = re.findall(r"\[이미지:\s*([^\]]+)\]", body)
    if not markers:
        return body, 0
    new_body = body
    ok = 0
    for i, query in enumerate(markers):
        query = query.strip()
        if not query:
            continue
        print(f"    [插图 {i + 1}] query: {query}")
        time.sleep(1.2)
        cand = pick_candidate(query)
        if not cand:
            fb = CATEGORY_FALLBACK.get(cat)
            if fb and fb != query:
                print(f"    -> 精确词无结果，兜底: {fb}")
                time.sleep(1.2)
                cand = pick_candidate(fb)
        if not cand:
            print("    -> 插图无匹配，跳过")
            continue
        thumb, wm_title, mime, w = cand
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
                f"![{query}](/images/{dest_name})", new_body, count=1
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
    for name, title, cat in todo:
        query = derive_query(title, cat)
        print(f"{name}\n  标题: {title[:40]}\n  query: {query}")
        time.sleep(1.2)  # Wikimedia 限速
        cand = pick_candidate(query)
        if not cand:
            fb = CATEGORY_FALLBACK.get(cat)
            if fb and fb != query:
                print(f"   -> 精确词无结果，用分类兜底词重试: {fb}")
                time.sleep(1.2)
                cand = pick_candidate(fb)
        if not cand:
            print("   -> 无匹配结果，保留 SVG ❌")
            fail += 1
            continue
        thumb, wm_title, mime, w = cand
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
            # 处理正文插图（[이미지: ...] 标记 → 真实照片）
            txt3, inline_ok = process_inline_images(name, txt2, cat, dry)
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
