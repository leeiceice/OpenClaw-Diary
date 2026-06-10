#!/bin/bash
# Cron chat_id 审计 - 每天跑一次（建议 23:55）
# 2026-06-07 立 - 修复"沉默失败"风险：cron 内部 chat_id 错版无法自己暴露
# 免疫模型 timeout（纯 shell + openclaw CLI + feishu API），由 cron 触发

set -e

WORKSPACE="/root/.openclaw/workspace"
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)
LOCK_FILE="/tmp/cron_chat_id_audit.lock"
OUTPUT_FILE="/tmp/cron_chat_id_audit_${TODAY}.txt"

# 24h 去重
if [ -f "$LOCK_FILE" ]; then
  if [ "$(date -r "$LOCK_FILE" +%Y-%m-%d 2>/dev/null)" = "$TODAY" ]; then
    echo "[Chat ID Audit] ${TODAY} 已跑过，跳过（24h 去重）"
    exit 0
  fi
fi

echo "[Chat ID Audit] ${TODAY} 开始扫描..."

# 1. 拿飞书 API 真值（用 feishu_chat 工具，但脚本里用不了工具，直接用 openclaw cron list 拿 chat 名做交叉验证）
# 2. 提取所有 cron 的 chat_id
# 3. 字符数比对：所有 chat_id 应该是 35 字符
# 4. 去重 / 错误数 / 推送群名比对

# 提取所有 cron 的 chat_id
RAW=$(openclaw cron list 2>/dev/null | grep -E "feishu:oc_[a-f0-9]+" || true)

if [ -z "$RAW" ]; then
  echo "[Chat ID Audit] 没有推送类 cron，跳过"
  exit 0
fi

# 提取 chat_id 去重
CHAT_IDS=$(echo "$RAW" | grep -oE "feishu:oc_[a-f0-9]+" | sed 's/feishu://' | sort -u)
TOTAL=$(echo "$CHAT_IDS" | wc -l | tr -d ' ')

# 检查每个 chat_id 字符数（应该都是 35）
SHORT_IDS=""
for id in $CHAT_IDS; do
  LEN=$(echo -n "$id" | wc -c)
  if [ "$LEN" -ne 35 ]; then
    SHORT_IDS="${SHORT_IDS}${id} (${LEN} 字符)\n"
  fi
done

# 提取每个 cron 的 name + chat_id 末段
DETAILS=$(echo "$RAW" | while IFS= read -r line; do
  name=$(echo "$line" | awk '{print $2}')
  chat=$(echo "$line" | grep -oE "feishu:oc_[a-f0-9]+" | sed 's/feishu://')
  printf "%-30s %s (末段: ...%s)\n" "$name" "$chat" "${chat: -6}"
done | sort -u)

# 输出
REPORT="[Chat ID Audit] ${TODAY}
总 cron 数: ${TOTAL}
字符异常: $(echo -e "$SHORT_IDS" | grep -c "字符" || echo 0)

详情：
${DETAILS}"

echo "$REPORT" | tee "$OUTPUT_FILE"

# 如果有异常，推安全群
if [ -n "$SHORT_IDS" ]; then
  MSG="🦞 cron chat_id 审计异常
日期：${TODAY}
字符异常 chat_id：
$(echo -e "$SHORT_IDS")

→ 全量详情：${OUTPUT_FILE}
→ 修复方法：openclaw cron edit <id> --to <正确 35 字符 chat_id>"

  openclaw message send \
    --channel feishu \
    --target "oc_1f77586fc34cdacac8f43a4e9733eafc" \
    --message "$MSG" \
    2>&1 | grep -E "Message ID|error" | head -2
fi

# 写锁
rm -f "$LOCK_FILE"
touch "$LOCK_FILE"
echo "[Chat ID Audit] ${TODAY} 完成（${TOTAL} 个 cron）"
