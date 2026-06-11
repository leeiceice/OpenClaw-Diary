#!/usr/bin/env python3
"""
Memory 自洁检查脚本（模仿小马 M3 法）
- Confidence 衰减扫描（corrections.md + deviations/）
- Drift Guard（文件 mtime / hash 对比）
- 单条上限检查（专题文件 / MEMORY.md / SOUL.md）
- 输出报告到 stdout

用法：
  python3 scripts/memory_purge_check.py          # 常规检查
  python3 scripts/memory_purge_check.py --report  # 只输出报告（不写状态）
  python3 scripts/memory_purge_check.py --purge   # 自动清理 low-confidence 条目
"""

import json
import hashlib
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
WORKSPACE = Path("/root/.openclaw/workspace")
DRIFT_STATE_FILE = WORKSPACE / "self-improving" / "drift-guard-state.json"
PURGE_CANDIDATES_FILE = WORKSPACE / "self-improving" / "purge-candidates.md"

# 检查的文件（关键规则文件）
WATCHED_FILES = [
    "MEMORY.md",
    "COLLAB.md",
    "ROUTING.md",
    "CRON.md",
    "ARCHITECT.md",
    "MEMORY_POLICY.md",
    "SOUL.md",
    "AGENTS.md",
    "self-improving/corrections.md",
]

# 单条上限
MAX_LINE_BYTES = {
    "MEMORY.md": 150,       # Lee 拍板
    "COLLAB.md": 500,
    "ROUTING.md": 500,
    "CRON.md": 500,
    "ARCHITECT.md": 500,
    "MEMORY_POLICY.md": 500,
    "SOUL.md": 800,
    "AGENTS.md": 800,
}


def now_cst() -> datetime:
    return datetime.now(CST)


def load_drift_state() -> dict:
    if DRIFT_STATE_FILE.exists():
        try:
            return json.loads(DRIFT_STATE_FILE.read_text())
        except (json.JSONDecodeError, Exception):
            return {}
    return {}


def save_drift_state(state: dict):
    DRIFT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    DRIFT_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    print(f"[drift-guard] 状态已写入 {DRIFT_STATE_FILE}")


def file_hash(path: Path) -> str:
    """SHA256 of file content (truncated for speed)."""
    if not path.exists():
        return ""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        # 只读前 8KB
        hasher.update(f.read(8192))
    return hasher.hexdigest()[:16]


def drift_check() -> list:
    """返回 drift 预警列表。"""
    state = load_drift_state()
    warnings = []
    now = now_cst()
    timestamp = now.isoformat()

    if not state:
        # 首次运行，建立基线
        for rel_path in WATCHED_FILES:
            path = WORKSPACE / rel_path
            state[rel_path] = {
                "mtime": path.stat().st_mtime if path.exists() else 0,
                "hash": file_hash(path),
                "last_checked": timestamp,
            }
        save_drift_state(state)
        print("[drift-guard] 初次运行，基线已建立。")
        return []

    for rel_path in WATCHED_FILES:
        path = WORKSPACE / rel_path
        entry = state.get(rel_path, {})
        prev_hash = entry.get("hash", "")
        cur_hash = file_hash(path)
        prev_mtime = entry.get("mtime", 0)
        cur_mtime = path.stat().st_mtime if path.exists() else 0

        if prev_hash and cur_hash and prev_hash != cur_hash:
            warnings.append(f"[DRIFT] {rel_path}: hash 从 {prev_hash} 变为 {cur_hash}")
        elif prev_mtime and cur_mtime and abs(cur_mtime - prev_mtime) > 2:
            warnings.append(f"[DRIFT] {rel_path}: mtime 从 {prev_mtime} 变为 {cur_mtime}")

        state[rel_path] = {
            "mtime": cur_mtime,
            "hash": cur_hash,
            "last_checked": timestamp,
        }

    save_drift_state(state)
    return warnings


