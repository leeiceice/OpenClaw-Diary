# MEMORY_POLICY.md — MEMORY.md 维护红线 🦞

> 本文件定义 MEMORY.md 本身的维护规则（清理频率 / 准入标准 / 版本规范），
> 不存业务内容，只存"MEMORY 怎么被维护"的元规则。

---

## 清理频率

- MEMORY.md 精简：**每月一次**，结合当月教训归档一起做
- 教训索引：>3 个月且不再适用的规则移入 `memory/archive.md`
- 里程碑：**永久保留**（时间线是资产）

## 版本行规范

- 格式：`版本：X.X | 最后更新：YYYY-MM-DD HH:MM | by 作者`
- patch（Bug 修正）/ minor（新增章节）/ major（结构重组）

## MEMORY.md 写作红线

1. **不全文照抄 L0** — L0 是中期过程记录，MEMORY.md 是长期索引
2. **每条索引 150 字符** — 只概括主题 + 指向文件路径，不记详情
3. **不记"什么会进 MEMORY"** — 不写"本次会议纪要 / 今日发生 / 临时状态"
4. **不记消息 ID / commit hash** — 查时走 git log / 飞书 API
5. **会复用的规则** vs **一次性事件**：规则进 MEMORY.md，事件进 L0

## MEMORY.md 准入门槛（4 步过滤）

逐项检查，遇否就拦：

1. **会复用规则吗？** — 否 → 不进 MEMORY（只进 L0）
   - 例外：里程碑 anchor（首次落地时间点）→ 留 11 条短行
2. **已升级到 SOUL / AGENTS / 其他专题文件？** — 是 → MEMORY 里只留指针
3. **是技术细节且会复用？**（.env 格式 / weread 查找 / DeepSeek 填充安全）— 是 → 可留
4. **里程碑 / 时间线：** 1 个 milestone = 1 行 anchor（< 30 字符），不写详情

**正例**（该在 MEMORY）：
- L0 实时写入（非 cron 补跑）= 规则
- Token Plan 5h 周期 = 4.16M tokens = 会复用的参数
- git pull --no-rebase origin main = 规则
- "全交班" 发生时在该日加个 anchor = 里程碑

---

_版本：1.0 | 建立：2026-06-11 | by 小龙虾_
