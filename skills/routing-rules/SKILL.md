---
name: routing-rules
description: 飞书群路由表/判定启发/免@直回/故障排查 — 触发时加载，不自动注入 system prompt
trigger: "提问涉及推送目标 / 群回复 / 路由故障 / 飞书群 ID"
---

# 飞书群路由与推送规则

## 群路由表
- 日常安排：`oc_ad39a8e943103c2164f1d0d9de503da5`（日程/喝水/补剂）
- 学习监督：`oc_3fb5240d43f24be367f5bcd981a0415b`（午间学习）
- 新闻群：`oc_e4686fe5eb6e865b68fae7625a5ce840`（每日简报）
- 进化群：`oc_8e02a9ced0671cac8413b4c98e76637a`（日报/技能/成果）
- 内容收集：`oc_20875a15a62ddeb3c3573d8d23c86daa`（书/收藏）
- 安全群：`oc_1f77586fc34cdacac8f43a4e9733eafc`（备份/审计）

## 判定启发
- 系统内部状态 → 进化群
- Lee 行为（喝水/GNC/学习）→ 日常安排群
- 外部信息 → 新闻群 / 内容收集群
- 安全 / 数据 → 安全群
- 不确定 → 进化群（兜底）

## 群回复
所有飞书群 = 免 @ 直回

## 故障排查
症状：群消息被路由成 DM → 根因：per-group 配置与 allowlist 冲突 → 修复：`openclaw config unset channels.feishu.groups.{chat_id}` + 重启
