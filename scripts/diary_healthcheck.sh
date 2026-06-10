#!/bin/bash
# 日记生成 cron 健康检查 - 每天 22:30 跑
# 2026-06-07 立 - 修复"5ms ok 但无产物"沉默失败
# 免疫模型 timeout（纯 shell），由 cron 触发

set -e

WORKSPACE="/root/.openclaw/workspace"
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)
LOCK_FILE="/tmp/diary_healthcheck_${TODAY}.lock"
FLAG_FILE="${WORKSPACE}/diary/flags/ran_${TODAY}.flag"
OBSIDIAN_DIARY="$HOME/Obsidian/日记/${TODAY:0:4}/${TODAY:5:2}/${TODAY}.md"
RAW_FILE="$HOME/Obsidian/日记/raw/微信-${TODAY}.md"

# 24h 去重
if [ -f "$LOCK_FILE" ]; then
  if [ "$(date -r "$LOCK_FILE" +%Y-%m-%d 2>/dev/null)" = "$TODAY" ]; then
    echo "[Diary Healthcheck] ${TODAY} 已跑过，跳过（24h 去重）"
    exit 0
  fi
fi

# 检查项
ISSUES=""

# 1. flag 文件存在？
if [ ! -f "$FLAG_FILE" ]; then
  ISSUES="${ISSUES}❌ flag 文件缺失: ${FLAG_FILE}\n"
else
  echo "✅ flag 文件存在: $(cat $FLAG_FILE 2>/dev/null | head -c 20)"
fi

# 2. Obsidian 日记存在？
if [ ! -f "$OBSIDIAN_DIARY" ]; then
  ISSUES="${ISSUES}❌ Obsidian 日记缺失: ${OBSIDIAN_DIARY}\n"
else
  SIZE=$(wc -c < "$OBSIDIAN_DIARY")
  echo "✅ Obsidian 日记存在: ${SIZE} 字符"
  # 太小报警（< 200 字符 = 可能是空文件）
  if [ "$SIZE" -lt 200 ]; then
    ISSUES="${ISSUES}⚠️ Obsidian 日记过小: ${SIZE} 字符\n"
  fi
fi

# 3. raw 文件存在（Lee 这一天有没有 ~ 触发）？
if [ -f "$RAW_FILE" ]; then
  RAW_LINES=$(wc -l < "$RAW_FILE")
  echo "✅ 微信 raw 归档: ${RAW_LINES} 条消息"
else
  echo "ℹ️ 微信 raw 归档: 无（Lee 今日未发 ~ 触发的消息）"
fi

# 4. 推送飞书成功？（看 flag 里的推送时间是否在 cron 应跑时间后）
if [ -f "$FLAG_FILE" ]; then
  FLAG_TIME=$(stat -c %Y "$FLAG_FILE" 2>/dev/null)
  NOW=$(date +%s)
  FLAG_AGE=$((NOW - FLAG_TIME))
  if [ "$FLAG_AGE" -gt 7200 ]; then
    ISSUES="${ISSUES}⚠️ flag 文件过旧: ${FLAG_AGE}s 前生成（> 2h）\n"
  fi
fi

# 5. 推安全群（如有异常）
if [ -n "$ISSUES" ]; then
  MSG="🦞 日记生成健康检查异常
日期：${TODAY}
问题清单：
$(echo -e "$ISSUES")

→ 修复方法：bash ${WORKSPACE}/scripts/diary_daily_report.py
→ 或手动检查：openclaw cron get e44d151d-1d61-4ffc-b735-e5d3a83c337f"

  openclaw message send \
    --channel feishu \
    --target "oc_1f77586fc34cdacac8f43a4e9733eafc" \
    --message "$MSG" \
    2>&1 | grep -E "Message ID|error" | head -2

  echo "⚠️ 异常已推安全群"
else
  echo "✅ 全部正常"
fi

# 写锁
rm -f "$LOCK_FILE"
touch "$LOCK_FILE"
echo "[Diary Healthcheck] ${TODAY} 完成"
