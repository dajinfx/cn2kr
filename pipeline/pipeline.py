#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国一手信息 → 韩文加工内容 → Markdown + SVG 配图（供 Nuxt Content 读取）
零依赖（只用 Python 标准库）

用法：
  python pipeline.py --category tech --count 10     # 生成 10 篇科技类
  python pipeline.py --category travel --count 10   # 生成 10 篇旅行类
  python pipeline.py --category direct --count 10   # 生成 10 篇电商类
  python pipeline.py --dry-run                       # 只生成，不写文件
"""
import json
import re
import sys
import time
import random
import datetime
import argparse
import urllib.request
from pathlib import Path


# ---------------------------------------------------------------- 配置
def load_config():
    try:
        with open("config.json", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ 找不到 config.json")
        sys.exit(1)


CFG = None

# 分类映射
CATEGORY_NAMES = {
    "tech": "중국 테크",
    "travel": "중국 여행",
    "direct": "중국 직구",
}

# 分类专属配图渐变色
CATEGORY_COLORS = {
    "중국 테크": ["#1e3a8a", "#2563eb", "#0ea5e9"],
    "중국 여행": ["#064e3b", "#10b981", "#34d399"],
    "중국 직구": ["#7c2d12", "#f97316", "#fbbf24"],
}

# 分类写作方向
CATEGORY_GUIDE = {
    "중국 테크": "聚焦中国科技：AI、智能手机、电动汽车、芯片、机器人、新消费电子等。重点写韩国人关心的中国科技趋势、科技产品直购指南、技术避坑。",
    "중국 여행": "聚焦中国旅行：热门城市、景点、美食、交通、支付、签证。重点写韩国人去中国旅行的攻略、必去目的地、实用 tips、避坑（可结合你自己的中国旅行知识，不必局限于下面的信息条目）。",
    "중국 직구": "聚焦中国电商/海淘：淘宝、1688、拼多多、Temu、AliExpress。重点写韩国人怎么买、省钱技巧、避坑、好物推荐、跨境支付物流。",
}

# 每篇随机切入角度，避免标题/内容重复
CATEGORY_ANGLES = {
    "중국 테크": [
        "AI 工具与软件", "智能手机新品", "电动汽车", "机器人/无人机",
        "芯片与半导体", "智能家居家电", "可穿戴设备", "中国科技巨头动态",
        "AI 生图/生视频工具", "国产操作系统与生态",
    ],
    "중국 여행": [
        "上海", "北京", "成都/重庆", "西安", "杭州/苏州",
        "云南(大理/丽江)", "海南", "美食小吃攻略", "支付与通讯准备", "交通与高铁出行",
    ],
    "중국 직구": [
        "1688 进货/批发", "Temu 省钱攻略", "AliExpress 避坑", "淘宝/天猫直购",
        "物流与关税", "支付与退款", "真假辨别", "优惠券与促销节奏", "特定品类好物(数码)", "特定品类好物(家居)",
    ],
}


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept": "*/*",
    })
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")


# ---------------------------------------------------------------- 1. 信息源
def fetch_baidu_hot(limit=15):
    url = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
    data = json.loads(_get(url))
    def _walk(node):
        words = []
        if isinstance(node, dict):
            if isinstance(node.get("word"), str) and node["word"].strip():
                words.append(node["word"].strip())
            for v in node.values():
                words += _walk(v)
        elif isinstance(node, list):
            for v in node:
                words += _walk(v)
        return words
    words = _walk(data.get("data", {}).get("cards", []))
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:limit]


def fetch_toutiao_hot(limit=15):
    url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    data = json.loads(_get(url))
    return [d["Title"] for d in data.get("data", [])][:limit]


def fetch_smzdm_rss(limit=10):
    url = "https://post.smzdm.com/feed/"
    raw = _get(url)
    items = re.findall(r"<item>(.*?)</item>", raw, re.S)
    out = []
    for it in items[:limit]:
        m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
        if m:
            out.append(m.group(1).strip())
    return out


def collect_items():
    items = []
    src = CFG.get("sources", {})
    if src.get("baidu_hot", True):
        try:
            items += fetch_baidu_hot()
            print("✅ 百度热搜", end="  ")
        except Exception as e:
            print(f"⚠️ 百度热搜失败", end="  ")
    if src.get("toutiao_hot", True):
        try:
            items += fetch_toutiao_hot()
            print("✅ 今日头条", end="  ")
        except Exception as e:
            print(f"⚠️ 今日头条失败", end="  ")
    if src.get("smzdm_rss", True):
        try:
            items += fetch_smzdm_rss()
            print("✅ 什么值得买", end="  ")
        except Exception as e:
            print(f"⚠️ 什么值得买失败", end="  ")
    return items


# ---------------------------------------------------------------- 2. LLM 加工
PROMPT = """你是资深韩国海淘/科技/旅行内容编辑。下面是一些「中国当下热门/值得买」的中文信息条目。

请把它们加工成一篇给韩国读者看的韩文文章。

【本篇文章的分类方向】{category}
{guide}

【本篇具体切入角度】{angle}（务必围绕这个角度展开，不要泛泛而谈，避免和其他文章重复）

