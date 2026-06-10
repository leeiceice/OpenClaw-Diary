#!/bin/bash
# 每天定时备份维护脚本（凌晨2:00运行）
# 1. git pull 确保最新
# 2. git add + push 推送本地改动
# 3. 备份文件清理（每类保留最新3个）
# 4. 日志记录

WORKSPACE="~/.openclaw/workspace"
BACKUP_DIR="~/.openclaw"
LOG="~/.openclaw/workspace/memory/cron-log.md"

cd "$WORKSPACE" || exit 1

# 1. git pull
git pull --no-rebase origin main >> /dev/null 2>&1

# 2. 检查并推送改动
if git diff --quiet && git diff --cached --quiet; then
    echo "$(date '+%Y-%m-%d %H:%M') - ✅ 无改动，跳过" >> "$LOG"
else
    git add -A
    git commit -m "auto-sync: $(date '+%Y-%m-%d %H:%M') workspace backup"
    timeout 30 git push >> /dev/null 2>&1
    echo "$(date '+%Y-%m-%d %H:%M') - ✅ 已推送" >> "$LOG"
fi

# 3. 备份清理（每类保留最新3个）
cleanup_backups() {
    local dir="$1"
    local pattern="$2"
    local count=$(ls -t "$dir"/$pattern 2>/dev/null | wc -l)
    if [ "$count" -gt 3 ]; then
        ls -t "$dir"/$pattern 2>/dev/null | tail -n +4 | xargs -r rm -f
    fi
}

cleanup_backups "$BACKUP_DIR/backups" "*.json"
cleanup_backups "$BACKUP_DIR" "openclaw.json.bak*"
cleanup_backups "$BACKUP_DIR" "openclaw.json.before-fix.*"
cleanup_backups "$BACKUP_DIR" "openclaw.json.clobbered.*"

echo "$(date '+%Y-%m-%d %H:%M') - ✅ 备份清理完成" >> "$LOG"
