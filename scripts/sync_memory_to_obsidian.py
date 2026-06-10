#!/usr/bin/env python3
"""
同步长期记忆到 Obsidian 备份仓库
将 MEMORY.md 和近期 memory/ 日记同步到 ~/Obsidian/wiki/_archive/2026-05-para-backup/resources/memory-backup/

运行：每日 23:45
"""
import shutil
import time
from datetime import date, datetime, timedelta
from _timezone import CST
from pathlib import Path

MEMORY_MD  = Path("~/.openclaw/workspace/MEMORY.md").expanduser()
MEMORY_DIR = Path("~/.openclaw/workspace/memory").expanduser()
OBSIDIAN   = Path.home() / "Obsidian" / "wiki" / "_archive" / "2026-05-para-backup" / "resources" / "memory-backup"
OBSIDIAN.mkdir(parents=True, exist_ok=True)

def sync_file(src, dst_name):
    """复制文件（带时间戳比较，仅在更新时复制）"""
    dst = OBSIDIAN / dst_name
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
        return True
    return False

def main():
    print(f"[{datetime.now(CST).strftime('%Y-%m-%d %H:%M')}] 同步记忆到 Obsidian...")
    copied = []

    # 1. MEMORY.md
    if sync_file(MEMORY_MD, "MEMORY.md"):
        copied.append("MEMORY.md")

    # 2. 近7天的 diary
    for i in range(7):
        day = date.today() - timedelta(days=i)
        md_file = MEMORY_DIR / f"{day}.md"
        if md_file.exists():
            name = f"diary-{day}.md"
            if sync_file(md_file, name):
                copied.append(name)

    # 3. SESSION-STATE.md (if exists)
    ss = Path("~/.openclaw/workspace/SESSION-STATE.md").expanduser()
    if ss.exists():
        if sync_file(ss, "SESSION-STATE.md"):
            copied.append("SESSION-STATE.md")

    if copied:
        print(f"  ✅ 已同步 {len(copied)} 个文件到 Obsidian:")
        for f in copied:
            print(f"     - {f}")
        # 自动 git 提交 + 推送
        _git_push()
    else:
        print("  ⏭️  无文件需要更新")

def _git_push():
    """自动 commit + push 到 GitHub"""
    import subprocess, os
    vault = Path.home() / "Obsidian"
    os.chdir(vault)
    date_str = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    msg = f"vault backup: {date_str}"
    # 设置 SSH 方式
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"
    for cmd in [
        ["git", "add", "."],
        ["git", "commit", "-m", msg],
        ["git", "push", "origin", "master"],
    ]:
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if r.returncode != 0 and "nothing to commit" not in r.stderr:
            print(f"  ⚠️  git {' '.join(cmd)}: {r.stderr[:100]}")
    print(f"  ✅ 已推送到 GitHub")

if __name__ == "__main__":
    main()
