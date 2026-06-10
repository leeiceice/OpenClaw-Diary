#!/bin/bash
# A2: 关联分析批量补跑（周日 04:00 跑）
# 扫所有 ~/Obsidian/收藏/**/*.md 中无 related 字段的 → 逐个跑
set -e
WORKSPACE="/root/.openclaw/workspace"
OBSIDIAN_COLLECT="/root/Obsidian/收藏"

cd "$WORKSPACE"

echo "=== [A2] 扫描历史欠账 ==="
ALL_FILES=$(find "$OBSIDIAN_COLLECT" -name "*.md" 2>/dev/null | while read f; do
  if ! head -30 "$f" 2>/dev/null | grep -q "^related:"; then
    echo "$f"
  fi
done)

COUNT=$(echo -n "$ALL_FILES" | grep -c ".*" 2>/dev/null | head -1)
echo "[A2] 找到 $COUNT 个历史欠账文件"

if [ "$COUNT" -eq 0 ]; then
  echo "✅ [A2] 无历史欠账"
  exit 0
fi

# 逐个跑
SUCCESS=0
FAIL=0
i=0
while IFS= read -r f; do
  if [ -n "$f" ]; then
    i=$((i+1))
    echo "[$i/$COUNT] $(basename "$f")"
    if python3 scripts/association_analysis.py "$f" 2>&1 | tail -3; then
      SUCCESS=$((SUCCESS+1))
    else
      FAIL=$((FAIL+1))
    fi
    # 每 10 个休息 3s（防 SiliconFlow QPS 限流）
    if [ $((i % 10)) -eq 0 ]; then
      echo "[A2] 休息 3s..."
      sleep 3
    fi
  fi
done <<< "$ALL_FILES"

echo ""
echo "=== [A2] 完成: success=$SUCCESS fail=$FAIL ==="
