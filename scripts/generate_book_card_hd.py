#!/usr/bin/env python3
"""
每日书籍推荐卡片 - 高清2x版（2026-04-27 规范版）
- 纯白背景 + 文字排版，不用AI生图
- 严格按 MEMORY.md 排版规范执行
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from _timezone import CST
import sys
sys.path.insert(0, str(Path(__file__).parent))
from association_analysis import run_analysis

# ──────────────────────────────────────────────────
ED = '/tmp/emoji_imgs'
_TODAY_STR = datetime.now(CST).strftime("%Y年%m月%d日")  # 生成卡片当天日期，模块级避免运行时未定义
EMOJI = {
    'book':    Image.open(f'{ED}/1f4da.png').convert('RGBA'),
    'speech':  Image.open(f'{ED}/1f4ac.png').convert('RGBA'),
    'light':   Image.open(f'{ED}/1f4a1.png').convert('RGBA'),
    'pencil':  Image.open(f'{ED}/270f.png').convert('RGBA'),
    'tag':     Image.open(f'{ED}/1f4f6.png').convert('RGBA'),
    'star':    Image.open(f'{ED}/2b50.png').convert('RGBA'),
}

def wrap_text(text, max_chars):
    lines = []
    for line in text.split('\n'):
        for i in range(0, len(line), max_chars):
            lines.append(line[i:i+max_chars])
    return lines

def paste_emoji(canvas, emoji_rgba, x, y_text, font_size):
    """emoji 与文字 baseline 对齐
    emoji 字符视觉中心约在方格 35.5/72 处（略偏下），
    文字 baseline 在 font_size - descent ≈ font_size*0.86 处。
    用经验偏移让 emoji 视觉上与文字对齐。
    """
    emoji_h = emoji_rgba.size[1]
    # 文字 baseline ≈ y_text + font_size * 0.86
    text_baseline = y_text + int(font_size * 0.86)
    # emoji 字符中心约在 emoji_h * 0.49 处
    emoji_center = int(emoji_h * 0.49)
    # paste_y = 文字baseline位置 - emoji中心位置
    paste_y = text_baseline - emoji_center
    canvas.paste(emoji_rgba, (x, paste_y), mask=emoji_rgba.split()[3])

def generate_card(book_data, output_path):
    scale = 2

    # ── 字体（严格按规范） ──
    font_title   = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc', 54 * scale)
    font_section = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 36 * scale)
    font_main    = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 32 * scale)
    font_small   = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 22 * scale)
    font_tag     = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 24 * scale)
    font_meta    = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 28 * scale)

    # ── 颜色 ──
    C_PURPLE = (100, 50, 130)
    C_BLUE   = (30, 90, 160)
    C_BODY   = (45, 45, 45)
    C_META   = (100, 100, 100)
    C_LIGHT  = (150, 150, 150)
    C_LINE   = (210, 210, 210)
    C_ACCENT = (180, 60, 60)

    MARGIN   = 120 * scale
    LH_TITLE = 64 * scale     # 书名行高（加大）
    LH_META  = 46 * scale     # 元信息行高
    LH_SEC   = 50 * scale     # 章节标题行高
    LH_BODY  = 46 * scale     # 正文行高（加大间距）
    LH_QUOTE = 44 * scale     # 金句行高

    SECTION_GAP = 30 * scale  # 章节间距（加大）
    PARA_GAP    = 16 * scale   # 段落内间距

    W = 1024 * scale

    # ── 构建内容行（用于计算总高度） ──
    content_rows = []

    # 顶部留白
    content_rows.append(('blank', 80 * scale))

    # 日期
    content_rows.append(('meta', _TODAY_STR, font_meta, C_META, LH_META))

    # 留白
    content_rows.append(('blank', 24 * scale))

    # 书名
    content_rows.append(('title', f"《{book_data['title']}》", font_title, C_PURPLE, LH_TITLE))

    # 留白
    content_rows.append(('blank', 16 * scale))

    # 作者
    content_rows.append(('meta', f"作者：{book_data['author']}（{book_data['year']}）", font_meta, C_META, LH_META))

    # 分类
    content_rows.append(('meta', f"类别：{book_data['genre']}", font_meta, C_META, LH_META))

    # 评分
    content_rows.append(('meta', f"评分：{book_data['stars']}（豆瓣 {book_data['douban']}）", font_meta, C_META, LH_META))

    # 留白
    content_rows.append(('blank', SECTION_GAP))

    # 分隔线
    content_rows.append(('line', C_LINE))

    # 留白
    content_rows.append(('blank', SECTION_GAP))

    # ── 摘要 ──
    e_book = EMOJI['book'].resize((36 * scale, 36 * scale), Image.LANCZOS)
    content_rows.append(('section', '书籍摘要', font_section, C_BLUE, LH_SEC, e_book, MARGIN))
    content_rows.append(('blank', 10 * scale))
    for line in wrap_text(book_data['summary'], 26):
        content_rows.append(('body', line, font_main, C_BODY, LH_BODY))
    content_rows.append(('blank', SECTION_GAP))

    # 分隔线
    content_rows.append(('line', C_LINE))
    content_rows.append(('blank', SECTION_GAP))

    # ── 金句 ──
    e_speech = EMOJI['speech'].resize((36 * scale, 36 * scale), Image.LANCZOS)
    content_rows.append(('section', '金句摘录', font_section, C_BLUE, LH_SEC, e_speech, MARGIN))
    content_rows.append(('blank', 10 * scale))
    for q in book_data['quotes']:
        for line in wrap_text(q, 24):
            content_rows.append(('quote', line, font_main, C_BODY, LH_QUOTE))
        content_rows.append(('blank', PARA_GAP))
    content_rows.append(('blank', 10 * scale))

    # 分隔线
    content_rows.append(('line', C_LINE))
    content_rows.append(('blank', SECTION_GAP))

    # ── 推荐理由 ──
    e_light = EMOJI['light'].resize((36 * scale, 36 * scale), Image.LANCZOS)
    content_rows.append(('section', '推荐理由', font_section, C_BLUE, LH_SEC, e_light, MARGIN))
    content_rows.append(('blank', 10 * scale))
    for line in wrap_text(book_data['reason'], 26):
        content_rows.append(('body', line, font_main, C_BODY, LH_BODY))

    content_rows.append(('blank', SECTION_GAP))

    # 分隔线
    content_rows.append(('line', C_LINE))
    content_rows.append(('blank', SECTION_GAP))

    # ── 标签 ──
    tags_text = ' '.join(['#' + t for t in book_data['tags']])
    content_rows.append(('tags', '标签：' + tags_text, font_tag, C_META, LH_META))

    content_rows.append(('blank', 30 * scale))

    # 底部
    content_rows.append(('footer', '每天推荐一本好书，一起成长', font_small, C_LIGHT, LH_META))

    content_rows.append(('blank', 40 * scale))

    # ── 计算总高度 ──
    total_h = sum(r[1] if r[0] == 'blank' else r[4] if r[0] not in ('line',) else 2 * scale for r in content_rows)

    # ── 创建画布（居中排版） ──
    canvas = Image.new('RGB', (W, int(total_h)), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    cy = 0
    for row in content_rows:
        kind = row[0]
        if kind == 'blank':
            cy += row[1]
        elif kind == 'line':
            draw.line([(MARGIN, cy), (W - MARGIN, cy)], fill=row[1], width=2 * scale)
            cy += 2 * scale
        elif kind == 'section':
            text, font, color = row[1], row[2], row[3]
            emoji_img = row[5]
            paste_emoji(canvas, emoji_img, MARGIN, cy, 36 * scale)
            draw.text((MARGIN + 42 * scale, cy), text, fill=color, font=font)
            cy += row[4]
        elif kind == 'title':
            # 书名《比正文字符多约8px左侧字距，左调使视觉左对齐
            draw.text((MARGIN - 8 * scale, cy), row[1], fill=row[3], font=row[2])
            cy += row[4]
        elif kind == 'meta':
            draw.text((MARGIN, cy + 4 * scale), row[1], fill=row[3], font=row[2])
            cy += row[4]
        elif kind == 'body':
            draw.text((MARGIN, cy + 2 * scale), row[1], fill=row[3], font=row[2])
            cy += row[4]
        elif kind == 'quote':
            draw.text((MARGIN, cy + 2 * scale), '│', fill=C_ACCENT, font=row[2])
            draw.text((MARGIN + 24 * scale, cy + 2 * scale), row[1], fill=row[3], font=row[2])
            cy += row[4]
        elif kind == 'tags':
            draw.text((MARGIN, cy + 4 * scale), row[1], fill=row[3], font=row[2])
            cy += row[4]
        elif kind == 'footer':
            draw.text((MARGIN, cy), row[1], fill=row[3], font=row[2])
            cy += row[4]

    # 保存时缩小到目标尺寸（2x渲染的图直接保存，messenger会自动缩放）
    # LANCZOS抗锯齿已内嵌在2x渲染中
    canvas.save(output_path, 'PNG', optimize=True)
    print(f"OK: {output_path}")
    return output_path

# ─── Git push（收藏红线规范）──────────────────────────
def push_to_github(book_title: str, retries: int = 3, interval: int = 30):
    """发飞书后立即同步 GitHub（收藏红线规范），失败自动重试"""
    import subprocess, time
    workspace = "~/.openclaw/workspace"
    slug = book_title.replace(' ', '-').replace('·', '-')
    date_str = datetime.now(CST).strftime("%Y-%m-%d")
    analysis_file = f"{workspace}/collections/ideas/关联分析-{date_str}-{slug}.md"
    
    if not os.path.exists(analysis_file):
        print(f"[push_to_github] 文件不存在，跳过: {analysis_file}")
        return False
    
    for attempt in range(1, retries + 1):
        try:
            subprocess.run(['git', 'add', f'collections/ideas/关联分析-{date_str}-{slug}.md'],
                cwd=workspace, capture_output=True, text=True)
            subprocess.run(['git', 'commit', '-m', f'每日书籍推荐 {date_str}: {book_title}'],
                cwd=workspace, capture_output=True, text=True)
            result = subprocess.run(['git', 'push', 'origin', 'main'],
                cwd=workspace, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[push_to_github] ✅ 已推送: {book_title}")
                return True
            else:
                print(f"[push_to_github] ⚠️ 推送失败 (尝试 {attempt}/{retries}): {result.stderr[:100]}")
        except Exception as e:
            print(f"[push_to_github] ⚠️ 推送异常 (尝试 {attempt}/{retries}): {e}")
        if attempt < retries:
            print(f"[push_to_github] ⏳ {interval}秒后重试...")
            time.sleep(interval)
    print(f"[push_to_github] ❌ 推送失败，已用尽 {retries} 次重试: {book_title}")
    return False

# ─── Obsidian 同步（收藏红线规范）──────────────────────
def write_obsidian_book(book: dict, date_str: str, *, use_weread: bool = True):
    """生成 Obsidian 格式书籍文件（不含 related，等 sync_all 填充）
    优先使用微信读书热门划线（来自 get_book_card_content 已填充的 quotes），
    无数据时用书库 quotes。use_weread=True 表示 quotes 已是微信划线格式"""
    obsidian_path = "/root/Obsidian/收藏/书籍"
    slug = book["title"].replace(' ', '-').replace('·', '-')
    filepath = f"{obsidian_path}/{date_str}-{slug}.md"
    
    stars = '⭐' * (int(float(book["douban"]) // 2))
    rating = f"{stars}（{book['douban']}/10）"
    
    # 判断来源：有 weread_bookId 表示来自微信读书
    book_id = book.get("weread_bookId", '')
    if use_weread and book_id:
        excerpt_block = '\n'.join([f'> {q}' for q in book["quotes"]])
        excerpt_source = '微信读书热门划线'
    else:
        excerpt_block = '\n'.join([f'> {q}' for q in book["quotes"]])
        excerpt_source = '书库摘录'
        book_id = '27689981'
    
    content = f"""---
