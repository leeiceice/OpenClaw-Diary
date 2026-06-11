#!/usr/bin/env python3
"""
check_cron_products_health.py — cron 产物 mtime 健康检查

背景: systemEvent 模式 cron 跑通 ≠ 业务跑通 (例: ontology pipeline 17 天
静默失败, 但 cron 一直显示 ok). 这个脚本检查关键 cron 跑完后**产物文件**
是否真的有更新.

v2 (2026-06-11): 阈值从 sqlite 实时计算 (schedule_interval × 1.5 + 30min),
避免 hardcoded 阈值和实际 schedule 漂移产生的 false positive. dead
(不存在于 DB) 的规则只 warn, 不计入失败.

运行: 建议每 4 小时一次 cron, 或手动 `python3 scripts/check_cron_products_health.py`
"""
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from _timezone import CST

WORKSPACE = Path("/root/.openclaw/workspace").expanduser()
SQLITE = Path("/root/.openclaw/state/openclaw.sqlite").expanduser()

# === 检查规则 ===
# (cron_id, cron_name, expected_product_path, severity, description)
# max_age 不再 hardcoded — 运行时从 sqlite schedule 计算
RULES = [
    {
        "cron_id": "f7b860cc-6321-4c58-8f60-0d8785156768",
        "name": "对话-Ontology管道",
        "product": WORKSPACE / "memory/ontology/graph.jsonl",
        "severity": "high",
        "description": "graph.jsonl 应按 cron 节奏更新 (当前 sqlite schedule)",
    },
    {
        "cron_id": "ab150a93-5714-4d74-9c97-29d34196e57c",
        "name": "每日Ontology图谱同步 (23:00)",
        "product": WORKSPACE / "memory/ontology/graph.jsonl",
        "severity": "medium",
        "description": "graph.jsonl 应每天 23:00 附近有 mtime 更新",
    },
    {
        "cron_id": "d0518b66-7116-470d-b726-6ec6ebc1e66a",
        "name": "偏差传感器周扫描 (周日 10:00)",
        "product": WORKSPACE / "self-improving/corrections.md",
        "severity": "low",
        "description": "corrections.md 应每周日 10:00 附近有 mtime 更新",
    },
    {
        "cron_id": "c9310669-4881-4dfa-a426-2ec17f516036",
        "name": "每日置信度分布快照 (22:30)",
        "product": WORKSPACE / "proactivity/intuition-snapshot.json",
        "severity": "medium",
        "description": "intuition-snapshot.json 应每天 22:30 附近有 mtime 更新",
    },
    {
        "cron_id": "b9f146c4-d62b-4f30-b8aa-e64a4f930667",
        "name": "heartbeat-maintenance",
        "product": WORKSPACE / "proactivity/heartbeat-state.json",
        "severity": "low",
        "description": "heartbeat-state.json 应按 cron 节奏更新 (sqlite schedule)",
    },
    {
        "cron_id": "f92708f2-a4b6-4dbb-bf87-20e14a12e6e3",
        "name": "午间记忆提炼 (12:30)",
        "product": WORKSPACE / "self-improving/corrections.md",
        "severity": "medium",
        "description": "corrections.md 应每天 12:30 附近有 mtime 更新",
    },
    {
        "cron_id": "823a779c-10b2-4890-8863-21905670bcb5",
        "name": "早间记忆提炼 (08:00)",
        "product": WORKSPACE / "self-improving/corrections.md",
        "severity": "medium",
        "description": "corrections.md 应每天 08:00 附近有 mtime 更新",
    },
]


def parse_cron_expr_to_seconds(expr: str) -> int | None:
    """简化版 cron 解析: 返回 schedule 周期 (秒).
    支持:
      - "0 */N * * *"      每 N 小时       → N*3600
      - "0 H * * *"        每天固定 H 点    → 86400
      - "M H * * *"        每天固定时间     → 86400
      - "0 H * * D"        每周 D 日 H 点   → 604800
      - "0 H D M *"        每年 M 月 D 日   → 31536000 (近似的)
    不识别返回 None (调用方按 24h 处理).
    """
    if not expr:
        return None
    parts = expr.split()
    if len(parts) != 5:
        return None
    minute, hour, dom, month, dow = parts
    if minute.isdigit() and hour.startswith("*/"):
        n = int(hour[2:])
        if 1 <= n <= 23:
            return n * 3600
    if minute.isdigit() and hour.isdigit() and dom == "*" and month == "*" and dow == "*":
        return 24 * 3600
    if minute.isdigit() and hour == "*" and dom == "*" and month == "*" and dow == "*":
        return 3600
    if minute.isdigit() and hour.isdigit() and dom == "*" and month == "*" and dow.isdigit():
        return 7 * 24 * 3600
    if minute.isdigit() and hour.isdigit() and dom.isdigit() and month.isdigit() and dow == "*":
        return 365 * 24 * 3600
    return None


