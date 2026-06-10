---
name: continuous-learning
description: |
  持续学习系统 — 从会话中自动提取模式，附带置信度评分，通过 /evolve 将直觉聚类为技能。
  基于 ECC continuous-learning-v2 框架改造，适合小龙虾的 OpenClaw workspace。
---

# 持续学习系统 🦞

## 核心概念

| 术语 | 定义 |
|------|------|
| **直觉 (Intuition)** | 从单次会话中观察到的模式/规律，尚未验证 |
| **经验 (Experience)** | 被验证 ≥3 次的直觉，置信度 > 60% |
| **技能 (Skill)** | 被提取为独立 .md 文件的结构化经验 |
| **置信度 (Confidence)** | 0-100%，基于验证次数和质量计算 |

## 置信度评分算法

```
基础分 = 30%
+ 验证次数加成：每次验证成功 +15%（上限 70%）
+ 来源质量加成：
  - 实测验证（代码/日志）→ +20%
  - 文档/记忆引用 → +10%
  - 推测/假设 → +0%
- 失败惩罚：每次失败 -20%（最低 10%）
```

| 置信度 | 状态 | 行动 |
|--------|------|------|
| < 30% | 猜测 | 不做决策，等待更多验证 |
| 30-59% | 直觉 | 记录但不作为关键依据 |
| 60-84% | 经验 | 可以作为常规决策依据 |
| ≥ 85% | 知识 | 可写入 MEMORY.md 作为长期记忆 |

## 工作流程

### 1. 观察（任何会话中）

发现问题/规律 → 立即记录到 `proactivity/daily-working-log.md`：

```markdown
## 观察 [timestamp]
- 内容：...
- 来源：实测/文档/推测
- 置信度：30%（初始）
- 待验证：...
```

### 2. 验证

下次遇到相同场景时：
- 成功 → 置信度 +15%
- 失败 → 置信度 -20%

更新 `proactivity/daily-working-log.md` 中的置信度。

### 3. 提炼（/evolve）

当置信度 ≥ 60% 时，评估是否需要聚类为技能：

```bash
# 查看当前所有直觉及置信度
cat proactivity/daily-working-log.md | grep "置信度"
```

**聚类条件**：
- 同一主题的直觉 ≥ 3 个
- 总置信度 ≥ 180（平均 60%）

**聚类动作**：
1. 在 `proactivity/` 下创建 `{topic}-intuitions.md`
2. 将相关直觉合并写入
3. 原记录标记为 `→ 已聚类为 skill`

### 4. 技能化（/promote）

当置信度 ≥ 85% 且主题明确时：

1. 在 `skills/` 下创建 `{skill-name}/SKILL.md`
2. 写入：描述、触发条件、使用方法、注意事项
3. 在 `proactivity/` 中标记 `✅ 已技能化`
4. 同步 GitHub

## 命令

| 命令 | 作用 |
|------|------|
| `/intuition new <描述>` | 快速记录新直觉 |
| `/intuition list` | 显示所有直觉及置信度 |
| `/intuition verify <id> <success\|fail>` | 验证直觉，更新置信度 |
| `/evolve` | 检查可聚类的直觉，生成技能建议 |
| `/promote <topic>` | 将高置信度直觉提升为正式技能 |
| `/instinct-status` | 显示直觉统计（含置信度分布） |

## 文件结构

```
proactivity/
├── daily-working-log.md      # 每日观察记录（含置信度）
├── intuitions/               # 按主题归档的直觉集合
│   ├── {topic}-intuitions.md
│   └── ...
├── log.md                    # 行为时间线
└── patterns.md               # 可复用模板

skills/
└── {skill-name}/             # 正式技能（置信度 ≥ 85%）
    ├── SKILL.md
    └── .meta/
        └── confidence.md     # 置信度追踪文件
```

## 与 HEARTBEAT 的关系

- HEARTBEAT 检查时顺便检查直觉状态
- 置信度变化时记录到 `log.md`
- 每 7 天生成直觉健康报告（conf ≥ 85% 比例）

## 版本

_版本：1.0 | 2026-05-27 | 来自 ECC continuous-learning-v2 框架改造_