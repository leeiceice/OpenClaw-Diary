# OpenClaw-Diary 五层结构

> 来源：2026-06-05 21:46 Lee 立 / 小龙虾设计
> 与 Lee 个人日记 (~/Obsidian/日记/) **完全隔离**。本系统**只记录小龙虾的迭代成长**。

## 层级定义

| 层 | 命名 | 周期 | 答的问题 | 路径 | cron |
|----|------|------|---------|------|------|
| L0 | 日记原文 | 每天 | 今天发生了什么 | `entries/YYYY-MM-DD.md` | `0eaef122` OpenClaw-Daily (21:10) |
| L1 | 每周分析 | 每周 | 模式识别 | `weekly-analysis/2026-Wnn.md` | `a2bcd085` L1-weekly-analysis (周日 22:00) |
| L2 | 每月趋势 | 每月 | 演变方向 | `monthly-trend/YYYY-MM.md` | 待建 (月底 23:00) |
| L3 | 综合分析 | 季度 | 深度挖掘 | `comprehensive/YYYY-Qn.md` | 待建 (季度末) |
| L4 | 概念实体 | 持续 | 主题积累 | `concepts/{主题}.md` | 内嵌 (L1-L3 调用) |

## 隔离原则（铁律）

- **只读**小龙虾自己的记忆：`MEMORY.md` + `memory/YYYY-MM-DD.md` + `proactivity/daily-working-log.md` + L0 entries
- **绝对不读** Lee 个人日记 `~/Obsidian/日记/`
- AI 日志内容**不暴露 Lee 私人信息**（如具体事件、情绪、私事场景）
- 任何推送目标**不含 Lee DM**（除非 L1-reminder-cron 等显式 reminder 任务）

## 触发与推送

- L0 触发：每天 21:10，跑完 DM Lee (ou_e7a18...)
- L1 触发：周日 22:00，跑完 DM Lee (简短摘要) + 推进化群 (详细)
- L1 提醒：周六 18:00 DM Lee 让他补 L0 (`4fbbf209` L1-reminder-cron)
- L2/L3：待建，节奏由 Lee 拍板

## 数据流

```
  每天 L0 ->  weekly L1 -> monthly L2 -> quarterly L3
                |
              L4 concepts (跨时间主题累积)
```

## 关联系统

- **不是**：记忆五层 (MEMORY.md v3.4) — 那是给小龙虾**记得** Lee 说过什么
- **是**：Diary 五层 — 让小龙虾**了解自己**、迭代成长
- 两个系统**数据源不同、目标不同**，严格隔离
