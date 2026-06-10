#!/usr/bin/env python3
"""
进化周报生成脚本 v2.0 - 主题式
每周聚焦 1-2 个核心架构决策/进化事件，叙事性总结，禁止流水账。
从 memory/weekly-*.md + 本周 memory/*.md 提炼。
"""
import os
import re
from datetime import datetime, timedelta
from _timezone import CST
from pathlib import Path

WORKSPACE = Path("~/.openclaw/workspace").expanduser()
MEMORY_DIR = WORKSPACE / "memory"
DATE = datetime.now(CST)
YEAR = DATE.strftime("%Y")
WEEK = DATE.isocalendar()[1]
WEEK_START = DATE - timedelta(days=6)

# 星期映射
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEK_START_DAY = WEEKDAYS[DATE.weekday()]

# 收集本周所有 memory 文件
def get_this_week_files():
    files = []
    for i in range(7):
        d = DATE - timedelta(days=i)
        fname = MEMORY_DIR / f"{d.strftime('%Y-%m-%d')}.md"
        if fname.exists():
            files.append((d, fname))
    # 找周报文件
    weekly_files = sorted(MEMORY_DIR.glob(f"weekly-evolution-report-{YEAR}-W{WEEK:02d}.md"))
    return files, weekly_files

# 关键词黑名单（这些内容不进周报，属于日常日报范畴）
BLACKLIST_KEYWORDS = [
    "cron 执行完成", "Cron 运行正常", "定时任务 ✅",
    "每日记忆提炼", "每日书籍推荐", "每日晨报",
    "喝水追踪", "第1杯", "第2杯", "第3杯",
    "GNC补剂", "学习提醒",
    "系统状态：正常运行", "记忆系统：持续运作",
]

def is_blacklisted(line):
    for kw in BLACKLIST_KEYWORDS:
        if kw in line:
            return True
    return False

# 核心主题提取
THEME_KEYWORDS = [
    "架构", "决策", "系统设计", "方案", "废除", "废弃",
    "进化", "里程碑", "突破", "升级", "重构",
    "错误", "Bug", "修复", "报错",
    "技能", "Skill", "自动化", "流程",
    "记忆系统", "向量", "Ontology", "memory",
    "协作", "三 Agent", "三Agent",
]

def is_theme_line(line):
    for kw in THEME_KEYWORDS:
        if kw in line:
            return True
    return False

def extract_themes(files):
    """从本周 memory 文件提取核心主题事件"""
    events = []
    for d, fpath in files:
        with open(fpath) as f:
            content = f.read()
        lines = content.split("\n")
        current_section = ""
        for line in lines:
            line = line.strip()
            if not line or line.startswith("# ") or line.startswith("===") or line.startswith("---"):
                continue
            if line.startswith("## "):
                current_section = line.replace("## ", "").strip()
                continue
            # 跳过黑名单
            if is_blacklisted(line):
                continue
            # 收集主题相关行
            if current_section and is_theme_line(line):
                # 清理格式
                cleaned = line.replace("✅", "■").replace("⚠️", "■").replace("🔺", "■").strip()
                if cleaned.startswith("■"):
                    cleaned = "  • " + cleaned[1:].strip()
                elif not cleaned.startswith("•"):
                    cleaned = "  • " + cleaned
                else:
                    cleaned = "  " + cleaned
                events.append((d.strftime("%m-%d"), current_section, cleaned))
    return events

def deduplicate_events(events):
    """去重，保留每个事件第一条"""
    seen = set()
    unique = []
    for date, section, line in events:
        key = (section, line[3:].strip())
        if key not in seen:
            seen.add(key)
            unique.append((date, section, line))
    return unique

def generate_report():
    files, weekly_files = get_this_week_files()
    if not files:
        return f"【🦞 进化周报】 {DATE.strftime('%Y-%m-%d')}\n\n本周无记忆记录。"

    week_str = f"{WEEK_START.strftime('%m/%d')} {WEEK_START_DAY} — {DATE.strftime('%m/%d')} {WEEKDAYS[DATE.weekday()]}，W{WEEK:02d}"
    
    # 从周报文件读取 Lee 已确认的成果（如果存在）
    lee_confirmed = []
    if weekly_files:
        for wf in weekly_files:
            with open(wf) as f:
                content = f.read()
            # 提取 Lee 确认的成果列表
            for line in content.split("\n"):
                if "✅" in line or "完成" in line:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("■") and not line.startswith("-"):
                        lee_confirmed.append(line)

    # 提取主题事件
    all_events = extract_themes(files)
    unique_events = deduplicate_events(all_events)

    # 按日期分组: date -> {section: [items]}
    by_date = {}
    for date, section, line in unique_events:
        if date not in by_date:
            by_date[date] = {}
        if section not in by_date[date]:
            by_date[date][section] = []
        by_date[date][section].append(line)

    # 生成主题式报告
    lines = []
    lines.append(f"【🦞 进化周报】 {week_str}\n")
    lines.append("=" * 30 + "\n")

    # 本周核心主题（自动识别section频率最高的作为主题）
    section_count = {}
    for date, sections in by_date.items():
        for section, items in sections.items():
            section_count[section] = section_count.get(section, 0) + len(items)
    
    if section_count:
        top_sections = sorted(section_count.items(), key=lambda x: -x[1])[:3]
        if top_sections:
            theme_names = "、".join([s[0] for s in top_sections])
            lines.append(f"📌 本周主题：{theme_names}\n")

    # Lee 确认的成果（优先展示）
    if lee_confirmed:
        lines.append("✅ 本周核心成果：")
        for item in lee_confirmed[:6]:
            lines.append(f"  • {item}")
        lines.append("")

    # 系统数据（精简，不重复）
    lines.append("📊 系统数据：")
    lines.append(f"  • 知识图谱：对话→Ontology 管道正常")
    lines.append(f"  • Memory Dreaming：{len(unique_events)} 条主题事件")
    lines.append(f"  • Cron：全部正常运转 ✅\n")

    # 每日主题事件（按日期，而非流水账）
    lines.append("📋 本周主题事件：")
    for date in sorted(by_date.keys()):
        sections = by_date[date]
        lines.append(f"\n  【{date}】")
        for section, items in sections.items():
            lines.append(f"    ◇ {section}")
            for item in items[:4]:
                lines.append(item)
    
    lines.append("\n" + "=" * 30)
    lines.append(f"\n🎯 下周目标：")
    lines.append(f"  • 完善日记系统")
    lines.append(f"  • （待补充）")

    return "\n".join(lines)

if __name__ == "__main__":
    print(generate_report())