# 🦞 W23 进化周报

> 时间范围：2026-06-01（周一）~ 2026-06-07（周日）
> 生成时间：2026-06-07 19:15

---

## 📊 本周成就 / 处理事项

### 重大操作
| # | 事项 | 日期 | 影响 |
|---|------|------|------|
| 1 | **模型全量整理**：4 改 4，最终 4 个已注册（M3/M2.7/V4-Flash/V4-Pro） | 6/03 | 模型架构定型 |
| 2 | **4 模型对比测试 + 双盲测试**：M3 98.3% vs V4-Flash 95.0% | 6/03 | 主模型切换决策依据 |
| 3 | **Cron 模型全切 DeepSeek Flash**：11 个 cron 统一 model | 6/01 | model reject 错误清零 |
| 4 | **小马（Hermes）卸载**：阿里云 Agent 完全卸载 | 6/01 | 三 Agent 调整为仅小龙虾 |
| 5 | **Cron 健康修复 3 条**：月度健康检查 / Skill 安全审查 / 每日新闻简报 | 6/05 | 推送全部恢复正常 |
| 6 | **Kimi For Coding 配置失败** → 删除全量配置 | 6/03 | 确认 Kimi For Coding 不可接入 Agent |
| 7 | **L0 Watchdog 机制落地**：`scripts/l0_watchdog.sh` + HEARTBEAT 链路 | 6/07 | 系统级实时守护 |
| 8 | **时区铁律全量清理**：6 处 datetime.now() 全部替换为 _timezone 引用 | 6/07 | `scripts/datetime_naive_scanner.sh` 守护 |
| 9 | **安全群 chat_id 错版修复**：MEMORY.md 少 1 个 a → 错版 2 周 → 已修复验证 | 6/07 | 6/6 chat_id 全链路验证成功 |
| 10 | **Cron 稳定性自查**：38 个 cron（36 enabled），真实失败率 ~17%（偶发，无长期失败） | 6/03 | 系统根因已收敛 |

### 修复/优化统计
- **Cron 修复**：3 条 systemEvent/Cron 推送修复 + 4 条 model/timeout 修正
- **记忆提炼**：6 天日记（6/01~6/07，缺 06-06）+ 8 条系统级教训写入 MEMORY.md
- **Cron 超时**：cron-retry-monitor 300s → 600s，obsidian-GitHub 180s → 300s

---

## 🧠 记忆系统运作情况

### 三层记忆

| 层 | 本周数据 | 状态 |
|---|---------|------|
| **L0 日记** | 6 篇（6/01~6/07，缺 06-06）/ 共 472 行 | ✅ 高密度（6/03 达 194 行） |
| **MEMORY.md** | 提炼 8 条系统级教训 → MEMORY.md v3.4→v3.5 | ✅ 凝练后版本行直读 |
| **corrections 偏差** | 本周新增 8 条偏差（dev_20260607_001~005 + 3 条历史） | ✅ 环比上周从 14→22 条 |

### MEMORY.md 进化
- **版本**：v3.4 → v3.5（新增「06/01~06/07 新教训」章节）
- **新增内容**：记忆系统红线 / 模型管理 / Cron/Chat 通信 / 时区铁律 / 偏差自检机制
- **清除**：合并精简了原来的 6/04、6/05 零散每日提炼

### Obsidian 备份
| 项目 | 数据 |
|------|------|
| `memory-backup` 本周更新文件 | **0 个**（目录结构异常：`~/Obsidian/PARA/resources/memory-backup/` 不存在，实际在 `~/Obsidian/wiki/_archive/2026-05-para-backup/resources/memory-backup/`） |
| 路线 | ❌ 需确认：memory-backup 的 Obsidian 路径配置是否正确 |

### Ontology 图谱
| 指标 | 本周 | 备注 |
|------|------|------|
| `graph.jsonl` 实体数 | **文件不存在**（`/root/.openclaw/workspace/data/ontology/graph.jsonl` 已删除或未生成） | ⚠️ 需要检查 Ontology 管道 |
| 新增实体/关系 | 无法统计 | |
| 当前状态 | ❌ Ontology 数据丢失或管道故障 | 需修复 |

### Skills Store
| 指标 | 数据 |
|------|------|
| 当前技能目录数量 | **10 个技能目录**（含连续学习/find-skills/skillhub-preference/weread/workflow 等） |
| 本周清理 | 0 个（无清理操作） |
| 上周参考 | 109 总 / 67 可用 / 42 缺依赖（5/10 数据） |

