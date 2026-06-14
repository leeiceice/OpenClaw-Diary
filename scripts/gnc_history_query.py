#!/usr/bin/env python3
"""
GNC 历史查询工具（2026-06-14 Lee 拍板配套）
- 读 data/gnc-history.jsonl
- 支持：按日期范围、关键字搜索、统计聚合
- 只读，不写
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

HISTORY_FILE = Path("~/.openclaw/workspace/data/gnc-history.jsonl").expanduser()


def load_history(path: Path = HISTORY_FILE) -> list:
    if not path.exists():
        return []
    out = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[warn] line {i} 解析失败: {e}", file=sys.stderr)
    return out


def filter_history(entries: list, date_from: str = None, date_to: str = None,
                   keyword: str = None) -> list:
    out = []
    for e in entries:
        if date_from and e.get('date', '') < date_from:
            continue
        if date_to and e.get('date', '') > date_to:
            continue
        if keyword and keyword not in e.get('note', ''):
            continue
        out.append(e)
    return out


def aggregate_by_day(entries: list) -> dict:
    """按天聚合：日期 → {records, keywords}"""
    agg = defaultdict(lambda: {'records': 0, 'keywords': set()})
    for e in entries:
        d = e.get('date', 'unknown')
        agg[d]['records'] += 1
        agg[d]['keywords'].add(e.get('note', ''))
    return dict(agg)


def print_entries(entries: list, limit: int = None):
    n = 0
    for e in entries:
        if limit and n >= limit:
            print(f"... ({len(entries) - n} more)")
            break
        print(f"  {e.get('date')} {e.get('time')} 💊 {e.get('note', '')}")
        n += 1


def print_aggregation(agg: dict):
    print(f"\n📊 按日聚合（共 {len(agg)} 天）:")
    print(f"{'日期':<12} {'记录数':>6} {'补剂种类':>8}")
    print("-" * 32)
    total = 0
    for d in sorted(agg.keys()):
        a = agg[d]
        keywords = ', '.join(sorted(a['keywords'])) if a['keywords'] else '-'
        print(f"{d:<12} {a['records']:>6} {keywords[:30]:>8}")
        total += a['records']
    print("-" * 32)
    print(f"{'总':<12} {total:>6}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GNC 历史查询（只读）')
    parser.add_argument('--from', dest='date_from', help='起始日期 YYYY-MM-DD')
    parser.add_argument('--to', dest='date_to', help='结束日期 YYYY-MM-DD')
    parser.add_argument('--keyword', help='按关键字过滤（note 包含）')
    parser.add_argument('--limit', type=int, default=50, help='明细显示上限（默认 50）')
    parser.add_argument('--agg-only', action='store_true', help='只显示聚合')
    parser.add_argument('--detail-only', action='store_true', help='只显示明细')
    parser.add_argument('--days', type=int, help='最近 N 天')
    args = parser.parse_args()

    if args.days:
        today = date.today()
        args.date_from = (today - timedelta(days=args.days - 1)).isoformat()
        args.date_to = today.isoformat()

    entries = load_history()
    if not entries:
        print("📭 GNC 历史为空（data/gnc-history.jsonl 不存在或无数据）")
        sys.exit(0)

    filtered = filter_history(entries, args.date_from, args.date_to, args.keyword)
    if not filtered:
        print(f"📭 无匹配记录 (from={args.date_from or '*'}, to={args.date_to or '*'}, keyword={args.keyword or '*'})")
        sys.exit(0)

    print(f"📜 GNC 历史（共 {len(filtered)} 条 / 总 {len(entries)} 条）")
    if args.date_from or args.date_to:
        print(f"  范围: {args.date_from or '*'} ~ {args.date_to or '*'}")
    if args.keyword:
        print(f"  关键字: {args.keyword}")

    if not args.agg_only:
        print(f"\n📋 明细:")
        print_entries(filtered, args.limit)

    if not args.detail_only:
        agg = aggregate_by_day(filtered)
        print_aggregation(agg)
