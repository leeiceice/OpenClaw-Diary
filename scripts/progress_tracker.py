#!/usr/bin/env python3
"""
进度追踪器 - 长时间任务向当前 session 发送进度更新
用法: python3 progress_tracker.py <sessionKey> <task_name> <duration_seconds>
"""
import sys
import time
import urllib.request
import json
from datetime import datetime
from _timezone import CST

SESSION_KEY = sys.argv[1] if len(sys.argv) > 1 else "agent:main:main"
TASK_NAME = sys.argv[2] if len(sys.argv) > 2 else "任务"
DURATION = int(sys.argv[3]) if len(sys.argv) > 3 else 30
INTERVAL = 10  # 每10秒更新一次

def send_message(msg):
    """通过 OpenClaw API 发送消息到 session"""
    try:
        # OpenClaw 的 API 在 12188 端口
        url = f"http://127.0.0.1:12188/v1/sessions/{SESSION_KEY}/messages"
        payload = json.dumps({
            "role": "assistant",
            "content": f"⏳ **{TASK_NAME}**\n{msg}"
        }).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            pass
    except Exception as e:
        print(f"  ⚠️  进度推送失败: {e}", file=sys.stderr)

def main():
    start = time.time()
    print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] 进度追踪启动: {TASK_NAME} (预计{DURATION}秒)")
    
    send_message(f"🚀 开始执行 (预计 {DURATION} 秒)")
    
    while True:
        time.sleep(INTERVAL)
        elapsed = int(time.time() - start)
        remaining = max(0, DURATION - elapsed)
        pct = min(100, int(elapsed / DURATION * 100))
        
        bar = "▓" * (pct // 10) + "░" * (10 - pct // 10)
        msg = f"⏳ 进行中... {elapsed}s / {DURATION}s\n▏{bar}▋ {pct}%\n剩余约 {remaining}s"
        
        print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] {msg}")
        send_message(msg)
        
        if elapsed >= DURATION:
            send_message(f"✅ {TASK_NAME} 即将完成...")
            break

if __name__ == "__main__":
    main()
