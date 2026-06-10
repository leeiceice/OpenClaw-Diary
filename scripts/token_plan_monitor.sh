#!/bin/bash
# Token Plan 采样脚本 — 10:00-15:00 周期监控
# 追加写入 /tmp/token_plan_log.csv，格式: timestamp,5h_remaining_pct,5h_used,total,weekly_pct,status_code

LOG_FILE="/tmp/token_plan_log.csv"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S +08:00')
ENV_FILE="/root/.openclaw/.env"

if [ ! -f "$LOG_FILE" ]; then
    echo "timestamp,5h_remaining_pct,5h_used,total,weekly_pct,status_code" > "$LOG_FILE"
fi

API_KEY=$(grep MINIMAX_API_KEY "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d ' \n' 2>/dev/null)
if [ -z "$API_KEY" ]; then
    echo "$TIMESTAMP,MINIMAX_API_KEY_NOT_FOUND,,,,," >> "$LOG_FILE"
    exit 1
fi

RESP=$(curl -s --max-time 10 https://api.minimaxi.com/v1/token_plan/remains \
    -H "Authorization: Bearer $API_KEY" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$RESP" ]; then
    echo "$TIMESTAMP,CURL_FAILED,,,,," >> "$LOG_FILE"
    exit 1
fi

# Parse response
PCT=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('model_remains',[{}])[0]; print(r.get('current_interval_remaining_percent','?'))" 2>/dev/null)
USED=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('model_remains',[{}])[0]; i=r.get('current_interval_usage_count',0); total=r.get('current_interval_total_count',0); print(f'{i},{total}')" 2>/dev/null)
WEEKLY=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('model_remains',[{}])[0]; print(r.get('current_weekly_remaining_percent','?'))" 2>/dev/null)
STATUS=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('model_remains',[{}])[0]; print(r.get('current_interval_status','?'))" 2>/dev/null)

if [ -z "$PCT" ] || [ "$PCT" = "?" ]; then
    echo "$TIMESTAMP,PARSE_FAILED,,,,," >> "$LOG_FILE"
    echo "$RESP" | head -200
    exit 1
fi

echo "$TIMESTAMP,$PCT,$USED,$WEEKLY,$STATUS" >> "$LOG_FILE"
echo "[OK] $TIMESTAMP | 5h剩余: ${PCT}% | 已用: ${USED%%/*} | 总数: ${USED##*/} | 周: ${WEEKLY}%"
