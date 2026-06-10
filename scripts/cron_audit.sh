#!/bin/bash
# Cron 健康周报生成器
# 2026-06-07 立: 拆 7a4d0ef9 weekly-cron-audit 出 agentTurn (timeout 600s 不够)
# 输出: 结构化 cron 报告 markdown (给 systemEvent 推安全群用)
# 来源规范: 6/3 cron 健康度规范 - 救命稻草类用 systemEvent + shell 子脚本

set -euo pipefail

JOBS_JSON="/root/.openclaw/cron/jobs.json"
STATE_JSON="/root/.openclaw/cron/jobs-state.json"
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)
NOW_TS=$(date +%s)
THIRTY_DAYS_AGO=$((NOW_TS - 30 * 86400))

# --- 收集 ---
ENABLED_COUNT=$(python3 -c "
import json
d = json.load(open('$JOBS_JSON'))
print(sum(1 for j in d.get('jobs', []) if j.get('enabled', True)))
")
TOTAL_COUNT=$(python3 -c "
import json
d = json.load(open('$JOBS_JSON'))
print(len(d.get('jobs', [])))
")

# 🔴 废弃任务 (disabled 超过30天, 或完全 disabled)
DISABLED_JOBS=$(python3 -c "
import json
d = json.load(open('$JOBS_JSON'))
out = []
for j in d.get('jobs', []):
    if not j.get('enabled', True):
        out.append(f\"- {j.get('name','?')} (id={j.get('id','?')[:8]})\")
print('\n'.join(out) if out else '无')
")

# 🟡 重复调度 (同一时间+时区 多个任务)
DUP_SCHEDULES=$(python3 -c "
import json
from collections import defaultdict
d = json.load(open('$JOBS_JSON'))
buckets = defaultdict(list)
for j in d.get('jobs', []):
    if not j.get('enabled', True):
        continue
    s = j.get('schedule', {})
    key = f\"{s.get('expr','')}@{s.get('tz','')}\"
    buckets[key].append(j.get('name','?'))
out = []
for k, v in buckets.items():
    if len(v) > 1:
        out.append(f\"- [{k}] {' / '.join(v)}\")
print('\n'.join(out) if out else '无')
")

# 🟡 长期未运行 (查 jobs-state.json)
STALE_JOBS=$(python3 -c "
import json
import time
d = json.load(open('$JOBS_JSON'))
try:
    st = json.load(open('$STATE_JSON'))
except Exception:
    st = {}
out = []
state_map = st.get('jobs', {})  # dict {jobId: {state: {...}}}
for j in d.get('jobs', []):
    if not j.get('enabled', True):
        continue
    jid = j.get('id')
    s = state_map.get(jid, {}).get('state', {})
    last_run = s.get('lastRunAtMs', 0) / 1000
    if last_run == 0:
        out.append(f\"- {j.get('name','?')} (从未运行)\")
    elif last_run < $THIRTY_DAYS_AGO:
        days = int((time.time() - last_run) / 86400)
        out.append(f\"- {j.get('name','?')} ({days}天未运行)\")
print('\n'.join(out) if out else '无')
")

# 🔴 连续3次以上 error
ERROR_JOBS=$(python3 -c "
import json
d = json.load(open('$JOBS_JSON'))
try:
    st = json.load(open('$STATE_JSON'))
except Exception:
    st = {}
out = []
state_map = st.get('jobs', {})  # dict {jobId: {state: {...}}}
for j in d.get('jobs', []):
    if not j.get('enabled', True):
        continue
    s = state_map.get(j.get('id'), {}).get('state', {})
    ce = s.get('consecutiveErrors', 0)
    if ce >= 3:
        out.append(f\"- {j.get('name','?')} (连续{ce}次error)\")
print('\n'.join(out) if out else '无')
")

# --- 输出 markdown ---
cat <<EOF
【🦞 Cron 健康周报 | $TODAY】

📊 任务总览: $ENABLED_COUNT / $TOTAL_COUNT 已启用

🔴 废弃任务 (disabled):
$DISABLED_JOBS

🟡 重复调度:
$DUP_SCHEDULES

🟡 长期未运行 (>30天):
$STALE_JOBS

🔴 连续3次以上 error:
$ERROR_JOBS

---
🛠️ 脚本: scripts/cron_audit.sh
🕐 生成于: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M:%S')
EOF
