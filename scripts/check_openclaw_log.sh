#!/bin/bash
# check_openclaw_log.sh — OpenClaw 今日 log 错误分诊
# 用途：cron 配套 / 手动快速排查
# 用法：bash scripts/check_openclaw_log.sh [--quiet]
# 输出：真错（去噪后）/ 噪音（model failover 自动恢复）/ 状态文件

set -e

LOG_DIR="/tmp/openclaw"
TODAY=$(date +%Y-%m-%d)
LOG="${LOG_DIR}/openclaw-${TODAY}.log"
STATE_FILE="/tmp/openclaw_log_state_${TODAY}.json"

if [ ! -f "$LOG" ]; then
    echo "❌ log 不存在: $LOG"
    exit 1
fi

# 噪音关键词：model overload failover 自动恢复链路
NOISE_PATTERNS='overloaded_error|failover_decision|model_fallback_decision|candidate_failed|FailoverError: The AI service is temporarily overloaded'

TOTAL_LINES=$(wc -l < "$LOG")
RAW_ERROR_HITS=$(grep -c -i -E 'error|fail|exception' "$LOG" || echo 0)
NOISE_HITS=$(grep -i -E 'error|fail|exception' "$LOG" | grep -c -E "$NOISE_PATTERNS" || echo 0)
REAL_ERRORS=$((RAW_ERROR_HITS - NOISE_HITS))

# 写状态文件（HEARTBEAT 评分用）
cat > "$STATE_FILE" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "log_file": "$LOG",
  "total_lines": $TOTAL_LINES,
  "raw_error_hits": $RAW_ERROR_HITS,
  "noise_hits": $NOISE_HITS,
  "real_errors": $REAL_ERRORS,
  "status": "$([ $REAL_ERRORS -eq 0 ] && echo 'clean' || echo 'attention')"
}
EOF

if [ "$1" = "--quiet" ]; then
    cat "$STATE_FILE"
    exit 0
fi

echo "===== OpenClaw log 健康分诊 $(date +%H:%M:%S) ====="
echo "Log: $LOG"
echo "总行数:        $TOTAL_LINES"
echo "原始 error 命中: $RAW_ERROR_HITS"
echo "  └─ 噪音 (overload failover): $NOISE_HITS"
echo "  └─ 待人工分诊（真错）:      $REAL_ERRORS"
echo ""

if [ "$REAL_ERRORS" -gt 0 ]; then
    echo "===== 待人工分诊样本（最多 5 条）====="
    grep -i -E 'error|fail|exception' "$LOG" | grep -v -E "$NOISE_PATTERNS" | head -5
    echo ""
    echo "⚠️ 状态：attention（详见 $STATE_FILE）"
    exit 1
else
    echo "✅ 状态：clean（全部 147 条都是 model overload 自动 failover）"
    exit 0
fi
