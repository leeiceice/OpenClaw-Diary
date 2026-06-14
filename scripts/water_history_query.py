#!/usr/bin/env python3
"""
喝水历史查询工具（2026-06-14 Lee 拍板 A+A 配套）
- 读 data/water-history.jsonl
- 支持：按日期范围、模式(append/override)、统计聚合
- 只读，不写
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

HISTORY_FILE = Path("~/.openclaw/workspace/data/water-history.jsonl").expanduser()


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
                   mode: str = None) -> list:
    out = []
    for e in entries:
        if date_from and e.get('date', '') < date_from:
            continue
        if date_to and e.get('date', '') > date_to:
            continue
        if mode and e.get('mode') != mode:
            continue
        out.append(e)
    return out


def aggregate_by_day(entries: list) -> dict:
    """按天聚合：日期 → {total_ml, cups, records, append_count, override_count}"""
    agg = defaultdict(lambda: {
        'total_ml': 0, 'cups': 0, 'records': 0,
        'append_count': 0, 'override_count': 0,
        'last_ts': ''
    })
    for e in entries:
        d = e.get('date', 'unknown')
        # 取当日最后一条的 ml_total（避免覆盖模式 + 追加模式混算）
        agg[d]['total_ml'] = e.get('ml_total', 0)
        agg[d]['cups'] = e.get('cups_total', 0)
        agg[d]['records'] += 1
        if e.get('mode') == 'override':
            agg[d]['override_count'] += 1
        else:
            agg[d]['append_count'] += 1
        if e.get('ts', '') > agg[d]['last_ts']:
            agg[d]['last_ts'] = e['ts']
    return dict(agg)


def print_entries(entries: list, limit: int = None):
    n = 0
    for e in entries:
        if limit and n >= limit:
            print(f"... ({len(entries) - n} more)")
            break
        mode_marker = '🔄' if e.get('mode') == 'override' else '➕'
        ml_delta = e.get('ml', 0)
        ml_total = e.get('ml_total', 0)
        cups = e.get('cups_total', 0)
        print(f"  {e.get('date')} {e.get('time')} {mode_marker} +{ml_delta}ml → {ml_total}ml ({cups}杯) | {e.get('note', '')}")
        n += 1


def print_aggregation(agg: dict):
    print(f"\n📊 按日聚合（共 {len(agg)} 天）:")
    print(f"{'日期':<12} {'总 ml':>8} {'杯数':>6} {'追加':>6} {'覆盖':>6} {'记录数':>6}")
    print("-" * 56)
    total_ml = 0
    total_cups = 0
    for d in sorted(agg.keys()):
        a = agg[d]
        print(f"{d:<12} {a['total_ml']:>8} {a['cups']:>6} {a['append_count']:>6} {a['override_count']:>6} {a['records']:>6}")
        total_ml = max(total_ml, a['total_ml'])  # 取最大避免覆盖重复算
        total_cups = max(total_cups, a['cups'])
    print("-" * 56)
    print(f"{'总(去重)':<12} {total_ml:>8} {total_cups:>6}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='喝水历史查询（只读）')
    parser.add_argument('--from', dest='date_from', help='起始日期 YYYY-MM-DD')
    parser.add_argument('--to', dest='date_to', help='结束日期 YYYY-MM-DD')
    parser.add_argument('--mode', choices=['append', 'override'], help='按模式过滤')
    parser.add_argument('--limit', type=int, default=50, help='明细显示上限（默认 50）')
    parser.add_argument('--agg-only', action='store_true', help='只显示聚合，不显示明细')
    parser.add_argument('--detail-only', action='store_true', help='只显示明细，不显示聚合')
    parser.add_argument('--days', type=int, help='最近 N 天（覆盖 --from/--to）')
    args = parser.parse_args()

    if args.days:
        today = date.today()
        args.date_from = (today - timedelta(days=args.days - 1)).isoformat()
        args.date_to = today.isoformat()

    entries = load_history()
    if not entries:
        print("📭 历史记录为空（data/water-history.jsonl 不存在或无数据）")
        sys.exit(0)

    filtered = filter_history(entries, args.date_from, args.date_to, args.mode)
    if not filtered:
        print(f"📭 无匹配记录 (from={args.date_from or '*'}, to={args.date_to or '*'}, mode={args.mode or '*'})")
        sys.exit(0)

    print(f"📜 喝水历史（共 {len(filtered)} 条 / 总 {len(entries)} 条）")
    if args.date_from or args.date_to:
        print(f"  范围: {args.date_from or '*'} ~ {args.date_to or '*'}")
    if args.mode:
        print(f"  模式: {args.mode}")

    if not args.agg_only:
        print(f"\n📋 明细:")
        print_entries(filtered, args.limit)

    if not args.detail_only:
        agg = aggregate_by_day(filtered)
        print_aggregation(agg)
