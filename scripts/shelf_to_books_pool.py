#!/usr/bin/env python3
"""
长期脚本：从 Lee 的微信读书书架批量抓取书籍元数据，自动补充书库
每次运行：拉取书架 → 获取元数据 → 追加到书库
建议 cron：每日或每周运行
"""

import json, subprocess, time, os, pickle
from datetime import datetime
from _timezone import CST

WEREAD_API_KEY = os.environ.get('WEREAD_API_KEY')
BOOKS_POOL_FILE = '/tmp/books_pool.pkl'
SHELF_LOG = '/tmp/shelf_crawl_log.json'

def api_call(payload, retries=3):
    cmd = [
        'curl', '-s', '-X', 'POST', 'https://i.weread.qq.com/api/agent/gateway',
        '-H', f'Authorization: Bearer {WEREAD_API_KEY}',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps(payload)
    ]
    for attempt in range(retries):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            data = json.loads(r.stdout)
            ec = data.get('errcode')
            if ec is None or ec == 0:
                return data
            if ec == -2014:
                time.sleep(10)
                continue
            return data
        except Exception as e:
            time.sleep(2)
    return None

def normalize(s):
    return s.replace('、','').replace('，','').replace(' ','').replace('《','').replace('》','')

def load_books_pool():
    if os.path.exists(BOOKS_POOL_FILE):
        with open(BOOKS_POOL_FILE, 'rb') as f:
            return pickle.load(f)
    return []

def save_books_pool(books):
    with open(BOOKS_POOL_FILE, 'wb') as f:
        pickle.dump(books, f)

def get_book_info(book_id):
    return api_call({'api_name': '/book/info', 'bookId': str(book_id)})

def fetch_shelf():
    """获取 Lee 的完整书架"""
    data = api_call({'api_name': '/shelf/sync', 'count': 500})
    if not data or data.get('errcode') != None and data.get('books') is None:
        return []
    return data.get('books', [])

def main():
    print(f'[{datetime.now(CST).strftime("%Y-%m-%d %H:%M")}] 开始抓取书架...')
    
    # 加载现有书库
    pool = load_books_pool()
    existing_titles = {normalize(b['title']) for b in pool if b.get('title')}
    print(f'现有书库: {len(pool)} 本')
    
    # 抓取书架
    shelf = fetch_shelf()
    print(f'书架书籍: {len(shelf)} 本')
    
    # 过滤非书籍
    skip = ['连载', '番外', '情色', '加料版', '二次修改版', 'z-lib']
    new_books = []
    for b in shelf:
        title = b.get('title', '')
        if any(k in title for k in skip):
            continue
        if not b.get('bookId'):
            continue
        if normalize(title) in existing_titles:
            continue
        new_books.append({'title': title, 'bookId': b.get('bookId'), 'author': b.get('author', '')})
    
    print(f'新增书籍: {len(new_books)} 本')
    
    if not new_books:
        print('无新增书籍，退出')
        return
    
    # 获取元数据
    added = 0
    for i, nb in enumerate(new_books):
        print(f'[{i+1}/{len(new_books)}] {nb["title"]}', end=' ')
        info = get_book_info(nb['bookId'])
        if info and info.get('intro'):
            intro = info.get('intro', '')
            book = {
                'title': nb['title'],
                'author': info.get('author', nb['author']) or nb['author'],
                'year': 0,
                'genre': info.get('category', ''),
                'douban': info.get('newRating', 0) / 100.0,
                'tags': [],
                'abstract': intro,
                'reason': f"来自 Lee 书架：{info.get('category', '')} 领域。",
                'quotes': "（暂无热门划线数据）"
            }
            pool.append(book)
            added += 1
            print(f'✓')
        else:
            print('❌ 无简介，跳过')
        time.sleep(0.8)
    
    save_books_pool(pool)
    
    # 记录日志
    log = {'date': datetime.now(CST).isoformat(), 'added': added, 'total': len(pool)}
    with open(SHELF_LOG, 'w') as f:
        json.dump(log, f)
    
    print(f'\n完成！本次新增 {added} 本，书库共 {len(pool)} 本')

if __name__ == '__main__':
    main()
