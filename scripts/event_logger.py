#!/usr/bin/env python3
"""
事件随手记 - 最低阻力记忆写入
用法: python3 scripts/event_logger.py "<一句话事件描述>"
       python3 scripts/event_logger.py "<描述>" --tag=喝水
       python3 scripts/event_logger.py --view

本质: 在 proactivity/daily-working-log.md 末尾追加一行
Cron 提炼时会读取并合并进正式 memory/YYYY-MM-DD.md
"""
import sys
import json
from datetime import datetime, date, timezone, timedelta
from _timezone import CST, now_cst
from pathlib import Path

LOG_FILE = Path("~/.openclaw/workspace/proactivity/daily-working-log.md").expanduser()
TAG_EMOJI = {
    "喝水": "💧",
    "书籍": "📚",
    "记忆": "🧠",
    "系统": "⚙️",
    "决策": "📌",
    "错误": "❌",
    "协作": "🤝",
    "飞书": "💬",
    "健康": "🏥",
    "default": "📝",
}

def get_tag_emoji(tag: str) -> str:
    return TAG_EMOJI.get(tag, TAG_EMOJI["default"])

def log_event(text: str, tag: str = "default"):
    ts = now_cst().strftime("%Y-%m-%d %H:%M")
    emoji = get_tag_emoji(tag)
    entry = f"{emoji} [{ts}] {text}"

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing = LOG_FILE.read_text() if LOG_FILE.exists() else ""
    today = datetime.now(CST).strftime("%Y-%m-%d")

    # 如果文件里有旧日期的记录，清掉，重新开始
    lines = existing.splitlines()
    new_lines = [l for l in lines if not l.startswith(f"# {today}")]
    header = f"# {today} 工作日志\n"
    body = "\n".join(new_lines + [entry, ""])

    LOG_FILE.write_text(header + body, encoding="utf-8")
    return entry

def view_log():
    if not LOG_FILE.exists():
        print("（今日工作日志为空）")
        return
    today = datetime.now(CST).strftime("%Y-%m-%d")
    lines = LOG_FILE.read_text().splitlines()
    # 只显示今天的
    today_lines = []
    show = False
    for line in lines:
        if line.startswith(f"# {today}"):
            show = True
        elif line.startswith("# "):
            show = False
        if show:
            today_lines.append(line)
    if today_lines:
        print("\n".join(today_lines))
    else:
        print("（今日工作日志为空）")

def main():
    if "--view" in sys.argv:
        view_log()
        return

    # 解析参数
    tag = "default"
    texts = []
    for arg in sys.argv[1:]:
        if arg.startswith("--tag="):
            tag = arg.replace("--tag=", "")
        elif not arg.startswith("--"):
            texts.append(arg)

    if not texts:
        print("用法: event_logger.py <事件描述> [--tag=标签] [--view]")
        print("标签可选: " + ", ".join(TAG_EMOJI.keys()))
        return

    text = " ".join(texts)
    entry = log_event(text, tag)
    print(f"✅ 已记: {entry}")

if __name__ == "__main__":
    main()
