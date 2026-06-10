#!/usr/bin/env python3
"""
长任务进度通知器
用法: python3 progress_notify.py "<message>" <chat_id>
每15秒重复发送，直到任务完成
"""
import sys, time
from datetime import datetime
from _timezone import CST

msg = sys.argv[1] if len(sys.argv) > 1 else "🔧 任务处理中..."
chat_id = sys.argv[2] if len(sys.argv) > 2 else "oc_ad39a8e943103c2164f1d0d9de503da5"
count = 0

print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] 开始发送进度通知: {msg}")

while count < 20:  # 最多发送20次（5分钟）
    print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] #{count+1} {msg}")
    count += 1
    time.sleep(15)
