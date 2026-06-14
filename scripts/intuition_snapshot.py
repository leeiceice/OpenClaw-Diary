#!/usr/bin/env python3
"""
intuition_snapshot.py
每日置信度分布快照生成器

目的：解决 HEARTBEAT 评分中"直觉状态"维度难以量化的问题。
机制：扫描 memory/ 下的置信度标注，统计四状态分布，写入
      proactivity/intuition-snapshot.json，供 HEARTBEAT 读取评分。

四状态（ECC 框架）：
- 猜测  (<30%)
- 直觉  (30-59%)
- 经验  (60-84%)
- 知识  (≥85%)
"""
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 路径
WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
SNAPSHOT_PATH = WORKSPACE / "proactivity" / "intuition-snapshot.json"

from _timezone import CST  # 唯一来源，不在此文件重复定义

# 置信度正则（匹配 [置信度: XX%] 格式）
CONFIDENCE_PATTERN = re.compile(r"\[置信度[::]\s*(\d{1,3})%\]")


def scan_confidence_in_file(path: Path) -> list[int]:
    """从单个文件扫描所有置信度标注"""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    return [int(m) for m in CONFIDENCE_PATTERN.findall(text) if 0 <= int(m) <= 100]


def categorize(score: int) -> str:
    """ECC 四状态分类"""
    if score < 30:
        return "guesses"
    if score < 60:
        return "intuitions"
    if score < 85:
        return "experiences"
    return "knowledge"


def scan_all_memory() -> Counter:
    """扫描所有记忆源，返回四状态计数"""
    counter = Counter()
    scan_dirs = [
        MEMORY_DIR,
        WORKSPACE / "proactivity",  # daily-working-log.md 等置信度 entry 来源
        Path("/root/.openclaw/workspace/日记/raw"),  # 优先工作区 raw
        Path.home() / "Obsidian" / "日记" / "raw",   # Obsidian raw 备查
    ]
    for d in scan_dirs:
        if not d.exists():
            continue
        for md in d.rglob("*.md"):
            for score in scan_confidence_in_file(md):
                counter[categorize(score)] += 1
    return counter


def build_snapshot() -> dict:
    """构建快照 JSON"""
    counts = scan_all_memory()
    total = sum(counts.values()) or 1
    distribution = {
        state: {"count": counts[state], "ratio": round(counts[state] / total, 3)}
        for state in ("guesses", "intuitions", "experiences", "knowledge")
    }

    # HEARTBEAT 评分启发：
    # 直觉占比≥50% → 15 分（健康，处于"已识别但未验证"合理范围）
    # 经验占比≥30% → 15 分（已积累实测验证）
    # 知识占比≥20% → 15 分（高质量沉淀充足）
    # 否则按比例打分
    intuition_score = 0
    if distribution["intuitions"]["ratio"] >= 0.5:
        intuition_score = 8  # 识别中，常规
    if distribution["experiences"]["ratio"] >= 0.3:
        intuition_score = 12  # 验证充分
    if distribution["knowledge"]["ratio"] >= 0.2:
        intuition_score = 15  # 知识沉淀充足

    snapshot = {
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "total_annotations": total,
        "distribution": distribution,
        "heartbeat_dimension": {
            "intuition_health": {
                "score": intuition_score,
                "max": 15,
                "rule": "intuitions≥50% →8; experiences≥30% →12; knowledge≥20% →15"
            }
        },
        "next_run_hint": "由 cron c9310669 每日 22:30 (Asia/Shanghai) 触发",
    }
    return snapshot


def append_snapshot_history(snapshot: dict) -> dict:
    """追加一条到 proactivity/intuition-snapshot-history.jsonl（2026-06-14 Lee 拍板 B：加 history）"""
    history_path = SNAPSHOT_PATH.parent / "intuition-snapshot-history.jsonl"
    try:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(snapshot, ensure_ascii=False)
        with open(history_path, 'a', encoding="utf-8") as f:
            f.write(line + '\n')
        return {"ok": True, "path": str(history_path)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main() -> int:
    """主入口"""
    try:
        snapshot = build_snapshot()
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        # 2026-06-14 Lee 拍板 B：追加历史（保留每一份快照）
        hres = append_snapshot_history(snapshot)
        if hres['ok']:
            print(f"📜 快照历史已 append → {hres['path']}")
        else:
            print(f"⚠️ 历史 append 失败：{hres.get('error')}")
        print(f"✅ 快照已写入: {SNAPSHOT_PATH}")
        print(f"   total={snapshot['total_annotations']}")
        print(f"   distribution={snapshot['distribution']}")
        print(f"   intuition_health score={snapshot['heartbeat_dimension']['intuition_health']['score']}/15")
        return 0
    except Exception as e:
        print(f"❌ 快照生成失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
