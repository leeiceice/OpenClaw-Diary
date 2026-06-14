#!/bin/bash
# 睡眠 tracker 自检（5 用例 dry-run — Lee 2026-06-14 拍 A 配套）
# 备份 history → 跑 5 用例 → 还原 history → 总结

set -e

WORKSPACE="/root/.openclaw/workspace"
HISTORY_FILE="${WORKSPACE}/data/sleep-history.jsonl"
BACKUP_HIST="/tmp/sleep-history-selftest-backup.jsonl"
LOG_DIR="/tmp/sleep_tracker_selftest"
LOCK_FILE="/tmp/sleep_tracker_selftest.lock"
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)
TODAY_HOUR=$(TZ=Asia/Shanghai date +%H)

mkdir -p "$LOG_DIR"
TODAY_LOG="${LOG_DIR}/${TODAY}.log"

# 24h 去重
if [ -f "$LOCK_FILE" ]; then
  echo "[sleep-selftest] ${TODAY} 已自检过，跳过（24h 去重）"
  exit 0
fi

# 备份 history
[ -f "$HISTORY_FILE" ] && cp "$HISTORY_FILE" "$BACKUP_HIST" || touch "$BACKUP_HIST"

PASS=0
FAIL=0
RESULTS=()

check() {
  local name="$1"
  local input="$2"
  local expect_min="$3"
  local stdin_json="${4:-}"  # 可选 stdin JSON
  
  cd "$WORKSPACE"
  if [ -n "$stdin_json" ]; then
    out=$(echo "$stdin_json" | python3 scripts/sleep_tracker.py $input 2>&1)
  else
    out=$(python3 scripts/sleep_tracker.py $input 2>&1)
  fi
  if echo "$out" | grep -q "✓ 睡眠记录已 append" && \
     [ "$(tail -1 $HISTORY_FILE | python3 -c 'import sys,json;print(json.loads(sys.stdin.read()).get("total_sleep_min"))')" = "$expect_min" ]; then
    PASS=$((PASS+1))
    RESULTS+=("✅ $name：total=$expect_min min")
  else
    FAIL=$((FAIL+1))
    RESULTS+=("❌ $name：未通过 | output: $out")
  fi
}

# 5 用例
check "A-stdin-480min"  "--from-stdin" "480"  '{"date":"2026-06-14","totalSleepMin":480}'
check "B-args-450min"   "--date 2026-06-13 --total-min 450" "450"
check "C-args-360min"   "--date 2026-06-12 --total-min 360 --quality 75" "360"
check "D-args-300min"   "--date 2026-06-11 --total-min 300 --quality 60" "300"
check "E-stdin-420min"  "--from-stdin" "420"  '{"date":"2026-06-10","totalSleepMin":420,"deepSleepMin":90,"remSleepMin":120}'

# 还原 history
cp "$BACKUP_HIST" "$HISTORY_FILE"
rm -f "$BACKUP_HIST"

# 写日志
{
  echo "[$(TZ=Asia/Shanghai date -Iseconds)] 睡眠自检: ${PASS} pass / ${FAIL} fail"
  printf '%s\n' "${RESULTS[@]}"
} >> "$TODAY_LOG"

# 失败时推进化群
if [ "$FAIL" -gt 0 ]; then
  MSG="🦞 睡眠 tracker 自检失败（${TODAY} ${TODAY_HOUR}）
通过：${PASS} / 5
失败：${FAIL}
详情：${TODAY_LOG}

→ 检查 scripts/sleep_tracker.py 参数解析
→ 5 用例见 scripts/sleep_tracker_selftest.sh"
  openclaw message send \
    --channel feishu \
    --target oc_8e02a9ced0671cac8413b4c98e76637a \
    --message "$MSG" \
    2>&1 || echo "[sleep-selftest] ⚠️ 推送失败"
fi

touch "$LOCK_FILE"
echo "[sleep-selftest] ${TODAY} 完成: ${PASS}/${PASS}+${FAIL} pass"
