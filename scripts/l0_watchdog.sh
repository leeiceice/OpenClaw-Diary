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

# === 2026-06-14 自愈（Lee 拍板 A）===
# 缺失或过小时：自动创建占位 L0，再推告知（不再等 Lee 推我）
AUTO_CREATED="false"
if [ ! -f "$L0_FILE" ]; then
  AUTO_CREATED="true"
  NOW_ISO=$(TZ=Asia/Shanghai date -Iseconds)
  cat > "$L0_FILE" <<EOF
---
date: ${TODAY}
type: l0-daily
agent: 小龙虾
created: ${NOW_ISO}
status: auto-created
trigger: l0_watchdog.sh (heartbeat 触发,Lee 拍板 A 改造)
---

# ${TODAY} L0（auto-created 占位）

## 事件
（暂无 — heartbeat 自愈建文件，后续 cron / 真实事件会自动追加）

## 决策
（暂无）

## 异常
（暂无）

---

_auto-created by l0_watchdog.sh at ${NOW_ISO} — heartbeat 自愈机制（Lee 拍板 A）_
EOF
  SIZE=$(stat -c %s "$L0_FILE")
  STATUS="auto_created"
fi

# 推送安全群（只告知，不再要求立即人工补）
MSG="🦞 L0 自愈报告
日期：${TODAY}
状态：${STATUS}（${SIZE} 字节）
路径：${L0_FILE}
动作：watchdog 已自动创建占位 L0，后续事件会按时间自动追加
（Lee 2026-06-14 拍板 A：自愈不再等人工介入）"

openclaw message send \
  --channel feishu \
  --target oc_1f77586fc34cdacac8f43a4e9733eafc \
  --message "$MSG" \
  2>&1 || echo "[L0 Watchdog] ⚠️ 推送失败，请人工检查"

# 写锁文件（24h 去重 — 即便后续再跑也不再推）
touch "$LOCK_FILE"
echo "[L0 Watchdog] ${TODAY} ${STATUS}（已自愈+推告知）"
