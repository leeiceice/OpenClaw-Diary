---
name: daily-news
description: 每日新闻简报产出发送流程（09:00 cron）— daily-briefing.sh 调用 + 飞书推送 + timeout 处理
trigger: "提问涉及每日新闻 / 新闻简报 / daily-briefing / 09:00 cron 相关"
---

# 每日新闻简报流程

## 执行命令
```
MSG=$(bash /root/.openclaw/workspace/scripts/daily-briefing.sh 2>&1)
openclaw message send --channel feishu --target chat:oc_e4686fe5eb6e865b68fae7625a5ce840 --message "$MSG"
```

## cron 参数
- 时间：每日 09:00 CST（cron 69e9d850-6172-4c0a-a2eb-7ac587e389d8）
- 模型：minimax/MiniMax-M3
- timeout：600s（2026-06-11 修复：180→600，因 09:00 miniMax 高并发尖峰经常 timeout）
- 推送目标：新闻群（oc_e4686fe5eb6e865b68fae7625a5ce840）
- delivery：mode=none（脚本自身推消息，不依赖 cron delivery）
- failureAlert：1 次失败 → 进化群

## 故障记录
- 2026-06-11 09:00：180s timeout（model-call-started 阶段卡死）
  根因：miniMax-M3 在 09:00 整点高并发 + 每次 180s 不够
  修复：timeout→600s（cron 健康度规范要求）
  09:00 第一次 timeout→180.4s，09:03 重试→OK（123.5s/50284 tokens，推送成功）
