#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国一手信息 → 韩文加工内容 → Markdown + 原文配图（供 Nuxt Content 读取）
零依赖（只用 Python 标准库）

铁律：
- 配图铁律：从哪里获得文章，就抓原文图片做首图（原文没图才图库兜底）。
- 内容铁律：原文不能机翻，要润色成自然韩文；核心内容（事实/数字/结论）不改。

用法：
  python pipeline.py --category tech --count 1      # 生成 1 篇科技类
  python pipeline.py --category travel --count 1
  python pipeline.py --dry-run                        # 只生成不写文件
"""
import json
import os
import re
import sys
import time
import random
import datetime
import argparse
import html as _html
import urllib.request
import urllib.parse
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

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


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
    cfg.setdefault("sources", {"baidu_hot": True, "toutiao_hot": True, "smzdm_rss": True, "jianshu": True, "sspai": True, "ifanr": True})
    cfg.setdefault("max_fetch", 8)  # 最多抓几篇原文正文

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

# 分类专属配图渐变色（兜底 SVG 用）
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

# 高频搜索关键词（韩国人实际会搜的词，让标题/正文自然命中）
KEYWORDS = {
    "중국 테크": ["중국 스마트폰 직구", "화웨이", "샤오미", "중국 전기차", "중국 AI", "딥시크", "중국 반도체", "중국 로봇청소기"],
    "중국 여행": ["중국 여행", "상하이 여행", "베이징 여행", "장가계 여행", "중국 여행 준비", "중국 여행 비자", "중국 고속철", "알리페이 등록"],
    "중국 직구": ["중국 직구", "타오바오 직구", "알리익스프레스", "테무", "1688 직구", "배송대행", "직구 관세", "직구 가품"],
    "중국사회": ["중국 생활", "중국 문화", "중국 사회", "중국 경제", "중국 교육", "중국 취업", "중국 결혼", "중국 집값"],
}

# 选题相关性过滤关键词（中文，匹配候选标题；过滤与本站定位无关的主题，如美股/通用数码/泛生活）
CATEGORY_RELEVANCE = {
    "중국 테크": [
        "中国", "国产", "华为", "小米", "比亚迪", "蔚来", "小鹏", "理想", "吉利",
        "芯片", "半导体", "光刻机", "中芯国际", "长江存储", "deepseek", "大模型",
        "人工智能", "机器人", "无人机", "大疆", "电动车", "新能源", "电池", "宁德时代",
        "鸿蒙", "麒麟", "5G", "折叠屏", "超级快充", "卫星", "量子",
    ],
    "중국 여행": [
        "中国", "旅游", "旅行", "景区", "景点", "签证", "高铁", "机票", "酒店",
        "北京", "上海", "成都", "重庆", "西安", "杭州", "苏州", "南京", "广州", "深圳",
        "云南", "丽江", "大理", "桂林", "张家界", "三亚", "海南", "西藏", "新疆", "哈尔滨", "厦门", "青岛",
        "故宫", "长城", "兵马俑", "西湖", "九寨沟", "熊猫", "古镇",
    ],
    "중국 직구": [
        "淘宝", "天猫", "1688", "拼多多", "temu", "京东", "抖音", "快手",
        "海外购", "海淘", "代购", "跨境", "直邮", "转运", "关税", "清关", "免税",
        "国货", "中国制造", "工厂", "爆款", "捡漏", "凑单", "满减", "双11", "双十二",
    ],
    "중국사회": [
        "中国", "社会", "文化", "生活", "经济", "政策", "教育", "就业", "房价", "楼市",
        "婚姻", "生育", "养老", "工资", "消费", "股市", "公务员", "高考", "春节", "中秋",
        "非遗", "方言", "美食", "彩礼", "相亲", "退休",
    ],
}

# 放宽兜底：中国相关关键词（分类词匹配不上时用，标题匹配）
CHINA_KEYWORDS = [
    "中国", "国产", "国货", "华为", "小米", "比亚迪", "淘宝", "1688", "拼多多", "京东",
    "北京", "上海", "深圳", "广州", "杭州", "成都", "重庆", "西安", "武汉",
]


def _get(url, timeout=15, headers=None):
    req = urllib.request.Request(url, headers=headers or UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")


def normalize_url(u):
    """补全协议、反转义 HTML 实体"""
    if not u:
        return ""
    u = _html.unescape(u).strip()
    if u.startswith("//"):
        u = "https:" + u
    return u


# ---------------------------------------------------------------- 1. 信息源
# 每个源返回 item 列表，item = {"title", "url", "image", "src"}
#   url   : 原文链接（没有则 None）
#   image : 原文头图直链（没有则 None）
def fetch_baidu_hot(limit=5):
    """百度热搜：只有热搜词 + 搜索链接，无原文文章，无图"""
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
            out.append({"title": w, "url": None, "image": None, "src": "百度热搜"})
    return out[:limit]


def fetch_toutiao_hot(limit=5):
    """今日头条热榜：有 Title + Url(原文) + Image.url(头图)；正文 JS 渲染抓不到"""
    url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    data = json.loads(_get(url))
    out = []
    for d in data.get("data", [])[:limit]:
        title = (d.get("Title") or "").strip()
        if not title:
            continue
        img = d.get("Image") or {}
        out.append({
            "title": title,
            "url": normalize_url(d.get("Url") or ""),
            "image": normalize_url(img.get("url") or ""),
            "src": "今日头条",
        })
    return out


def fetch_smzdm_rss(limit=5):
    """什么值得买 RSS：有 <title> + <link>(原文)，图需抓原文页（og:image 可抓）"""
    raw = _get("https://post.smzdm.com/feed/")
    items = re.findall(r"<item>(.*?)</item>", raw, re.S)
    out = []
    for it in items[:limit]:
        m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
        link = re.search(r"<link>(.*?)</link>", it, re.S)
        if not m:
            continue
        out.append({
            "title": m.group(1).strip(),
            "url": normalize_url(link.group(1).strip() if link else ""),
            "image": None,
            "src": "什么值得买",
        })
    return out


def fetch_jianshu(limit=4):
    """简书热门：有 title + slug(→原文链接)，正文/图可抓原文页"""
    url = "https://www.jianshu.com/asimov/trending/now"
    data = json.loads(_get(url))
    out = []
    for item in data[:limit]:
        obj = item.get("object", {}) or {}
        d = obj.get("data", {}) or {}
        title = (d.get("title") or "").strip()
        if not title:
            continue
        slug = d.get("slug") or ""
        out.append({
            "title": title,
            "url": f"https://www.jianshu.com/p/{slug}" if slug else "",
            "image": normalize_url(d.get("list_image_url") or ""),
            "src": "简书",
        })
    return out


def fetch_sspai(limit=4):
    """少数派 RSS：有 <title> + <link>(原文)，正文/图可抓原文页"""
    raw = _get("https://sspai.com/feed")
    items = re.findall(r"<item>(.*?)</item>", raw, re.S)
    out = []
    for it in items[:limit]:
        m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
        link = re.search(r"<link>(.*?)</link>", it, re.S)
        if not m:
            continue
        out.append({
            "title": m.group(1).strip(),
            "url": normalize_url(link.group(1).strip() if link else ""),
            "image": None,
            "src": "少数派",
        })
    return out


def fetch_ifanr(limit=8):
    """爱范儿 RSS（中国科技媒体）：正文和配图都在 RSS 里，无需抓原文页，不触发反爬"""
    raw = _get("https://www.ifanr.com/feed")
    items = re.findall(r"<item>(.*?)</item>", raw, re.S)
    out = []
    for it in items[:limit]:
        m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
        link = re.search(r"<link>(.*?)</link>", it, re.S)
        if not m:
            continue
        title = _html.unescape(m.group(1)).strip()
        # 正文和配图都从 content:encoded（或 description）里抽
        ce = re.search(r"<content:encoded>(.*?)</content:encoded>", it, re.S)
        if not ce:
            ce = re.search(r"<description>(.*?)</description>", it, re.S)
        html = ce.group(1) if ce else ""
        imgs = _extract_images(html, None)
        # 抽 <p> 文本做正文
        paras = re.findall(r"<p[^>]*>(.*?)</p>", html, re.S)
        texts = []
        for p in paras:
            t = re.sub(r"<[^>]+>", " ", p)
            t = _html.unescape(t)
            t = re.sub(r"\s+", " ", t).strip()
            if len(t) >= 20:
                texts.append(t)
        body = "\n".join(texts)[:3000] if texts else None
        out.append({
            "title": title,
            "url": normalize_url(link.group(1).strip() if link else ""),
            "image": imgs[0] if imgs else None,
            "images": imgs,
            "body": body,
            "src": "爱范儿",
        })
    return out


def collect_items():
    items = []
    src = CFG.get("sources", {})
    if src.get("baidu_hot", True):
        try:
            items += fetch_baidu_hot()
            print("✅ 百度热搜", end="  ")
        except Exception as e:
            print(f"⚠️ 百度热搜失败({e})", end="  ")
    if src.get("toutiao_hot", True):
        try:
            items += fetch_toutiao_hot()
            print("✅ 今日头条", end="  ")
        except Exception as e:
            print(f"⚠️ 今日头条失败({e})", end="  ")
    if src.get("smzdm_rss", True):
        try:
            items += fetch_smzdm_rss()
            print("✅ 什么值得买", end="  ")
        except Exception as e:
            print(f"⚠️ 什么值得买失败({e})", end="  ")
    if src.get("jianshu", True):
        try:
            items += fetch_jianshu()
            print("✅ 简书", end="  ")
        except Exception as e:
            print(f"⚠️ 简书失败({e})", end="  ")
    if src.get("sspai", True):
        try:
            items += fetch_sspai()
            print("✅ 少数派", end="  ")
        except Exception as e:
            print(f"⚠️ 少数派失败({e})", end="  ")
    if src.get("ifanr", True):
        try:
            items += fetch_ifanr()
            print("✅ 爱范儿", end="  ")
        except Exception as e:
            print(f"⚠️ 爱范儿失败({e})", end="  ")
    print()
    return items


def filter_relevant(items, category, min_keep=3):
    """按分类关键词过滤候选（标题匹配），过滤与本站定位无关的主题（美股/通用数码/泛生活等）。

    不足 min_keep 时放宽到「中国相关」关键词；仍没有则全部保留（避免空跑）。
    """
    kws = CATEGORY_RELEVANCE.get(category, [])
    if kws:
        kept = [it for it in items if any(kw in (it.get("title") or "") for kw in kws)]
        if len(kept) >= min_keep:
            return kept
    kept = [it for it in items if any(kw in (it.get("title") or "") for kw in CHINA_KEYWORDS)]
    return kept if kept else items


# ---------------------------------------------------------------- 1.5 抓原文
# 这些是头像/logo/图标/装饰图，不算正文配图，要过滤掉
_BAD_IMG = (
    "avatar", "logo", "icon", "emoji", "level", "the-end", "user_logo",
    "default_", "qrcode", "wechat", "share", "loading", "placeholder",
)
_GOOD_IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")


def _extract_images(html, og):
    """抽取页面全部正文配图：og:image 优先，再抓 <img>，过滤头像/logo/图标，去重"""
    imgs = []
    if og:
        imgs.append(og)
    for src in re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html):
        u = normalize_url(src)
        low = u.lower()
        if not u or u in imgs:
            continue
        if not low.endswith(_GOOD_IMG_EXT):
            continue
        if any(b in low for b in _BAD_IMG):
            continue
        imgs.append(u)
    return imgs


def fetch_article(url, timeout=12):
    """抓原文页面，返回 (正文文本, og:image, 全部图片列表)。失败返回 (None, None, [])"""
    try:
        html = _get(url, timeout=timeout)
    except Exception:
        return None, None, []

    # og:image（两种属性顺序都兼容）
    og = None
    m = (re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
         or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html))
    if m:
        og = normalize_url(m.group(1))

    imgs = _extract_images(html, og)

    # 正文：抽取 <p> 文本
    paras = re.findall(r"<p[^>]*>(.*?)</p>", html, re.S)
    texts = []
    for p in paras:
        t = re.sub(r"<[^>]+>", " ", p)
        t = _html.unescape(t)
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) >= 20:
            texts.append(t)
    body = "\n".join(texts)[:3000] if texts else None
    return body, og, imgs


def enrich_items(items, max_fetch=8):
    """给有原文链接的 item 抓正文+头图（按来源轮询，保证来源多样；失败不影响）

    注意：今日头条正文是 JS 渲染抓不到，但它的头图(Image.url)已经直接给到了 item，
    所以这里跳过头条的正文抓取，其余源(smzdm/sspai/jianshu)抓正文 + og:image。
    """
    # 需要抓正文的来源：有 url 且非「头条(JS渲染)/爱范儿(图已在RSS里)」
    to_fetch = [it for it in items if it.get("url") and it.get("src") not in ("今日头条", "爱范儿")]
    groups = {}
    for it in to_fetch:
        groups.setdefault(it["src"], []).append(it)

    # 按来源交错排列（什么值得买/少数派/简书 轮流），避免只抓同一个源
    interleaved = []
    keys = list(groups.keys())
    max_len = max((len(v) for v in groups.values()), default=0)
    for i in range(max_len):
        for k in keys:
            if i < len(groups[k]):
                interleaved.append(groups[k][i])

    fetched = 0
    for it in interleaved:
        if fetched >= max_fetch:
            break
        print(f"  抓原文: {it['src']} 《{it['title'][:22]}》...")
        body, og, imgs = fetch_article(it["url"])
        if body:
            it["body"] = body
        if imgs:
            it["images"] = imgs
            if not it.get("image"):
                it["image"] = imgs[0]
        fetched += 1
        time.sleep(0.3)
    return items


# ---------------------------------------------------------------- 2. LLM 加工
PROMPT = """당신은 중국 테크·여행·직구·사회 정보를 다루는 전문 에디터다. 아래의 중국 원문 기사 후보들 중 **하나를 골라**, 한국 독자에게 진짜 도움 되는 글 한 편으로 **재작성(윤문)**하라.

