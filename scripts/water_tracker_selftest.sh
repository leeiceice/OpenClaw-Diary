#!/bin/bash
# 喝水脚本自检 — 5 用例 dry-run（Lee 2026-06-14 16:46 拍板 A）
# 目的：每次心跳跑一次，发现 dry-run 解析回归时推进化群（24h 去重）
# 用例来源：scripts/water_tracker.py D/B 分支 override 关键词改造验证
# 状态：备份当前 data → 跑 5 用例 → 还原 data → 总结

set -e

WORKSPACE="/root/.openclaw/workspace"
DATA_FILE="${WORKSPACE}/data/water-log.json"
BACKUP_FILE="/tmp/water-log-selftest-backup.json"
LOG_DIR="/tmp/water_tracker_selftest"
LOCK_FILE="/tmp/water_tracker_selftest.lock"
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)
TODAY_HOUR=$(TZ=Asia/Shanghai date +%H)

mkdir -p "$LOG_DIR"
TODAY_LOG="${LOG_DIR}/${TODAY}.log"

# 24h 去重（心跳频率，不需要更高频）
if [ -f "$LOCK_FILE" ]; then
  echo "[selftest] ${TODAY} 已自检过，跳过（24h 去重）"
  exit 0
fi

# 备份
if [ ! -f "$DATA_FILE" ]; then
  echo "[selftest] ⚠️ data 文件不存在，跳过"
  exit 0
fi
cp "$DATA_FILE" "$BACKUP_FILE"

# 5 用例 dry-run 验证
PASS=0
FAIL=0
RESULTS=()

check() {
  local name="$1"
  local input="$2"
  local expected_ml="$3"
  local expected_cups="$4"
  
  cd "$WORKSPACE"
  out=$(python3 scripts/water_tracker.py "$input" --dry-run 2>&1)
  actual_ml=$(echo "$out" | grep "今日累计" | grep -oP '\d+(?=ml)' | head -1)
  actual_cups=$(echo "$out" | grep -oP '\d+(?=杯)' | head -1)
  
  if [ "$actual_ml" = "$expected_ml" ] && [ "$actual_cups" = "$expected_cups" ]; then
    PASS=$((PASS+1))
    RESULTS+=("✅ $name：${actual_ml}ml/${actual_cups}杯")
  else
    FAIL=$((FAIL+1))
    RESULTS+=("❌ $name：期望 ${expected_ml}ml/${expected_cups}杯，实际 ${actual_ml}ml/${actual_cups}杯 | input='$input'")
  fi
}

# 5 用例（基于 2 杯 700ml 起始状态）
check "A-我喝了两杯"     "我喝了两杯"     "700"  "2"
check "B-第3杯"          "第3杯"          "1050" "3"
check "C-漏了一杯补上"   "漏了一杯补上"   "350"  "1"
check "D-再喝一杯"       "再喝一杯"       "1050" "3"
check "E-今天共三杯"     "今天共三杯"     "1050" "3"

# 还原 data
cp "$BACKUP_FILE" "$DATA_FILE"
rm "$BACKUP_FILE"

# 写日志
{
  echo "[$(TZ=Asia/Shanghai date -Iseconds)] 自检结果: ${PASS} pass / ${FAIL} fail"
  printf '%s\n' "${RESULTS[@]}"
} >> "$TODAY_LOG"

# 失败时推进化群（仅 fail > 0）
if [ "$FAIL" -gt 0 ]; then
  MSG="🦞 喝水脚本自检失败（${TODAY} ${TODAY_HOUR}）
通过：${PASS} / 5
失败：${FAIL}
详情：${TODAY_LOG}

→ 检查 scripts/water_tracker.py 解析逻辑回归
→ 5 用例见 scripts/water_tracker_selftest.sh"

  openclaw message send \
    --channel feishu \
    --target oc_8e02a9ced0671cac8413b4c98e76637a \
    --message "$MSG" \
    2>&1 || echo "[selftest] ⚠️ 推送失败"
fi

# 写锁（24h 去重）
touch "$LOCK_FILE"
echo "[selftest] ${TODAY} 完成: ${PASS}/${PASS}+${FAIL} pass"
