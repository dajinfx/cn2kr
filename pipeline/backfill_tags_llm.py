#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 DeepSeek 给现有文章逐篇生成「精准」搜索关键词（SEO/Naver 长尾词）。

不用词池匹配——词池只能产出分类级/城市级泛词（선전, 중국 테크），
无法覆盖每篇文章的具体实体（品牌/型号/地点/场景）。
本脚本把每篇的标题+描述+正文摘要喂给 DeepSeek，让它筛出韩国人实际会搜的具体词。

用法：
  python backfill_tags_llm.py --dry-run              # 全部生成，只打印不写盘
  python backfill_tags_llm.py                        # 全部生成并写盘
  python backfill_tags_llm.py --only <slug>           # 只跑一篇（写盘）
  python backfill_tags_llm.py --only <slug> --dry-run # 只跑一篇（不写盘）
"""
import sys
import os
import re
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pipeline as P  # noqa: E402
from pathlib import Path  # noqa: E402

P.CFG = P.load_config()
OUT_DIR = Path(P.CFG.get("output_dir", P.DEFAULT_OUTPUT_DIR))

MAX_TAGS = 6
BODY_CHARS = 1200  # 喂给模型的正文字数上限（正文前半段足够定主题）


def parse_article(txt):
    """返回 (title, desc, body, fm_start, fm_end, fm_text)"""
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return None
    fm_text = m.group(1)
    title = re.search(r'^title:\s*"([^"]*)"', fm_text, re.M)
    desc = re.search(r'^description:\s*"([^"]*)"', fm_text, re.M)
    title = title.group(1) if title else ""
    desc = desc.group(1) if desc else ""
    body = txt[m.end():].strip()
    return {
        "title": title, "desc": desc,
        "body": body[:BODY_CHARS],
        "fm_start": m.start(1), "fm_end": m.end(1), "fm": fm_text,
    }


def build_prompt(title, desc, body):
    return (
        "당신은 한국인 대상 중국 정보 사이트의 SEO 키워드 전문가입니다.\n\n"
        "아래 글을 읽고, 한국인이 네이버·구글에서 실제로 검색할 법한 "
        "'구체적인 검색 키워드'를 4~6개 뽑아 주세요.\n\n"
        "규칙:\n"
        "1. 분류·카테고리 단어(중국 테크, 중국 여행, 중국 직구 같은 광범위한 단어)만 "
        "나열하지 마세요. 이런 단어는 최대 1개까지만 허용합니다.\n"
        "2. 반드시 구체적인 대상이 담긴 키워드여야 합니다: 브랜드명, 상품·모델명, "
        "도시·지명, 구체적인 상황·문제.\n"
        "   예) 화웨이, AITO M8, DJI 드론, 선전 여행, 알리익스프레스 환불, 타오바오 관세\n"
        "3. 한국인이 실제 검색창에 입력할 법한 자연스러운 한글 표현으로 쓰세요.\n"
        "4. 쉼표(,)로 구분해 한 줄로만 출력하세요. 다른 설명은 붙이지 마세요.\n\n"
        f"글 제목: {title}\n글 설명: {desc}\n본문(일부):\n{body}\n"
    )


def parse_tags(raw):
    raw = raw.strip()
    # 去掉可能的列表符号/引号
    raw = raw.split("\n")[0]  # 只要第一行
    raw = re.sub(r"^[#\-*\d.\s]+", "", raw)
    parts = re.split(r"[,，]", raw)
    tags = []
    for p in parts:
        p = p.strip().strip('"\'').strip()
        if not p:
            continue
        if p not in tags:
            tags.append(p)
    return tags[:MAX_TAGS]


def rewrite_frontmatter(txt, info, tags):
    tag_lines = "\n".join(f"  - {t}" for t in tags)
    # 删除旧 tags 块（若有）
    fm = re.sub(r"\n?tags:\n(?:  - .+\n?)+", "\n", info["fm"])
    new_fm = fm.rstrip() + f"\ntags:\n{tag_lines}\n"
    return txt[:info["fm_start"]] + new_fm + txt[info["fm_end"]:]


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    only = None
    if "--only" in args:
        i = args.index("--only")
        if i + 1 < len(args):
            only = args[i + 1]

    files = sorted(OUT_DIR.glob("*.md"))
    done = 0
    failed = 0
    for f in files:
        slug = f.stem
        if only and slug != only:
            continue
        txt = f.read_text(encoding="utf-8")
        info = parse_article(txt)
        if not info:
            print(f"[skip] {slug}: 无 frontmatter")
            continue

        prompt = build_prompt(info["title"], info["desc"], info["body"])
        try:
            raw = P.call_deepseek(prompt)
            tags = parse_tags(raw)
        except Exception as e:
            print(f"[FAIL] {slug}: {e}")
            failed += 1
            continue

        if not tags:
            print(f"[skip] {slug}: 未解析到 tag")
            continue

        print(f"{slug}  →  {tags}")
        if not dry:
            new_txt = rewrite_frontmatter(txt, info, tags)
            f.write_text(new_txt, encoding="utf-8")
        done += 1

    print(f"\n{'DRY-RUN' if dry else '完成'}：成功 {done} 篇，失败 {failed} 篇")


if __name__ == "__main__":
    main()
