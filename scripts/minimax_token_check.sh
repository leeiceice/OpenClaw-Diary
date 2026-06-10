#!/bin/bash
# MiniMax Token Plan 实时用量查询
# 用法：bash scripts/minimax_token_check.sh [--quiet]
#   默认：打印 + 阈值告警
#   --quiet：只在 <20% 时输出
set -e

ENV_FILE="/root/.openclaw/.env"
[ ! -f "$ENV_FILE" ] && ENV_FILE="/root/.openclaw/workspace/.env"
API_KEY=$(grep "MINIMAX_API_KEY" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)

if [ -z "$API_KEY" ]; then
  echo "[MiniMax Check] ❌ API key 未找到"
  exit 1
fi

# 5h 周期额度（Plus ¥49/月 = 600M tokens）
# 30 天 × 24h / 5h = 144 周期
PER_5H=4166667  # tokens

# 调 API
RESP=$(curl -s -X GET "https://www.minimaxi.com/v1/token_plan/remains" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" 2>&1)

if [ -z "$RESP" ]; then
  echo "[MiniMax Check] ❌ API 无响应"
  exit 1
fi

# 解析 JSON
GENERAL_5H=$(echo "$RESP" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    for m in d.get('model_remains', []):
        if m.get('model_name') == 'general':
            print(f\"5h_remaining={m.get('current_interval_remaining_percent',0)}\")
            print(f\"weekly_remaining={m.get('current_weekly_remaining_percent',0)}\")
            print(f\"5h_status={m.get('current_interval_status',0)}\")
            print(f\"weekly_status={m.get('current_weekly_status',0)}\")
            break
except Exception as e:
    print(f'5h_remaining=ERR', file=sys.stderr)
    print(f'5h_remaining=0')
" 2>&1)

FIVE_HOUR_PCT=$(echo "$GENERAL_5H" | grep "^5h_remaining=" | cut -d= -f2)
WEEKLY_PCT=$(echo "$GENERAL_5H" | grep "^weekly_remaining=" | cut -d= -f2)
FIVE_HOUR_STATUS=$(echo "$GENERAL_5H" | grep "^5h_status=" | cut -d= -f2)

# 剩余 token 数
FIVE_HOUR_TOKENS=$(python3 -c "print(int($PER_5H * $FIVE_HOUR_PCT / 100))")
USED_5H=$(python3 -c "print($PER_5H - $FIVE_HOUR_TOKENS)")

# 输出
echo "[MiniMax Check] $(date '+%Y-%m-%d %H:%M:%S CST' 2>/dev/null || date)"
echo "  5h 周期剩余: ${FIVE_HOUR_PCT}% (${FIVE_HOUR_TOKENS} / ${PER_5H} tokens)"
echo "  5h 已用: ${USED_5H} tokens"
echo "  本周剩余: ${WEEKLY_PCT}%"
echo "  5h 状态码: ${FIVE_HOUR_STATUS} (1=充足 2=警告 3=耗尽)"

# 阈值告警（写入 /tmp 状态文件供 HEARTBEAT 读）
STATE_FILE="/tmp/minimax_token_state.json"
cat > "$STATE_FILE" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "five_hour_remaining_pct": $FIVE_HOUR_PCT,
  "five_hour_used_tokens": $USED_5H,
  "five_hour_total_tokens": $PER_5H,
  "five_hour_remaining_tokens": $FIVE_HOUR_TOKENS,
  "weekly_remaining_pct": $WEEKLY_PCT,
  "five_hour_status": $FIVE_HOUR_STATUS
}
EOF

# 阈值判断
ALERT=""
if [ "$FIVE_HOUR_PCT" -lt 10 ]; then
  ALERT="🔴 危急"
elif [ "$FIVE_HOUR_PCT" -lt 30 ]; then
  ALERT="🟠 警告"
elif [ "$FIVE_HOUR_PCT" -lt 50 ]; then
  ALERT="🟡 偏低"
fi

if [ -n "$ALERT" ]; then
  echo ""
  echo "  $ALERT 5h 剩余 < 50%"
  echo "$ALERT" > /tmp/minimax_token_alert.txt
else
  rm -f /tmp/minimax_token_alert.txt
fi

# --quiet 模式
if [ "$1" != "--quiet" ]; then
  echo ""
  echo "  状态文件: $STATE_FILE"
fi

# exit 0=正常 1=告警
if [ -n "$ALERT" ]; then
  exit 1
fi
exit 0
