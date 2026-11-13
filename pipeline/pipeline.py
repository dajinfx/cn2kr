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
import os
import re
import sys
import time
import random
import datetime
import argparse
import urllib.request
from pathlib import Path

# 强制 UTF-8 输出（Windows 计划任务 cp949 环境会崩溃）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# repo 根目录（pipeline 的上一级）
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT_DIR = os.path.join(REPO_ROOT, "frontend", "content", "articles")
DEFAULT_IMAGE_DIR = os.path.join(REPO_ROOT, "frontend", "public", "images")


# ---------------------------------------------------------------- 配置
def load_config():
    cfg = {}
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"), encoding="utf-8") as f:
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
    cfg.setdefault("output_dir", DEFAULT_OUTPUT_DIR)
    cfg.setdefault("image_dir", DEFAULT_IMAGE_DIR)
    cfg.setdefault("sources", {"baidu_hot": True, "toutiao_hot": True, "smzdm_rss": True})

    if not cfg.get("deepseek_api_key"):
        print("❌ 找不到 DeepSeek API key（需要 config.json 或 DEEPSEEK_API_KEY 环境变量）")
        sys.exit(1)
    return cfg


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

# 高频搜索关键词（韩国人实际会搜的词，让标题/正文自然命中）
KEYWORDS = {
    "중국 테크": [
        "중국 스마트폰 직구", "화웨이", "샤오미", "중국 전기차",
        "중국 AI", "딥시크", "중국 반도체", "중국 로봇청소기",
    ],
    "중국 여행": [
        "중국 여행", "상하이 여행", "베이징 여행", "장가계 여행",
        "중국 여행 준비", "중국 여행 비자", "중국 고속철", "알리페이 등록",
    ],
    "중국 직구": [
        "중국 직구", "타오바오 직구", "알리익스프레스", "테무",
        "1688 직구", "배송대행", "직구 관세", "직구 가품",
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
PROMPT = """당신은 중국 테크·여행·직구 정보를 다루는 전문 에디터다. 아래의 중국 실시간 인기 정보를 보고, 한국 독자에게 진짜 도움 되는 글 한 편을 써라.

【분야】{category}
【이번 글의 소재】{angle}（이 소재를 중심으로, 다른 글과 겹치지 않게）
{guide}

[글쓰기 스타일 — 가장 중요하다]
- 객관적인 정보 가이드처럼 써라. '저는/제가/제 생각' 같은 1인칭 체험담으로 쓰지 말고, 사실과 정보를 차분히 정리·설명하는 톤으로 써라.
- **반드시 존댓말로 써라. 합니다체('-ㅂ니다' / '-습니다') 또는 해요체('-요')로 문장을 끝내라. 반말(해체)은 절대 금지.**
- 구조를 틀에 억지로 맞추지 마라. 어떤 글은 소제목 2개, 어떤 글은 그냥 줄글로 흐르게. 모든 글을 "1. 2. 3." 목록으로 쪼개지 마라.
- 구체적인 숫자·가격·앱 이름·예시를 넣어라. 추상적인 조언만 나열하지 마라.
- 문장 길이를 들쭉날쭉하게. 짧게 끊는 문장과 길게 풀어쓰는 문장을 섞어라.
- 차분하고 정보 밀도는 높게. 과장·호들갑·이모티콘 금지. 번역투 금지.

[절대 쓰지 말 것]
"~에 대해 알아보자", "~를 소개한다", "~를 정리했다", "총정리", "완전정복", "꿀팁", "안녕하세요", "오늘은", "마지막으로", "결론적으로", "~할 수 있습니다" 반복 사용.
"저는", "제가", "제 생각", "직접 써보니", "직접 겪어보니" 같은 1인칭 체험담 표현은 절대 금지. 객관적인 설명 톤만 사용.
문장 끝의 반말(해체) 종결 '-다', '-어', '-냐', '-니', '-자', '-지'(반말), '-는데'는 절대 금지. 존댓말('-ㅂ니다' 또는 '-요')로만 끝내라.

[기타 규칙]
- 분야와 무관한 정보는 버려라.
- 연도는 반드시 올해({year}년)로 써라. 옛 연도 금지.
- 아래 검색 키워드 중 1~2개를 제목이나 본문에 자연스럽게 포함시켜라(억지로 나열하지 말 것): {keywords}
- 글 길이는 고정하지 마라. 주제에 따라 300자부터 2000자까지 자연스럽게 써라. 내용이 끝나면 바로 끝내고, 억지로 채우거나 자르지 마라. 글마다 길이가 제각각이어야 자연스럽다.
- 본문 중간, 이미지가 자연스러운 위치(예: 특정 상품·장소·음식·기기를 설명하는 문단 뒤)에 "[이미지: 영문 검색어 | 한글 설명]" 표시를 넣어라. 영문 검색어는 **해당 문단에서 실제로 다루는 구체적인 제품/장소/물건/화면**의 영문명으로(예: "Temu coupon page", "1688 order tracking screen"). "online shopping" 같은 뭉뚱그린 분류어는 금지. 한글은 이미지 대체텍스트(alt)용. 개수는 주제와 글 길이에 따라 자연스럽게(짧은 글은 0~1개, 긴 글은 3~4개).

[출력 형식 — 이것만 출력]
제목: [구체적이고 클릭하고 싶은 제목]
설명: [한 줄 요약, 30자 이내]
슬러그: [영문 키워드 슬러그, 소문자+하이픈만, 3~6단어, 예: china-high-speed-rail-guide]
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
    kw_list = KEYWORDS.get(category, [])
    keywords = "、".join(random.sample(kw_list, min(4, len(kw_list))))
    prompt = PROMPT.format(
        category=category,
        guide=CATEGORY_GUIDE[category],
        angle=angle,
        year=year,
        keywords=keywords,
    ) + "\n\n中文信息条目：\n" + "\n".join(f"- {i}" for i in items)
    raw = call_deepseek(prompt)

    def grab(field):
        m = re.search(rf"{field}\s*[:：]\s*(.+)", raw)
        return m.group(1).strip() if m else None

    title = grab("제목") or f"{category} 트렌드"
    desc = grab("설명") or ""
    slug = grab("슬러그") or ""

    content = raw
    for field in ("제목", "설명", "슬러그"):
        content = re.sub(rf"^{field}\s*[:：].*\n?", "", content, count=1, flags=re.M)
    content = content.strip()

    return {"title": title, "category": category, "description": desc, "content": content, "slug": slug}


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
def make_slug(raw_slug):
    """把 DeepSeek 生成的英文关键词 slug 规范化；失败则回退时间戳"""
    s = (raw_slug or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        s = f"article-{ts}"
    return s[:60]


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

        slug = make_slug(article.get("slug"))
        image_url = generate_svg(category, slug, image_dir)
        path = save_markdown(article, image_url, slug)
        print(f"✅ slug：{slug}")
        print(f"✅ 已保存：{path}")
        print(f"✅ 配图：{image_url}")

        if i < args.count - 1:
            time.sleep(2)


if __name__ == "__main__":
    main()