【분야】{category}
{guide}

【재작성 원칙 — 가장 중요】
- 원문을 **기계번역해서 그대로 붙여넣지 말 것**. 자연스럽고 유려한 한국어로 다시 쓰되(윤문), **원문의 핵심 내용(사실·숫자·결론·입장)은 절대 바꾸지 말 것**.
- 원문에 없는 내용을 지어내지 말 것. 추측·과장 금지.
- 원문 본문이 없는 후보(제목만)는 그 제목 주제로 새로 쓰되, 위 원칙(자연스러운 한국어, 구체적 사실)을 지켜라.
- **중국어(한자) 표현은 모두 자연스러운 한국어로 옮겨라. 제목·설명·본문에 원문 한자를 그대로 남기지 말 것.** 상표명·고유명사는 예외지만, 일반 중국어 용어는 반드시 한국어로 풀어 써라(예: '凑单' → '끼워 넣기 주문', '满减' → '금액 구간 할인').
- 제목과 설명은 반드시 **순수 한국어**로. 숫자·단위는 한국 독자 기준으로 자연스럽게.

[글쓰기 스타일]
- 객관적인 정보 가이드처럼 써라. '저는/제가/제 생각' 같은 1인칭 체험담으로 쓰지 말고, 사실과 정보를 차분히 정리·설명하는 톤으로 써라.
- **반드시 존댓말로 써라. 합니다체('-ㅂ니다' / '-습니다') 또는 해요체('-요')로 문장을 끝내라. 반말(해체)은 절대 금지.**
- 본문에 '## 소제목' 형태의 H2 소제목을 2~4개 넣어 구조를 잡아라. 소제목은 그 섹션의 핵심을 요약하는 구체적인 문장으로.
- 구체적인 숫자·가격·앱 이름·예시를 넣어라. 추상적인 조언만 나열하지 마라.
- 문장 길이를 들쭉날쭉하게. 짧게 끊는 문장과 길게 풀어쓰는 문장을 섞어라.
- 차분하고 정보 밀도는 높게. 과장·호들갑·이모티콘 금지. 번역투 금지.

