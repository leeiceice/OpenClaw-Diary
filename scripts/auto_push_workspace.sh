#!/bin/bash
# 自动推送 workspace 到 GitHub（每天 20:00 执行）
# 规则：只推 scripts/ + memory/ + notes/ + MEMORY.md + AGENTS.md 等核心文件

cd ~/.openclaw/workspace
TOKEN=$(cat ~/.openclaw/.credentials/github_token 2>/dev/null)
if [ -z "$TOKEN" ]; then
    echo "No token found, skip push"
    exit 0
fi

# 只精确添加关键目录和文件
git add scripts/ memory/ notes/ collections/ proactivity/ data/ config/
git add MEMORY.md AGENTS.md USER.md SOUL.md IDENTITY.md HEARTBEAT.md TOOLS.md


# 检查是否有变更
git diff --staged --quiet && echo "No changes, skip push" && exit 0

# 提交并推送
git commit -m "Auto-sync $(date '+%Y-%m-%d %H:%M') by workspace" 2>/dev/null || exit 0
git push origin main 2>&1 | tail -3