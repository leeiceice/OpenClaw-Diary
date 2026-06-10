#!/usr/bin/env python3
"""
WAL 协议执行脚本
每次 Lee 确认重要事实时，运行此脚本固化到三处：
  1. MEMORY.md（长期记忆索引）
  2. memory/YYYY-MM-DD.md（当日事件日志）
  3. TOOLS.md（单一真相源）

用法：
  python3 scripts/wal_protocol.py --rule "新规则描述" --location "归属小节" [--detail "补充说明"]
"""
import sys
import json
from datetime import datetime, timezone, timedelta
from _timezone import CST
from pathlib import Path

MEMORY = Path("~/.openclaw/workspace/MEMORY.md").expanduser()
TODAY_MEMORY = Path(f"~/.openclaw/workspace/memory/{datetime.now(CST).strftime('%Y-%m-%d')}.md").expanduser()
TOOLS = Path("~/.openclaw/workspace/TOOLS.md").expanduser()

def log(msg):
    print(f"[WAL] {msg}", file=sys.stderr)

def today_str():
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M")

def read_file(p):
    return p.read_text(encoding="utf-8") if p.exists() else ""

def append_to_memory(content: str):
    """追加到 MEMORY.md"""
    text = read_file(MEMORY)
    # 找最后一个 ## 章节，在其后追加
    lines = text.splitlines()
    insert = -1
    for i in range(len(lines)-1, -1, -1):
        if lines[i].startswith("## ") and not lines[i].startswith("## "):
            insert = i
            break
    entry = f"\n\n### {today_str()} 自动记录\n{content}"
    if insert == -1:
        lines.append(entry)
    else:
        lines.insert(insert+1, entry)
    MEMORY.write_text("\n".join(lines), encoding="utf-8")
    log(f"已写入 MEMORY.md")

def append_to_today(content: str):
    """追加到今日 memory 文件"""
    TODAY_MEMORY.parent.mkdir(parents=True, exist_ok=True)
    existing = read_file(TODAY_MEMORY)
    entry = f"\n## {today_str()} WAL 记录\n{content}"
    TODAY_MEMORY.write_text(existing + entry, encoding="utf-8")
    log(f"已写入 {TODAY_MEMORY.name}")

def append_to_tools(section: str, content: str):
    """追加到 TOOLS.md 指定小节"""
    text = read_file(TOOLS)
    marker = f"## {section}"
    if marker in text:
        # 找到小节，追加内容
        idx = text.index(marker) + len(marker)
        # 找下一个 ## 标题
        next_section = text.index("\n## ", idx) if "\n## " in text[idx:] else len(text)
        section_content = text[idx:next_section]
        # 追加到小节末尾
        new_section = section_content.rstrip() + f"\n- {content}"
        text = text[:idx] + new_section + text[next_section:]
    else:
        # 新增小节
        text += f"\n\n## {section}\n{content}"
    TOOLS.write_text(text, encoding="utf-8")
    log(f"已追加到 TOOLS.md [{section}]")

def main():
    args = sys.argv[1:]
    if "--rule" not in args:
        print(__doc__)
        return

    rule_idx = args.index("--rule")
    rule = args[rule_idx+1] if rule_idx+1 < len(args) else ""

    location_idx = args.index("--location") if "--location" in args else -1
    location = args[location_idx+1] if location_idx != -1 and location_idx+1 < len(args) else "通用"

    detail_idx = args.index("--detail") if "--detail" in args else -1
    detail = args[detail_idx+1] if detail_idx != -1 and detail_idx+1 < len(args) else ""

    if not rule:
        print("Error: --rule 参数不能为空", file=sys.stderr)
        return

    entry = f"- **{rule}**"
    if detail:
        entry += f" — {detail}"

    # 写入 MEMORY.md（追加到当天最后一个章节后）
    append_to_memory(entry)

    # 写入今日 memory
    append_to_today(entry)

    # 写入 TOOLS.md
    append_to_tools(location, entry)

    print(f"✅ WAL 三处已固化：{rule[:50]}")

if __name__ == "__main__":
    main()
