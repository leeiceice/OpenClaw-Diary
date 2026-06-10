#!/bin/bash
# Vector store freshness check - HEARTBEAT 第五步集成
# 2026-06-09 立 - 修复 vector_store.db 8 天未更新盲区
# 免疫模型 timeout（纯 shell + stat），由 l0_watchdog.sh 触发

set -e

WORKSPACE="/root/.openclaw/workspace"
VEC_DB="${WORKSPACE}/data/vector_store.db"
THRESHOLD_DAYS=3  # mtime > 3 天 → 告警
STATE_FILE="/tmp/vector_store_freshness_state.json"

# 24h 去重（避免每小时心跳重复推）
LOCK_FILE="/tmp/vector_store_freshness_alert.lock"

# 1. 文件不存在？
if [ ! -f "$VEC_DB" ]; then
  # 不去重：文件丢失是大事故，每次心跳都该报
  echo "{\"status\":\"missing\",\"vec_db\":\"$VEC_DB\"}" > "$STATE_FILE"
  echo "[Vector Freshness] ⚠️  $VEC_DB 不存在"
  exit 1
fi

# 2. 取 mtime + chunks 数
MTIME_EPOCH=$(stat -c %Y "$VEC_DB" 2>/dev/null || echo 0)
NOW_EPOCH=$(date +%s)
AGE_DAYS=$(( (NOW_EPOCH - MTIME_EPOCH) / 86400 ))

# chunks 数（轻量 SQL 查询）
CHUNK_COUNT=$(python3 -c "
import sqlite3
try:
    db = sqlite3.connect('$VEC_DB')
    cur = db.cursor()
    cur.execute('SELECT COUNT(*) FROM chunks')
    print(cur.fetchone()[0])
except Exception as e:
    print(f'ERR:{e}')
" 2>/dev/null || echo "ERR")

# 3. 写状态
cat > "$STATE_FILE" << EOF
{
  "status": "$([ $AGE_DAYS -gt $THRESHOLD_DAYS ] && echo "stale" || echo "ok")",
  "vec_db": "$VEC_DB",
  "mtime_epoch": $MTIME_EPOCH,
  "age_days": $AGE_DAYS,
  "threshold_days": $THRESHOLD_DAYS,
  "chunk_count": "$CHUNK_COUNT"
}
EOF

# 4. 判定
if [ "$AGE_DAYS" -gt "$THRESHOLD_DAYS" ]; then
  echo "[Vector Freshness] ⚠️  $VEC_DB ${AGE_DAYS} 天未更新（阈值 ${THRESHOLD_DAYS} 天，chunks: ${CHUNK_COUNT}）"
  exit 1
else
  echo "[Vector Freshness] ✅  $VEC_DB ${AGE_DAYS} 天前更新（chunks: ${CHUNK_COUNT}）"
  exit 0
fi
