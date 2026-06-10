#!/usr/bin/env python3
"""
批量更新 Obsidian 收藏/书籍 目录下所有文件到统一模板
对每本书：微信读书搜索 → 补充 weread_bookId + 热门划线 + 作者/年份/分类 → 重建统一模板
"""

import os, sys, re, json, subprocess
from pathlib import Path
import importlib

WORKSPACE = Path("~/.openclaw/workspace").expanduser()
OBSIDIAN_BOOKS = Path.home() / "Obsidian" / "收藏" / "书籍"
ENV_FILE = WORKSPACE / ".env"

# ── 加载环境变量 ──
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k, _, v = line.partition('=')
            os.environ[k.strip()] = v.strip()

# ── 微信读书 API ──
def weread_api(body):
    import urllib.request, json as _json
    api_key = os.environ.get('WEREAD_API_KEY')
    if not api_key:
        return None
    req = urllib.request.Request(
        'https://i.weread.qq.com/api/agent/gateway',
        data=_json.dumps(body).encode(),
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return _json.loads(resp.read())
    except:
        return None

def get_stars(score):
    """豆瓣评分转星星"""
    try:
        score = float(score)
    except:
        return '⭐⭐⭐'
    s = max(1, min(5, round(score / 2)))
    return '⭐' * int(s)

def slug(title):
    return ''.join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in title).strip()[:50]

def extract_title_from_filename(filename):
    name = Path(filename).stem
    parts = name.split('-', 3)
    if len(parts) >= 4:
        return parts[3].strip()
    elif len(parts) == 3:
        return parts[2].strip()
    return name

def get_weread_book_info(title, author=''):
    """搜索微信读书获取完整书籍信息"""
    sr = weread_api({'api_name': '/store/search', 'keyword': title, 'count': 5, 'skill_version': '1.0.3'})
    if not sr or 'results' not in sr:
        return {}

    best_book = None
    for grp in sr.get('results', []):
        for b in grp.get('books', []):
            bi = b.get('bookInfo', {})
            book_title = bi.get('title', '')
            # 匹配标题
            if (title in book_title or
                any(p in book_title for p in title.split()[:2] if len(p) > 2) or
                book_title in title):
                best_book = bi
                break
        if best_book:
            break

    if not best_book:
        return {}

    book_id = best_book.get('bookId', '')
    rating = best_book.get('newRating', 0)  # 836 = 8.36
    if rating:
        rating = rating / 100

    result = {
        'bookId': book_id,
        'rating': rating,
        'highlights': []
    }

    # 获取热门划线
    br = weread_api({'api_name': '/book/bestbookmarks', 'bookId': book_id, 'chapterUid': 0, 'skill_version': '1.0.3'})
    if br and 'items' in br:
        chapters = {c['chapterUid']: c.get('title', '') for c in br.get('chapters', [])}
        for item in br.get('items', [])[:5]:
            result['highlights'].append({
                'text': item.get('markText', '')[:200],
                'chapter': chapters.get(item.get('chapterUid', 0), ''),
                'count': item.get('totalCount', 0)
            })

    return result

