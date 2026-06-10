#!/bin/bash
# L0 Watchdog — 心跳时强制检查当日 L0 存在性
# 2026-06-07 立 — 修复 L0 连续 2 天缺口
# 免疫模型 timeout（纯 shell），由 cron 触发

set -e

WORKSPACE="/root/.openclaw/workspace"
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)
L0_FILE="${WORKSPACE}/memory/${TODAY}.md"
LOCK_FILE="/tmp/l0_watchdog_${TODAY}.lock"
MIN_SIZE=200  # 字节，空模板视为缺失
HOUR=$(TZ=Asia/Shanghai date +%H)

# 清醒窗口：00:00-08:00 静默（人在睡觉，不该打扰）
if [ "$HOUR" -lt 8 ]; then
  echo "[L0 Watchdog] ${TODAY} ${HOUR}:xx 清醒窗口外（00:00-08:00），静默"
  exit 0
fi

# 24h 去重
if [ -f "$LOCK_FILE" ]; then
  echo "[L0 Watchdog] ${TODAY} 已推送过预警，跳过（24h 去重）"
  exit 0
fi

# 主动检查
if [ ! -f "$L0_FILE" ]; then
  STATUS="missing"
  SIZE=0
elif [ $(stat -c %s "$L0_FILE" 2>/dev/null || echo 0) -lt $MIN_SIZE ]; then
  STATUS="too_small"
  SIZE=$(stat -c %s "$L0_FILE")
else
  echo "[L0 Watchdog] ${TODAY} L0 正常（$(stat -c %s "$L0_FILE") 字节）"
  # 顺手扫时区铁律（不阻断 L0 路径）
  bash "${WORKSPACE}/scripts/datetime_naive_scanner.sh" || true
  # 2026-06-09 新增：顺手扫 cron 沉默故障（HEARTBEAT 第四步增强）
  bash "${WORKSPACE}/scripts/cron_health_check.sh" || true
  # 2026-06-09 新增：顺手扫 vector_store.db 陈旧（HEARTBEAT 第五步增强）
  bash "${WORKSPACE}/scripts/check_vector_store_freshness.sh" || true
  # 2026-06-10 新增：顺手扫 MiniMax Token Plan 5h 剩余（Lee 拍板接入）
  bash "${WORKSPACE}/scripts/minimax_token_check.sh" --quiet || true
  exit 0
fi

# 推送安全群
MSG="🦞 L0 缺口预警
日期：${TODAY}
状态：${STATUS}（文件不存在或 < ${MIN_SIZE} 字节）
路径：${L0_FILE}

→ 原因：实时写入全靠手动，无机制保证
→ 修复：见 corrections.md dev_20260607_001
→ 动作：小龙虾请立即评估并补写"

# 用 openclaw message send 推送到安全群
openclaw message send \
  --channel feishu \
  --target oc_1f77586fc34cdacac8f43a4e9733eafc \
  --message "$MSG" \
  2>&1 || echo "[L0 Watchdog] ⚠️ 推送失败，请人工检查"

# 写锁文件（24h 去重）
touch "$LOCK_FILE"
echo "[L0 Watchdog] ${TODAY} 预警已推送（${STATUS}）"
