# 🦞 进化周报 — 2026 W21（05/11 - 05/17）

---

## 📊 本周大事记 & 处理事项

### 🔧 系统建设（4项）
1. ~~**三 Agent 通信方案落地**（5/12）：HTTP webhook 8080 端口 + systemd 服务，小马→小龙虾互联~~ → **已弃用（2026-05-18），由 Lee 居中协调**
2. **Memory Dreaming 循环稳定运行**：03:00 自动分析短期 recall，推广判定机制成熟
3. **轨迹挖掘 v3**（5/17）：27 天日志深度挖掘 → 47 条去重 → 38 条高价值教训/模式
4. **PARA-Inbox 整理**（5/17）：扫描近 7 天，2 篇新文章加入待分类

### 🔐 安全事件（3项）
1. **Git force push 误删事故**（5/13）：四次 force push 覆盖仓库 → 教训固化到 MEMORY.md
2. **Git SSH rewrite 导致 push 卡死**（5/15）：global config HTTPS rewrite 规则，SSH 测试正常 ≠ git 能用 SSH
3. **DeepSeek v4 Flash 权限红线**（5/14）：cron 内可使用，cron 外需 Lee 授权，违规则是红线

### 🧠 重要决策 & 规则更新
- **任务执行流程统一红线**（5/15）：Lee 确认所有交流（任务/沟通/闲聊）统一执行「理解→分解→步骤→可行性→建议→Lee确认→执行→汇报→修正」，禁止跳过确认
- **三 Agent 仓库分配确认**：小龙虾→xiaolongxia-openclaw，小马→xiaoma-hermes，完全独立
- **本地文件唯一真相源**：GitHub 仅备份，绝不移动或删除本地文件
- **模型使用规范固化**：MiniMax-M2.7 主力，DeepSeek v4 Flash 仅 cron

### 🗑️ 清理 & 精简
- Cron 清理：神州租车退款提醒、下班补卡提醒、小古文提醒（已完成的任务删 cron）
- MemOS Cloud 完全卸载：插件移除 + 记忆系统精简为纯本地文件
- MEMORY.md 清理：删除过时 xiaolongxia/ 路径引用，合并重复提炼条目

---

## 📈 记忆系统运作情况

### 三层记忆
| 层 | 本周状态 |
|------|---------|
| 短期（SESSION-STATE.md） | 正常，无活跃任务 |
| 中期（memory/YYYY-MM-DD.md） | 7 天日记完整（05-11 ~ 05-17） |
| 长期（MEMORY.md） | v2.8 → **v2.9**（本周新增多条条目） |

本周提炼到 MEMORY.md 的内容：
- 任务执行流程统一红线
- Git SSH rewrite 教训
- 三 Agent 仓库分配
- 模型使用安全规则
- 轨迹挖掘 v3 成果

### Obsidian 备份
- `~/Obsidian/PARA/resources/memory-backup/` 本周更新 **6 个文件**（05-11 ~ 05-16）
- 备份覆盖连续，但 05-14 当日同步延迟

### Ontology 图谱
- 对话→Ontology 管道：04:03/12:03/18:03 定时运行
- 状态：正常
- 问题：本周多次检出 entities.json 为空（graph.jsonl 0 行），管道输出格式有待排查

### Skills-Store
- 当前安装技能数：**4**（find-skills, skillhub-preference, weread, workflow）
- 本周新增：lee-content-auto-collect（5/14）
- 状态稳定，无冗余技能

### 自动化 Cron 运行情况

| 任务 | 本周运行 | 状态 |
|------|---------|------|
| 每日记忆提炼（03:00） | 7 次 | ✅ 正常（MiniMax 模型） |
| Obsidian 备份（02:00） | 7 次 | ✅ 正常（含一次网络重试） |
| 对话→Ontology 管道 | 21 次 | ✅ 正常 |
| 轨迹挖掘（周日19:00） | 1 次 | ✅ v3 成功 |
| PARA-Inbox 整理（周日19:30） | 1 次 | ✅ 正常（2篇） |
| workspace 备份维护 | 7 次 | ✅ 正常 |
| Memory Dreaming（03:00） | 2 次 | ✅ 正常 |

---

## ⚠️ 待改进点

### 🔴 高优先级
1. **Ontology entities.json 为空**：graph.jsonl 有 0 行，管道的 Persistence 层需排查
2. **GitHub 推送不稳定**：腾讯云→GitHub 持续网络超时/500 错误，需关注

### 🟡 中优先级
1. **Obsidian 备份脚本缺失**：`sync_memory_to_obsidian.py` 未找到，当前依赖 GitHub 同步
2. **memory_auto_refine.py 不存在**：部分记忆提炼脚本在 5/14 时已被移除（已用 Memory Dreaming 替代）
3. **Conversation_ontology_state 卡在 05-13**：processed_sessions 最后时间戳为 05-13 08:06，5 天未更新

### 🟢 低优先级
1. MEMORY.md 中部分过时引用待清理（xiaoma/、xiaolongxia/、MemOS/Memos 相关文件历史）
2. 磁盘清理后 8.3GB 已释放，但需持续监控

---

## 🎯 下周计划

1. **排查 Ontology 管道 persistence 问题** — 修复 entities.json 为空
2. **修复 conversation_ontology_state 卡住** — 确保 processed_sessions 持续更新
3. **持续推进 Notion / 印象笔记导入** — 等待 Lee 评估数据量级
4. **强化 GitHub 推送可靠性** — 考虑fallback策略（小马中转或多远程仓库）
5. ~~**三Agent协作深入** — 与小马演练 webhook 互联场景~~ → **已停用（2026-05-18）**

---

_版本：1.0 | 生成：2026-05-17 20:00 | by 小龙虾 🦞_