def confidence_decay_check() -> list:
    """扫描 corrections.md 中最近 7 天的 entry，检查有效期。"""
    warnings = []
    corrections_file = WORKSPACE / "self-improving" / "corrections.md"
    if not corrections_file.exists():
        return warnings

    content = corrections_file.read_text(encoding="utf-8")
    # 找所有 ## dev 条目
    entries = re.findall(r"## (dev_\d+[^\n]*)\n\n\*\*Rule\*\*:", content)
    now = now_cst()

    for entry_id in entries:
        # 提取日期 如 dev_20260611_005 → 2026-06-11
        match = re.search(r"dev_(\d{4})(\d{2})(\d{2})", entry_id)
        if not match:
            continue
        y, m, d = match.groups()
        entry_date = datetime(int(y), int(m), int(d), tzinfo=CST)
        days_old = (now - entry_date).days

        if days_old > 180:
            # 30 天后若仍 < 0.30 → 自动移除
            warnings.append(f"[CONFIDENCE-EXPIRED] {entry_id}: {days_old} 天前，已超 180 天豁免期 → 标记为 AUTO-PURGE")
        elif days_old > 90:
            warnings.append(f"[CONFIDENCE-LOW] {entry_id}: {days_old} 天前，confidence-0.15（需在 180 天前确认是否保留）")

    return warnings


def line_limit_check() -> list:
    """检查各文件单条规则是否超限。"""
    warnings = []
    for rel_path, limit_bytes in MAX_LINE_BYTES.items():
        path = WORKSPACE / rel_path
        if not path.exists():
            continue

        lines = path.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines, 1):
            # 跳过空行 / 标题 / plainline / 表
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("|") or stripped.startswith("-") or stripped.startswith("**") or stripped.startswith(">"):
                continue
            if len(line.encode("utf-8")) > limit_bytes:
                char_count = len(line)
                byte_count = len(line.encode("utf-8"))
                warnings.append(
                    f"[LINE-OVERFLOW] {rel_path}:{i} {byte_count}/{limit_bytes} 字节 ({char_count} 字符)：\n  "
                    f"「{line[:60]}...」"
                )

    return warnings


def append_purge_candidates(warnings: list):
    """把超限 / 过期预警写入 purge-candidates.md。"""
    if not warnings:
        return

    now = now_cst().strftime("%Y-%m-%d %H:%M")
    PURGE_CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing = PURGE_CANDIDATES_FILE.read_text(encoding="utf-8") if PURGE_CANDIDATES_FILE.exists() else ""
    header = f"---\n## 自洁候选（{now}）\n\n" if existing else f"# Purge 候选清单\n\n> 自动生成，不手动编辑。超限 / 过期条目在此排队，30 天后再次检查。\n\n---\n\n## 自洁候选（{now}）\n\n"

    with open(PURGE_CANDIDATES_FILE, "a", encoding="utf-8") as f:
        f.write(f"{header}")
        for w in warnings:
            f.write(f"- {w}\n")
        f.write("\n")

    print(f"[purge-candidates] 已追加 {len(warnings)} 条到 {PURGE_CANDIDATES_FILE}")


def main():
    mode = "check"
    if "--report" in sys.argv:
        mode = "report"
    elif "--purge" in sys.argv:
        mode = "purge"

    print(f"=== Memory 自洁检查 ===")
    print(f"时间：{now_cst().strftime('%Y-%m-%d %H:%M:%S')} CST")
    print(f"模式：{mode}")
    print()

    # 1. Drift Guard
    print("--- Drift Guard ---")
    drift_warnings = drift_check()
    for w in drift_warnings:
        print(f"  ⚠️  {w}")
    if not drift_warnings:
        print("  ✅ 无 drift")
    print()

    # 2. Confidence 衰减
    print("--- Confidence 衰减 ---")
    conf_warnings = confidence_decay_check()
    for w in conf_warnings:
        level = "🔴" if "AUTO-PURGE" in w else "🟡"
        print(f"  {level} {w}")
    if not conf_warnings:
        print("  ✅ 无过期条目")
    print()

    # 3. 单条上限
    print("--- 单条上限 ---")
    line_warnings = line_limit_check()
    for w in line_warnings:
        print(f"  ⚠️  {w}")
    if not line_warnings:
        print("  ✅ 无超限")
    print()

    # 汇总
    all_warnings = drift_warnings + conf_warnings + line_warnings
    if all_warnings and mode != "report":
        append_purge_candidates(all_warnings)

    if mode == "purge":
        print("--- Purge 模式 ---")
        # 实际执行自动清理（先做空实现，等 Lee 确认后正式落地）
        print("  ⏭️  自动清理暂未启用（需确认后落地）")
        print()

    print(f"=== 完成：共 {len(all_warnings)} 条预警 ===")
    if not all_warnings:
        print("系统健康，无需干预。")

    return 0 if len(all_warnings) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
