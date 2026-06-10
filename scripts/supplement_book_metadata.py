#!/usr/bin/env python3
"""
批量补充书籍元数据 v3 - 带检查点保存
"""

import json, subprocess, time, os, pickle, re

WEREAD_API_KEY = os.environ.get('WEREAD_API_KEY')
CHECKPOINT_FILE = '/tmp/books_checkpoint.json'
LOG_FILE = '/tmp/book_v3.log'

def log(msg):
    print(msg, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(msg + '\n')

def api_call(payload, retries=5):
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
                log(f'  [限流等待 10s...]')
                time.sleep(10)
                continue
            return data
        except Exception as e:
            time.sleep(3)
    return None

def get_book_info(book_id):
    return api_call({'api_name': '/book/info', 'bookId': str(book_id)})

def search_book(title, author=''):
    keyword = f"{title} {author}".strip()
    data = api_call({'api_name': '/store/search', 'keyword': keyword, 'count': 3})
    if not data:
        return None
    results = data.get('results', [])
    if not results:
        return None
    books = results[0].get('books', []) if isinstance(results[0], dict) else []
    if not books:
        return None
    for b in books:
        bi = b.get('bookInfo', {})
        bid = bi.get('bookId')
        if not bid:
            continue
        bt = bi.get('title', '')
        if title in bt or bt in title or (len(bt) > 2 and title[:2] in bt):
            info = get_book_info(bid)
            if info:
                info['_matchedTitle'] = bt
                return info
    return None

def normalize(s):
    return s.replace('、','').replace('，','').replace(' ','').replace('《','').replace('》','')

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_checkpoint(data):
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    start = time.time()
    
    # 加载数据
    with open('/tmp/books_parsed.pkl', 'rb') as f:
        existing_books = pickle.load(f)
    with open('/tmp/lee_shelf.json', 'r', encoding='utf-8') as f:
        shelf_books = json.load(f)
    
    # 加载检查点
    checkpoint = load_checkpoint()
    
    log('=== 批量补充书籍元数据 v3 ===')
    log(f'现有书籍: {len(existing_books)}, Lee书架: {len(shelf_books)}')
    
    existing_titles = {normalize(b['title']) for b in existing_books}
    
    # === 阶段1: Lee 书架新书 ===
    if 'shelf_done' not in checkpoint:
        shelf_added = 0
        for i, sb in enumerate(shelf_books):
            if not sb.get('bookId'):
                continue
            title = sb['title']
            if normalize(title) in existing_titles:
                continue
            
            log(f'[书架 {i+1}] {title} ')
            info = get_book_info(sb['bookId'])
            if info and info.get('intro'):
                intro = info.get('intro', '')
                author = info.get('author', sb.get('author', '')) or sb.get('author', '')
                rating = info.get('newRating', 0)
                genre = info.get('category', '')
                existing_books.append({
                    'title': title, 'author': author, 'year': 0, 'genre': genre,
                    'douban': rating / 100.0 if rating else 0, 'tags': [],
                    'abstract': intro,
                    'reason': f"来自 Lee 书架推荐：{genre} 领域佳作。",
                    'quotes': "（暂无热门划线数据）"
                })
                shelf_added += 1
                log(f'✓ {rating}')
            else:
                log('❌ 无简介')
            time.sleep(2.0)
            
            if (i+1) % 50 == 0:
                # 保存检查点
                save_checkpoint({'shelf_done': True, 'shelf_added': shelf_added, 'books': existing_books})
                log(f'  [检查点已保存: {shelf_added} 本]')
        
        checkpoint['shelf_done'] = True
        checkpoint['shelf_added'] = shelf_added
        checkpoint['books'] = existing_books
        save_checkpoint(checkpoint)
        log(f'书架阶段完成: +{shelf_added} 本')
    else:
        existing_books = checkpoint.get('books', existing_books)
        log(f'书架阶段已完成 ({checkpoint.get("shelf_added", 0)} 本)，跳过')
    
    # === 阶段2: 补充现有书籍 abstract ===
    log('\n=== 阶段2: 补充现有书籍 abstract ===')
    no_abs = [b for b in existing_books if not b.get('abstract')]
    log(f'缺abstract: {len(no_abs)} 本')
    
    # 按 title 去重
    seen = {}
    for b in no_abs:
        n = normalize(b['title'])
        if n not in seen:
            seen[n] = b
    
    unique = list(seen.values())
    log(f'去重后: {len(unique)} 本')
    
    supp_ok = checkpoint.get('supp_ok', 0)
    supp_fail = checkpoint.get('supp_fail', [])
    
    for i, book in enumerate(unique):
        title = book.get('title', '')
        if not title or len(title) < 2:
            continue
        
        idx = i + 1
        log(f'[{idx}/{len(unique)}] {title}')
        
        info = search_book(title, book.get('author', ''))
        if info and info.get('intro'):
            intro = info.get('intro', '')
            book['abstract'] = intro
            if not book.get('reason'):
                book['reason'] = f"涵盖 {book.get('genre', '该领域')} 的经典内容。"
            if not book.get('quotes'):
                book['quotes'] = "（暂无热门划线数据）"
            nr = info.get('newRating', 0)
            if nr > 0:
                book['douban'] = nr / 100.0
            supp_ok += 1
            log(f'✓ ({len(intro)}字)')
        else:
            supp_fail.append(title)
            log('❌')
        
        # 每20本保存检查点
        if (i+1) % 20 == 0:
            checkpoint['supp_ok'] = supp_ok
            checkpoint['supp_fail'] = supp_fail[-50:]  # 只保留最后50个失败
            checkpoint['books'] = existing_books
            save_checkpoint(checkpoint)
            elapsed = time.time() - start
            log(f'  [检查点] 补充{supp_ok}本, 失败{len(supp_fail)}本, 耗时{elapsed/60:.1f}分钟')
        
        time.sleep(3.0)  # 搜索接口更慢
    
    # === 完成 ===
    checkpoint['supp_ok'] = supp_ok
    checkpoint['supp_fail'] = supp_fail[-50:]
    checkpoint['books'] = existing_books
    save_checkpoint(checkpoint)
    
    complete = [b for b in existing_books if b.get('abstract') and b.get('reason') and b.get('quotes')]
    elapsed = time.time() - start
    
    log(f'\n=== 完成 ===')
    log(f'总书籍: {len(existing_books)} 本')
    log(f'完整(3字段): {len(complete)} 本')
    log(f'补充abstract成功: {supp_ok} 本')
    log(f'失败: {len(supp_fail)} 本')
    log(f'总耗时: {elapsed/60:.1f} 分钟')

if __name__ == '__main__':
    main()
