#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性迁移：给现有文章生成英文关键词 slug，重命名 .md + 图片 + 更新引用"""
import json
import os
import re
import glob
import time
import urllib.request

CONTENT_DIR = "D:/Git/cn2kr/frontend/content/articles"
IMAGE_DIR = "D:/Git/cn2kr/frontend/public/images"
CONFIG_PATH = "D:/Git/cn2kr/pipeline/config.json"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def call_deepseek(prompt):
    cfg = load_config()
    body = json.dumps({
        "model": cfg.get("model", "deepseek-chat"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }).encode("utf-8")
    url = cfg["deepseek_base_url"].rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + cfg["deepseek_api_key"],
    })
    resp = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
    return resp["choices"][0]["message"]["content"].strip()


def sanitize(s):
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:60]


def gen_slug(title):
    prompt = (
        "把下面这个韩文标题翻译成一个简短的英文关键词 slug（小写字母+连字符，3~6个单词）。"
        "只输出 slug 本身，不要解释。\n\n"
        f"标题：{title}\n\nslug:"
    )
    try:
        return sanitize(call_deepseek(prompt))
    except Exception as e:
        print(f"    [DeepSeek 失败] {e}")
        return ""


def main():
    md_files = sorted(glob.glob(os.path.join(CONTENT_DIR, "*.md")))
    print(f"共 {len(md_files)} 篇文章\n")

    # 已存在的 slug（避免冲突）
    existing = set(os.path.basename(f)[:-3] for f in md_files)

    mapping = {}
    for f in md_files:
        old_slug = os.path.basename(f)[:-3]
        if not old_slug.startswith("article-"):
            print(f"[跳过] {old_slug}（已是关键词 slug）")
            continue
        txt = open(f, encoding="utf-8").read()
        m = re.search(r'title:\s*"([^"]+)"', txt)
        title = m.group(1) if m else old_slug
        new_slug = gen_slug(title)
        if not new_slug or new_slug in existing:
            new_slug = f"article-{old_slug[-14:]}"  # 冲突/失败时保留时间戳兜底
        print(f"{old_slug}\n  -> {new_slug}")
        mapping[old_slug] = new_slug
        existing.add(new_slug)
        time.sleep(0.4)

    if not mapping:
        print("\n无需迁移")
        return

    print(f"\n=== 开始重命名 {len(mapping)} 篇 ===")
    for old_slug, new_slug in mapping.items():
        # 1. 重命名 .md 并更新内容引用
        old_md = os.path.join(CONTENT_DIR, old_slug + ".md")
        new_md = os.path.join(CONTENT_DIR, new_slug + ".md")
        txt = open(old_md, encoding="utf-8").read()
        txt = txt.replace(f"/images/{old_slug}", f"/images/{new_slug}")
        os.rename(old_md, new_md)
        open(new_md, "w", encoding="utf-8").write(txt)
        # 2. 重命名图片（保留后缀，如 -1.jpg）
        for img in glob.glob(os.path.join(IMAGE_DIR, old_slug + "*")):
            base = os.path.basename(img)
            suffix = base[len(old_slug):]
            os.rename(img, os.path.join(IMAGE_DIR, new_slug + suffix))
        print(f"✅ {old_slug} -> {new_slug}")

    print("\n=== 迁移完成 ===")


if __name__ == "__main__":
    main()
