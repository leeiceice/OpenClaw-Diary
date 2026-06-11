---
name: diary-daily
description: 每日日记生成流程（22:00 cron）— python3 scripts/diary_daily_report.py 执行 + 异常处理 + fallback 机制
trigger: "提问涉及每日日记生成 / 日记脚本 / diary_daily / 日记写入 Obsidian 相关"
---

# 每日日记生成流程

## 执行命令
```
cd /root/.openclaw/workspace
python3 scripts/diary_daily_report.py 2>&1 | tail -30
```

## cron 参数
- 时间：每日 22:00 CST
- 模型：minimax/MiniMax-M3
- fallback：deepseek/deepseek-v4-flash（M3 调用失败时走）
- timeout：600s
- sessionTarget：isolated（不锁 channel）
- 推送目标：日常安排群（oc_ad39a8e943103c2164f1d0d9de503da5）

## 故障记录
- 2026-06-07：原 sessionKey 锁死微信 IM channel，改为 isolated + agentTurn
- 2026-06-10 22:05：原 model=deepseek-v4-flash + timeout 300s → 302s timeout（model-call-started）
  修复：model→minimax/MiniMax-M3 + timeout→600s，deepseek 降为 fallback

## 健康检查（兜底 cron 63bb338f）
- 每日 22:30 CST 跑 diary_healthcheck.sh
- 检查：flag 文件存在？Obsidian 日记已写入？微信 raw 已归档？
- 异常推安全群（oc_1f77586fc34cdacac8f43a4e9733eafc），24h 去重
- model: deepseek/deepseek-v4-flash（轻量 shell 检查，60s 够用）
