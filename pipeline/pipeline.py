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
    "중국 테크": "중국 테크에 집중: AI, 스마트폰, 전기차, 반도체, 로봇, 신가전 등. 한국인이 관심 가질 중국 테크 트렌드, 직구 가이드, 피해야 할 함정을 다뤄라.",
    "중국 여행": "중국 여행에 집중: 인기 도시, 명소, 음식, 교통, 결제, 비자. 한국인의 중국 여행 코스, 꼭 가볼 곳, 실전 팁, 피해야 할 것.",
    "중국 직구": "중국 직구/해외직구에 집중: 타오바오, 1688, 핀둬둬, 테무, 알리익스프레스. 한국인이 어떻게 사는지, 돈 아끼는 법, 함정 피하기, 추천 상품, 결제·배송.",
}

# 每篇随机切入角度，避免标题/内容重复
CATEGORY_ANGLES = {
    "중국 테크": [
        "AI 도구와 소프트웨어", "스마트폰 신제품", "전기차", "로봇/드론",
        "반도체와 칩", "스마트홈 가전", "웨어러블", "중국 테크 기업 동향",
        "AI 이미지/영상 생성 도구", "중국 OS와 생태계",
    ],
    "중국 여행": [
        "상하이", "베이징", "청두/충칭", "시안", "항저우/쑤저우",
        "윈난(다리/리장)", "하이난", "먹거리/맛집", "결제·통신 준비", "교통·고속철",
    ],
    "중국 직구": [
        "1688 도매", "테무 돈 아끼기", "알리익스프레스 함정", "타오바오/티몰 직구",
        "배송·관세", "결제·환불", "가품 구별", "할인·프로모션 타이밍", "디지털 추천템", "홈/생활 추천템",
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
PROMPT = """당신은 중국 직구·여행·테크를 직접 경험해본 한국인 블로거다. 아래의 중국 실시간 인기 정보를 보고, 한국 독자에게 진짜 도움 되는 글 한 편을 써라.

【분야】{category}
【이번 글의 소재】{angle}（이 소재를 중심으로, 다른 글과 겹치지 않게）
{guide}

[글쓰기 스타일 — 가장 중요하다]
- 사람이 실제로 겪고 쓴 글처럼 써라. 1인칭(저는/제가)으로, 내 생각과 경험을 자연스럽게 섞어라.
- **반드시 합니다체(존댓말)로 써라. 모든 문장을 '-ㅂ니다' / '-습니다'로 끝내라. '-요'로 끝나는 문장과 반말은 절대 금지. 문장 끝에 '-요', '-다', '-어'가 나오면 안 된다.**
- 구조를 틀에 억지로 맞추지 마라. 어떤 글은 소제목 2개, 어떤 글은 그냥 줄글로 흐르게. 모든 글을 "1. 2. 3." 목록으로 쪼개지 마라.
- 구체적인 숫자·가격·앱 이름·실제 사례를 넣어라. 추상적인 조언만 나열하지 마라.
- 문장 길이를 들쭉날쭉하게. 짧게 끊는 문장과 길게 풀어쓰는 문장을 섞어라.
- 차분하고 정보 밀도는 높게. 과장·호들갑·이모티콘 금지. 번역투 금지.

[절대 쓰지 말 것]
"~에 대해 알아보자", "~를 소개한다", "~를 정리했다", "총정리", "완전정복", "꿀팁", "안녕하세요", "오늘은", "마지막으로", "결론적으로", "~할 수 있습니다" 반복 사용.
문장 끝의 '-요', '-더군요', '-네요', '-죠', '-거든요', '-는데' 같은 해요체/구어체 종결은 절대 금지. 모든 종결은 '-ㅂ니다' / '-습니다'뿐이다.

[기타 규칙]
- 분야와 무관한 정보는 버려라.
- 연도는 반드시 올해({year}년)로 써라. 옛 연도 금지.
- 본문 500~900자, 정보 밀도 높게.

[출력 형식 — 이것만 출력]
제목: [구체적이고 클릭하고 싶은 제목]
설명: [한 줄 요약, 30자 이내]
[본문]

참고할 중국 실시간 정보:"""


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
