# 进化周报 | W22（2026-05-25 → 2026-05-31）

> 生成时间：2026-05-31 20:42（CST）by 小龙虾
> 覆盖范围：memory/2026-05-25~30 + diary/raw/微信 + cron-log + Git history

---

## 📊 本周成就 / 处理事项

### 系统层面
| 事项 | 结果 |
|------|------|
| 飞书日常安排群消息路由修复 | ✅ 根因定位 + 修复，per-group 配置要慎用 |
| 日报生成脚本 L0/向量库检查修复 | ✅ L0缺口从7天→1天，向量库16条正常 |
| Skills 仓库阅读（ECC / Taste-Skill / Understand-Anything）| ✅ ECC/Taste-Skill 不装，Understand-Anything 备选 |
| HEARTBEAT.md v3.0 升级（ECC verification-loop 健康评分闭环）| ✅ 已完成 |
| skills/continuous-learning/ 新增（ECC continuous-learning-v2）| ✅ 置信度评分 + 四状态体系已建立 |
| Git 写前pull + 冲突处理机制 | ✅ 小龙虾+小马同步落地 |
| 脚本路径 /root/.openclaw → ~/.openclaw 迁移 | ✅ 完成 |
| 腾讯云→xiaolongxia-openclaw 迁移 | ✅ 完成 |
| OpenClaw 2026.5.27 升级 | ✅ 完成（e116023）|
| 飞书路由 delivery 失败告警排查 | ⚠️ delivery 仍显示 "Unsupported channel: feishu" |

### 协作层面
- 多 Agent 协作调试：日记写入兼容性问题多次测试
- 小马主协作，小龙虾做提醒的分工持续磨合
- 三 Agent（Lee主导 / 小马协作 / 小龙虾助理）角色分工明确

### 业务层面
- 云商平台：首次完成商品上架
- 苹果手表钢带提醒触发（飞书推送）

---

## 🧠 记忆系统运作情况

### 三层记忆
- **L0（memory/YYYY-MM-DD.md）**：本周共 6 天有记录（5/25, 26, 27, 28, 30）
  - **实际写入 4 条新 entry**（05-25时区/多Agent协作，05-26时区冲突修复，05-27飞书路由+L0检查修复+技能升级，05-30每日备份）
  - ⚠️ 5/29 空白，L0 实时写入新流程刚建立，尚在适应
- **L1（提炼）**：本周 L0→MEMORY 提炼较少，仅5/27有大量提炼
- **L2（向量库）**：16条向量，正常

### Obsidian 备份
- 本周更新文件数：**12 个**（diary-05-21~28，MOMEY.md，SESSION-STATE.md）
- 备份 cron 每日 02:00 CST + 15:04 CST 运行，共 14 条 cron-log 记录
- 状态：✅ 正常运行

### Ontology 图谱
- 本周状态：graph.json 未找到（可能路径变更或损坏）
- ⚠️ 待确认 conversation_to_ontology.py 的输出路径

### Skills-store
- 当前候选技能数量：**0 个**
- 说明：skills-store 已清空，本周无新增候选

### 自动化 Cron 运行情况
| Cron | 本周运行 |
|------|---------|
| 每日记忆提炼（cron:workspace每日备份维护）| ✅ 每日 02:00 + 15:04 CST，共 14 次，成功 |
| 进化日报 | ✅ 5/27 触发，内容正常 |
| 每周进化报告 | ✅ 本次（W22）|

---

## 🔑 本周学到的重要知识

1. **per-group 飞书配置要慎用**：allowlist 与 per-group false 冲突会导致 @ 机器人路由成 DM
2. **L0 实时写入流程**：cron 夜间补跑依赖停用的 memory-tdai，改为实时写入更可靠
3. **时区定义层要同步**：服务器UTC vs 业务CST，如果定义时间的方式不同步，同一时间在不同Agent理解中是不同瞬间
4. **多 Agent 协作难度是指数级**：不是 1+1 的叠加，需要从底层一致性开始反复调试
5. **身体信号优先级高于系统调试**：饿了/累了比任何系统问题优先级都高

---

## ⚠️ 待改进点

1. **L0 写入连续性**：5/29 完全空白，本周应建立稳定习惯
2. **飞书 delivery 告警**：cron delivery 目前仍报 "Unsupported channel: feishu"，需要排查
3. **Ontology 图谱状态不明**：graph.json 找不到，需要确认同步脚本是否正常
4. **喝水追踪中断**：本周 water-log 无数据（可能 cron 喝水提醒未触发）
5. **日记 raw 完整性**：5/29 微信 raw 也缺失

---

## 📅 下周计划

- [ ] 修复 Ontology graph.json 路径问题，确认同步正常
- [ ] 飞书 delivery 告警问题排查
- [ ] 5/29 L0 补写
- [ ] 喝水追踪 cron 重启/确认
- [ ] 持续稳定 L0 实时写入习惯

---

_🦞 W22 进化周报 | 小龙虾 | 2026-05-31_