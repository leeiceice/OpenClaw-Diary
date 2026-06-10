#!/bin/bash
# Cron 失败任务自动重试脚本
# 纯 shell 实现，不调模型 → 不会被 300s/600s timeout 反复 kill
# 设计目标：每 15 分钟跑一次，发现失败任务就触发 openclaw cron run

set -u
WORKSPACE="/root/.openclaw/workspace"
LOG_FILE="$WORKSPACE/memory/cron-retry.log"
NOTIFY_GROUP="oc_8e02a9ced0671cac8413b4c98e76637a"  # 进化群
MAX_RETRIES_PER_RUN=3  # 每次最多重试 3 个任务，避免雪崩
COOLDOWN_FILE="/tmp/cron_retry_cooldown.json"

mkdir -p "$(dirname "$LOG_FILE")"
TS() { date '+%Y-%m-%d %H:%M:%S'; }

log() { echo "[$(TS)] $*" | tee -a "$LOG_FILE"; }

# 1. 拉取所有任务
JOBS_JSON=$(openclaw cron list --json 2>/dev/null) || {
  log "ERROR: openclaw cron list 失败"
  exit 1
}

# 2. 提取连续失败任务（consecutiveErrors >= 2）
FAILED_IDS=$(echo "$JOBS_JSON" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    jobs = data.get('jobs', data) if isinstance(data, dict) else data
    failed = []
    for j in jobs:
        if not j.get('enabled', True): continue
        st = j.get('state', {})
        ce = st.get('consecutiveErrors', 0)
        if ce >= 2:
            failed.append({
                'id': j['id'],
                'name': j.get('name','?'),
                'errors': ce,
                'last_status': st.get('lastRunStatus','?'),
                'last_error': (st.get('lastError') or st.get('lastDiagnosticSummary') or '')[:80]
            })
    print(json.dumps(failed))
except Exception as e:
    print('[]', file=sys.stderr)
    sys.exit(0)
")

if [ -z "$FAILED_IDS" ] || [ "$FAILED_IDS" = "[]" ]; then
  log "无失败任务，跳过"
  exit 0
fi

log "发现失败任务：$FAILED_IDS"

# 3. 简单的冷却期：上次重试过的任务在 30 分钟内不再重试
if [ -f "$COOLDOWN_FILE" ]; then
  COOLDOWN_DATA=$(cat "$COOLDOWN_FILE" 2>/dev/null || echo "{}")
else
  COOLDOWN_DATA="{}"
fi

NOW=$(date +%s)
COOLDOWN_TTL=1800  # 30 分钟

# 4. 触发重试（最多 MAX_RETRIES_PER_RUN 个）
RETRIED=0
echo "$FAILED_IDS" | python3 -c "
import json, sys
failed = json.loads('''$FAILED_IDS''')
print('\n'.join(f\"{f['id']}|{f['name']}|{f['errors']}|{f['last_error']}\" for f in failed))
" | while IFS='|' read -r JID JNAME JERR JERR_MSG; do
  if [ $RETRIED -ge $MAX_RETRIES_PER_RUN ]; then
    log "已达本轮重试上限 ($MAX_RETRIES_PER_RUN)，剩余任务留待下轮"
    break
  fi

  # 检查冷却期
  LAST_RETRY=$(echo "$COOLDOWN_DATA" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('$JID', 0))
except: print(0)
")
  if [ -n "$LAST_RETRY" ] && [ $((NOW - LAST_RETRY)) -lt $COOLDOWN_TTL ]; then
    log "SKIP: $JNAME (冷却中，剩余 $((COOLDOWN_TTL - (NOW - LAST_RETRY)))s)"
    continue
  fi

  log "重试 $JNAME ($JID, 连续 ${JERR} 次失败)..."
  if openclaw cron run "$JID" --timeout 90000 >/dev/null 2>&1; then
    log "  → 已触发重试"
    RETRIED=$((RETRIED + 1))
    # 更新冷却期
    python3 -c "
import json
try:
    d = json.load(open('$COOLDOWN_FILE'))
except: d = {}
d['$JID'] = $NOW
json.dump(d, open('$COOLDOWN_FILE','w'))
" 2>/dev/null
  else
    log "  → 重试命令失败"
  fi
done

log "本轮重试完成"
