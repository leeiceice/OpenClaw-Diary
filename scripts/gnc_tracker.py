#!/usr/bin/env python3
"""
GNC 补剂追踪（2026-06-14 Lee 拍板 A：建 tracker + 加 history）
- 当日态: data/gnc-log.json（reset cron 不动）
- 历史归档: data/gnc-history.jsonl（永不清空）

输入：自然语言描述（例：'吃了维生素D' / 'GNC补剂' / '补了镁'）
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path("~/.openclaw/workspace").expanduser()
LOG_FILE = Path("~/.openclaw/workspace/data/gnc-log.json").expanduser()
HISTORY_FILE = Path("~/.openclaw/workspace/data/gnc-history.jsonl").expanduser()

# 时区统一 Asia/Shanghai
CST = timezone(timedelta(hours=8))


def load_log():
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return {"date": datetime.now(CST).strftime("%Y-%m-%d"), "records": []}


def save_log(data):
    with open(LOG_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_gnc_message(text: str) -> bool:
    """GNC 消息识别：含补剂/营养/维生素等关键词"""
    keywords = ["补剂", "GNC", "gnc", "维生素", "镁", "锌", "钙", "铁", "鱼油",
                "复合维生素", "益生菌", "叶黄素", "B族", "维C", "维D", "维E",
                "蛋白", "营养", "吃", "补", "💊", "🧴"]
    return any(kw in text for kw in keywords)


def process_message(text: str) -> str:
    """返回补剂描述（不解析数量，GNC 是单条记录）"""
    if not is_gnc_message(text):
        return ""
    return text.strip()


def append_history(data: dict, note: str) -> dict:
    """追加一条到 data/gnc-history.jsonl"""
    now = datetime.now(CST)
    entry = {
        "ts": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "note": note,
    }
    line = json.dumps(entry, ensure_ascii=False)
    try:
        with open(HISTORY_FILE, 'a') as f:
            f.write(line + '\n')
        return {"ok": True, "line": line, "path": str(HISTORY_FILE)}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": str(HISTORY_FILE)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GNC 补剂追踪 → 当日 log + 历史 append')
    parser.add_argument('text', nargs='+', help='GNC 消息文本')
    parser.add_argument('--dry-run', action='store_true', help='只解析不保存')
    args = parser.parse_args()

    text = ' '.join(args.text)
    note = process_message(text)
    if not note:
        print(f"未识别为 GNC 消息：{text}")
        sys.exit(0)

    print(f"识别为 GNC 补剂：{note}")

    if args.dry_run:
        print(f"[dry-run] 不会保存记录、不写历史")
        sys.exit(0)

    # 加载当日 log
    log = load_log()
    today = datetime.now(CST).strftime("%Y-%m-%d")
    if log.get('date') != today:
        log = {"date": today, "records": []}

    now_str = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    log['records'].append({"time": now_str, "note": note})
    save_log(log)

    # 追加历史
    hres = append_history(log, note)
    if hres['ok']:
        print(f"✓ 已记录：{now_str} {note}")
        print(f"✓ 历史已 append → {hres['path']}")
        print(f"  今日记录数：{len(log['records'])}")
    else:
        print(f"⚠️ 当日 log 已保存，但历史 append 失败：{hres.get('error')}")
