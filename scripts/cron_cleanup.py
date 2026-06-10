#!/usr/bin/env python3
"""
Cron 定期清理脚本
功能：
  1. 列出所有 cron 任务
  2. 识别老化任务（idle 且超过指定天数未运行）
  3. 识别重复任务（名称相似）
  4. 支持 dry-run（只报告不删除）和自动清理模式
"""

import subprocess
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional


def get_crons() -> List[Dict]:
    """通过 openclaw cron list 获取所有 cron 任务"""
    result = subprocess.run(
        ["openclaw", "cron", "list"],
        capture_output=True, text=True, timeout=30
    )
    crons = []
    for line in result.stdout.strip().split("\n"):
        # 格式: <id> <name> cron <schedule> ... in <next> <last> <status> ...
        # 例如: 57f3e445-311e-4f47-97ae-6adbfeb6f77b 进化日报提醒 cron 20 17 * * * (exact) in 8h 16h ago ok isolated announce -> feishu:...
        parts = line.split()
        if len(parts) < 6:
            continue
        cron_id = parts[0]
        name = parts[1]
        
        # 提取 last 运行时
        last_ago = None
        status = None
        try:
            # 找 "in X ago" 模式
            for i, p in enumerate(parts):
                if p == "in" and i+2 < len(parts):
                    next_val = parts[i+1]
                    if i+3 < len(parts) and parts[i+2] == "ago":
                        last_val = parts[i+3] if parts[i+3] != "ago" else "?"
                        if i+4 < len(parts) and parts[i+4] == "ago":
                            last_val = parts[i+5] if parts[i+5] != "ago" else "?"
                        last_ago = f"{next_val} {parts[i+2]}"
                        break
                if p in ("ok", "idle", "error", "running"):
                    status = p
        except Exception:
            pass
        
        crons.append({
            "id": cron_id,
            "name": name,
            "last_ago": last_ago,
            "status": status,
            "raw": line
        })
    return crons


def parse_ago_to_days(ago_str: str) -> Optional[float]:
    """将 '16h ago' 或 '3d ago' 转换为天数"""
    if not ago_str:
        return None
    match = re.match(r"(\d+)([hdwm])", ago_str.replace("ago", "").strip())
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2)
    multipliers = {"h": 1/24, "d": 1, "w": 7, "m": 30}
    return val * multipliers.get(unit, 0)


def find_stale_crons(crons: List[Dict], threshold_days: int = 7) -> List[Dict]:
    """识别 idle 且超过 threshold 天未运行的任务"""
    stale = []
    for cron in crons:
        if cron.get("status") == "idle" and cron.get("last_ago"):
            days = parse_ago_to_days(cron["last_ago"])
            if days is not None and days >= threshold_days:
                stale.append({**cron, "stale_days": round(days, 1)})
    return stale


def find_duplicate_names(crons: List[Dict]) -> List[List[Dict]]:
    """
    识别完全同名 + 同目标群的任务（真正重复）
    仅名称相似不算（可能是有意设置的不同时间/不同推送群）
    """
    # 按 name + target_group 分组，完全相同才报警
    groups: Dict[str, List[Dict]] = {}
    for cron in crons:
        # 提取目标群（从 raw 中解析 announce -> feishu:xxx (expli...）
        target = ""
        if "-> feishu:" in cron["raw"]:
            m = re.search(r"-> feishu:([a-z0-9_]+)", cron["raw"])
            if m:
                target = m.group(1)
        key = f"{cron['name']}|{target}"
        groups.setdefault(key, []).append(cron)
    return [g for g in groups.values() if len(g) > 1]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cron 定期清理脚本")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="只报告不删除（默认）")
    parser.add_argument("--remove", action="store_true",
                        help="实际执行删除（需明确指定）")
    parser.add_argument("--threshold", type=int, default=7,
                        help="超过多少天未运行的 idle cron 视为老化（默认7天）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    crons = get_crons()
    
    if args.json:
        print(json.dumps(crons, ensure_ascii=False, indent=2))
        return

    print(f"📋 共发现 {len(crons)} 个 cron 任务\n")

    # 1. 老化任务
    stale = find_stale_crons(crons, args.threshold)
    if stale:
        print(f"🗑️  老化任务（idle ≥ {args.threshold} 天未运行）：")
        for c in stale:
            print(f"   [{c['id']}] {c['name']} — {c['stale_days']}天前 ({c['last_ago']})")
        print()
    else:
        print("✅ 无老化任务\n")

    # 2. 重复名称
    dups = find_duplicate_names(crons)
    if dups:
        print(f"🔴 发现重复名称任务：")
        for group in dups:
            for c in group:
                print(f"   [{c['id']}] {c['name']}")
            print()
    else:
        print("✅ 无重复名称任务\n")

    # 3. 汇总
    total_issues = len(stale) + sum(len(g) for g in dups)
    if total_issues == 0:
        print("🎉 所有 cron 任务状态正常！")
    else:
        print(f"⚠️  共 {total_issues} 个问题需要处理")

    # 4. 执行删除
    if stale and args.remove:
        print(f"\n🗑️  开始删除 {len(stale)} 个老化任务...")
        for c in stale:
            res = subprocess.run(["openclaw", "cron", "remove", c["id"]],
                                capture_output=True, text=True, timeout=10)
            status = "✅" if res.returncode == 0 else "❌"
            print(f"   {status} {c['name']} ({c['id']})")
    elif stale and args.dry_run:
        print(f"\n💡 使用 --remove 执行实际删除（当前为 dry-run 模式）")


if __name__ == "__main__":
    main()
