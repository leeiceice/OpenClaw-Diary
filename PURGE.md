# PURGE.md — 清理触发器 🦞

> 当专题文件（COLLAB / ROUTING / CRON / ARCHITECT / MEMORY_POLICY）累计变更满 50 条时触发清理。

---

## 触发条件

- 每次自洁脚本运行时检查专题文件行数变更
- 任何专题文件对比基线变动 > 50 行 → 触发清理信号
- 月度 purge cron（每月 1 日 03:00）强制触发

## 清理规则

| 类型 | 处理方式 |
|---|---|
| low-confidence 条目（confidence < 0.30）| 自动移除 |
| LINE-OVERFLOW（超限 + 持续 30 天）| 自动修剪至上限 |
| DRIFT（外部修改 + 持续 7 天）| 推安全群预警，不自动写 |
| 重复 / 合并 | 手动确认后统一合并（走 skill_workshop）|

## 变更计数

记录于 `self-improving/purge-candidates.md`，每次脚本运行自动更新。

---

_版本：1.0 | 建立：2026-06-11 | by 小龙虾_
