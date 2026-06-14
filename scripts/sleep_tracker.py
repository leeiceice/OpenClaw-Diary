#!/usr/bin/env python3
"""
睡眠追踪（2026-06-14 Lee 拍板：建 tracker + 加 history）
- 当日态: data/sleep-log.json（由 sleep_api.py 写,本脚本只读不写）
- 历史归档: data/sleep-history.jsonl（永不清空）
- 模式: append-only,接收 sleep_api.py 推送的简化格式

输入示例:
{
  "date": "2026-06-14",
  "totalSleepMin": 480,
  "deepSleepMin": 90,
  "remSleepMin": 120,
  "awakeSleepMin": 30,
  "bedTime": "23:30",
  "wakeTime": "07:30",
  "sleepQuality": 85
}
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path("~/.openclaw/workspace").expanduser()
LOG_FILE = Path("~/.openclaw/workspace/data/sleep-log.json").expanduser()
HISTORY_FILE = Path("~/.openclaw/workspace/data/sleep-history.jsonl").expanduser()

CST = timezone(timedelta(hours=8))


def append_history(entry: dict) -> dict:
    """追加一条到 data/sleep-history.jsonl"""
    now = datetime.now(CST)
    history_entry = {
        "ts": now.isoformat(),
        "date": entry.get('date', now.strftime("%Y-%m-%d")),
        "total_sleep_min": entry.get('totalSleepMin', 0),
        "deep_sleep_min": entry.get('deepSleepMin', 0),
        "rem_sleep_min": entry.get('remSleepMin', 0),
        "awake_sleep_min": entry.get('awakeSleepMin', 0),
        "bed_time": entry.get('bedTime', ''),
        "wake_time": entry.get('wakeTime', ''),
        "sleep_quality": entry.get('sleepQuality', 0),
        "source": "sleep_tracker.py",
    }
    line = json.dumps(history_entry, ensure_ascii=False)
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, 'a') as f:
            f.write(line + '\n')
        return {"ok": True, "line": line, "path": str(HISTORY_FILE)}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": str(HISTORY_FILE)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='睡眠记录 → 历史 append')
    parser.add_argument('--from-stdin', action='store_true', help='从 stdin 读取 JSON')
    parser.add_argument('--date', help='日期 YYYY-MM-DD')
    parser.add_argument('--total-min', type=int, help='总睡眠分钟')
    parser.add_argument('--quality', type=int, help='睡眠质量 0-100')
    args = parser.parse_args()

    if args.from_stdin:
        try:
            entry = json.loads(sys.stdin.read())
        except Exception as e:
            print(f"⚠️ stdin JSON 解析失败: {e}")
            sys.exit(1)
    elif args.date and args.total_min is not None:
        entry = {
            'date': args.date,
            'totalSleepMin': args.total_min,
            'sleepQuality': args.quality or 0,
        }
    else:
        print("用法: --from-stdin 或 --date YYYY-MM-DD --total-min N --quality 0-100")
        sys.exit(1)

    hres = append_history(entry)
    if hres['ok']:
        print(f"✓ 睡眠记录已 append → {hres['path']}")
    else:
        print(f"⚠️ append 失败: {hres.get('error')}")