title: {book["title"]}
author: {book["author"]}
year: {book["year"]}
genre: {book["genre"]}
rating: {rating}
status: 已阅读
source: 每日书籍推荐
tags:
{chr(10).join([f' - {t}' for t in book["tags"]])}
weread_bookId: "{book_id}"
---

# {book["title"]}

**作者：** {book["author"]} · {book["year"]}年

**类型：** {book["genre"]}

**评分：** {rating}

---

## 摘要

{book.get("summary") or book.get("abstract")}

---

## 摘录（{excerpt_source}）

{excerpt_block}

---

## 推荐理由

{book["reason"]}
"""
    
    os.makedirs(obsidian_path, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print(f"[write_obsidian] ✅ 已写入 Obsidian: {filepath}")
    if use_weread and '微信读书' in excerpt_source:
        print(f"[write_obsidian] ✅ 使用微信读书热门划线")
    elif use_weread:
        print(f"[write_obsidian] ⚠️ 使用书库 quotes（无微信读书数据）")
    return filepath

# _get_recent_related_books 已移除，由 association_analysis.sync_all() 替代

def push_obsidian_github(book_title: str, date_str: str, retries: int = 3, interval: int = 30):
    """推送 Obsidian 书籍文件到 GitHub（关联分析完成后执行），失败自动重试"""
    import subprocess, time
    obsidian_repo = "/root/Obsidian"
    slug = book_title.replace(' ', '-').replace('·', '-')
    filepath = f"收藏/书籍/{date_str}-{slug}.md"
    
    full_path = f"{obsidian_repo}/{filepath}"
    if not os.path.exists(full_path):
        print(f"[push_obsidian] 文件不存在，跳过: {full_path}")
        return False
    
    for attempt in range(1, retries + 1):
        try:
            subprocess.run(['git', 'add', filepath], cwd=obsidian_repo, capture_output=True, text=True)
            subprocess.run(
                ['git', 'commit', '-m', f'每日书籍推荐 {date_str}: {book_title}'],
                cwd=obsidian_repo, capture_output=True, text=True
            )
            result = subprocess.run(
                ['git', 'push', 'origin', 'master'],
                cwd=obsidian_repo, capture_output=True, text=True,
                env={**os.environ, 'GIT_SSH_COMMAND': 'ssh -i ~/.ssh/id_ed25519'}
            )
            if result.returncode == 0:
                print(f"[push_obsidian] ✅ 已推送 Obsidian: {book_title}")
                return True
            else:
                print(f"[push_obsidian] ⚠️ 推送失败 (尝试 {attempt}/{retries}): {result.stderr[:100]}")
        except Exception as e:
            print(f"[push_obsidian] ⚠️ 推送异常 (尝试 {attempt}/{retries}): {e}")
        if attempt < retries:
            print(f"[push_obsidian] ⏳ {interval}秒后重试...")
            time.sleep(interval)
    print(f"[push_obsidian] ❌ 推送失败，已用尽 {retries} 次重试: {book_title}")
    return False

if __name__ == '__main__':
    # 从临时 JSON 文件读取今日书籍
    import json
    _tmp = "/tmp/today_book.json"
    if os.path.exists(_tmp):
        with open(_tmp, 'r') as _f:
            _today = json.load(_f)
    else:
        # fallback: 运行 run_daily_book_card 选书
        import subprocess
        _r = subprocess.run([sys.executable, str(Path(__file__).parent / 'run_daily_book_card.py')], capture_output=True, text=True)
        _today = json.loads(_r.stdout)
    _stars = str(_today.get("stars", "")).replace('⭐', '★')
    TODAY_BOOK = {
        "title": _today["title"],
        "author": _today["author"],
        "year": str(_today.get("year", "")) if _today.get("year", 0) > 0 else "",
        "genre": _today.get("genre", ""),
        "douban": _today["douban"],
        "stars": _stars,
        "summary": _today.get("abstract", ""),
        "quotes": _today.get("quotes", []) if isinstance(_today.get("quotes"), list) else [_today.get("quotes", "")] if _today.get("quotes") else [],
        "reason": _today.get("reason", ""),
        "tags": _today.get("tags", []),
    }
    _TODAY_STR = datetime.now(CST).strftime("%Y年%m月%d日")
    _TODAY_DATE = datetime.now(CST).strftime("%Y-%m-%d")

    book_slug = TODAY_BOOK["title"].replace(' ', '-').replace('·', '-')
    # 带日期的归档文件
    dated_output = os.path.expanduser(f"~/.openclaw/media/tool-image-generation/book_card_{_TODAY_DATE}.png")
    generate_card(TODAY_BOOK, dated_output)
    # 固定名称供飞书推送（同步覆盖）
    fixed_output = os.path.expanduser("~/.openclaw/media/tool-image-generation/book_card_pil_hd.png")
    import shutil
    shutil.copy(dated_output, fixed_output)
    print(f"书籍卡片已生成: {TODAY_BOOK['title']} by {TODAY_BOOK['author']}")

    # ─── 关联分析文件生成 ───
    collections_dir = os.path.expanduser("~/.openclaw/workspace/collections/ideas")
    os.makedirs(collections_dir, exist_ok=True)
    analysis_path = f"{collections_dir}/关联分析-{_TODAY_DATE}-{book_slug}.md"
    
    stars_display = '⭐' * int(TODAY_BOOK['douban'] // 2)
    content = f"""# 🔗 关联分析报告 · {_TODAY_DATE}

