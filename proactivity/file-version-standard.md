# 文件版本行标准 🦞

> Lee 指令（2026-05-18）：所有带版本行的文件，版本行必须在最后一行。

---

## 规则

带版本行的文件（`_版本：x.x | 最后更新：...`），版本行必须是文件的**最后一行**，不得在版本行后追加任何内容。

---

## 受控文件清单

| 文件 | 路径 |
|------|------|
| MEMORY.md | `~/.openclaw/workspace/MEMORY.md` |
| SOUL.md | `~/.openclaw/workspace/SOUL.md` |
| IDENTITY.md | `~/.openclaw/workspace/IDENTITY.md` |
| USER.md | `~/.openclaw/workspace/USER.md` |
| TOOLS.md | `~/.openclaw/workspace/TOOLS.md` |
| HEARTBEAT.md | `~/.openclaw/workspace/HEARTBEAT.md` |
| AGENTS.md | `~/.openclaw/workspace/AGENTS.md` |
| corrections.md | `~/self-improving/corrections.md` |
| *(其他带版本行的文件)* | *(依此类推)* |

---

## 版本行格式

```
_版本：X.X | 最后更新：YYYY-MM-DD HH:MM | by 作者_
```

---

## 编辑规则

1. **编辑前**：先确认版本行位置，必须是最后一行
2. **编辑时**：新增内容插在版本行**上方**，不得追加在版本行之后
3. **编辑后**：更新版本行时间和版本号
4. **完成后**：验证版本行在最后一行（`tail -1`）

---

## 验证命令

```bash
# 检查版本行是否在最后一行
tail -1 ~/.openclaw/workspace/MEMORY.md
# 期望输出包含 "_版本：" 

# 批量检查所有受控文件
for f in ~/.openclaw/workspace/MEMORY.md ~/.openclaw/workspace/SOUL.md ~/.openclaw/workspace/IDENTITY.md ~/.openclaw/workspace/USER.md ~/.openclaw/workspace/TOOLS.md ~/.openclaw/workspace/HEARTBEAT.md ~/.openclaw/workspace/AGENTS.md; do
  echo -n "$f: "
  tail -1 "$f" | grep "_版本：" > /dev/null && echo "✅" || echo "❌ 需要修复"
done
```

---

## 自动修复脚本

```python
#!/usr/bin/env python3
"""fix-version-line.py — 确保版本行在文件最后一行"""

def fix_file(filepath):
    with open(filepath, "r") as f:
        lines = f.readlines()
    
    # 找出版本行索引
    version_idx = None
    for i, l in enumerate(lines):
        if l.startswith("_版本："):
            version_idx = i
            break
    
    if version_idx is None:
        return f"  {filepath}: 无版本行，跳过"
    
    # 版本行必须在最后
    if version_idx == len(lines) - 1:
        return f"  ✅ {filepath}: 版本行已在最后"
    
    # 重组：版本行之前的内容 + 版本行
    before = lines[:version_idx]
    version = lines[version_idx]
    
    with open(filepath, "w") as f:
        f.writelines(before)
        f.write(version)
    
    return f"  🔧 {filepath}: 已修复（原来在第{version_idx+1}行）"

if __name__ == "__main__":
    import sys
    for fp in sys.argv[1:]:
        print(fix_file(fp))
```

---

_版本：1.0 | 最后更新：2026-05-18 14:45 | by 小龙虾_