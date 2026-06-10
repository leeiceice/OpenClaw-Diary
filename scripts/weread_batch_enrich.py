#!/usr/bin/env python3
"""
weread_batch_enrich.py - 微信读书批量补充书籍元数据
从 Lee 的书架 API 批量获取书籍热门划线，自动补充到 BOOKS 书库

用法:
  python3 weread_batch_enrich.py [--dry-run] [--limit N]

流程:
  1. 从 weread 书架 API 获取 Lee 的书籍列表
  2. 对每本书：搜索 → 获取 bestbookmarks → 提取 abstract/quotes
  3. 更新 daily_book_card_prompt.py 中的 BOOKS 条目
  4. git commit + push

注意:
  - 需要 WEREAD_API_KEY 环境变量
  - API 有频率限制，每次请求间隔 2 秒
  - 使用 --dry-run 先预览不实际写入
"""
import os
import sys
import json
import time
import argparse
import urllib.request
import re
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("~/.openclaw/workspace").expanduser()
BOOKS_FILE = WORKSPACE / "scripts/daily_book_card_prompt.py"
LOCK_FILE = "/tmp/daily_book_lock.json"

# ========================
# 微信读书 API
# ========================

def load_api_key():
    env_file = WORKSPACE / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())
    key = os.environ.get('WEREAD_API_KEY')
    if not key:
        raise ValueError("WEREAD_API_KEY not found in environment or .env file")
    return key


def weread_api(body, key, retries=3):
    """调用微信读书 API"""
    req = urllib.request.Request(
        'https://i.weread.qq.com/api/agent/gateway',
        data=json.dumps(body).encode(),
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
        method='POST'
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"  [WARN] Attempt {attempt+1} failed: {e}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  [ERROR] All {retries} attempts failed: {e}")
                return None


def fetch_book_highlights(key, title, author=""):
    """获取单本书的热门划线"""
    # 1. 搜索书籍
    sr = weread_api({
        'api_name': '/store/search',
        'keyword': title,
        'count': 5,
        'skill_version': '1.0.3'
    }, key)
    if not sr or 'results' not in sr:
        return None

    # 匹配最接近的一本
    book_id = None
    best_match = None
    for grp in sr.get('results', []):
        for b in grp.get('books', []):
            bi = b.get('bookInfo', {})
            # 优先精确匹配作者
            if author and author in bi.get('author', ''):
                best_match = bi
                book_id = bi.get('bookId')
                break
            elif title in bi.get('title', ''):
                if best_match is None:
                    best_match = bi
                    book_id = bi.get('bookId')
        if book_id:
            break

    if not book_id or not best_match:
        return None

    # 2. 获取热门划线
    br = weread_api({
        'api_name': '/book/bestbookmarks',
        'bookId': book_id,
        'chapterUid': 0,
        'skill_version': '1.0.3'
    }, key)
    if not br:
        return None

    chapters = {c['chapterUid']: c.get('title', '') for c in br.get('chapters', [])}
    highlights = []
    for item in br.get('items', [])[:10]:
        cu = item.get('chapterUid', 0)
        text = item.get('markText', '')[:200]
        if text:
            highlights.append({
                'text': text,
                'chapter': chapters.get(cu, ''),
                'count': item.get('totalCount', 0)
            })

    return {
        'bookId': book_id,
        'rating': best_match.get('newRating', 0),
        'highlights': highlights,
        'matchedTitle': best_match.get('title', '')
    }


def normalize(s):
    """归一化书名"""
    s = re.sub(r'[（(][^)）]*[)）]', '', s)
    return s.replace('、', '').replace('，', '').replace(' ', '').strip()


# ========================
# BOOKS 文件更新
# ========================

def load_books():
    """从 daily_book_card_prompt.py 加载 BOOKS 列表（内存中解析）"""
    content = BOOKS_FILE.read_text()
    # 简单提取：找到 BOOKS = [ 到 ] 之间的所有 dict
    m = re.search(r'^BOOKS\s*=\s*\[', content, re.MULTILINE)
    if not m:
        raise ValueError("Cannot find BOOKS list in script")

    start = m.end()
    # 找到对应的结束 ]
    depth = 0
    end = start
    for i, c in enumerate(content[start:], start):
        if c == '[':
            depth += 1
        elif c == ']':
            if depth == 0:
                end = i
                break
            depth -= 1

    books_text = content[start:end]
    # 用正则匹配每个 dict
    books = []
    # 匹配 {"title": "...", "author": "...", ...},
    # 简单策略：逐行读取，手动解析
    # 这里用 ast.literal_eval 的简化版
    import ast
    try:
        books = ast.literal_eval('[' + books_text + ']')
    except Exception as e:
        print(f"[WARN] Failed to parse BOOKS with ast: {e}")
        # 回退：返回空列表
        books = []
    return books


def update_books_entry(books, title, new_fields):
    """更新 BOOKS 中指定书名的条目"""
    for book in books:
        if book.get('title') == title:
            book.update(new_fields)
            return True
    return False


