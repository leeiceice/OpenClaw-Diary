#!/bin/bash
# 时区铁律守护 - 扫描 naive datetime.now() 用法
# 2026-06-07 立 — 5/26 红线规则的历史欠账清理
# 免疫模型 timeout（纯 shell + grep），由 heartbeat / l0_watchdog 调用

set -e

WORKSPACE="/root/.openclaw/workspace"
SCRIPTS="${WORKSPACE}/scripts"
LOCK_FILE="/tmp/datetime_naive_scanner.lock"
TODAY=$(TZ=Asia/Shanghai date +%Y-%m-%d)

# 24h 去重
if [ -f "$LOCK_FILE" ]; then
  # 检查 lock 是否今日（跨天重置）
  if [ "$(date -r "$LOCK_FILE" +%Y-%m-%d 2>/dev/null)" = "$TODAY" ]; then
    exit 0
  fi
fi

# 扫描：找 .py / .sh 里的 naive datetime.now()
# 排除：
#   - _timezone.py 自身（注释/规范）
#   - 本 scanner 自身（注释里写了示例 datetime.now()）
#   - 已经带时区的：datetime.now(CST) / datetime.now(timezone.utc) / datetime.now(timezone(timedelta...))
#   - 注释行（# 开头的行）
HITS=$(grep -rn "datetime\.now()" "${SCRIPTS}" 2>/dev/null \
  | grep -v "${SCRIPTS}/_timezone.py" \
  | grep -v "${SCRIPTS}/datetime_naive_scanner.sh" \
  | grep -vE "datetime\.now\(CST\)|datetime\.now\(timezone" \
  | grep -vE "^[^:]+:[0-9]+:\s*#" \
  || true)

# 合并去重
ALL_HITS=$(printf "%s\n%s\n" "$HITS" "$HITS_SH" | grep -v "^$" | sort -u || true)

if [ -z "$ALL_HITS" ]; then
  # 干净，无需通知
  rm -f "$LOCK_FILE"
  touch "$LOCK_FILE"
  exit 0
fi

# 违规：推安全群
COUNT=$(echo "$ALL_HITS" | wc -l | tr -d ' ')
MSG="🦞 时区铁律违规预警
日期：${TODAY}
违规数：${COUNT} 处

触发规则：SOUL.md 2026-05-26 红线 — 禁止 datetime.now()（naive datetime）
参考：MEMORY.md 时区规则 / scripts/_timezone.py

违规清单：
${ALL_HITS}

→ 修复方法：改用 from _timezone import now_cst + now_cst() 替换 datetime.now()
→ 历史欠账参考：corrections.md dev_20260607_002（6/7 18:30 全量修复记录）"

openclaw message send \
  --channel feishu \
  --target oc_1f77586fc34cdacac8f43a4e9733eafc \
  --message "$MSG" \
  2>&1 || echo "[Datetime Scanner] ⚠️ 推送失败"

# 写锁（24h 去重）
rm -f "$LOCK_FILE"
touch "$LOCK_FILE"
echo "[Datetime Scanner] ${TODAY} 违规预警已推送（${COUNT} 处）"
