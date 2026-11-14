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
    cfg.setdefault("sources", {"baidu_hot": True, "toutiao_hot": True, "smzdm_rss": True, "jianshu": True, "sspai": True})

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
    "society": "중국사회",
}

# 分类专属配图渐变色
CATEGORY_COLORS = {
    "중국 테크": ["#1e3a8a", "#2563eb", "#0ea5e9"],
    "중국 여행": ["#064e3b", "#10b981", "#34d399"],
    "중국 직구": ["#7c2d12", "#f97316", "#fbbf24"],
    "중국사회": ["#4c1d95", "#8b5cf6", "#c4b5fd"],
}

# 分类写作方向
CATEGORY_GUIDE = {
    "중국 테크": "중국 테크에 집중: AI, 스마트폰, 전기차, 반도체, 로봇, 신가전 등. 한국인이 관심 가질 중국 테크 트렌드, 직구 가이드, 피해야 할 함정을 다뤄라.",
    "중국 여행": "중국 여행에 집중: 인기 도시, 명소, 음식, 교통, 결제, 비자. 한국인의 중국 여행 코스, 꼭 가볼 곳, 실전 팁, 피해야 할 것.",
    "중국 직구": "중국 직구/해외직구에 집중: 타오바오, 1688, 핀둬둬, 테무, 알리익스프레스. 한국인이 어떻게 사는지, 돈 아끼는 법, 함정 피하기, 추천 상품, 결제·배송.",
    "중국사회": "중국의 사회·문화·생활·경제·법률·교육·취미 등 일상과 사회 이슈에 집중. 한국인이 궁금해할 중국의 생활상, 사회 이슈, 문화, 제도 변화를 다뤄라.",
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
    "중국사회": [
        "중국 생활", "중국 문화", "중국 사회", "중국 경제",
        "중국 교육", "중국 취업", "중국 결혼", "중국 집값",
    ],
}


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept": "*/*",
    })
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")


# ---------------------------------------------------------------- 1. 信息源
# 配图策略（重要）：
#   1) 如果原始信息源自带配图 → 直接用原图，不修改、不新增
#   2) 如果原始信息源没有配图 → 用 DeepSeek 生成精确搜索词，去图库找高度相关的图
# 当前三个源（百度热搜/今日头条/什么值得买RSS）都是纯文字、无图，
# 所以走第 2 条路（fetch_images.py 里用精确搜索词 + 相关兜底词）。
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


def fetch_jianshu(limit=15):
    """抓取简书热门文章（标题+摘要），作为选题素材（主题多样，避免重复）"""
    url = "https://www.jianshu.com/asimov/trending/now"
    data = json.loads(_get(url))
    out = []
    for item in data:
        obj = item.get("object", {}) or {}
        d = obj.get("data", {}) or {}
        title = (d.get("title") or "").strip()
        abbr = (d.get("public_abbr") or "").strip()
        if title:
            out.append(f"{title}｜{abbr[:100]}" if abbr else title)
    return out[:limit]


def fetch_sspai(limit=10):
    """抓取少数派 RSS（中国数码/效率工具媒体，主题贴科技）"""
    url = "https://sspai.com/feed"
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
    if src.get("jianshu", True):
        try:
            items += fetch_jianshu()
            print("✅ 简书", end="  ")
        except Exception as e:
            print(f"⚠️ 简书失败", end="  ")
    if src.get("sspai", True):
        try:
            items += fetch_sspai()
            print("✅ 少数派", end="  ")
        except Exception as e:
            print(f"⚠️ 少数派失败", end="  ")
    return items


# ---------------------------------------------------------------- 2. LLM 加工
PROMPT = """당신은 중국 테크·여행·직구 정보를 다루는 전문 에디터다. 아래의 중국 실시간 인기 정보를 보고, 한국 독자에게 진짜 도움 되는 글 한 편을 써라.

【분야】{category}
{guide}

【选题要求 — 가장 중요】아래 참고 정보(中文信息条目)에서 "가장 구체적이고 새로운" 주제 하나를 골라라. 그 주제 하나에 깊게 파고들어, 제목과 본문에 구체적인 제품명·지명·이슈·숫자를 담아라. 다른 글과 겹치는 뻔한 주제는 피하고, 이 글만의 구체적인 소재를 정해라.

[글쓰기 스타일 — 가장 중요하다]
- 객관적인 정보 가이드처럼 써라. '저는/제가/제 생각' 같은 1인칭 체험담으로 쓰지 말고, 사실과 정보를 차분히 정리·설명하는 톤으로 써라.
- **반드시 존댓말로 써라. 합니다체('-ㅂ니다' / '-습니다') 또는 해요체('-요')로 문장을 끝내라. 반말(해체)은 절대 금지.**
- 본문에 '## 소제목' 형태의 H2 소제목을 2~4개 넣어 구조를 잡아라. 소제목은 그 섹션의 핵심을 요약하는 구체적인 문장으로.
- 규정·법규(관세·전파법 등)나 공식 데이터를 다룰 때는 해당 공식 기관(관세청, 한국전파진흥원 등)의 공식 페이지 링크를 1~2개 넣어 신뢰도를 높여라.
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


# ---------------------------------------------------------------- 去重
# 主题关键词（判断新文章主题是否和已有文章重复）
TOPIC_KEYWORDS = [
    "드론", "로봇", "스마트폰", "테무", "알리", "타오바오", "1688",
    "청두", "충칭", "고속철", "딥시크", "반도체", "전기차", "테슬라",
    "환불", "관세", "가품", "웨어러블", "노광기", "샤오미", "화웨이",
    "베이징", "상하이", "시안", "리장", "다리", "항저우", "쑤저우", "장가계",
    "길거리 음식", "생태계",
]


def load_existing_titles():
    """读取已有文章标题（用于去重）"""
    out_dir = Path(CFG.get("output_dir", DEFAULT_OUTPUT_DIR))
    titles = []
    try:
        for f in out_dir.glob("*.md"):
            txt = f.read_text(encoding="utf-8")
            m = re.search(r'title:\s*"([^"]+)"', txt)
            if m:
                titles.append(m.group(1))
    except Exception:
        pass
    return titles


def topic_overlap(title, existing_titles):
    """判断新标题主题是否和已有标题重复"""
    new_topics = {kw for kw in TOPIC_KEYWORDS if kw in title}
    if not new_topics:
        return False
    for t in existing_titles:
        for kw in new_topics:
            if kw in t:
                return True
    return False


def generate(items, category):
    year = datetime.datetime.now().year
    kw_list = KEYWORDS.get(category, [])
    keywords = "、".join(random.sample(kw_list, min(4, len(kw_list))))
    prompt = PROMPT.format(
        category=category,
        guide=CATEGORY_GUIDE[category],
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
    ap.add_argument("--category", default="direct", choices=["tech", "travel", "direct", "society"], help="分类")
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

        # 去重检查：主题重复则换角度重试（最多 5 次）
        existing = load_existing_titles()
        article = None
        for attempt in range(5):
            article = generate(items, category)
            if not topic_overlap(article["title"], existing):
                break
            print(f"⚠️ 主题重复，换角度重试 ({attempt + 1}/5)")
        if article is None or topic_overlap(article["title"], existing):
            print("⚠️ 连续 5 次都重复，本篇跳过")
            continue
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