def save_books(books):
    """将更新后的 BOOKS 写回文件"""
    # 读取文件
    content = BOOKS_FILE.read_text()
    # 找到 BOOKS 块
    m = re.search(r'^BOOKS\s*=\s*\[', content, re.MULTILINE)
    start = m.start()
    # 找到结束位置
    depth = 0
    end_pos = m.end()
    for i, c in enumerate(content[m.end():], m.end()):
        if c == '[':
            depth += 1
        elif c == ']':
            if depth == 0:
                end_pos = i
                break
            depth -= 1

    # 生成新的 BOOKS 内容
    books_repr = 'BOOKS = [\n'
    for book in books:
        books_repr += '    ' + repr(book).replace('}, ', '},\n    ') + ',\n'
    books_repr += ']\n'

    new_content = content[:start] + books_repr + content[end_pos+1:]
    BOOKS_FILE.write_text(new_content)


def get_incomplete_books():
    """获取所有 incomplete 的书籍（无 abstract/reason/quotes）"""
    books = load_books()
    incomplete = [b for b in books if not (b.get('abstract') and b.get('reason') and b.get('quotes'))]
    return incomplete


def build_reason_from_highlights(title, author, highlights):
    """从热门划线自动生成 reason"""
    if not highlights:
        return ""
    # 简单策略：取最高 count 的划线，结合主题生成 reason
    top = highlights[0]['text'][:50]
    return f"微信读书热门划线书籍，高赞读者的选择：{top}..."


# ========================
# 主流程
# ========================

def main():
    parser = argparse.ArgumentParser(description='微信读书批量补充书籍元数据')
    parser.add_argument('--dry-run', action='store_true', help='只预览不写入')
    parser.add_argument('--limit', type=int, default=0, help='最多处理 N 本（0=全部）')
    parser.add_argument('--since', type=int, default=0, help='只处理最近 N 天新增的 incomplete 书')
    parser.add_argument('--sleep', type=int, default=2, help='每次 API 调用间隔秒数')
    args = parser.parse_args()

    print(f"[weread_batch_enrich] 开始批量补充元数据")
    print(f"  dry-run: {args.dry_run}")
    print(f"  sleep between calls: {args.sleep}s")

    key = load_api_key()

    # 加载当前 BOOKS
    books = load_books()
    print(f"  当前 BOOKS: {len(books)} 本")

    incomplete = [b for b in books if not (b.get('abstract') and b.get('reason') and b.get('quotes'))]
    print(f"  incomplete: {len(incomplete)} 本")

    if args.limit > 0:
        incomplete = incomplete[:args.limit]

    if not incomplete:
        print("[INFO] 没有需要补充的 incomplete 书籍")
        return

    print(f"\n[INFO] 开始处理 {len(incomplete)} 本书...")
    updated = 0
    failed = 0

    for i, book in enumerate(incomplete):
        title = book.get('title', '')
        author = book.get('author', '')
        print(f"\n[{i+1}/{len(incomplete)}] {title} ({author})")

        result = fetch_book_highlights(key, title, author)
        if not result or not result['highlights']:
            print(f"  [SKIP] 无热门划线数据")
            failed += 1
            continue

        highlights = result['highlights']
        print(f"  [OK] bookId={result['bookId']}, rating={result['rating']}, {len(highlights)} 条划线")
        print(f"  TOP: {highlights[0]['text'][:60]}")

        # 生成新字段
        new_fields = {
            'abstract': f"微信读书热门书籍。{highlights[0]['text'][:100]}...",
            'quotes': [h['text'] for h in highlights[:5]],
            'reason': build_reason_from_highlights(title, author, highlights)
        }

        if args.dry_run:
            print(f"  [DRY-RUN] 会更新为: abstract={new_fields['abstract'][:40]}...")
        else:
            if update_books_entry(books, title, new_fields):
                updated += 1
                print(f"  [UPDATED]")
            else:
                print(f"  [ERROR] 更新失败")

        time.sleep(args.sleep)

    print(f"\n[RESULT] 更新 {updated} 本, 失败 {failed} 本")

    if updated > 0 and not args.dry_run:
        print("\n[INFO] 保存更新到文件...")
        save_books(books)

        print("\n[INFO] Git 提交...")
        import subprocess
        try:
            r = subprocess.run(['git', 'add', 'scripts/daily_book_card_prompt.py'],
                             cwd=WORKSPACE, capture_output=True, text=True)
            r2 = subprocess.run(['git', 'commit', '-m',
                                f'feat(books): 批量补充 {updated} 本书籍元数据 - weread_batch_enrich'],
                                cwd=WORKSPACE, capture_output=True, text=True)
            r3 = subprocess.run(['git', 'push'],
                                cwd=WORKSPACE, capture_output=True, text=True)
            if r3.returncode == 0:
                print("[OK] 已推送 GitHub")
            else:
                print(f"[WARN] Git push failed: {r3.stderr}")
        except Exception as e:
            print(f"[ERROR] Git 操作失败: {e}")

    print("\n[INFO] 完成!")


if __name__ == '__main__':
    main()