[절대 쓰지 말 것]
"~에 대해 알아보자", "~를 소개한다", "~를 정리했다", "총정리", "완전정복", "꿀팁", "안녕하세요", "오늘은", "마지막으로", "결론적으로", "~할 수 있습니다" 반복 사용.
"저는", "제가", "제 생각", "직접 써보니", "직접 겪어보니" 같은 1인칭 체험담 표현은 절대 금지.
문장 끝의 반말(해체) 종결 '-다', '-어', '-냐', '-니', '-자', '-지'(반말), '-는데'는 절대 금지.
URL·링크를 지어내지 말 것. 출처 URL을 100% 확신할 수 없으면 링크를 아예 넣지 말고, 기관 이름만 언급하라. 법규·관세·인증 등 규제 정보는 구체적 수치를 지어내지 말고 일반적인 수준으로만 다뤄라.

[기타 규칙]
- 분야와 무관한 정보는 버려라.
- 연도는 반드시 올해({year}년)로 써라. 옛 연도 금지.
- 아래 검색 키워드 중 1~2개를 제목이나 본문에 자연스럽게 포함시켜라(억지로 나열하지 말 것): {keywords}
- 글 길이는 고정하지 마라. 주제에 따라 300자부터 2000자까지 자연스럽게 써라. 내용이 끝나면 바로 끝내라.
- 본문 중간, 이미지가 자연스러운 위치(예: 특정 상품·장소·음식·기기를 설명하는 문단 뒤)에 "[이미지: 영문 검색어 | 한글 설명]" 표시를 넣어라. 영문 검색어는 해당 문단에서 실제로 다루는 구체적인 제품/장소/물건의 영문명으로. 한글은 alt용. 개수는 주제에 따라 자연스럽게(짧은 글 0~1개, 긴 글 3~4개).

