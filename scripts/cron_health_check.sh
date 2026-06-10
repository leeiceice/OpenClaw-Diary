#!/bin/bash
# Cron 状态健康检查（轻量版） — HEARTBEAT 第四步集成
# 2026-06-09 立 — 修复"skipped ≠ error"漏洞：心跳时顺手扫
# 与 cron_disabled_audit.sh 区别：不推送，仅累加日志 + 异常时 exit 1
# 由 l0_watchdog.sh 在 L0 正常时顺带调用

set -e

WORKSPACE="/root/.openclaw/workspace"
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)
STATE_FILE="/tmp/cron_health_state_${TODAY}.json"
THRESHOLD=3
HEALTHY=0

# 拉取所有 cron 状态
CRON_LIST=$(openclaw cron list --all --json 2>/dev/null)
if [ -z "$CRON_LIST" ]; then
  echo "[Cron Health] openclaw cron list 返回空，跳过"
  exit 0
fi

# 解析：找出健康风险项
ISSUES=$(echo "$CRON_LIST" | python3 -c "
import json, sys
data = json.load(sys.stdin)
threshold = ${THRESHOLD}
issues = []
healthy = 0
total = 0
for job in data.get('jobs', []):
    total += 1
    state = job.get('state', {}) or {}
    skip = state.get('consecutiveSkipped', 0) or 0
    err = state.get('consecutiveErrors', 0) or 0
    last_status = state.get('lastRunStatus', 'unknown')
    last_error = state.get('lastError', '') or ''
    name = job.get('name', '?')
    jid = job.get('id', '?')
    # 命中：consecutiveSkipped > 3 或 lastError=disabled 或 consecutiveErrors > 0
    if skip > threshold or last_error == 'disabled' or err > 0:
        issues.append({'id': jid, 'name': name, 'skip': skip, 'err': err, 'last_status': last_status, 'last_error': last_error})
    else:
        healthy += 1
print(json.dumps({'total': total, 'healthy': healthy, 'issues': issues}))
")

# 解析结果
TOTAL=$(echo "$ISSUES" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])")
HEALTHY=$(echo "$ISSUES" | python3 -c "import json,sys; print(json.load(sys.stdin)['healthy'])")
ISSUE_COUNT=$(echo "$ISSUES" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['issues']))")

# 写状态文件（供后续读取/告警）
echo "$ISSUES" > "$STATE_FILE"

# 报告
if [ "$ISSUE_COUNT" -gt 0 ]; then
  echo "[Cron Health] ${TODAY} ⚠️  ${ISSUE_COUNT}/${TOTAL} 个 cron 有健康风险"
  echo "$ISSUES" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for i in data['issues']:
    print(f\"  • {i['name']} [{i['id'][:8]}...]  skip={i['skip']} err={i['err']} status={i['last_status']} last_error={i['last_error']}\")
"
  # 异常 → exit 1，让 l0_watchdog 把"cron 异常"信息也写进 L0 缺口报告（如有）
  exit 1
else
  echo "[Cron Health] ${TODAY} ✅  ${HEALTHY}/${TOTAL} 个 cron 状态正常"
  exit 0
fi