要求：
1. 不是死翻译，而是「翻译+解读+本土化」：把中国人视角的信息，转成韩国人关心、能省钱、能避坑、能照着做/照着买的内容
2. 标题必须具体点出本篇的切入角度（例：角度是"1688进货"就写"1688 공장가 직구 완벽 가이드"；角度是"上海"就写"상하이 3박4일 여행 코스"）。严禁使用"총정리/완전정복/가이드/정리"这类空泛的词作为标题主干
3. 结构：开头钩子 → 3~5 个要点（每个写清：是什么 / 为什么火 / 韩国人怎么买或怎么用 / 注意什么坑）→ 结尾一句行动号召
4. 语气像真人博主，自然、有信息量，不要机器腔，不要用"大家好/오늘은"这类套话开头
5. 与分类方向无关的条目，直接跳过不写
6. 标题和正文中如需写年份，一律用当前年份（{year}年），严禁写旧年份
7. 正文 500~900 字左右，信息密度要高，不要注水
8. 只输出下面这个格式，不要解释你在做什么、不要加多余说明：

제목: [韩文标题]
설명: [一句话摘要，30字以内]
[韩文正文]"""


def call_deepseek(prompt):
    body = json.dumps({
        "model": CFG.get("model", "deepseek-chat"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }).encode("utf-8")
    url = CFG["deepseek_base_url"].rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + CFG["deepseek_api_key"],
    })
    resp = json.loads(urllib.request.urlopen(req, timeout=180).read().decode("utf-8"))
    return resp["choices"][0]["message"]["content"]


def generate(items, category):
    year = datetime.datetime.now().year
    angle = random.choice(CATEGORY_ANGLES[category])
    prompt = PROMPT.format(
        category=category,
        guide=CATEGORY_GUIDE[category],
        angle=angle,
        year=year,
    ) + "\n\n中文信息条目：\n" + "\n".join(f"- {i}" for i in items)
    raw = call_deepseek(prompt)

    def grab(field):
        m = re.search(rf"{field}\s*[:：]\s*(.+)", raw)
        return m.group(1).strip() if m else None

    title = grab("제목") or f"{category} 트렌드"
    desc = grab("설명") or ""

    content = raw
    for field in ("제목", "설명"):
        content = re.sub(rf"^{field}\s*[:：].*\n?", "", content, count=1, flags=re.M)
    content = content.strip()

    return {"title": title, "category": category, "description": desc, "content": content}


# ---------------------------------------------------------------- 3. 配图（SVG 渐变）
def generate_svg(category, slug, image_dir):
    colors = CATEGORY_COLORS.get(category, ["#1e3a8a", "#2563eb"])
    c1, c2, c3 = colors
    svg = f'''<svg width="800" height="450" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="50%" stop-color="{c2}"/>
      <stop offset="100%" stop-color="{c3}"/>
    </linearGradient>
  </defs>
  <rect width="800" height="450" fill="url(#g)"/>
  <circle cx="690" cy="70" r="160" fill="rgba(255,255,255,0.07)"/>
  <circle cx="70" cy="400" r="120" fill="rgba(255,255,255,0.05)"/>
  <circle cx="400" cy="-60" r="180" fill="rgba(255,255,255,0.04)"/>
  <text x="400" y="212" font-family="'Noto Sans KR', sans-serif" font-size="34" font-weight="700" fill="#ffffff" text-anchor="middle">{category}</text>
  <text x="400" y="258" font-family="sans-serif" font-size="16" fill="rgba(255,255,255,0.7)" text-anchor="middle">cn2kr</text>
</svg>'''
    path = image_dir / f"{slug}.svg"
    path.write_text(svg, encoding="utf-8")
    return f"/images/{slug}.svg"


# ---------------------------------------------------------------- 4. 存 Markdown
def slugify():
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return f"article-{ts}"


def save_markdown(article, image_url, slug):
    out_dir = Path(CFG.get("output_dir", "content/articles"))
    out_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.date.today().isoformat()

    md = f"""---
title: "{article['title']}"
category: "{article['category']}"
description: "{article['description']}"
date: {date}
image: "{image_url}"
---

{article['content']}
"""
    path = out_dir / f"{slug}.md"
    path.write_text(md, encoding="utf-8")
    return path


# ---------------------------------------------------------------- main
def main():
    global CFG
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="direct", choices=["tech", "travel", "direct"], help="分类")
    ap.add_argument("--count", type=int, default=1, help="生成几篇")
    ap.add_argument("--dry-run", action="store_true", help="只生成不写文件")
    args = ap.parse_args()

    CFG = load_config()
    category = CATEGORY_NAMES[args.category]
    image_dir = Path(CFG.get("image_dir", "public/images"))
    image_dir.mkdir(parents=True, exist_ok=True)

    for i in range(args.count):
        print(f"\n===== [{category}] 第 {i+1}/{args.count} 篇 =====")
        items = collect_items()
        if not items:
            print("❌ 什么都没抓到")
            return
        print(f"共 {len(items)} 条")

        article = generate(items, category)
        print(f"标题：{article['title']}")
        print(f"摘要：{article['description']}")

        if args.dry_run:
            print(article["content"][:250] + "...")
            continue

        slug = slugify()
        image_url = generate_svg(category, slug, image_dir)
        path = save_markdown(article, image_url, slug)
        print(f"✅ 已保存：{path}")
        print(f"✅ 配图：{image_url}")

        if i < args.count - 1:
            time.sleep(2)


if __name__ == "__main__":
    main()
