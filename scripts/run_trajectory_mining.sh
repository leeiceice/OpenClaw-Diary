#!/bin/bash
# 轨迹挖掘 wrapper（systemEvent 模式专用）
# 跑 trajectory_mining.py + 推飞书摘要 + 错误处理
# 2026-06-07 改造：解决 127k token abort 问题

set -uo pipefail

WORKSPACE="/root/.openclaw/workspace"
LOG="/tmp/trajectory_mining.log"
EVOLUTION_CHAT="oc_8e02a9ced0671cac8413b4c98e76637a"
SECURITY_CHAT="oc_1f77586fc34cdacac8f43a4e9733eafc"

cd "$WORKSPACE" || {
    openclaw message send --channel feishu --target chat:"$SECURITY_CHAT" --message "❌ 轨迹挖掘 wrapper: cd workspace 失败" 2>&1 || true
    exit 1
}

# 跑脚本（捕获 stdout+stderr）
if ! python3 scripts/trajectory_mining.py > "$LOG" 2>&1; then
    # 跑挂了
    TAIL=$(tail -10 "$LOG" 2>/dev/null)
    openclaw message send --channel feishu --target chat:"$SECURITY_CHAT" --message "❌ 轨迹挖掘失败

\`\`\`
$TAIL
\`\`\`" 2>&1 || true
    exit 1
fi

# 跑通了，提取摘要（最后 8-10 行）
SUMMARY=$(tail -10 "$LOG" 2>/dev/null)

# 检查是否有 findings（高价值 > 0）
HIGH=$(grep -oP '高价值：\K[0-9]+' "$LOG" | head -1)
HIGH=${HIGH:-0}

if [ "$HIGH" -eq 0 ]; then
    # 没新东西，简化推送
    openclaw message send --channel feishu --target chat:"$EVOLUTION_CHAT" --message "🦞 轨迹挖掘（每周）：本周 30 天回溯未发现新的高价值 patterns。系统稳。✅" 2>&1 || true
else
    # 有内容，推摘要 + 链接
    openclaw message send --channel feishu --target chat:"$EVOLUTION_CHAT" --message "🦞 轨迹挖掘（每周）：**${HIGH} 条高价值**（30 天回溯）

\`\`\`
$SUMMARY
\`\`\`

📝 完整内容已追加到 \`~/self-improving/corrections.md\`" 2>&1 || true
fi

echo "✅ trajectory mining done, high=$HIGH"