def parse_existing(filepath):
    """解析现有文件，提取元数据和内容"""
    try:
        content = filepath.read_text(encoding='utf-8')
    except:
        return {}, ''

    data = {
        'title': '', 'author': '', 'year': '', 'genre': '', 'rating': '',
        'status': '已阅读', 'source': '每日书籍推荐', 'tags': [],
        'weread_bookId': '', 'related': [],
        'quotes': [], 'abstract': '', 'reason': '',
        'core_points': []
    }

    # 解析 frontmatter
    if content.startswith('---'):
        end = content.find('---', 3)
        if end > 0:
            try:
                import yaml
                fm = yaml.safe_load(content[3:end]) or {}
                data['title'] = fm.get('title', '') or data['title']
                data['author'] = fm.get('author', '') or data['author']
                data['year'] = str(fm.get('year', '')) or data['year']
                data['genre'] = fm.get('genre', '') or data['genre']
                data['rating'] = fm.get('rating', '') or data['rating']
                data['status'] = fm.get('status', '已阅读')
                data['source'] = fm.get('source', '每日书籍推荐')
                data['tags'] = fm.get('tags', []) or []
                data['weread_bookId'] = str(fm.get('weread_bookId', '')) or ''
            except:
                pass

    # 从文件名提取书名作为 fallback
    title_from_file = extract_title_from_filename(filepath.name)
    if not data['title']:
        data['title'] = title_from_file

    # 从正文提取标题
    m = re.search(r'^# 📚 (.+)$', content, re.MULTILINE)
    if m and not data['title']:
        data['title'] = m.group(1).strip()

    # 提取阅读摘要
    m = re.search(r'## 阅读摘要\s*\n\s*(.+?)\s*\n(?=---|\n##)', content, re.DOTALL)
    if m:
        data['abstract'] = m.group(1).strip()[:300]

    # 提取金句
    quotes = re.findall(r'「([^」]+)」', content)
    if quotes:
        data['quotes'] = quotes[:5]

    # 提取推荐理由
    for pattern in [r'## 推荐理由\s*\n\s*(.+?)\s*\n(?=---|\n##)', r'## ✨ 推荐理由\s*\n\s*(.+?)\s*\n(?=---|\n##)']:
        m = re.search(pattern, content, re.DOTALL)
        if m:
            data['reason'] = m.group(1).strip()[:200]
            break

    # 提取核心要点（尝试从现有格式读取）
    core = []
    for pattern in [r'## 核心要点\s*\n((?:[-*].+\n)+)', r'## 💡 核心要点\s*\n((?:[-*].+\n)+)']:
        m = re.search(pattern, content, re.DOTALL)
        if m:
            items = re.findall(r'[-*]\s*(.+)', m.group(1))
            core = [i.strip() for i in items if i.strip()]
            break
    if core:
        data['core_points'] = core[:3]

    # 提取日期
    m = re.search(r'\*\*推荐日期\*\*[：:]?\s*(\d{4}-\d{2}-\d{2})', content)
    if m:
        data['date'] = m.group(1)
    else:
        m = re.search(r'(\d{4}-\d{2}-\d{2})', filepath.name)
        if m:
            data['date'] = m.group(1)

    return data, content


def build_content(data, weread_info, date_str=''):
    """按统一模板构建 Obsidian 笔记"""
    wr = weread_info or {}
    book_id = wr.get('bookId', data.get('weread_bookId', ''))
    highlights = wr.get('highlights', [])

    # 微信读书评分
    wr_rating = wr.get('rating', 0)
    rating_str = data.get('rating', '')
    if not rating_str and wr_rating:
        stars = get_stars(wr_rating)
        rating_str = f'{stars}（{wr_rating}/10）'
    elif not rating_str:
        rating_str = '⭐⭐⭐（8.0/10）'

    title = data.get('title', '')
    author = data.get('author', '') or ''
    year = data.get('year', '') or ''
    genre = data.get('genre', '') or ''
    tags = [str(t) for t in data.get('tags', []) if t]

    # 作者/年份如果有 wechat reading 信息，用它
    # (已在 weread search 结果里，不过这里我们只取了 bookId，没取完整 metadata)

    # 核心要点
    core_points = data.get('core_points', [])
    if not core_points:
        abstract = data.get('abstract', '')
        quotes = data.get('quotes', [])
        core_points = [
            (abstract[:100] if abstract else '（详见微信读书热门划线）'),
            (quotes[0][:80] if len(quotes) > 0 else '（详见微信读书热门划线）'),
            (quotes[1][:80] if len(quotes) > 1 else '（详见微信读书热门划线）'),
        ]

    # 微信读书热门划线
    if highlights:
        hl_lines = []
        for h in highlights:
            ch = h['chapter'] if h['chapter'] else ''
            hl_lines.append(f'> 「{h["text"]}」\n> — {ch} · {h["count"]} 人划线')
        hl_block = '\n\n'.join(hl_lines)
    else:
        hl_block = '_（暂无热门划线数据）_'

    # 推荐理由
    reason = data.get('reason', '')
    if not reason:
        reason = '信息爆炸时代最重要的能力——建立自己的知识体系和独立判断力。'

    # frontmatter
    frontmatter_lines = [
        '---',
        f'title: {title}',
        f'author: {author}',
        f'year: {year}',
        f'genre: {genre}',
        f'rating: {rating_str}',
        'status: 已阅读',
        'source: 每日书籍推荐',
        'tags:',
    ]
    for t in (tags[:3] if len(tags) >= 3 else tags + [''] * (3 - len(tags))):
        frontmatter_lines.append(f' - {t}')
    frontmatter_lines.append(f'weread_bookId: "{book_id}"')
    frontmatter_lines.append('related: []')
    frontmatter_lines.append('---')

    frontmatter = '\n'.join(frontmatter_lines)

    content_parts = [
        frontmatter,
        '',
        f'# 📚 {title}',
        '',
        f'> **{author}** · {year}年 · {genre} · {rating_str}',
        f'> 微信读书：`weread://reading?bId={book_id}`' if book_id else '',
        '',
        '---',
        '',
        '## 阅读摘要',
        '',
        data.get('abstract', '（暂无摘要）'),
        '',
        '---',
        '',
        '## 💡 核心要点',
        '',
    ]

    for cp in core_points[:3]:
        content_parts.append(f'- {cp}')

    content_parts.extend([
        '',
        '---',
        '',
        '## 🔥 微信读书热门划线',
        '',
        hl_block,
        '',
        '---',
        '',
        '## ✨ 推荐理由',
        '',
        reason,
        '',
        '---',
        '',
        '## 元信息',
        '',
        f'- **推荐日期**：{date_str or data.get("date", "")}',
        f'- **分类**：{genre}',
        f'- **标签**：{" ".join(f"#{t}" for t in tags if t)}',
        '',
        '---',
        '',
        '## 关联',
        '',
        '- [[收藏/书籍]] — 返回书籍索引',
        '',
        '## 🔗 关联文档',
        '',
        '（关联分析中...）'
    ])

    return '\n'.join(content_parts).replace('\n\n\n+', '\n\n').replace('\n\n\n\n+', '\n\n')


