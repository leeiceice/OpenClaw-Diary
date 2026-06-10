#!/usr/bin/env python3
"""
日末工作日志合并脚本
读取 proactivity/daily-working-log.md 中的今日随手记，
追加到正式的 memory/YYYY-MM-DD.md，然后清空随手记。

由日末 cron 触发（建议 23:50 执行）。
"""
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

WORKING_LOG = Path("~/.openclaw/workspace/proactivity/daily-working-log.md").expanduser()
MEMORY_DIR = Path("~/.openclaw/workspace/memory").expanduser()

def main():
    today = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    memory_file = MEMORY_DIR / f"{today}.md"

    if not WORKING_LOG.exists():
        print("（无随手记，跳过）")
        return

    lines = WORKING_LOG.read_text(encoding="utf-8").splitlines()
    today_entries = []
    in_today = False

    for line in lines:
        if line.startswith(f"# {today}"):
            in_today = True
        elif line.startswith("# "):
            in_today = False
        elif in_today and line.strip():
            today_entries.append(line)

    if not today_entries:
        print("（今日随手记为空，跳过）")
        return

    # 追加到正式 memory
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    existing = memory_file.read_text(encoding="utf-8") if memory_file.exists() else ""

    merger_note = f"\n## {today} 日末合并（来自随手记）\n"
    entries_text = "\n".join(today_entries)

    memory_file.write_text(existing + merger_note + entries_text + "\n", encoding="utf-8")

    # 清空随手记（只保留其他日期的）
    other_lines = [l for l in lines if not (l.startswith(f"# {today}") or (in_today and l.strip() == ""))]
    # 重新判断 in_today
    filtered = []
    skip_today = False
    for line in lines:
        if line.startswith(f"# {today}"):
            skip_today = True
            continue
        elif line.startswith("# ") and skip_today:
            skip_today = False
        if not skip_today:
            filtered.append(line)

    WORKING_LOG.write_text("\n".join(filtered), encoding="utf-8")

    print(f"✅ 已合并 {len(today_entries)} 条到 {memory_file.name}")
    print(f"随手记已清空")

if __name__ == "__main__":
    main()