[출력 형식 — 이것만 출력]
来源链接: [선택한 후보의 '链接' 항목을 그대로 복사]
제목: [순수 한국어 제목]
설명: [한 줄 요약, 30자 이내, 순수 한국어]
슬러그: [영문 키워드 슬러그, 소문자+하이픈만, 3~6단어]
태그: [한국어 검색 키워드 3~5개, 쉼표로 구분. 한국인이 실제로 검색할 법한 구체적인 키워드, 예: 화웨이, 중국 전기차, AITO M8]

(위 다섯 줄 다음부터 바로 본문을 써라. 본문에 별도의 '본문' 라벨은 붙이지 말 것.)

후보 원문 목록:"""


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


# ---------------------------------------------------------------- 韩文化兜底
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _has_cjk(text):
    return bool(text) and bool(CJK_RE.search(text))


def koreanize(text):
    """文本里残留中文字符时，再调一次 DeepSeek 把中文转成纯韩文（内容不动，失败原样返回）"""
    if not _has_cjk(text):
        return text
    prompt = (
        "아래 한국어 글에 중국어(한자)가 섞여 있습니다. 모든 중국어를 자연스러운 한국어로 바꿔 주세요.\n"
        "- 고유명사(지명·브랜드·상품명)는 한글 음역, 일반 명사·표현은 한국어로 번역.\n"
        "- 이미 한국어로 쓰인 부분은 그대로 두고, 중국어 부분만 한국어로 바꾸세요.\n"
        "- 내용·구조·문장·숫자는 절대 바꾸지 말고, 순수 한국어 텍스트만 출력하세요.\n\n"
        + text
    )
    try:
        out = call_deepseek(prompt).strip()
        return out or text
    except Exception:
        return text


def koreanize_title_desc(title, desc):
    """标题/说明里残留中文时一起转韩文（返回新 title, desc）"""
    if not (_has_cjk(title) or _has_cjk(desc)):
        return title, desc
    prompt = (
        "아래 제목과 설명에 중국어(한자)가 섞여 있습니다. 중국어를 자연스러운 한국어로 바꿔 주세요.\n"
        "- 고유명사는 한글 음역, 일반 명사는 한국어로 번역. 한국어 부분은 그대로.\n"
        "- 내용·숫자·구조는 절대 바꾸지 말 것.\n"
        "- 아래 형식만 출력:\n"
        "제목: ...\n설명: ...\n\n"
        f"제목: {title}\n설명: {desc}"
    )
    try:
        raw = call_deepseek(prompt)
        m1 = re.search(r"제목\s*[:：]\s*(.+)", raw)
        m2 = re.search(r"설명\s*[:：]\s*(.+)", raw)
        if m1:
            title = m1.group(1).strip()
        if m2:
            desc = m2.group(1).strip()
    except Exception:
        pass
    return title, desc


# ---------------------------------------------------------------- 去重
TOPIC_KEYWORDS = [
    "드론", "로봇", "스마트폰", "테무", "알리", "타오바오", "1688",
    "청두", "충칭", "고속철", "딥시크", "반도체", "전기차", "테슬라",
    "환불", "관세", "가품", "웨어러블", "노광기", "샤오미", "화웨이",
    "베이징", "상하이", "시안", "리장", "다리", "항저우", "쑤저우", "장가계",
    "길거리 음식", "생태계",
]


def load_existing_titles():
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
    new_topics = {kw for kw in TOPIC_KEYWORDS if kw in title}
    if not new_topics:
        return False
    for t in existing_titles:
        for kw in new_topics:
            if kw in t:
                return True
    return False


# ---------------------------------------------------------------- 3. 生成
def build_candidate_block(items):
    """把候选原文列表拼成 prompt 片段（带链接，供 DeepSeek 原样复制来源）"""
    lines = []
    for i, it in enumerate(items):
        lines.append(f"[{i}] 《{it['title']}》")
        if it.get("url"):
            lines.append(f"链接: {it['url']}")
        body = it.get("body")
        if body:
            lines.append(f"원문: {body[:1500]}")
        else:
            lines.append("(본문 없음 — 제목만 보고 주제를 정해라)")
        lines.append("")
    return "\n".join(lines)


def generate(items, category):
    year = datetime.datetime.now().year
    kw_list = KEYWORDS.get(category, [])
    keywords = "、".join(random.sample(kw_list, min(4, len(kw_list))))
    prompt = PROMPT.format(
        category=category,
        guide=CATEGORY_GUIDE[category],
        year=year,
        keywords=keywords,
    ) + "\n\n" + build_candidate_block(items)
    raw = call_deepseek(prompt)

    def grab(field):
        m = re.search(rf"{field}\s*[:：]\s*(.+)", raw)
        return m.group(1).strip() if m else None

    title = grab("제목") or f"{category} 트렌드"
    desc = grab("설명") or ""
    slug = grab("슬러그") or ""

    # 태그：한국어 검색 키워드 3~5개
    tags = []
    t = grab("태그")
    if t:
        tags = [x.strip() for x in re.split(r"[,，、]", t) if x.strip()][:6]

    # 来源链接（DeepSeek 原样复制的原文 URL，用于精确匹配候选）
    src_url = None
    m = re.search(r"来源链接\s*[:：]\s*(.+)", raw)
    if m:
        src_url = m.group(1).strip().strip(".,;，。；")

    content = raw
    for field in ("来源链接", "제목", "설명", "슬러그", "태그"):
        content = re.sub(rf"^{field}\s*[:：].*\n?", "", content, count=1, flags=re.M)
    # 去掉可能残留的 '[본문]' / '[正文]' 标签行
    content = re.sub(r"^\[본문\]\s*", "", content, flags=re.M)
    content = re.sub(r"^\[正文\]\s*", "", content, flags=re.M)
    content = content.strip()

    return {
        "title": title,
        "category": category,
        "description": desc,
        "content": content,
        "slug": slug,
        "source_url": src_url,
        "tags": tags,
    }


def match_source_index(title, items):
    """标题相似度兜底匹配：返回最相似的候选下标（无则 0）。中文候选 vs 生成标题，中文重叠加权。"""
    best, best_score = 0, 0

    def cjk(s):
        return set(re.findall(r"[\u4e00-\u9fff]", s))

    def allch(s):
        return set(re.findall(r"[\u4e00-\u9fff\uac00-\ud7af0-9a-zA-Z]", s))

    tcjk, tall = cjk(title), allch(title)
    for i, it in enumerate(items):
        icjk, iall = cjk(it["title"]), allch(it["title"])
        if not tall or not iall:
            continue
        overlap = len(tall & iall)
        cjk_overlap = len(tcjk & icjk)
        score = overlap + cjk_overlap * 4
        if score > best_score:
            best_score, best = score, i
    return best


def resolve_source(article, items):
    """确定文章实际来自哪个候选：URL 精确匹配 > 标题相似度兜底"""
    url = (article.get("source_url") or "").strip()
    if url:
        for i, it in enumerate(items):
            cu = it.get("url") or ""
            if cu and (url == cu or url in cu or cu in url):
                return i
    return match_source_index(article["title"], items)


# ---------------------------------------------------------------- 4. 配图（原文图）
def download_image(url, dest_base, referer=None):
    """下载图片到 dest_base.ext，返回相对路径 /images/xxx.ext 或 None。

    referer：原文链接（很多图床/CDN 需要 Referer 防盗链，403 时带上原文页做 Referer）。
    太小(<8KB)的图视为缩略图/占位图，跳过。
    """
    def _fetch(headers):
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read(), r.headers.get("Content-Type", "")

    data, ctype = None, ""
    try:
        headers = dict(UA)
        if referer:
            headers["Referer"] = referer
        data, ctype = _fetch(headers)
    except Exception as e:
        # 403 等防盗链：若无 referer，则用图片自身域名根再试一次
        if referer is None:
            try:
                parts = urllib.parse.urlsplit(url)
                ref = f"{parts.scheme}://{parts.netloc}/"
                headers = dict(UA)
                headers["Referer"] = ref
                data, ctype = _fetch(headers)
            except Exception:
                print(f"    [图下载失败] {e}")
                return None
        else:
            print(f"    [图下载失败] {e}")
            return None

    if not data or len(data) < 8 * 1024:
        print(f"    [图太小/为空，跳过] {len(data) if data else 0}B")
        return None

    ext = None
    if "png" in ctype:
        ext = ".png"
    elif "webp" in ctype:
        ext = ".webp"
    elif "jpeg" in ctype or "jpg" in ctype:
        ext = ".jpg"
    else:
        path = urllib.parse.urlparse(url).path.lower()
        for e in (".png", ".webp", ".jpg", ".jpeg"):
            if path.endswith(e):
                ext = ".jpg" if e == ".jpeg" else e
                break
        ext = ext or ".jpg"

    dest = dest_base + ext
    with open(dest, "wb") as f:
        f.write(data)
    return f"/images/{os.path.basename(dest)}"


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


def resolve_cover(chosen, slug, category, image_dir):
    """首图优先用原文头图；没有则抓的 og:image；再没有才 SVG 兜底"""
    img = (chosen or {}).get("image")
    if img:
        rel = download_image(img, str(Path(image_dir) / slug), referer=(chosen or {}).get("url"))
        if rel:
            print(f"  ✅ 原文头图 -> {rel}")
            return rel
    print("  ⚠️ 无原文图，用 SVG 占位（之后 fetch_images.py 兜底）")
    return generate_svg(category, slug, image_dir)


def download_inline_images(slug, content, inline_images, image_dir, referer=None, max_inline=6):
    """把原文插图(除头图外)放进正文，返回 (新正文, 张数)。

    1) 先用原文图替换正文里的 [이미지: ...] 标记（按顺序）
    2) 多余的原文图均匀插到段落之间（最多共 max_inline 张插图）
    """
    if not inline_images:
        return content, 0

    # 下载最多 max_inline 张插图
    rels = []
    for i, u in enumerate(inline_images[:max_inline]):
        rel = download_image(u, str(Path(image_dir) / f"{slug}-{i + 1}"), referer=referer)
        if rel:
            rels.append(rel)
            print(f"  ✅ 原文插图{i + 1} -> {rel}")
    if not rels:
        return content, 0

    # 1) 用前几张替换 [이미지:] 标记
    pattern = re.compile(r"\[이미지:\s*[^\]]+\]")
    markers = re.findall(r"\[이미지:\s*([^\]]+)\]", content)
    new_content = content
    used = 0
    for i, marker in enumerate(markers):
        if i >= len(rels):
            break
        parts = [p.strip() for p in marker.split("|")]
        alt = parts[1] if len(parts) > 1 and parts[1] else "이미지"
        new_content = pattern.sub(f"![{alt}]({rels[i]})", new_content, count=1)
        used += 1

    # 2) 剩余图片均匀插到段落之间
    extra = rels[used:]
    if extra:
        blocks = [b for b in new_content.split("\n\n") if b.strip()]
        if len(blocks) >= 2:
            gap = max(1, len(blocks) // (len(extra) + 1))
            out = []
            idx = 0
            for i, b in enumerate(blocks):
                out.append(b)
                if idx < len(extra) and (i + 1) % gap == 0 and (i + 1) < len(blocks):
                    out.append(f"![이미지 {used + idx + 1}]({extra[idx]})")
                    idx += 1
            while idx < len(extra):
                out.append(f"![이미지 {used + idx + 1}]({extra[idx]})")
                idx += 1
            new_content = "\n\n".join(out)

    return new_content, len(rels)


# ---------------------------------------------------------------- 5. 存 Markdown
def make_slug(raw_slug):
    s = (raw_slug or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        s = f"article-{ts}"
    return s[:60]


def save_markdown(article, image_url, slug, source_url=""):
    out_dir = Path(CFG.get("output_dir", DEFAULT_OUTPUT_DIR))
    out_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.date.today().isoformat()

    src_line = f'source: "{source_url}"\n' if source_url else ""

    tags = article.get("tags") or []
    if tags:
        tags_lines = "\n".join(f"  - {t}" for t in tags)
        tags_block = f"tags:\n{tags_lines}\n"
    else:
        tags_block = ""

    md = f"""---
