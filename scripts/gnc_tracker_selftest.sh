#!/bin/bash
# GNC tracker 自检（5 用例 dry-run — Lee 2026-06-14 拍 A 配套）
# 类比 water_tracker_selftest.sh 模式
# 备份当前 data → 跑 5 用例 → 还原 data + history → 总结

set -e

WORKSPACE="/root/.openclaw/workspace"
DATA_FILE="${WORKSPACE}/data/gnc-log.json"
HISTORY_FILE="${WORKSPACE}/data/gnc-history.jsonl"
BACKUP_DATA="/tmp/gnc-log-selftest-backup.json"
BACKUP_HIST="/tmp/gnc-history-selftest-backup.json"
LOG_DIR="/tmp/gnc_tracker_selftest"
LOCK_FILE="/tmp/gnc_tracker_selftest.lock"
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)
TODAY_HOUR=$(TZ=Asia/Shanghai date +%H)

mkdir -p "$LOG_DIR"
TODAY_LOG="${LOG_DIR}/${TODAY}.log"

# 24h 去重
if [ -f "$LOCK_FILE" ]; then
  echo "[gnc-selftest] ${TODAY} 已自检过，跳过（24h 去重）"
  exit 0
fi

# 备份
if [ ! -f "$DATA_FILE" ]; then
  echo "[gnc-selftest] ⚠️ data 文件不存在，跳过"
  exit 0
fi
cp "$DATA_FILE" "$BACKUP_DATA"
[ -f "$HISTORY_FILE" ] && cp "$HISTORY_FILE" "$BACKUP_HIST" || touch "$BACKUP_HIST"

PASS=0
FAIL=0
RESULTS=()

check() {
  local name="$1"
  local input="$2"
  local expect_match="$3"  # 子串包含即过
  
  cd "$WORKSPACE"
  out=$(python3 scripts/gnc_tracker.py "$input" --dry-run 2>&1)
  if echo "$out" | grep -q "$expect_match"; then
    PASS=$((PASS+1))
    RESULTS+=("✅ $name：$input → 识别为 GNC")
  else
    FAIL=$((FAIL+1))
    RESULTS+=("❌ $name：$input 未识别 | output: $out")
  fi
}

# 5 用例（覆盖常见 GNC 关键词）
check "A-吃了维生素D"        "吃了维生素D"        "维生素D"
check "B-GNC补剂"            "GNC补剂"            "GNC"
check "C-补了镁"             "补了镁"             "镁"
check "D-复合维生素"          "复合维生素"          "复合维生素"
check "E-不相关消息"          "今天天气真好"        "未识别"

# 还原 data + history
cp "$BACKUP_DATA" "$DATA_FILE"
cp "$BACKUP_HIST" "$HISTORY_FILE"
rm -f "$BACKUP_DATA" "$BACKUP_HIST"

# 写日志
{
  echo "[$(TZ=Asia/Shanghai date -Iseconds)] GNC 自检: ${PASS} pass / ${FAIL} fail"
  printf '%s\n' "${RESULTS[@]}"
} >> "$TODAY_LOG"

# 失败时推进化群
if [ "$FAIL" -gt 0 ]; then
  MSG="🦞 GNC tracker 自检失败（${TODAY} ${TODAY_HOUR}）
通过：${PASS} / 5
失败：${FAIL}
详情：${TODAY_LOG}

→ 检查 scripts/gnc_tracker.py 关键词识别逻辑
→ 5 用例见 scripts/gnc_tracker_selftest.sh"
  openclaw message send \
    --channel feishu \
    --target oc_8e02a9ced0671cac8413b4c98e76637a \
    --message "$MSG" \
    2>&1 || echo "[gnc-selftest] ⚠️ 推送失败"
fi

touch "$LOCK_FILE"
echo "[gnc-selftest] ${TODAY} 完成: ${PASS}/${PASS}+${FAIL} pass"