## 📌 本次收藏

**{TODAY_BOOK['title']}**

**标签**：`{'` `'.join(TODAY_BOOK['tags'])}`

**摘要**：📚 {TODAY_BOOK['title']}

> {TODAY_BOOK['author']} · {TODAY_BOOK['year']}年 · {TODAY_BOOK['genre']} · {stars_display}（{TODAY_BOOK['douban']}/10）
> 微信读书：`weread://reading?bId=27689981`

---

阅读摘要

{TODAY_BOOK['summary']}

---

## 💬 摘录

{chr(10).join([f'> {q}' for q in TODAY_BOOK['quotes']])}

---

## 📝 推荐理由

{TODAY_BOOK['reason']}
"""
    
    with open(analysis_path, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print(f"关联分析已生成: {analysis_path}")
    
    # ─── GitHub 同步（收藏红线） ───
    push_to_github(TODAY_BOOK['title'])

    # ─── Obsidian 同步（收藏红线）- 一次性完成写文件+关联分析+推送 ───
    obsidian_path = write_obsidian_book(TODAY_BOOK, _TODAY_DATE, use_weread=True)
    print(f"[sync_all] 开始关联分析: {obsidian_path}")
    result = run_analysis(obsidian_path)
    if result:
        print(f"[sync_all] ✅ 关联分析完成，强关联{result.get('strong_count',0)}个，中弱关联{result.get('medium_count',0)}个")
        print(f"[sync_all] 输出: {result.get('output', 'N/A')}")
    push_obsidian_github(TODAY_BOOK['title'], _TODAY_DATE)