title: "{article['title']}"
category: "{article['category']}"
description: "{article['description']}"
date: {date}
image: "{image_url}"
{src_line}{tags_block}---

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
    image_dir = Path(CFG.get("image_dir", DEFAULT_IMAGE_DIR))
    image_dir.mkdir(parents=True, exist_ok=True)
    max_fetch = int(CFG.get("max_fetch", 6))

    for i in range(args.count):
        print(f"\n===== [{category}] 第 {i+1}/{args.count} 篇 =====")
        items = collect_items()
        if not items:
            print("❌ 什么都没抓到")
            return

        # 过滤与本站定位无关的主题（美股/通用数码/泛生活等）
        before = len(items)
        items = filter_relevant(items, category)
        print(f"  过滤后相关候选 {len(items)}/{before} 条")

        # 抓原文正文+头图（best-effort）
        items = enrich_items(items, max_fetch=max_fetch)
        with_body = sum(1 for it in items if it.get("body"))
        with_img = sum(1 for it in items if it.get("image"))
        print(f"  候选 {len(items)} 条 | 抓到正文 {with_body} | 有头图 {with_img}")

        # 候选排序：有正文+头图 > 有头图 > 有正文 > 仅标题（优先让 DeepSeek 看到能改写又有图的原件）
        def _rank(it):
            b = bool(it.get("body"))
            m = bool(it.get("image"))
            return 0 if (b and m) else 1 if m else 2 if b else 3
        items.sort(key=_rank)
        items = items[:20]

        # 去重检查：主题重复则换角度重试（最多 5 次）
        existing = load_existing_titles()
        article = None
        for attempt in range(5):
            article = generate(items, category)
            if not topic_overlap(article["title"], existing):
                break
            print(f"⚠️ 主题重复，重试 ({attempt + 1}/5)")
        if article is None or topic_overlap(article["title"], existing):
            print("⚠️ 连续 5 次都重复，本篇跳过")
            continue
        # 韩文化兜底：残留中文字符 → 二次转韩文（内容/结构不动，只换中文词）
        article["title"], article["description"] = koreanize_title_desc(article["title"], article["description"])
        article["content"] = koreanize(article["content"])
        print(f"标题：{article['title']}")
        print(f"摘要：{article['description']}")

        # 定位选中的原文候选（URL 精确匹配 > 标题相似度）
        idx = resolve_source(article, items)
        chosen = items[idx] if 0 <= idx < len(items) else None
        if chosen:
            print(f"  来源: {chosen['src']} 《{chosen['title'][:30]}》 {chosen.get('url') or '(无链接)'}")

        if args.dry_run:
            print(article["content"][:250] + "...")
            continue

        slug = make_slug(article.get("slug"))
        image_url = resolve_cover(chosen, slug, category, image_dir)
        # 原文插图：用原文剩余图片(除头图外)替换正文里的 [이미지: ...] 标记
        inline_imgs = (chosen or {}).get("images") or []
        if len(inline_imgs) > 1:
            article["content"], _ = download_inline_images(slug, article["content"], inline_imgs[1:], image_dir, referer=(chosen or {}).get("url"))
        source_url = (chosen or {}).get("url") or ""
        path = save_markdown(article, image_url, slug, source_url)
        print(f"✅ slug：{slug}")
        print(f"✅ 已保存：{path}")
        print(f"✅ 首图：{image_url}")

        if i < args.count - 1:
            time.sleep(2)


if __name__ == "__main__":
    main()
