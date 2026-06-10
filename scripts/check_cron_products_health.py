#!/usr/bin/env python3
"""
check_cron_products_health.py — cron 产物 mtime 健康检查

背景: systemEvent 模式 cron 跑通 ≠ 业务跑通 (例: ontology pipeline 17 天
静默失败, 但 cron 一直显示 ok). 这个脚本检查关键 cron 跑完后**产物文件**
是否真的有更新.

运行: 建议每 2 小时一次 cron, 或手动 `python3 scripts/check_cron_products_health.py`
"""
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from _timezone import CST

WORKSPACE = Path("/root/.openclaw/workspace").expanduser()

# === 检查规则 ===
# (cron_id, cron_name, expected_product_path, max_age_seconds, severity, action)
RULES = [
    {
        "cron_id": "f7b860cc-6321-4c58-8f60-0d8785156768",
        "name": "对话-Ontology管道 (2h)",
        "product": WORKSPACE / "memory/ontology/graph.jsonl",
        "max_age_seconds": 2 * 3600 + 1800,  # 2h cron + 30min 容差
        "severity": "high",
        "description": "graph.jsonl 应每 2h 有新实体或 mtime 更新",
    },
    {
        "cron_id": "ab150a93-5714-4d74-9c97-29d34196e57c",
        "name": "每日Ontology图谱同步 (23:00)",
        "product": WORKSPACE / "memory/ontology/graph.jsonl",
        "max_age_seconds": 25 * 3600,  # 1 天 + 1h 容差
        "severity": "medium",
        "description": "graph.jsonl 应每天 23:00 附近有 mtime 更新",
    },
    {
        "cron_id": "d0518b66-7116-470d-b726-6ec6ebc1e66a",
        "name": "偏差传感器周扫描 (周日 10:00)",
        "product": WORKSPACE / "self-improving/corrections.md",
        "max_age_seconds": 8 * 24 * 3600,  # 7 天 + 1 天容差
        "severity": "low",
        "description": "corrections.md 应每周日 10:00 附近有 mtime 更新 (新增或 rewrite)",
    },
    {
        "cron_id": "c9310669-4881-4dfa-a426-2ec17f516036",
        "name": "每日置信度分布快照 (22:30)",
        "product": WORKSPACE / "proactivity/intuition-snapshot.json",
        "max_age_seconds": 25 * 3600,
        "severity": "medium",
        "description": "intuition-snapshot.json 应每天 22:30 附近有 mtime 更新",
    },
    {
        "cron_id": "52f5f99e-798f-41a3-9b21-d3cd7eb9d878",
        "name": "heartbeat-maintenance (每小时)",
        "product": WORKSPACE / "proactivity/heartbeat-state.json",
        "max_age_seconds": 2 * 3600,
        "severity": "low",
        "description": "heartbeat-state.json 应每小时有 mtime 更新",
    },
    {
        "cron_id": "f92708f2-a4b6-4dbb-bf87-20e14a12e6e3",
        "name": "午间记忆提炼 (12:30)",
        "product": WORKSPACE / "self-improving/corrections.md",
        "max_age_seconds": 25 * 3600,
        "severity": "medium",
        "description": "corrections.md 应每天 12:30 附近有 mtime 更新 (提炼活动)",
    },
    {
        "cron_id": "823a779c-10b2-4890-8863-21905670bcb5",
        "name": "早间记忆提炼 (08:00)",
        "product": WORKSPACE / "self-improving/corrections.md",
        "max_age_seconds": 25 * 3600,
        "severity": "medium",
        "description": "corrections.md 应每天 08:00 附近有 mtime 更新",
    },
]


def check_rule(rule: dict) -> dict:
    """检查单条规则"""
    product = rule["product"]
    now = datetime.now(CST).timestamp()
    result = {
        "cron_id": rule["cron_id"],
        "name": rule["name"],
        "product": str(product.relative_to(WORKSPACE)) if product.is_absolute() else str(product),
        "description": rule["description"],
        "severity": rule["severity"],
        "ok": True,
        "issue": None,
        "mtime_age_seconds": None,
    }

    if not product.exists():
        result["ok"] = False
        result["issue"] = f"产物文件不存在: {product}"
        return result

    mtime = product.stat().st_mtime
    age = now - mtime
    result["mtime_age_seconds"] = int(age)
    result["mtime"] = datetime.fromtimestamp(mtime, tz=CST).isoformat()

    if age > rule["max_age_seconds"]:
        result["ok"] = False
        result["issue"] = (
            f"产物 mtime 过旧: {age/3600:.1f}h 前 (阈值 {rule['max_age_seconds']/3600:.1f}h)"
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
        age = f"({r['mtime_age_seconds']/3600:.1f}h 前)" if r["mtime_age_seconds"] is not None else "(无文件)"
        print(f"  {icon} [{r['severity']:6}] {r['name']} {age}")
        if not r["ok"]:
            print(f"        ⚠️  {r['issue']}")
        else:
            print(f"        mtime: {r['mtime']}")

    print()
    if failed:
        # 按严重度排序输出
        failed.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3))
        print(f"🚨 {len(failed)} 个 cron 产物过旧，建议检查:")
        for r in failed:
            print(f"   [{r['severity']:6}] {r['name']}")
            print(f"           {r['issue']}")
        return 1
    else:
        print("🎉 所有 cron 产物 mtime 正常")
        return 0


if __name__ == "__main__":
    sys.exit(main())