def get_schedule_seconds(cron_id: str) -> tuple[int | None, dict | None]:
    """从 sqlite 读 cron 的 schedule + state; 返回 (interval_seconds, info_dict).
    job 不存在时返回 (None, None).
    """
    if not SQLITE.exists():
        return None, None
    con = sqlite3.connect(str(SQLITE))
    con.row_factory = sqlite3.Row
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT schedule_kind, schedule_expr, last_run_at_ms, last_run_status, "
            "next_run_at_ms, enabled FROM cron_jobs WHERE job_id = ?",
            (cron_id,),
        )
        row = cur.fetchone()
        if not row:
            return None, None
        info = {
            "schedule_kind": row["schedule_kind"],
            "schedule_expr": row["schedule_expr"],
            "last_run_at_ms": row["last_run_at_ms"],
            "last_run_status": row["last_run_status"],
            "next_run_at_ms": row["next_run_at_ms"],
            "enabled": bool(row["enabled"]),
        }
        if row["schedule_kind"] == "cron":
            return parse_cron_expr_to_seconds(row["schedule_expr"] or ""), info
        if row["schedule_kind"] == "every":
            return 24 * 3600, info  # 暂不解析 everyMs
        return 24 * 3600, info
    finally:
        con.close()


def compute_max_age(interval_s: int) -> int:
    """threshold = interval × 1.5 + 30 分钟容差, 至少 2.5h."""
    return max(int(interval_s * 1.5) + 1800, 2 * 3600 + 1800)


def check_rule(rule: dict) -> dict:
    """检查单条规则"""
    product = rule["product"]
    now = datetime.now(CST).timestamp()
    interval_s, sched_info = get_schedule_seconds(rule["cron_id"])
    max_age = compute_max_age(interval_s) if interval_s else 2 * 3600 + 1800
    rel = lambda p: str(p.relative_to(WORKSPACE)) if p.is_absolute() else str(p)

    result = {
        "cron_id": rule["cron_id"],
        "name": rule["name"],
        "product": rel(product),
        "description": rule["description"],
        "severity": rule["severity"],
        "ok": True,
        "issue": None,
        "mtime_age_seconds": None,
        "schedule_expr": sched_info["schedule_expr"] if sched_info else None,
        "max_age_seconds": max_age,
        "dead_job": sched_info is None,
    }

    if sched_info is None:
        result["ok"] = False
        result["issue"] = f"cron job 不在 sqlite ({rel(product)} 永远不会再被更新)"
        return result

    if not sched_info["enabled"]:
        result["ok"] = False
        result["issue"] = f"cron job 已 disabled (expr={sched_info['schedule_expr']})"
        return result

    if not product.exists():
        result["ok"] = False
        result["issue"] = f"产物文件不存在: {product}"
        return result

    mtime = product.stat().st_mtime
    age = now - mtime
    result["mtime_age_seconds"] = int(age)
    result["mtime"] = datetime.fromtimestamp(mtime, tz=CST).isoformat()

    if age > max_age:
        result["ok"] = False
        result["issue"] = (
            f"产物 mtime 过旧: {age/3600:.1f}h 前 "
            f"(阈值 {max_age/3600:.1f}h, schedule={sched_info['schedule_expr']})"
        )
    return result


def main() -> int:
    results = [check_rule(r) for r in RULES]
    failed = [r for r in results if not r["ok"]]

    print(f"[{datetime.now(CST).strftime('%Y-%m-%d %H:%M')}] cron 产物 mtime 健康检查")
    print(f"  检查 {len(RULES)} 条规则")
    print(f"  ✅ 通过: {len(results) - len(failed)}")
    print(f"  ❌ 失败: {len(failed)}")
    print()

    for r in results:
        icon = "✅" if r["ok"] else "❌"
        if r["mtime_age_seconds"] is not None:
            age = f"({r['mtime_age_seconds']/3600:.1f}h 前)"
        else:
            age = "(无文件)" if not r["dead_job"] else "(job 不存在)"
        sched = f" [{r['schedule_expr']}]" if r["schedule_expr"] else ""
        print(f"  {icon} [{r['severity']:6}] {r['name']} {age}{sched}")
        if not r["ok"]:
            print(f"        ⚠️  {r['issue']}")
        elif "mtime" in r:
            print(f"        mtime: {r['mtime']}")

    print()
    if failed:
        failed.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3))
        print(f"🚨 {len(failed)} 个 cron 产物过旧 / 异常:")
        for r in failed:
            print(f"   [{r['severity']:6}] {r['name']}")
            print(f"           {r['issue']}")
        # dead_job 单独统计 (非业务失败)
        dead = [r for r in failed if r["dead_job"]]
        real = [r for r in failed if not r["dead_job"]]
        if dead and not real:
            print("\n(全部为 dead_job 误报, 需清理 RULES — 不是真实 cron 失败)")
        return 1
    else:
        print("🎉 所有 cron 产物 mtime 正常")
        return 0


if __name__ == "__main__":
    sys.exit(main())
