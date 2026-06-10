#!/bin/bash
# Cron 沉默故障审计 - 每天跑一次（建议 0:30）
# 2026-06-09 立 - 修复"skipped ≠ error"漏洞：main session 被冻结时静默跳过
# 免疫模型 timeout（纯 shell + openclaw CLI），由 cron 触发

set -e

WORKSPACE="/root/.openclaw/workspace"
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)
LOCK_FILE="/tmp/cron_disabled_audit.lock"
OUTPUT_FILE="/tmp/cron_disabled_audit_${TODAY}.txt"
THRESHOLD=3  # consecutiveSkipped 阈值

# 24h 去重
if [ -f "$LOCK_FILE" ]; then
  if [ "$(date -r "$LOCK_FILE" +%Y-%m-%d 2>/dev/null)" = "$TODAY" ]; then
    echo "[Disabled Audit] ${TODAY} 已跑过，跳过（24h 去重）"
    exit 0
  fi
fi

echo "[Disabled Audit] ${TODAY} 开始扫描 cron 沉默故障..."

# 1. 拉取所有 cron 状态（--all 包含 disabled；--json 输出完整 state）
CRON_LIST=$(openclaw cron list --all --json 2>/dev/null)

if [ -z "$CRON_LIST" ]; then
  echo "[Disabled Audit] openclaw cron list 返回空，跳过"
  exit 0
fi

# 2. 解析每个 cron 的 id/name/consecutiveSkipped/lastRunStatus/lastError
# openclaw cron list 输出是 JSON 数组格式（已验证），用 python 解析更稳
DETECTED=$(echo "$CRON_LIST" | python3 -c "
import json, sys
data = json.load(sys.stdin)
threshold = ${THRESHOLD}
issues = []
for job in data.get('jobs', []):
    state = job.get('state', {}) or {}
    skip = state.get('consecutiveSkipped', 0) or 0
    err = state.get('consecutiveErrors', 0) or 0
    last_status = state.get('lastRunStatus', 'unknown')
    last_error = state.get('lastError', '') or ''
    name = job.get('name', '?')
    jid = job.get('id', '?')
    # 命中条件：consecutiveSkipped > 3 或 lastError == 'disabled'
    hit = []
    if skip > threshold:
        hit.append('consecutiveSkipped=' + str(skip))
    if last_error == 'disabled':
        hit.append('lastError=disabled')
    if hit and last_status == 'skipped':
        issues.append({
            'id': jid,
            'name': name,
            'skip': skip,
            'err': err,
            'status': last_status,
            'reason': ', '.join(hit)
        })
# 按 skip 倒序
issues.sort(key=lambda x: -x['skip'])
for i in issues:
    # 用 \x1f (Unit Separator) 做字段分隔，避开 | 歧义
    print(i['id'] + '\x1f' + i['name'] + '\x1f' + str(i['skip']) + '\x1f' + str(i['err']) + '\x1f' + i['status'] + '\x1f' + i['reason'])
")

# 3. 统计（-n 防止 echo 末尾多空行，wc -l 统计行数）
if [ -n "$DETECTED" ]; then
  TOTAL_HITS=$(echo "$DETECTED" | wc -l | tr -d ' ')
else
  TOTAL_HITS=0
fi

# 4. 详情（用 \x1f 分隔，避开 name 里可能含 | 的问题）
if [ "$TOTAL_HITS" -gt 0 ]; then
  DETAILS=$(echo "$DETECTED" | awk -F'\x1f' '{printf "  • %s [%s]  skipped=%d  err=%d  status=%s  原因=%s\n", $2, $1, $3, $4, $5, $6}')
else
  DETAILS=""
fi

# 5. 报告
if [ -n "$DETAILS" ]; then
  REPORT="[Cron Disabled Audit] ${TODAY}
扫描 cron 总数: $(echo "$CRON_LIST" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('jobs',[])))")
沉默故障命中: ${TOTAL_HITS}
阈值: consecutiveSkipped > ${THRESHOLD} 或 lastError=disabled

详情：
${DETAILS}"
else
  REPORT="[Cron Disabled Audit] ${TODAY}
扫描 cron 总数: $(echo "$CRON_LIST" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('jobs',[])))")
沉默故障命中: 0
阈值: consecutiveSkipped > ${THRESHOLD} 或 lastError=disabled
✅ 所有 cron 状态正常"
fi

echo "$REPORT" | tee "$OUTPUT_FILE"

# 6. 有命中则推安全群
if [ "$TOTAL_HITS" -gt 0 ]; then
  MSG="🦞 cron 沉默故障审计
日期：${TODAY}
命中：${TOTAL_HITS} 个 cron 处于 skipped/disabled 状态
阈值：consecutiveSkipped > ${THRESHOLD} 或 lastError=disabled

${DETAILS}

→ 根因：OpenClaw main session 入口被冻结，导致 sessionTarget:main + systemEvent 的 cron 静默跳过
→ 修复：把这些 cron 改成 sessionTarget:isolated + agentTurn
→ 全量详情：${OUTPUT_FILE}
→ 参考：corrections.md dev_20260609_003"

  openclaw message send \
    --channel feishu \
    --target "oc_1f77586fc34cdacac8f43a4e9733eafc" \
    --message "$MSG" \
    2>&1 | grep -E "Message ID|error" | head -2
fi

# 写锁
rm -f "$LOCK_FILE"
touch "$LOCK_FILE"
echo "[Disabled Audit] ${TODAY} 完成（命中 ${TOTAL_HITS} 个）"
