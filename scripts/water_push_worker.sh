#!/bin/bash
# 喝水推送 worker：消费 /tmp/water_push_queue/push_*.json，调 openclaw CLI 推飞书
# 背景：openclaw CLI 启动 ~50s 不可同步，必须后台跑
# 设计：single-flight（一次只跑一个），跑完一个检查队列里有没有下一个
# 重试：失败自动重试 3 次，间隔 10s
# 写时间：2026-06-08（Lee 要求喝水自动推送不再依赖 Agent 记忆）

set -u

QUEUE_DIR="/tmp/water_push_queue"
LOG_DIR="/tmp/water_push_logs"
mkdir -p "$QUEUE_DIR" "$LOG_DIR"

PAYLOAD_FILE="${1:-}"

run_one() {
    local pf="$1"
    if [ ! -f "$pf" ]; then
        echo "[$(date '+%F %T')] payload 文件不存在: $pf" >&2
        return 1
    fi

    # 解析 payload（jq 优先，否则用 python）
    local channel target message card_path
    if command -v jq >/dev/null 2>&1; then
        channel=$(jq -r '.channel' "$pf")
        target=$(jq -r '.target' "$pf")
        message=$(jq -r '.message' "$pf")
        card_path=$(jq -r '.card_path' "$pf")
    else
        read -r channel target message card_path < <(python3 -c "
import json, sys
with open('$pf') as f:
    d = json.load(f)
print(d['channel'], d['target'], d['message'].replace('\n', '\\n'), d['card_path'])
")
    fi

    echo "[$(date '+%F %T')] 开始推送: target=$target card=$card_path"

    local attempt=1
    local max_attempts=3
    while [ $attempt -le $max_attempts ]; do
        echo "[$(date '+%F %T')] 尝试 $attempt/$max_attempts"

        # openclaw message send，timeout 90s（CLI 启动 50s+）
        local out
        out=$(timeout 90 openclaw message send \
            --channel "$channel" \
            --target "$target" \
            --message "$message" \
            --media "$card_path" 2>&1)
        local rc=$?

        if [ $rc -eq 0 ] && echo "$out" | grep -q "Message ID"; then
            local msgid
            msgid=$(echo "$out" | grep -oE "Message ID: [^ ]+" | head -1)
            echo "[$(date '+%F %T')] ✅ 推送成功: $msgid"
            # 推完删除 payload
            rm -f "$pf"
            return 0
        fi

        echo "[$(date '+%F %T')] ❌ 尝试 $attempt 失败 (rc=$rc): $out" | head -c 500
        attempt=$((attempt + 1))
        if [ $attempt -le $max_attempts ]; then
            sleep 10
        fi
    done

    echo "[$(date '+%F %T')] 💀 重试 $max_attempts 次均失败，payload 保留: $pf"
    return 1
}

# 主循环：跑完指定文件，再检查队列里有没有其他
if [ -n "$PAYLOAD_FILE" ]; then
    run_one "$PAYLOAD_FILE"
else
    # 没有指定文件 → 处理队列里最旧的一个
    first=$(ls -1tr "$QUEUE_DIR"/push_*.json 2>/dev/null | head -1)
    if [ -n "$first" ]; then
        run_one "$first"
    fi
fi

# 顺带处理队列剩余
remaining=$(ls -1tr "$QUEUE_DIR"/push_*.json 2>/dev/null | head -3)
for pf in $remaining; do
    run_one "$pf"
done
