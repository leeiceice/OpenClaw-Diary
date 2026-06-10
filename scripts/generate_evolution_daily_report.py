#!/usr/bin/env python3
"""
进化日报生成脚本 v2.0 - 主题式精简
聚焦 AI 协作心得、决策、错误模式，不报系统状态（系统状态归日常日报）。
从当日 memory 文件提炼。
"""
import os
from datetime import datetime
from _timezone import CST
from pathlib import Path

DATE = datetime.now(CST).strftime("%Y-%m-%d")
MEMORY_FILE = Path(f"~/.openclaw/workspace/memory/{DATE}.md").expanduser()

# 收录关键词（聚焦 AI 协作、决策、进化）
INCLUDE_KEYWORDS = [
    "ai", "协作", "skill", "进化", "工作流", "自动化",
    "openclaw", "报错", "修复", "完成", "新增",
    "决策", "架构", "方案", "教训", "错误", "模式",
    "记忆", "Ontology", "向量", "检索",
]

# 排除关键词（这些归日常日报，不进进化日报）
EXCLUDE_KEYWORDS = [
    "cron", "定时任务", "执行完成", "执行失败",
    "每日记忆提炼", "每日书籍推荐", "每日晨报",
    "喝水追踪", "第1杯", "第2杯", "第3杯",
    "GNC补剂", "学习提醒",
    "系统状态：正常运行", "记忆系统：持续运作",
    "系统状态", "定时任务",
]

def is_excluded(line):
    for kw in EXCLUDE_KEYWORDS:
        if kw in line:
            return True
    return False

def generate_report():
    if not MEMORY_FILE.exists():
        return f"【🦞 进化日报】 {DATE}\n\n今日无记忆记录，AI协作心得待补充。"

    with open(MEMORY_FILE) as f:
        content = f.read()

    lines = content.split("\n")
    entries = []
    current_section = ""

    for line in lines:
        line = line.strip()
        if not line or line.startswith("# ") or line.startswith("===") or line.startswith("---"):
            continue
        if line.startswith("## "):
            current_section = line.replace("## ", "").strip()
            continue
        if current_section and line:
            if is_excluded(line):
                continue
            if any(k in line.lower() for k in INCLUDE_KEYWORDS):
                # 清理格式
                cleaned = line.replace("✅", "■").replace("⚠️", "■").replace("🔺", "■").strip()
                if cleaned.startswith("■"):
                    cleaned = "  • " + cleaned[1:].strip()
                elif not cleaned.startswith("•"):
                    cleaned = "  • " + cleaned
                else:
                    cleaned = "  " + cleaned
                entries.append((current_section, cleaned))

    if not entries:
        return f"【🦞 进化日报】 {DATE}\n\n今日无重大AI协作心得，系统正常运行。"

    # 按 section 分组展示
    by_section = {}
    for section, entry in entries[:15]:
        if section not in by_section:
            by_section[section] = []
        by_section[section].append(entry)

    report_lines = [f"【🦞 进化日报】 {DATE}\n"]
    report_lines.append("🦞 今日AI协作心得：\n")

    # 按 section 展示
    for section, items in by_section.items():
        report_lines.append(f"  ◇ {section}")
        for item in items[:5]:
            report_lines.append(item)
        report_lines.append("")

    return "\n".join(report_lines)

if __name__ == "__main__":
    print(generate_report())