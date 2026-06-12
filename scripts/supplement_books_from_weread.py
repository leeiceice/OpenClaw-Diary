#!/usr/bin/env python3
"""
全量补 944 本 abstract（用微信读书 /book/info 拿 intro）— 并发版
- 8 并发
- 429/限流退避 60s
- 进度快写（10 本）
- 断点续传
"""
import json, os, time, sys, urllib.request, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore, Lock

# 1) 加载 .env
ENV = Path(os.path.expanduser('~/.openclaw/.env'))
if ENV.exists():
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

API = 'https://i.weread.qq.com/api/agent/gateway'
API_KEY = os.environ.get('WEREAD_API_KEY', '')

# 限流：极端保守（30s 间隔）
SEM = Semaphore(1)
RATE_LIMIT_SLEEP = 30.0  # 30s 间隔
WRITE_LOCK = Lock()

def call(api_name, params, retries=4):
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {API_KEY}'}
    payload = {'api_name': api_name, 'skill_version': '1.0.5', **params}
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(API, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8')), None
        except urllib.error.HTTPError as e:
            err = f'HTTP {e.code}'
            try:
                err = f'HTTP {e.code}: {e.read().decode("utf-8")[:100]}'
            except: pass
            if e.code == 429 or e.code == 503:
                # 限流：退避 10 分钟
                print(f'    [限流] 退避 10 分钟', flush=True)
                time.sleep(600)
                continue
            if attempt < retries:
                time.sleep(5 * attempt)
                continue
            return None, err
        except Exception as e:
            if attempt < retries:
                time.sleep(5 * attempt)
                continue
            return None, str(e)
    return None, 'max retries'

def gen_reason(b):
    genre = b.get('genre', '')
    if genre:
        return f'了解{genre}领域的经典作品。'
    return f'{b.get("author", "")}的代表作。'

# 2) 加载
with open('data/books.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)
data = raw.get('books', raw) if isinstance(raw, dict) else raw

# 3) 进度
PROG = 'data/weread_supplement_progress.json'
done = set()
fail = []
if Path(PROG).exists():
    with open(PROG, 'r') as f:
        d = json.load(f)
        done = set(d.get('done', []))
        fail = d.get('fail', [])

# 4) 找空 abstract 的（标题索引）
title_to_book = {b['title']: b for b in data}
need = [b for b in data if not b.get('abstract') and b['title'] not in done]
print(f'待补: {len(need)} 本 (已 done={len(done)} fail={len(fail)})', flush=True)

# 5) 处理单本
results_lock = Lock()
results_ok = []
results_fail = []

def process_one(book):
    title = book['title']
    if book.get('abstract'):
        return 'skip'
    SEM.acquire()
    try:
        # 1) 搜
        time.sleep(RATE_LIMIT_SLEEP)
        s, err = call('/store/search', {'keyword': title, 'scope': 10, 'count': 5})
        if err:
            return ('fail', title, f'search: {err}')
        if s.get('errcode', 0) not in (0, None):
            return ('fail', title, f'errcode={s.get("errcode")}')

        found = None
        for group in s.get('results', []):
            for x in group.get('books', []):
                bi = x.get('bookInfo', {})
                bid = str(bi.get('bookId', ''))
                if bid and bid != '0':
                    found = bid
                    break
            if found: break
        if not found:
            return ('fail', title, 'no bookId')

        # 2) intro
        time.sleep(RATE_LIMIT_SLEEP)
        info, err = call('/book/info', {'bookId': found})
        if err:
            return ('fail', title, f'info: {err}')
        intro = info.get('intro', '').strip()
        if not intro:
            return ('fail', title, f'no intro bid={found}')

        # 3) 划线
        time.sleep(RATE_LIMIT_SLEEP)
        bm, _ = call('/book/bestbookmarks', {'bookId': found})
        quotes = []
        if bm and bm.get('items'):
            for item in bm['items'][:10]:
                text = item.get('markText', '').strip()
                if text:
                    count = item.get('totalCount', 0)
                    quotes.append(f'{text}（{count}人划线）' if count > 1 else text)

        # 4) 写回
        book['abstract'] = intro
        book['reason'] = gen_reason(book)
        book['quotes'] = quotes
        book['weread_bookId'] = found
        if info.get('category'):
            book['weread_category'] = info['category']
        return ('ok', title, None)
    finally:
        SEM.release()

# 6) 并发主循环
start = time.time()
processed = 0
SAVE_EVERY = 10

with ThreadPoolExecutor(max_workers=1) as ex:
    futures = {ex.submit(process_one, b): b for b in need}
    for fut in as_completed(futures):
        b = futures[fut]
        try:
            r = fut.result()
        except Exception as e:
            r = ('fail', b['title'], str(e))

        with results_lock:
            if r == 'skip':
                continue
            status, title, err = r
            if status == 'ok':
                results_ok.append(title)
            else:
                results_fail.append((title, err))
            processed += 1

            if processed % 25 == 0:
                elapsed = time.time() - start
                speed = len(results_ok) / elapsed if elapsed > 0 else 0
                print(f'  [ok={len(results_ok)} fail={len(results_fail)} | {speed:.1f} 本/s] 最新: {title}', flush=True)

            if processed % SAVE_EVERY == 0:
                with open('data/books.json', 'w', encoding='utf-8') as f:
                    json.dump(raw, f, ensure_ascii=False, indent=2)
                all_done = list(done | set(results_ok))
                with open(PROG, 'w') as f:
                    json.dump({'done': all_done, 'fail': results_fail + fail}, f, ensure_ascii=False)
                print(f'  💾 进度（ok={len(results_ok)} fail={len(results_fail)}）', flush=True)

# 7) 最终写回
with open('data/books.json', 'w', encoding='utf-8') as f:
    json.dump(raw, f, ensure_ascii=False, indent=2)
all_done = list(done | set(results_ok))
with open(PROG, 'w') as f:
    json.dump({'done': all_done, 'fail': results_fail + fail}, f, ensure_ascii=False)

elapsed = time.time() - start
print(f'\n=== 全量完成 ===', flush=True)
print(f'耗时: {elapsed:.1f}s', flush=True)
print(f'本轮成功: {len(results_ok)}', flush=True)
print(f'本轮失败: {len(results_fail)}', flush=True)
print(f'历史总 done: {len(all_done)}', flush=True)
print(f'速度: {len(results_ok)/elapsed:.2f} 本/s', flush=True)
if results_fail:
    print(f'\n失败样例:', flush=True)
    for t, why in results_fail[:10]:
        print(f'  {t}: {why}', flush=True)