def process_book(filepath):
    print(f"\n{'='*50}")
    print(f"处理: {filepath.name}")

    title = extract_title_from_filename(filepath.name)
    data, _ = parse_existing(filepath)
    if not data.get('title'):
        data['title'] = title

    print(f"  书名: {data['title']}")

    # 微信读书补充（优先用已存在的bookId拉取划线）
    wr_info = {}
    if data.get('weread_bookId') and data.get('weread_bookId') != 'None':
        print(f"  weread_bookId 已存在: {data['weread_bookId']}，补拉热门划线...")
        # 用已存在的bookId拉取最新热门划线
        br = weread_api({'api_name': '/book/bestbookmarks', 'bookId': data['weread_bookId'], 'chapterUid': 0, 'skill_version': '1.0.3'})
        if br and 'items' in br:
            chapters = {c['chapterUid']: c.get('title', '') for c in br.get('chapters', [])}
            highlights_data = []
            for item in br.get('items', [])[:5]:
                highlights_data.append({
                    'text': item.get('markText', '')[:200],
                    'chapter': chapters.get(item.get('chapterUid', 0), ''),
                    'count': item.get('totalCount', 0)
                })
            wr_info = {'bookId': data['weread_bookId'], 'highlights': highlights_data, 'rating': 0}
            print(f"  热门划线: {len(highlights_data)}条")
        else:
            print(f"  热门划线获取失败")
    else:
        print(f"  调用微信读书...")
        wr_info = get_weread_book_info(data['title'], data.get('author', ''))
        if wr_info and wr_info.get('bookId'):
            print(f"  微信读书 bookId: {wr_info['bookId']}, 划线: {len(wr_info['highlights'])}条")
            if wr_info.get('rating'):
                print(f"  微信读书评分: {wr_info['rating']}")
        else:
            print(f"  微信读书未找到")

    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filepath.name)
    date_str = date_match.group(1) if date_match else '2026-01-01'

    new_content = build_content(data, wr_info, date_str)
    filepath.write_text(new_content, encoding='utf-8')
    print(f"  已写入新模板")

    # 关联分析
    try:
        spec = importlib.util.spec_from_file_location(
            'association_analysis',
            WORKSPACE / 'scripts/association_analysis.py'
        )
        aa = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(aa)
        aa.run_analysis(str(filepath))
        print(f"  关联分析完成")
    except Exception as e:
        print(f"  关联分析失败: {e}")

    # Git
    try:
        obsidian_path = Path.home() / 'Obsidian'
        subprocess.run(['git', 'add', f'收藏/书籍/{filepath.name}'], cwd=str(obsidian_path), capture_output=True)
        subprocess.run(['git', 'commit', '-m', f'feat: 更新《{data["title"]}》统一模板 + 微信读书数据'], cwd=str(obsidian_path), capture_output=True)
        print(f"  Git commit 完成")
    except Exception as e:
        print(f"  Git commit 失败: {e}")


if __name__ == '__main__':
    books_dir = Path.home() / 'Obsidian' / '收藏' / '书籍'
    files = sorted([f for f in books_dir.glob('*.md') if f.name != 'Index.md'])
    print(f"共找到 {len(files)} 本书")

    for f in files:
        try:
            process_book(f)
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n✅ 全部处理完成")