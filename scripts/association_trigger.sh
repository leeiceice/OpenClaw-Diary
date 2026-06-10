#!/bin/bash
# A1: 关联分析触发器（每 2h 跑一次）
# 扫近 4 小时 ~/Obsidian/收藏/**/*.md 中无 related 字段的 → 逐个跑
# 跑完推进化群
set -e
WORKSPACE="/root/.openclaw/workspace"
OBSIDIAN_COLLECT="/root/Obsidian/收藏"

cd "$WORKSPACE"

echo "=== [A1] 扫描 Obsidian 收藏目录 ==="
# 找 4 小时内新增的 .md 文件，且 frontmatter 无 related: 字段
NEW_FILES=$(find "$OBSIDIAN_COLLECT" -name "*.md" -mmin -240 2>/dev/null | while read f; do
  if ! head -30 "$f" 2>/dev/null | grep -q "^related:"; then
    echo "$f"
  fi
done)

COUNT=$(echo -n "$NEW_FILES" | grep -c ".*" 2>/dev/null | head -1)
echo "[A1] 找到 $COUNT 个待分析新收藏"

if [ "$COUNT" -eq 0 ]; then
  echo "✅ [A1] 无新文件待分析"
  exit 0
fi

# 逐个跑
SUCCESS=0
FAIL=0
while IFS= read -r f; do
  if [ -n "$f" ]; then
    echo "--- 分析: $(basename "$f") ---"
    if python3 scripts/association_analysis.py "$f" 2>&1 | tail -5; then
      SUCCESS=$((SUCCESS+1))
    else
      FAIL=$((FAIL+1))
    fi
  fi
done <<< "$NEW_FILES"

echo ""
echo "=== [A1] 完成: success=$SUCCESS fail=$FAIL ==="
