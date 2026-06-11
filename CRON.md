# CRON.md — 定时任务规范与健康度 🦞

> 所有 cron 相关规则统一存储，新增 / 修改 cron 前优先查阅。

---

## 新建 Cron 规范

- 新建 cron：必须 `channel:feishu` + `to:oc_xxx`，禁止 `channel:last`
- 并发冲突：新 cron 与已有 cron 错开 ≥30 分钟
- timeout：进化日报 120s，每日简报 400s（长任务需按健康度规范设 ≥600s）
- 任务完成后**立即删除** cron 提醒，避免重复发送
- **高频 cron（≤15min）必须 `lightContext: true`**（2026-06-10 立）
  - 默认 bootstrap 加载 = ~200K 字符 = ~71K tokens
  - 1min cron 跑一小时 = 4.3M tokens，超过 5h 周期额度 4.16M 的 100%
  - 修复后 jsonl 200KB → 4KB（省 50 倍）
  - 纯 shell 任务可考虑 systemEvent（更轻量），但 light-context 已够用

## Cron 健康度规范（2026-06-03 立）

### 根因
- OpenClaw cron agentTurn 默认 timeout=300s，但实际很多任务需 5-10 分钟
- 全量 4481 次运行中 401 次 timeout（占失败 48%），其中 cron-retry-monitor 自己 152 次
- 救命稻草也是病人 → 兜底机制失灵

### 强制规范
- **agentTurn 任务 timeoutSeconds ≥ 600s**（任何含 1 次以上工具调用的任务）
- **救命稻草类 cron 必须用 systemEvent 或纯 shell**（不依赖模型调用）
- **OpenClaw cron update patch 不支持局部字段** → 必须传完整 payload（kind/message/model/timeoutSeconds）

### 验证
- 实际耗时参考：6e9478c2 晨间简报 12s、52f5f99e heartbeat 22s、81f34340 备份 389s（最长的 6.5min）
- timeout 600s 后这些任务都不会被杀

## 模型安全规则（Cron 模型分流）

- DeepSeek v4 Flash：**仅限** cron 定时任务使用，禁止主动调用
- 主会话主力：MiniMax-M3（M2.7 → fb1）
- cron 任务：`minimax/MiniMax-M3`（2026-06-07 反转，原 V4-Flash 降 fb3）
- cron 以外需要 DeepSeek：必须立即通知 Lee 或获得授权
- **DeepSeek 填充安全**：无内容写「（当日未记录）」，不编造

## MiniMax Token Plan 参数

- 起计日：2026-06-05
- Plus ¥49/月 = 600M tokens/月
- **5h 周期 = 4.16M tokens**
- 周期重置：00:00 / 05:00 / 10:00 / 15:00 / 20:00
- 实际查询：`bash scripts/minimax_token_check.sh`

---

_版本：1.0 | 建立：2026-06-11 | by 小龙虾_
