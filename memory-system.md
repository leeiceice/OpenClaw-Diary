# 记忆系统使用经验

## 三层架构
- 短期：SESSION-STATE.md（当前会话决策/状态/WAL协议）
- 中期：memory/YYYY-MM-DD.md（每日复盘）
- 长期：MEMORY.md（核心知识/偏好/规则）

---

## 记忆搜索架构 v2（2026-05-15 更新·重要）

> MemOS 已卸载，本地向量库已删除。旧版 `memory_search` 工具依赖 MemOS Local DB，已失效。
> 新版基于 BM25 + 意图路由实现，不依赖外部向量服务。

### 架构概览

```
Lee 查询
     ↓
┌─────────────────────────────────────┐
│ L1 意图分类（Intent Router）         │ 规则匹配，纯 stdlib
│ "Lee偏好" → preference             │
│ "怎么做的" → pattern                │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ L2 文件路由（File Router）           │ 按意图定向文件子集
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ L3 BM25 搜索（rank-bm25）            │ pip install 可用
│ + 查询扩展（LLM API）                │
└──────────────┬──────────────────────┘
               ↓
         Top-K JSON 结果
```

### 搜索实现

**脚本**：`/root/.openclaw/workspace/scripts/memory_search.py`

**依赖**：
```bash
pip install rank-bm25 --break-system-packages
```

**CLI 用法**：
```bash
python3 scripts/memory_search.py "Lee的偏好" --top-k 5
python3 scripts/memory_search.py "喝水怎么做" --no-expand  # 禁用 LLM 扩展
```

**JSON 输出字段**：
- `path` — 来源文件路径
- `snippet` — 文本片段（前 200 字符）
- `score` — BM25 综合评分
- `textScore` — 同 score，用于排序
- `citation` — 格式化引用
- `rank` — 结果排名
- `expanded_terms` — LLM 扩展的查询词

### 意图分类规则

| 意图 | 触发词 | 搜索范围 |
|------|--------|----------|
| preference | 偏好、喜欢、Lee喜欢 | MEMORY.md, USER.md |
| correction | 不要、避免、错误、纠正 | corrections.md, validated.md |
| pattern | 怎么做的、之前、模式 | self-improving/domains/ |
| status | 现在、还正常吗、最近 | memory/最近7天/ |
| factual | 谁、什么时候、多少 | memory/全量/ |

### 搜索范围

扫描以下文件构建索引：
- MEMORY.md、USER.md、SOUL.md
- self-improving/memory.md、corrections.md、domains/*.md
- memory/YYYY-MM-DD.md（最近 30 天）

### 查询扩展

启用时：调用 LLM API 扩展同义词
- 原文 "喝水" → 扩展为 `["喝水", "饮水量", "water intake", "每日喝水"]`
- 多轮搜索合并去重，结果更全面

禁用时（`--no-expand`）：只用原始查询词，适合快速精确匹配

---

## 记忆类型分类（Claude Code 四型 Taxonomy）

**收到信息立即判断类型，对号入座：**

| 类型 | 内容 | 存储位置 |
|------|------|----------|
| **user** | 用户角色/偏好/知识背景 | MEMORY.md 或 memory/当日.md |
| **feedback** | 纠正（avoid）+ 确认（keep doing）| self-improving/corrections.md 或 validated.md |
| **project** | 进行中工作/目标/截止/决策 | self-improving/projects/<项目>.md |
| **reference** | 外部系统指针（飞书/Notion/其他工具） | MEMORY.md reference 节 |

**feedback 双面性（重要）：**
> "Record from failure AND success: if you only save corrections, you will avoid past mistakes but drift away from validated approaches"

**纠正** → `self-improving/corrections.md`
**确认（做对了）** → `self-improving/validated.md`

---

## 写入时机

| 事件 | 写入位置 |
|------|----------|
| Lee 纠正/纠错 | self-improving/corrections.md（必须含 Why + How to apply） |
| 可复用偏好/模式/原则（确认过有效的） | self-improving/validated.md（必须含 Why + How to apply） |
| 可复用偏好/模式/原则（初步形成） | self-improving/memory.md |
| 领域经验（Skill/Cron/记忆） | self-improving/domains/<领域>.md |
| 项目执行记录 | self-improving/projects/<项目>.md |
| 每日重要事件/决策 | memory/YYYY-MM-DD.md |
| 核心知识/偏好/规则变更 | MEMORY.md |

---

## 召回时验证步骤

> "A memory naming a specific function/file/flag is a claim about when it was written.
> It may have been renamed, removed, or never merged."

**召回后必做：**
1. 读记忆内容
2. 如果记忆提到了具体文件/函数/路径 → `grep` 或 `ls` 验证是否仍存在
3. 验证通过才应用，否则标注「可能已过时，需重新确认」

---

## MemOS 即时同步规范（已废弃，仅作参考）

> ⚠️ MemOS 已卸载，此规范仅作历史参考。BM25 搜索不依赖任何外部服务。

---

## Main Session 实时写入规范

**问题**：main session 的决策没有实时写入 memory/YYYY-MM-DD.md，导致每日提炼脚本读不到重要内容。

**规则**：
- Main session 进行中时，每完成一个重要决策，**立即写入** `memory/YYYY-MM-DD.md`
- 写入内容：决策结论 + 时间戳（不写过程）
- 格式：`### [时间] 决策标题\n- 具体结论`
- 不要等到 session 结束再批量写

**触发条件**：
- Lee 说「确认」「就这样」「没问题」等确认语
- 执行了系统配置/技能安装/流程变更
- Lee 明确要求设置新 cron/删除 cron/修改规范

---

## self-improving 更新规则

- 每次纠正后顺手写入 corrections.md（必须含 Why + How to apply）
- 每次确认后写入 validated.md（必须含 Why + How to apply）
- 每次踩坑后写入 domains/<领域>.md
- 每周末（周日 20:00 进化周报前）汇总 self-improving 进展报告 → 发进化群

---

_版本：1.0 | 最后更新：2026-05-15 11:47 | by 小马 + 小龙虾_