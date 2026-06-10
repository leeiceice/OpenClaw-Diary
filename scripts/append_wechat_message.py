#!/usr/bin/env python3
"""
微信消息追加到日记原始记录
1. 存档前先 sync 远程（git fetch + 合并去重）
2. 追加新消息（~ 标记已在传入前去掉）
3. Git push
"""

import os, sys, json, subprocess, hashlib, re
from datetime import datetime
from _timezone import CST
from pathlib import Path

WORKSPACE = Path("~/.openclaw/workspace").expanduser()
LOCAL_RAW = WORKSPACE / "diary" / "raw"
OBSIDIAN_RAW = Path(os.path.expanduser("~/Obsidian/日记/raw"))
CHECKPOINT_FILE = "/tmp/wechat_checkpoint.json"

def run(cmd, check=False, timeout=None):
    return subprocess.run(cmd, check=check, capture_output=True, text=True, timeout=timeout)

def log(msg):
    print(msg, flush=True)

def msg_hash(msg):
    return hashlib.sha256(msg.encode('utf-8')).hexdigest()[:16]

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return set(json.load(f).get('written_hashes', []))
    return set()

def save_checkpoint(hashes):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({'written_hashes': list(hashes)}, f)

def strip_tilde(text):
    """去掉消息内容首尾的 ~ 或 ～ 标记"""
    return re.sub(r'^[～~]+|[～~]+$', '', text)

def sync_before_append(date_str):
    """同步前：fetch 远程 + 合并本地和远程的微信消息文件"""
    obsidian_file = OBSIDIAN_RAW / f"微信-{date_str}.md"
    remote_file = Path(f"/tmp/微信-{date_str}_remote.md")

    run(["git", "-C", str(OBSIDIAN_RAW.parent), "fetch", "origin", "master"])

    result = run(["git", "-C", str(OBSIDIAN_RAW.parent), "show", f"origin/master:日记/raw/微信-{date_str}.md"])
    if result.returncode == 0:
        remote_file.write_text(result.stdout, encoding='utf-8')
    else:
        remote_file.write_text("", encoding='utf-8')

    remote_lines = set()
    for line in remote_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            remote_lines.add(line)

    local_lines = set()
    if obsidian_file.exists():
        for line in obsidian_file.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line:
                local_lines.add(line)

    all_lines = remote_lines | local_lines

    obsidian_file.parent.mkdir(parents=True, exist_ok=True)
    content_lines = []
    seen = set()
    if obsidian_file.exists():
        for line in obsidian_file.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and line not in seen:
                content_lines.append(line)
                seen.add(line)
    for line in sorted(all_lines):
        if line not in seen:
            content_lines.append(line)
            seen.add(line)

    obsidian_file.write_text("\n".join(content_lines) + "\n", encoding='utf-8')

    new_count = len(all_lines) - len(remote_lines)
    log(f"🔄 Sync完成: +{new_count}条新消息 (合并{len(all_lines)})")
    return len(all_lines)

def append_wechat_message(message: str, sender: str = "Lee"):
    """追加微信消息到当日 raw 文件，含 sync + 去重 + Git push"""
    now = datetime.now(CST)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    # 去掉首尾 ~ 或 ～
    clean_message = strip_tilde(message)

    entry = f"## {time_str} [{sender}]\n{clean_message}\n"
    h = msg_hash(entry)

    written_hashes = load_checkpoint()
    if h in written_hashes:
        return {"status": "duplicate", "new": False}

    sync_before_append(date_str)

    local_file = LOCAL_RAW / f"微信-{date_str}.md"
    obsidian_file = OBSIDIAN_RAW / f"微信-{date_str}.md"

    for path in [local_file, obsidian_file]:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(entry)

    written_hashes.add(h)
    save_checkpoint(written_hashes)

    try:
        run(["git", "-C", str(OBSIDIAN_RAW.parent), "add", f"raw/微信-{date_str}.md"], check=True)
        run(["git", "-C", str(OBSIDIAN_RAW.parent), "commit", "-m", f"📓 微信消息同步 {date_str} {time_str}"], check=True)
        
        # 第一次 push（不强制）
        result = run(["git", "-C", str(OBSIDIAN_RAW.parent), "push"], timeout=20)
        if result.returncode == 0:
            git_status = "✅ Git同步成功"
        else:
            # push 失败 → 重试：fetch → rebase → push（减少 merge commit）
            log(f"⚠️ 第一次push失败，重试中... {result.stderr[:80]}")
            run(["git", "-C", str(OBSIDIAN_RAW.parent), "fetch", "origin", "master"], timeout=15)
            run(["git", "-C", str(OBSIDIAN_RAW.parent), "rebase", "origin/master"], timeout=15)
            result2 = run(["git", "-C", str(OBSIDIAN_RAW.parent), "push"], timeout=20)
            if result2.returncode == 0:
                git_status = "✅ Git同步成功（重试）"
            else:
                git_status = f"⚠️ Git同步失败: {result2.stderr[:80]}"
    except Exception as e:
        git_status = f"⚠️ Git异常: {e}"

    # 验证：检查 GitHub 远程文件是否写入成功
    verify_result = run(["git", "-C", str(OBSIDIAN_RAW.parent), "show", f"origin/master:日记/raw/微信-{date_str}.md"])
    if verify_result.returncode != 0:
        # 远程没有文件，返回失败，让调用方不回复
        result = {"status": "failed", "new": False, "time": time_str, "git": git_status, "verified": False}
        log(f"❌ 验证失败：远程无文件，Git状态: {git_status}")
        return result

    result = {"status": "success", "new": True, "time": time_str, "git": git_status, "verified": True}
    log(f"✅ 已存档 {time_str} | {git_status}")
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 append_wechat_message.py <消息内容>")
        sys.exit(1)
    result = append_wechat_message(sys.argv[1])
    print(result)
