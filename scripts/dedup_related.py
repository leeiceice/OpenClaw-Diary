#!/usr/bin/env python3
"""
清理所有Obsidian笔记中重复的related条目并修复YAML格式
修复 write_related_back 追加bug导致的重复 + 双重引号包裹使Obsidian兼容YAML
"""
import re
import os
from pathlib import Path

OBSIDIAN = Path.home() / "Obsidian"
PATHS_TO_SCAN = [
    OBSIDIAN / "收藏/书籍",
    OBSIDIAN / "收藏/文章",
    OBSIDIAN / "收藏/公众号",
    OBSIDIAN / "PARA",
]

def extract_title_from_link(item):
    m = re.match(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', item)
    return m.group(1).strip() if m else item.strip()

def _yaml_quote(item):
    s = item.strip()
    if s.startswith("- "):
        s = s[2:]
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return '  - "' + escaped + '"'

def dedup_related_block(lines):
    seen = {}
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("- [["):
            continue
        title = extract_title_from_link(stripped)
        if title not in seen:
            seen[title] = True
            result.append(line)
    return result

def fix_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content

    # ── Step 1: Fix frontmatter ──────────────────────────────────────
    # Obsidian frontmatter: starts with "---" on line 0, 
    # first "---" after line 0 is the closing delimiter
    if content.startswith("---"):
        # Find first "---" AFTER position 3 (skip the opening one)
        e1 = content.find("---", 3)
        if e1 > 0:
            # frontmatter INNER content (without the opening "---")
            fm_inner = content[3:e1]
            body = content[e1 + 3:]

            # Parse frontmatter fields
            in_related = False
            related_lines = []
            new_fm_fields = []

            for line in fm_inner.split("\n"):
                if re.match(r"^related:", line):
                    in_related = True
                    continue
                elif in_related and (line.strip().startswith("- [[") or line.startswith("  - [[")):
                    related_lines.append(line)
                else:
                    if in_related and related_lines:
                        deduped = dedup_related_block(related_lines)
                        new_fm_fields.append("related:")
                        new_fm_fields.extend([_yaml_quote(l) for l in deduped])
                        related_lines = []
                        in_related = False
                    new_fm_fields.append(line)

            if in_related and related_lines:
                deduped = dedup_related_block(related_lines)
                new_fm_fields.append("related:")
                new_fm_fields.extend([_yaml_quote(l) for l in deduped])

            frontmatter = "---\n" + "\n".join(new_fm_fields) + "\n---\n"
            content = frontmatter + body

    # ── Step 2: Fix body section ─────────────────────────────────────
    section_marker = "## 🔗 关联文档"
    if section_marker in content:
        sec_idx = content.find(section_marker)
        rest = content[sec_idx + len(section_marker):]
        next_h2 = re.search(r"\n## ", rest)
        block_end = next_h2.start() if next_h2 else len(rest)
        block_text = rest[:block_end]
        block_lines = block_text.strip().split("\n")
        list_items = [l for l in block_lines if l.strip().startswith("- [[")]
        if list_items:
            deduped = dedup_related_block(list_items)
            new_block_lines = ["## 🔗 关联文档", ""]
            for l in deduped:
                stripped = l.strip()
                if stripped.startswith("- "):
                    stripped = stripped[2:]
                escaped = stripped.replace("\\", "\\\\").replace('"', '\\"')
                new_block_lines.append("  - \"" + escaped + "\"")
            new_block_lines.append("")
            content = content[:sec_idx] + "\n".join(new_block_lines) + rest[block_end:]

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False

def main():
    fixed_count = 0
    for base in PATHS_TO_SCAN:
        if not base.exists():
            continue
        for filepath in base.rglob("*.md"):
            try:
                if fix_file(filepath):
                    print(f"Fixed: {filepath.relative_to(OBSIDIAN)}")
                    fixed_count += 1
            except Exception as e:
                print(f"Error {filepath}: {e}")
    print(f"\nTotal: {fixed_count} files")

if __name__ == "__main__":
    main()