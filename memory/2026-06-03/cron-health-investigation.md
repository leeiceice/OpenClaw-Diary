# 2026-06-03 Cron 健康度调查

## 调查背景
Lee 让我观察 cron 的运行健康度 → 主动调查 → 发现系统性 timeout 问题

## 关键发现
- 全量 cron 运行 4481 次 → 失败 834 次（18.6%）
- timeout 错误 401 次，占失败的 48%
- max timeout 312784ms（>300s）→ OpenClaw cron 默认 300s 误杀长任务
- cron-retry-monitor 自己也是 agentTurn → 被 timeout 杀 152 次（救命的自己也是病人）
- 旧模型名错误（5-29 ~ 6-01 期间）已经自愈

## 执行修复
- A: 3 个任务的旧模型名修正
  - 015c625e 周报提醒: minimax-portal/MiniMax-M2.7 → deepseek/deepseek-v4-flash
  - 69830285 Skill 安全周报: 同上
  - 75f8d6c2 月度 Cron 检查: deepseek-flash/deepseek-v4-flash → deepseek/deepseek-v4-flash
- B: cron-retry-monitor timeout 300s → 600s
- C: 根因分析（发现 401 次 timeout 全是同一根因）
- D: **32 个 agentTurn 任务 timeout 全部调到 600s**
- E: **新建 scripts/cron_retry.sh（纯 shell） + agentTurn wrapper 包装**
  - shell 自包含检测+重试+冷却（30 分钟）
  - 每轮限流 3 个任务
  - 实测 2-3 秒完成，wrapper 300s 足够

## 根因链（供未来参考）
1. agentTurn 任务需要多次模型调用+工具调用+飞书推送，常超过 5 分钟
2. OpenClaw 默认 300s timeout 强制 kill
3. cron-retry-monitor（15 分钟兜底）自己也是 agentTurn
4. 兜底机制自己挂 → 失败任务没人救
5. 被 kill 的任务保留在下次调度继续跑（不丢数据），所以表面看不严重
6. 旧模型名错误是 5-29 ~ 6-01 的事件，已自愈

## 设计原则提炼
- **救命稻草必须独立于被救系统的失败模式** → retry-monitor 改为纯 shell
- **agentTurn 任务 timeout 安全阈值 = 模型调用 × 工具调用 × 推送时间，建议 ≥600s**
- **OpenClaw cron 的 timeoutSeconds 不支持局部 patch，必须传完整 payload**

## 后续建议（待 Lee 决定）
- 观察 24-48h，看 timeout 错误是否彻底消除
- 若 24h 后仍有 timeout 错误，考虑把常用脚本也改为 systemEvent（直接调 shell）
- shell 脚本是真正的兜底层，应该成为更多 cron 的标准模式
