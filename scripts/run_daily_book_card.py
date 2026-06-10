#!/usr/bin/env python3
"""运行每日书籍卡片生成 - 修复 import 问题"""
import sys, os, json, random, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime
from _timezone import CST

sys.path.insert(0, str(Path(__file__).parent))

# 直接从 daily_book_card_prompt 拿 BOOKS 数据
from daily_book_card_prompt import BOOKS

# 加载 .env 环境变量
ENV_FILE = Path(os.path.expanduser("~/.openclaw/.env"))
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

_LOCK_FILE = "/tmp/daily_book_lock.json"
_HISTORY_FILE = os.path.expanduser("~/.openclaw/workspace/data/book_history.json")
_WEREAD_API = "https://i.weread.qq.com/api/agent/gateway"

def call_weread(api_name: str, params: dict = {}, retries: int = 3, interval: int = 15):
    """调用微信读书 API，失败自动重试"""
    api_key = os.environ.get("WEREAD_API_KEY", "")
    if not api_key:
        print("[weread] ⚠️ WEREAD_API_KEY 未配置，跳过划线拉取")
        return None
    
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {"api_name": api_name, "skill_version": "1.0.5", **params}
    
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                _WEREAD_API,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')[:200]
            print(f"[weread] HTTP {e.code} (尝试 {attempt}/{retries}): {body}")
        except Exception as e:
            print(f"[weread] 异常 (尝试 {attempt}/{retries}): {e}")
        if attempt < retries:
            print(f"[weread] ⏳ {interval}秒后重试...")
            time.sleep(interval)
    return None

def sync_book_quotes(book: dict) -> dict:
    """拉取微信读书热门划线，失败自动重试；无 bookId 时自动搜索获取"""
    book_id = book.get("weread_bookId", "") or book.get("bookId", "")
    title = book.get("title", "")
    
    # 无有效 bookId → 先搜索获取 bookId
    if not book_id or book_id == "27689981":
        print(f"[weread] 无 bookId，搜索书名获取: {title}")
        search_data = call_weread("/store/search", {
            "keyword": title,
            "scope": 10,  # 电子书
            "count": 5
        })
        
        if search_data and search_data.get("results"):
            for group in search_data["results"]:
                if group.get("books"):
                    for b in group["books"]:
                        bi = b.get("bookInfo", {})
                        found_id = str(bi.get("bookId", ""))
                        if found_id and found_id != "0":
                            book_id = found_id
                            print(f"[weread] ✅ 找到 bookId: {book_id} - {bi.get('title')}")
                            break
                if book_id and book_id != "27689981":
                    break
        
        if not book_id or book_id == "27689981":
            print(f"[weread] ⚠️ 搜索未找到 bookId，跳过划线拉取: {title}")
            return book
    
    print(f"[weread] 拉取热门划线: {title} (bookId={book_id})")
    data = call_weread("/book/bestbookmarks", {"bookId": book_id})
    
    if data and data.get("items"):
        quotes = []
        for item in data["items"][:10]:  # 取前10条热门划线
            text = item.get("markText", "").strip()
            if text:
                count = item.get("totalCount", 0)
                quotes.append(f"{text}（{count}人划线）" if count > 1 else text)
        
        if quotes:
            book["quotes"] = quotes
            book["weread_bookId"] = book_id
            print(f"[weread] ✅ 获取 {len(quotes)} 条热门划线: {title}")
            return book
        else:
            print(f"[weread] ⚠️ 热门划线为空: {title}")
    else:
        print(f"[weread] ⚠️ 获取热门划线失败: {title}")
    
    return book

def get_today_book():
    """选今日书籍（带锁，防止同天多次选出不同书）"""
    today = datetime.now(CST).strftime("%Y-%m-%d")
    
    # 检查 lock 文件
    if os.path.exists(_LOCK_FILE):
        with open(_LOCK_FILE, 'r') as f:
            lock = json.load(f)
        if lock.get("date") == today:
            idx = lock.get("index")
            if idx is not None and 0 <= idx < len(BOOKS):
                return BOOKS[idx]
    
    # 选书：排除最近选过的 + 随机
    recent_titles = set()
    history_data = {}
    if os.path.exists(_HISTORY_FILE):
        with open(_HISTORY_FILE, 'r') as f:
            history_data = json.load(f)
        if isinstance(history_data, dict) and 'titles' in history_data:
            recent_titles = set(history_data['titles'][-30:])
        elif isinstance(history_data, list):
            recent_titles = set(b.get('title','') for b in history_data[-30:])
            history_data = {'titles': [b.get('title','') for b in history_data]}
    
    if not isinstance(history_data, dict):
        history_data = {}
    
    # 优先选有abstract/reason/quotes的
    candidates = [b for b in BOOKS if b.get('abstract') and b.get('reason') and b.get('quotes') and b.get('title') not in recent_titles]
    if not candidates:
        candidates = [b for b in BOOKS if b.get('title') not in recent_titles]
    if not candidates:
        candidates = BOOKS
    
    chosen = random.choice(candidates)
    idx = BOOKS.index(chosen)
    
    # 保存 lock
    with open(_LOCK_FILE, 'w') as f:
        json.dump({"date": today, "index": idx}, f)
    
    # 更新历史
    history_data.setdefault('titles', []).append(chosen['title'])
    with open(_HISTORY_FILE, 'w') as f:
        json.dump(history_data, f, ensure_ascii=False)
    
    return chosen

def main():
    book = get_today_book()
    # 拉取微信读书热门划线（失败不影响，保留原有 quotes）
    book = sync_book_quotes(book)
    
    # 输出到 stdout（供 generate_book_card_hd.py 使用）+ 保存到临时文件
    tmp = "/tmp/today_book.json"
    with open(tmp, 'w') as f:
        json.dump(book, f, ensure_ascii=False)
    
    print(json.dumps(book, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()