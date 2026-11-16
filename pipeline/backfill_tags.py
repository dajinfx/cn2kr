#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给现有文章批量补 tags（关键词匹配，不调 LLM）。

匹配来源：标题 + 描述 + 分类，对照标签池（分类关键词 + 主题关键词 + 实体词）。
用法：python backfill_tags.py [--dry-run]
"""
import sys
import os
import re

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pipeline as P  # noqa: E402
from pathlib import Path  # noqa: E402

P.CFG = P.load_config()
OUT_DIR = Path(P.CFG.get("output_dir", P.DEFAULT_OUTPUT_DIR))

# 标签池：分类搜索词 + 主题关键词 + 补充实体词
TAG_POOL = []
for kw in P.KEYWORDS.values():
    TAG_POOL += kw
TAG_POOL += P.TOPIC_KEYWORDS
TAG_POOL += [
    "중국 스마트폰", "중국 전기차", "중국 AI", "중국 로봇", "중국 드론",
    "중국 반도체", "중국 배터리", "중국 여행지", "중국 고속철", "중국 맛집",
    "중국 직구 사이트", "중국 쇼핑", "중국 결제", "중국 앱", "중국 소비",
    "아이폰", "안드로이드", "애플", "테슬라", "엔비디아", "오픈AI",
    "선전", "광저우", "칭다오", "샤먼", "톈진", "난징", "우한", "쿤밍", "구이린", "창사",
    "DJI", "아이토", "AITO", "오포", "비보", "원플러스", "레노버", "메이주",
]
seen = set()
TAG_POOL = [x for x in TAG_POOL if not (x in seen or seen.add(x))]


def extract_tags(title, desc, category):
    text = f"{title} {desc} {category}"
    tags = [kw for kw in TAG_POOL if kw in text]
    tags = list(dict.fromkeys(tags))  # 去重保序
    if category and category not in tags:
        tags.append(category)
    return tags[:6]


def main():
    dry = "--dry-run" in sys.argv
    todo = 0
    for f in sorted(OUT_DIR.glob("*.md")):
        txt = f.read_text(encoding="utf-8")
        # 解析 frontmatter
        m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
        if not m:
            continue
        fm = m.group(1)
        if re.search(r"^tags:", fm, re.M):
            continue  # 已有 tags

        title = re.search(r'^title:\s*"([^"]*)"', fm, re.M)
        desc = re.search(r'^description:\s*"([^"]*)"', fm, re.M)
        cat = re.search(r'^category:\s*"([^"]*)"', fm, re.M)
        title = title.group(1) if title else ""
        desc = desc.group(1) if desc else ""
        cat = cat.group(1) if cat else ""

        tags = extract_tags(title, desc, cat)
        if not tags:
            continue

        tag_lines = "\n".join(f"  - {t}" for t in tags)
        new_fm = fm.rstrip() + f"\ntags:\n{tag_lines}\n"
        new_txt = txt[:m.start(1)] + new_fm + txt[m.end(1):]

        todo += 1
        print(f"{f.name}: {tags}")
        if not dry:
            f.write_text(new_txt, encoding="utf-8")

    print(f"\n{'DRY-RUN' if dry else '完成'}：共处理 {todo} 篇")


if __name__ == "__main__":
    main()
