#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cn2kr 配图升级：把渐变 SVG 占位图换成 Wikimedia Commons 的真实照片。

用法：
  python fetch_images.py --dry-run     # 只预览匹配结果，不下载
  python fetch_images.py               # 真正下载并更新 frontmatter
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

CONTENT_DIR = "D:/Application/cn2kr-frontend/content/articles"
IMAGE_DIR = "D:/Application/cn2kr-frontend/public/images"
UA = {"User-Agent": "cn2kr-image-fetcher/1.0 (personal project)"}

# 文件名 -> 英文检索词（Wikimedia Commons 检索）
QUERIES = {
    "article-20261106-065727-340298": "Huawei smartphone",
    "article-20261106-065740-530947": "smartphone display",
    "article-20261106-065754-229467": "semiconductor wafer",
    "article-20261106-065805-938459": "smartphone in hand",
    "article-20261106-065819-492160": "electric car",
    "article-20261106-065830-969665": "video editing",
    "article-20261106-065844-129229": "data center",
    "article-20261106-065856-994124": "mobile phone closeup",
    "article-20261106-065908-499215": "smartwatch",
    "article-20261106-065922-113140": "computer chip",
    "article-20261106-065935-350281": "China high-speed railway",
    "article-20261106-065951-056516": "Beijing Forbidden City",
    "article-20261106-070005-378439": "Chongqing skyline",
    "article-20261106-070021-082128": "Chinese street food",
    "article-20261106-070037-696982": "Hangzhou West Lake",
    "article-20261106-070050-674269": "hot pot",
    "article-20261106-070102-506460": "Chinese dumplings",
    "article-20261106-070115-180464": "Lijiang old town",
    "article-20261106-070128-703384": "QR code mobile payment",
    "article-20261106-070143-423482": "Terracotta Army",
    "article-20261106-070153-048792": "online shopping",
    "article-20261106-070205-129682": "luxury handbag",
    "article-20261106-070216-184573": "sneakers",
    "article-20261106-070227-939940": "credit card payment",
    "article-20261106-070241-986671": "parcel",
    "article-20261106-070255-514302": "container port",
    "article-20261106-070309-995903": "container ship",
    "article-20261106-070324-234816": "logistics warehouse",
    "article-20261106-070337-363166": "shipping boxes",
    "article-20261106-070350-684594": "factory manufacturing",
}

GOOD_MIME = {"image/jpeg", "image/png"}


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
                wait = 3 * (attempt + 1)
                time.sleep(wait)
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
    # 按 index 排序，优先 jpeg/png 且宽度足够的
    items = sorted(pages.values(), key=lambda p: p.get("index", 99))
    for p in items:
        ii = (p.get("imageinfo") or [{}])[0]
        mime = ii.get("mime", "")
        w = ii.get("width", 0)
        if mime in GOOD_MIME and w >= 800:
            thumb = ii.get("thumburl") or ii.get("url")
            return thumb, p.get("title", ""), mime, w
    # 放宽：只要 jpeg/png，不管尺寸
    for p in items:
        ii = (p.get("imageinfo") or [{}])[0]
        mime = ii.get("mime", "")
        if mime in GOOD_MIME:
            thumb = ii.get("thumburl") or ii.get("url")
            return thumb, p.get("title", ""), mime, ii.get("width", 0)
    return None


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def main():
    dry = "--dry-run" in sys.argv
    mode = "DRY-RUN (预览)" if dry else "DOWNLOAD (下载)"
    print(f"=== {mode} ===\n")
    ok = fail = 0
    for name in sorted(QUERIES):
        query = QUERIES[name]
        md_path = os.path.join(CONTENT_DIR, name + ".md")
        if not os.path.exists(md_path):
            print(f"[MISSING MD] {name}")
            continue
        print(f"{name}\n   query: {query}")
        time.sleep(1.2)  # Wikimedia 限速：每个搜索请求间隔
        cand = pick_candidate(query)
        if not cand:
            print("   -> 无匹配结果 ❌")
            fail += 1
            continue
        thumb, title, mime, w = cand
        print(f"   -> {title} ({mime}, {w}px)")
        if dry:
            ok += 1
            continue
        # 下载
        ext = ".jpg" if mime == "image/jpeg" else ".png"
        dest = os.path.join(IMAGE_DIR, name + ext)
        try:
            nbytes = download(thumb, dest)
            # 更新 frontmatter
            with open(md_path, encoding="utf-8") as f:
                txt = f.read()
            new_img = f"/images/{name}{ext}"
            txt2, cnt = re.subn(
                r'image:\s*"/images/[^"]+"', f'image: "{new_img}"', txt
            )
            if cnt == 0:
                print(f"   ⚠ frontmatter image 未替换成功")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(txt2)
            print(f"   ✅ 已下载 {nbytes//1024}KB -> {new_img}")
            ok += 1
        except Exception as e:
            print(f"   [DOWNLOAD ERROR] {e}")
            fail += 1
        time.sleep(0.3)  # 礼貌限速

    print(f"\n=== 完成: {ok} 成功 / {fail} 失败 ===")


if __name__ == "__main__":
    main()
