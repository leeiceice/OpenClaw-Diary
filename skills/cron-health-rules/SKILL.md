---
name: cron-health-rules
description: Cron 健康度/新建规范/模型分流/timeout/lightContext — 触发时加载，不自动注入 system prompt
trigger: "提问涉及 cron 新建 / 改 timeout / 问健康度 / Token Plan 相关"
---

# Cron 健康与新建规则

## 新建 Cron 规范
- 新建 cron：必须 `channel:feishu` + `to:oc_xxx`，禁止 `channel:last`
- 并发冲突：新 cron 与已有 cron 错开 ≥30 分钟
- 任务完成后**立即删除** cron 提醒
- **高频 cron（≤15min）必须 `lightContext: true`**（bootstrap 200KB → 4KB）
- 纯 shell 任务可考虑 systemEvent

## 健康度规范
- **agentTurn 任务 timeoutSeconds ≥ 600s**
- **救命稻草类 cron 必须用 systemEvent 或纯 shell**
- **cron update patch 不支持局部字段** → 必须传完整 payload

## 模型分流
- 主会话：MiniMax-M3；cron 任务：minimax/MiniMax-M3
- DeepSeek v4 Flash：仅限 cron 定时任务
- cron 以外 DeepSeek：需通知 Lee

## Token Plan 参数
- Plus ¥49/月 = 600M tokens/月；**5h 周期 = 4.16M tokens**
- 周期重置：00:00 / 05:00 / 10:00 / 15:00 / 20:00
- 查询：`bash scripts/minimax_token_check.sh`
