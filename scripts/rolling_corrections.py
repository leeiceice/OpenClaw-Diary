#!/usr/bin/env python3
"""
corrections.md 月度滚动压缩脚本
用法：python3 scripts/rolling_corrections.py [--dry-run]
"""
import re, sys
from datetime import datetime
from _timezone import CST
from pathlib import Path
from collections import defaultdict

CORRECTIONS = Path("~/.openclaw/workspace/self-improving/corrections.md").expanduser()
ARCHIVE_DIR = Path("~/.openclaw/workspace/self-improving/archives").expanduser()
MONTH = datetime.now(CST).strftime("%Y-%m")

def log(msg):
    print(f"[Rolling] {msg}", file=sys.stderr)

def read_file(p):
    return p.read_text(encoding="utf-8") if p.exists() else ""

def parse_entries(text: str):
    """解析 corrections.md 所有条目"""
    # 找到第一个 ## 条目位置
    first_idx = text.find("\n## ")
    if first_idx == -1:
        return "", []
    header = text[:first_idx].rstrip()
    body = text[first_idx:].lstrip("\n")
    
    raw_entries = re.split(r"\n(?=## )", body)
    entries = []
    for block in raw_entries:
        if not block.strip():
            continue
        # 提取日期：[YYYY-MM-DD] 或 （YYYY-MM-DD...）
        date_m = re.search(r"\[(\d{4}-\d{2}-\d{2})\]", block)
        if not date_m:
            date_m = re.search(r"（(\d{4}-\d{2}-\d{2})", block)
        date = date_m.group(1) if date_m else "unknown"
        
        # 提取标题（第一行 ## 后的内容）
        title_m = re.match(r"## (.+)", block)
        title = title_m.group(1).strip() if title_m else "unknown"
        
        entries.append({"date": date, "title": title, "body": block.strip()})
    return header, entries

def extract_domain(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["water", "喝水", "水卡"]): return "喝水系统"
    if any(k in t for k in ["book", "书籍", "书卡", "推荐"]): return "书籍推荐"
    if any(k in t for k in ["cron", "定时", "任务"]): return "定时任务"
    if any(k in t for k in ["memory", "记忆", "提", "固化"]): return "记忆系统"
    if any(k in t for k in ["skill", "安装", "vetter"]): return "Skill管理"
    if any(k in t for k in ["feishu", "飞书", "推送", "群"]): return "飞书/推送"
    if any(k in t for k in ["token", "消耗", "预算"]): return "成本/Turbo"
    return "其他"

def compress_domain(entries: list) -> str:
    """将同一领域多条合并为一条"""
    entries.sort(key=lambda x: x["date"])
    
    if len(entries) == 1:
        return entries[0]["body"]
    
    dates = [e["date"] for e in entries if e["date"] != "unknown"]
    min_d, max_d = (min(dates), max(dates)) if dates else ("", "")
    domain = extract_domain(entries[0]["title"])
    
    # 提取各条 Rule
    rule_lines = []
    for e in entries:
        body = e["body"]
        rule_m = re.search(r"\*\*Rule:\*\* (.+?)(?:\n|$)", body)
        if rule_m:
            rule_lines.append(f"  - [{e['date']}] {rule_m.group(1).strip()}")
    
    merged_title = f"【滚动合并】{domain}（{min_d}～{max_d}，共{len(entries)}条）"
    merged = f"""## {merged_title}

> 自动生成 | 原始条目 {len(entries)} 条已合并为本索引

**领域**: {domain}
**时间跨度**: {min_d} ~ {max_d}
**累计次数**: {len(entries)} 次

### 各条规则
"""
    for r in rule_lines:
        merged += r + "\n"
    
    merged += f"""
### 综合规则
**Rule:** （见上方各条细则）

**Why:** 同一领域多次同类错误，需系统性加固执行流程。

**How to apply:** 参见上方各条，优先固化到 MEMORY.md / TOOLS.md 执行路径。
"""
    return merged

def main(dry_run=True):
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    text = read_file(CORRECTIONS)
    header, entries = parse_entries(text)
    
    if not entries:
        log("无条目，无需压缩")
        return
    
    log(f"共 {len(entries)} 条")
    
    # 按领域分组
    groups = defaultdict(list)
    for e in entries:
        domain = extract_domain(e["title"])
        groups[domain].append(e)
    
    log(f"分为 {len(groups)} 个领域:")
    for d, es in groups.items():
        log(f"  {d}: {len(es)} 条")
    
    # 重建文件
    output_lines = [header, ""] if header else ["# Corrections.md — 纠正记录"]
    output_lines.append("> 每次纠正后顺手写入。格式：**Rule + Why + How to apply**\n")
    
    for domain, es in sorted(groups.items(), key=lambda x: -len(x[1])):
        merged = compress_domain(es)
        output_lines.append(merged)
        output_lines.append("")
    
    new_text = "\n\n".join(output_lines)
    stats = f"压缩完成：{len(entries)} 条 → {len(groups)} 条"
    
    if dry_run:
        log(f"[DRY RUN] {stats}（原 {len(text)} 字 → 新 {len(new_text)} 字）")
        print(new_text)
    else:
        archive = ARCHIVE_DIR / f"corrections_{MONTH}.md"
        archive.write_text(text, encoding="utf-8")
        log(f"已归档: {archive}")
        CORRECTIONS.write_text(new_text, encoding="utf-8")
        log(f"已写入: {CORRECTIONS}")
        print(f"✅ {stats}")

if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
