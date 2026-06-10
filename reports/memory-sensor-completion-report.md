# 小马工程控制论记忆系统 — 落地完成报告

**日期**: 2026-05-21
**版本**: 1.0
**执行者**: 小龙虾 <span class="emoji">🦞</span>

---

## 一、已完成任务概览

| 任务 | 状态 | 说明 |
|------|------|------|
| corrections.md 结构化 | <span class="emoji">✅</span> 已完成 | 8 条偏差记录，已从小龙虾经验迁移 |
| memory_sensor.py CLI | <span class="emoji">✅</span> 已完成 | 支持 write / scan / convergence / list / stats |
| L2 场景块目录 | <span class="emoji">✅</span> 已完成 | memory/deviations/scenes/ 已建立 |
| 样例场景块 | <span class="emoji">✅</span> 已完成 | 2 个：GitHub操作安全规范 / 收藏流程红线 |
| 每周日 cron 扫描 | <span class="emoji">✅</span> 已完成 | 已创建，ID: d0518b66 |

---

## 二、当前偏差统计

```
总计: 8 条
L0a (立即修正): 7 条
L0b (会话末修正): 1 条
已收敛: 0
收敛中: 0
待验证: 8
```

### 偏差明细

| ID | 主题 | 严重程度 | 触发次数 | 状态 |
|----|------|---------|---------|------|
| dev_20260503_001 | 假期「下周一/二」语义歧义 | L0a | 1 | 待验证 |
| dev_20260503_002 | 数据记录按上传时间倒序 | L0a | 1 | 待验证 |
| dev_20260503_003 | Cron token 爆炸监控 | L0a | 1 | 待验证 |
| dev_20260508_001 | 喝水记录数量歧义 | L0b | 1 | 待验证 |
| dev_20260513_001 | GitHub force push 误删 | L0a | 1 | 待验证 |
| dev_20260513_002 | 一次性任务完成后未删除 cron | L0a | 1 | 待验证 |
| dev_20260515_001 | Git SSH rewrite 导致 push 卡死 | L0a | 1 | 待验证 |
| dev_20260518_001 | 书籍推荐必须走完整流程 | L0a | 1 | 待验证 |

---

## 三、memory_sensor.py CLI 用法

### 3.1 写入新偏差

自动检测同类主题，trigger_count +1，N≥2 触发 L2 生成：

```bash
python3 scripts/memory_sensor.py write \
  --subject "Lee学习时间偏好" \
  --wrong "以为Lee喜欢14点学习" \
  --right "Lee不喜欢14点，觉得太干，偏好16点" \
  --severity "L0b"
```

### 3.2 扫描 → 生成 L2 场景块

```bash
python3 scripts/memory_sensor.py scan
```

### 3.3 其他命令

```bash
# 收敛检测
python3 scripts/memory_sensor.py convergence

# 列表
python3 scripts/memory_sensor.py list

# 统计
python3 scripts/memory_sensor.py stats
```

---

## 四、文件结构

```
~/.openclaw/workspace/
├── self-improving/
│   └── corrections.md          ← 偏差记录（结构化格式）
├── memory/deviations/scenes/   ← L2 场景块目录
│   ├── github-操作安全规范.md
│   └── 收藏流程红线.md
└── scripts/
    └── memory_sensor.py        ← 偏差传感器 CLI
```

---

## 五、严重程度分级

| 等级 | 含义 | 处理时机 |
|------|------|---------|
| L0a | 立刻修正 | 明显事实错误（工具名、API参数等） |
| L0b | 会话末修正 | 偏好类（沟通风格、语气） |
| L1 | 积分验证 | 框架性问题，放入 L1 积分队列 |
| L2 | 长期聚合 | 跨次验证的聚合认知 |

---

## 六、收敛判断

- trigger_count ≥ 3 → **已收敛**
- trigger_count = 2 → **收敛中**
- trigger_count = 1 → **待验证**

---

## 七、Cron 任务

| 名称 | 调度 | 功能 | 状态 |
|------|------|------|------|
| 偏差传感器周扫描 | 每周日 10:00 | scan → N≥2 触发 L2 生成 | 已创建 |

---

## 八、核心哲学

> **记忆不是存储，记忆是控制系统。**
>
> 存储解决「记住什么」，控制系统解决「记住后如何验证、偏差如何消除、系统如何趋向稳定」。

---

## 九、后续计划

**可选阶段：向量库 schema 扩展**

- 增加 `hit_count`（被引用次数）
- 增加 `confidence_score`（动态可信度，0.0~1.0）
- 实现 RRF × confidence_score 自适应权重

需调研现有向量库接口兼容性后决定。

---

_版本：1.0 | 生成日期：2026-05-21 | by 小龙虾 <span class="emoji">🦞</span>_