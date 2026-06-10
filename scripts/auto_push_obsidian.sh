#!/bin/bash
# 自动推送 Obsidian 到 GitHub（每天 21:00 执行）
cd /root/Obsidian
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519" git pull --rebase origin master 2>&1 || exit 1
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519" git push origin master 2>&1