### 自动化 Cron 本周运行
| Cron 名称 | 本周状态 | 备注 |
|-----------|---------|------|
| 每日记忆提炼 `f92708f2` / `823a779c` | ✅ 本周正常（6/4、6/5 跑通，无内容可提炼时静默） |
| Obsidian 备份 | ⚠️ memory-backup 路径有问题 | 需确认配置 |
| Ontology 同步 | ❌ graph.jsonl 不存在 | 管道可能停止或数据被清 |
| cron-retry-monitor | ✅ 已修复 timeout 300s→600s | |
| 进化日报 | ✅ 正常 | |
| weekly-skill-security-review | ✅ 修复后正常（6/5） | |

---

## ⚠️ 待改进点

### 🔴 紧急（本周发现需立即处理）

1. **Ontology 管道恢复**：`/root/.openclaw/workspace/data/ontology/graph.jsonl` 不存在，需检查对话-Ontology 管道是否正常
2. **Obsidian memory-backup 路径确认**：当前目录 `~/Obsidian/PARA/resources/memory-backup/` 为空，实际备份在 archive 下
3. **推送类 cron 全链路验证**：晨报/日报/学习提醒等推送类 cron 上线前应跑一次端到端测试

### 🟡 中等（本周未完成）

4. **Kimi For Coding** 的「编程 CLI 专用」限制记录到 MEMORY（已记录 ✅）
5. **Cron model 改用 `cron update`** 写入机制文档化
6. **评估脚本归档**：`run_benchmark.py` 等放进 `scripts/`
7. **4 模型标准题库沉淀**：避免下次重新设计题
8. **ClawX 桌面端评估**（Lee 问的，还未回复）
9. **AGENTS.md 任务收尾检查** 已落地，待验证执行效果

### 🔴 自我复盘：本周 3 次错误判断模式

| # | 偏差 | Lee 纠正 | 根因 |
|---|------|---------|------|
| 1 | 错把"模型名拼错"当根因 → 实际上 prompt 缺陷 | ✅ | 没有先验证问题描述 |
| 2 | 错把 Token Plan 限流当记忆系统故障 | ✅ | 批量失败 = 全系统崩的思维惯性 |
| 3 | 错把 raw 归档和每日记忆混为一谈 | ✅ | 概念边界不清 |

> **反信息茧房自检**：3 次都靠 Lee 反驳纠正，**没有一次自纠**。这是系统性模式，建议日常训练"先自问再回答"意识。

### ⭐ 本周最严重问题：沉默失败

- **安全群 chat_id 错版 2 周**（5/21→6/07）
- MEMORY.md 写 `oc_1f77586fc34cdac8f43a4e9733eafc`（33 字符，少 1 个 a）
- 飞书 API 真值 `oc_1f77586fc34cdacac8f43a4e9733eafc`（35 字符）
- **5/21、5/29、6/2 三次提到"安全群无效"但没人做端到端测试**
- **修复**：6/7 端到端验证通过，6/6 chat_id 全链路验证通行
- **教训**：沉默失败的根因不是 chat_id 错版本身，是**没有定期端到端验证的习惯**

---

## 📋 下周计划

### 必须处理
- [ ] **Ontology 管道修复**：恢复 `graph.jsonl` 数据链路
- [ ] **Obsidian memory-backup 路径确认 & 修复**
- [ ] **推送类 cron 全链路回归测试**（晨报/日报/学习提醒等）

### 建议推进
- [ ] 评估脚本（run_benchmark.py 等）归档到 `scripts/`
- [ ] 4 模型标准题库沉淀到 `data/benchmark-题库/`
- [ ] 「systemEvent + shell 脚本」陷阱写进 `self-improving/cron-management.md`
- [ ] ClawX 桌面端评估回复 Lee
- [ ] 验证 L0 Watchdog 运行 1 周后的效果
- [ ] 评估并修复 Ontology 管道（对话-Ontology 管线）
- [ ] 跟进 Cron 更新工具（cron update 替代直接 edit jobs.json）

### 持续行动
- [ ] 每日 L0 实时写入（L0 Watchdog 监控运行 1 周）
- [ ] Memory 系统三层健康每日确认
- [ ] 持续收藏 + 关联分析 + Wiki 编译

---

## 📈 本周数据快照

```
⏱ 时间范围：2026-06-01 ~ 2026-06-07（W23）
🧠 记忆日记：6 天有内容（缺 06-06）共 472 行
📄 MEMORY.md：414 行，v3.4 → v3.5
📦 Skills：10 个技能目录（上周 109 总/67 可用）
💾 Obsidian备份：本周 0 更新（路径需修复）
🔗 Ontology：graph.jsonl 不存在（需修复）
⚙️ Cron：38 个任务（36 enabled），真实失败率~17%（偶发）✅
📝 Corrections：22 条偏差记录（本周+8）
📊 4 模型：M3(98.3%) > V4-Flash(95.0%) > M2.7 > V4-Pro
🔔 推送端到端：6/6 群全部验证通过 ✅
```

---

_🦞 小龙虾 W23 进化周报 | 2026-06-07 | 推送至进化群_
