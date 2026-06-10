#!/usr/bin/env python3
"""
进度广播器 - 通过 OpenClaw 消息通道发送进度
每 10 秒向目标 session 发送一次进度，直到主任务完成
"""
import sys, time, json
from datetime import datetime
from _timezone import CST

SESSION_KEY = sys.argv[1] if len(sys.argv) > 1 else "agent:main:main"
TASK_NAME = sys.argv[2] if len(sys.argv) > 2 else "长任务"
TOTAL_SEC = int(sys.argv[3]) if len(sys.argv) > 3 else 30
INTERVAL = 10

done_file = f"/tmp/progress_{SESSION_KEY.replace(':','_')}.done"

def load_progress():
    f = open(done_file) if __import__('os').path.exists(done_file) else None
    return (f.read().strip() if f else None)

def poll_done():
    return __import__('os').path.exists(done_file)

def get_msg(elapsed, total, task):
    pct = min(100, int(elapsed / total * 100))
    bar = "▓" * (pct // 10) + "░" * (10 - pct // 10)
    remaining = max(0, total - elapsed)
    return (f"⏳ **{task}**\n"
            f"已运行 {elapsed}s / 预计{total}s\n"
            f"▏{bar}▋ {pct}%\n"
            f"剩余约 {remaining}s")

def main():
    print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] 进度广播: {TASK_NAME} (会话={SESSION_KEY}, 预计{TOTAL_SEC}s)")
    
    # 初始化完成文件
    with open(done_file, 'w') as f:
        f.write("")
    
    start = time.time()
    
    # 每10秒检查一次，直到完成文件被删除
    while True:
        time.sleep(INTERVAL)
        elapsed = int(time.time() - start)
        
        if poll_done():
            print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] 任务完成，退出")
            break
        
        msg = get_msg(elapsed, TOTAL_SEC, TASK_NAME)
        print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] {msg}")
        
        # 写入进度到共享文件，供主 agent 读取并发送
        progress_file = f"/tmp/progress_msg_{SESSION_KEY.replace(':','_')}.txt"
        with open(progress_file, 'w') as f:
            f.write(msg)
        
        # 如果超过预期时间的2倍，更新预期
        if elapsed > TOTAL_SEC * 2:
            TOTAL_SEC = elapsed + 20  # 动态延长期望

if __name__ == "__main__":
    main()
