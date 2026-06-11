# Memory 自动自洁规范

> 来源：2026-06-11 下午 Lee 拍板「自洁脚本 + confidence 衰减 + drift guard」
> 模仿小马 MEMORY 管理方法 3（时效自洁）

---

## 三大自洁维度

### 1. Confidence 衰减（小马法）
- 每 24h 扫描一次 `corrections.md` + `deviations/` 中的条目
- 自洽规则：条目记录时间 > 90 天 → confidence 基准 -0.15
- 自洽规则：> 180 天 → confidence 基准 -0.30
- 衰减后 confidence < 0.30 → 标记为 `[AUTO-PURGE: low-confidence]`，30 天后再检查（仍 < 0.30 → 自动移除）

### 2. Drift Guard（外部修改检测）
- FILE MTIME 存储：`self-improving/drift-guard-state.json`（记录各关键文件的 mtime + hash）
- 每次自洁运行时：对比文件当前 mtime/hash 与存储值
- 不一致 → 标记为 `[DRIFT: external-edit]` → 自洁脚本不写该文件（避免覆盖外部修改）
- 不一致持续 > 7 天 → 推安全群预警

### 3. 单条上限控制
- 专题文件（COLLAB / ROUTING / CRON / ARCHITECT / MEMORY_POLICY）：单条规则 ≤ 500 字符
- MEMORY.md：单条索引 ≤ 150 字符（Lee 拍板）
- SOUL.md / AGENTS.md：单条规则 ≤ 800 字符
- 超限 → 写入 `self-improving/purge-candidates.md`（带超限字符数 + 建议拆法）
- 超限持续 > 7 天不处理 → 推进化群提醒

---

## 自洁触发点

| 触发点 | 频率 | 动作 |
|--------|------|------|
| HEARTBEAT 自检路径 | 每小时 | 轻量检查（文件是否超过月初基线 + no drift） |
| 月度 purge cron | 每月 1 日 03:00 | 全维度检查 + 自动清理 low-confidence + 推报告到安全群 |
| 手动触发 | 按需 | `python3 scripts/memory_purge_check.py --report` |

---

## 月度 purge cron 参数

- 执行时间：每月 1 日 03:00 CST
- 模型：minimax/MiniMax-M3（light-context）
- timeout：600s
- 推送目标：安全群（oc_1f77586fc34cdacac8f43a4e9733eafc）
- failureAlert：3 次失败推进化群

---

_版本：1.0 | 建立：2026-06-11 | by 小龙虾_
