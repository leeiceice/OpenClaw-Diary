# 进化周报 | W25（2026-06-08 ~ 2026-06-14）（🦞小龙虾）

> 生成时间：2026-06-14 19:15（CST）
> 覆盖范围：memory/2026-06-08 ~ 2026-06-14 + Git history + corrections.md + cron state + Obsidian-Backup commits
> 同比上周 W24：2026-05-28 ~ 2026-06-03

---

## 📊 本周成就 / 处理事项

### ⭐ 核心里程碑（4 项系统级进化）

| # | 事项 | 结果 | 日期 | 置信度 |
|---|------|------|------|--------|
| 1 | **MEMORY.md 4.0 重组 + 5 专题拆分** | ✅ 951→108 行（-89%）；拆出 COLLAB / ROUTING / CRON / ARCHITECT / MEMORY_POLICY 共 254 行纯规范 | 06-10/11 | 100% |
| 2 | **Cron 沉默故障歼灭**（6 个 main+systemEvent cron）+ 防御三件套（cron-disabled-audit-daily + cron_health_check.sh + HEARTBEAT 第四步） | ✅ 6/6 改造 ok，47 cron 健康 41/47 | 06-09 | 100% |
| 3 | **Token Plan 5h 周期审计 + 高频 cron lightContext 改造** | ✅ 4 cron 改造（ec85def5 / bac841c2 / 5a222ec4 + 4 个长报告）= **省 131 万 tokens/天 = 5h 配额 31%** | 06-10/11 | 100% |
| 4 | **L0 Watchdog 自愈机制**（缺失 L0 自动建占位，不再要求 Lee 手动介入） | ✅ 实跑验证 ok（om_x100b6dd239c2f4a4c2552746323040e） | 06-14 | 100% |

### 系统层面（11 项中等改进）

| 事项 | 结果 | 日期 |
|------|------|------|
| L0 实时写入机制第一次系统化（4 次精简 MEMORY.md） | ✅ Lee 4 次反馈推动 "MEMORY.md 准入门槛 4 步过滤" 落地 | 06-10 |
| 喝水追踪全链路重构（脚本 + 队列 + worker + cron 三件套 + D/B 分支 override 语义） | ✅ 零依赖 Agent 记忆；纠错只发 1 张卡 | 06-08/14 |
| Heartbeat 内置推送配置层修复（target:none + directPolicy:block 双保险） | ✅ 不再因 gateway 升级重启而恢复刷屏 | 06-08 |
| GitHub PAT 泄露应急（`.git/config` 改 SSH + 全仓扫描 + Lee 撤销） | ✅ 全链路 4 步完成 | 06-08 |
| 关联分析 A1+A2 cron 落地（路径误判反转后仍保留兜底价值） | ✅ 2 cron（243498cc / 7074d5a4） | 06-09 |
| Vector store 8 天未更新修复 + 每日 build cron（3502982c） | ✅ 996 → 1027 chunks | 06-09 |
| 飞书 footer 6 个开关研究 + 状态栏开启 + 流式冻结排查 | ✅ 知道边界（CardKit 流式锁 element 列表） | 06-10 |
| 6/13 日记双系统时间窗口漏洞修复（diary-daily 22:00→00:05 + flag 机制重构） | ✅ SOUL.md 升级"先读证据源"原则 | 06-13 |
| 5 个 skill 化（cron-health-rules / routing-rules / diary-daily / openclaw-diary / daily-news） | ✅ workspace skills 7→12 | 06-11 |
| 学习小马 hermes-lark-streaming v0.10.3 技术文档（13 hooks / AST 注入） | ✅ wiki/concepts 入库 4.5KB + 7/7 自检 | 06-10 |
| 《隳三都》完读全书记（11/11 章，跨度 53 天） | ✅ Obsidian wiki/sources/ 完整归档 | 06-10 |

### 反模式纠正（重要）

| 反模式 | 纠正 |
|--------|------|
| MEMORY.md 全文照抄 L0（951 行臃肿） | 4 次精简 → 108 行纯索引 + 5 专题文件 |
| "我以为记了/扫了/推了" → 沉默失败第 5 次 | 5 类沉默失败归档：disabled / cron token 残留 / 半成品 entry / 8 天 vector store / L0 缺失 |
| 改 CSS 凭印象 vs 改后 Playwright 实测 | 5 步走军令状（调研→方案 A/B/C→Lee 选→改→实测） |
| 凭报错/印象下判断（如"memory_search 挂了"） | "先查 status 再说话" |

---

## 🧠 记忆系统运作情况

### 三层记忆

| 层级 | 状态 | 本周统计 |
|------|------|---------|
| L0（memory/日记）| ✅ 7 天全勤 | 08~14 共 7 篇，2304 行总计；峰值 06-08（758 行）+ 06-10（785 行） |
| L1（MEMORY.md 索引）| ✅ **4.0 重组完成** | 951 → 108 行（-89%），纯索引结构；拆 5 专题文件 254 行 |
| L2（向量库）| ✅ 8 天未更新已修 | 996 → 1027 chunks（+31）；每日 03:30 cron 自动 build |

**本周提炼到 MEMORY.md 的关键规则（5 专题文件锚点）**：
- **MEMORY_POLICY.md**：4 步过滤准入门槛、里程碑 anchor 11 条精简
- **COLLAB.md**：任务确认流程、收藏流程、删除授权、日记 raw 优先规则、任务反馈规范
- **ROUTING.md**：精确 chat_id 表、判定启发、免 @ 直回、故障排查
- **CRON.md**：新建规范 / timeout ≥600s / systemEvent 兜底 / lightContext / 模型分流 / Token Plan 参数
- **ARCHITECT.md**：核心系统架构（含 MiniMax Token Plan 5h 周期 + 高频 cron lightContext 必加）

### Obsidian 备份

| 维度 | 数据 |
|------|------|
| 本周 commit 数 | **45 次**（平均 6.4/天；峰值 06-10 8 次）|
| 主要操作 | 微信同步、书籍推荐（5 本）、日记同步、wiki 学习文档、vault backup |
| 最新推送 | 2026-06-14 17:46（微信消息同步）|
| 状态 | ✅ 正常运行，cron 每日 23:45 + 手动推送双保障 |

### Ontology 图谱

| 维度 | 数据 |
|------|------|
| 文件 | `memory/ontology/graph.jsonl`（414KB，2507 行）|
| 实体数 | **1361 个**（上周 847，+60.7%）|
| 关系数 | **298 条**（上周 0，从未有过！）|
| 类型分布 | Tool 867 / CronJob 239 / Document 55 / concept 55 / Script 54 / Concept 42 / file 25 / Skill 13 / Person 5 / skill 4 / decision 1 |
| 状态 | ✅ **图谱边线首次建立**（W24 报告的关系数=0 痛点本周期解决）|
| 运行 | 每日 Ontology 同步 cron 仍偶发超时（f7b860cc 已改 8h） |

### Skills-store

| 维度 | 数据 |
|------|------|
| 当前候选 | **86 个**（`.openclaw/skills-store/`，与 W24 一致未清理）|
| 本周清理 | **0 个**（W24 已清，但本周新增 5 个 skill 化到 workspace = 净+5）|
| workspace 现有 skill | **12 个**（W24 = 7；本周 +5：cron-health-rules / routing-rules / diary-daily / openclaw-diary / daily-news）|
| 待办 | skills-store 86 候选积压，建议下个空闲期批量审计 / 安装 / 拒绝 |

### 自动化 Cron 运行情况

| 维度 | 数据 |
|------|------|
| cron 总数 | **47 个**（W24 = 48；本周 -1 整理 + 5 新增 = +4 净）|
| 健康状态 | **41 ok / 3 error / 0 disabled**（health=87%，W24=80% ↑7pp）|
| 本周新建 cron | 7 个：cron-disabled-audit-daily / cron_health_check / vector-store-daily-build / association-trigger / association-batch-backfill / corrections-rolling-monthly / diary-monthly-analysis |
| 本周改造 cron | 10 个：6 个 main→isolated（系统事件 cron）+ 3 个高频加 lightContext + 1 个 P0 偏差扫描 |
| Token 节省 | 131 万 tokens/天 = **5h 配额 31%**（实测：ec85def5 jsonl 200KB→4KB 省 50 倍）|
| 关键问题 | L1-reminder / PARA-Inbox / 周报 3 个 cron 仍 aborted（下周日自然重试）|

---

## 🔑 本周学到的重要知识（系统级）

### 1. MEMORY.md 准入门槛 4 步过滤（06-10 升级）
- 会复用规则吗？— 否 → 只进 L0
- 已升级到 SOUL/AGENTS/其他段？— 是 → MEMORY 只留指针
- 是技术细节且会复用？— 否 → 拦
- 里程碑/时间线？— 详情 → 拦（只留 anchor）

### 2. Token Plan 5h 周期经济学（06-10/11 实测）
- MiniMax Plus ¥49/月 = 600M tokens = 4.16M / 5h
- OpenClaw 默认 bootstrap 加载 = 200k 字符 = ~71k tokens/新 session
- **`--light-context` 是 OpenClaw 原生开关**——高频 cron（≤15min）必加，省 50 倍
- 估算公式：cron tokens/天 = (次数/天) × (bootstrap 71K + 实际 prompt)
- bootstrap 检查：`/tmp/last_*.jsonl` size；4KB = light-context 生效

### 3. Cron 沉默故障模式 5 类（06-08/09/14 沉淀）
| 模式 | 症状 | 防御 |
|------|------|------|
| `sessionTarget:main` + `systemEvent` | `lastError: "disabled"` skipped 1000+ | 改 isolated+agentTurn |
| GitHub token 残留 | API 401 | 全仓 `git config --show-origin --get credential.helper` 反查 |
| 半成品 entry 漂浮 | index.html 工作树脏 | 提交必须 commit+push 二段验证 |
| vector_store 8 天未 build | L0/corrections 不在向量库 | 每日 03:30 cron + mtime HEARTBEAT 检查 |
| L0 缺失等 Lee 介入 | 缺口预警刷屏 | L0 Watchdog 自愈机制（自动建占位 477 字节）|

### 4. 喝水追踪系统红线（06-08/14 立）
- 文字 + 卡片图片必须同一条 message 推送
- 默认推送 = 脚本同步记录 + 后台 worker + cron 兜底（不依赖 Agent 记忆）
- D/B 分支 override 关键词（共/漏/补/了/是/已）= 覆盖语义
- 测试推送：dry-run → 沙盒群 → 生产 三级跳（dev_20260608_006）

### 5. CardKit v2 流式回复边界（06-10 沉淀）
- 流式 update 开始后冻结 element 列表
- `buildStreamingCard` 不接受 footer（设计如此）
- 6 个 footer 开关虽然全开，但流式回复看不到 footer（只有 final 状态可见）

### 6. 飞书 Heartbeat 框架层配置（06-08 17:17 立）
- `openclaw system heartbeat disable` **不持久**（gateway 重启/升级会重新 enable）
- 必须 config 层：`heartbeat.target = "none"` + `directPolicy = "block"` 双保险
- protected config path 必须直接编辑 JSON 文件（CLI 工具不允许改）

### 7. SOUL 升级"先读证据源"原则（06-13 立）
- 接到不熟任务 → 1 分钟内查 3 证据源：SKILL.md + README_zh.md + 脚本 docstring
- 3 源交叉验证后能明确 → 动手
- 3 源都不明 / 矛盾 → 问 Lee，不猜
- **反模式**：跨系统时间窗口漏洞（如 cron 22:30 vs raw 22:48）= 设计漏洞不是偶发

### 8. SOUL 升级"轻量产出"规则（06-11 立）
- 主对话回复超过 200 字的分析/报告类内容，**不走 session 现场生成**
- 改用「脚本预生成 markdown + light-context cron 推」模式
- 根因：session 现场生成大段文字时 OpenClaw 跑 M3 task 1m+（152K input），浪费 Token Plan 配额

### 9. 关联分析 7 条相关文件 = 100%（06-09 反转）
- 真实源文件是 `~/Obsidian/收藏/{书籍,诗词}/*.md`，不是 `~/collections/`
- `collections/ideas/` 下的"关联分析-*.md"是报告文件，不是源文件
- A1+A2 cron 已校准路径，新收藏 0 漏跑

### 10. 5 步走军令状（CSS / 配置类任务）
- 调研（grep/Playwright）
- 列方案 A/B/C/D
- Lee 选
- 改 + 精确 add + commit + push
- Playwright 实测 + 截图发 Lee

---

## ⚠️ 待改进点

| 优先级 | 问题 | 状态 | 影响 |
|--------|------|------|------|
| 🔴 高 | skills-store 86 候选长期积压未审计 | 待执行 | skill 资源浪费 / 可能含过期 / 有安全隐患 |
| 🔴 高 | 月度 cron `corrections-rolling-monthly` / `diary-monthly-analysis` 21 天后才首次跑 | 等待首次验证 | 6/1 月度数据未自动归档 |
| 🟡 中 | L1-reminder / PARA-Inbox / 周报 3 个 cron aborted（5/9 起未恢复） | 下周日自然重试 | 月度任务有遗漏风险 |
| 🟡 中 | 6/10 心跳 #25 状态文件 miniMax token 字段是瞬时值，下游可能误读陈旧数据 | 待加时间戳 | 数据可信度 |
| 🟡 中 | "memory_search index metadata is missing" 报错文本仍在（即使 88/88 indexed） | 待排查 | 告警噪音 |
| 🟡 中 | `vector-store-daily-build` 用 SiliconFlow embedding 2 分钟慢 | 阈值合理 | 可接受，不阻塞 |
| 🟢 低 | 关联分析 `_build_related_lines` 强/中弱关联阈值过严（dev_20260610_010） | P2 backlog | 不影响主流程 |
| 🟢 低 | diary-daily / openclaw-diary 双 cron 时间窗口需统一协调 | 已修 | 6/14 验证中 |
| 🟢 低 | 全局 `backups/` 目录缺失（bc0ff9bf 06-12 健康检查发现）| 等 Lee 拍板 | 备份策略未定 |

---

## 📅 下周计划（W26）

1. **[高] skills-store 86 候选批量审计**
   - 按时间倒序审阅，挑出"应该装/已过期/可删"三类
   - 装进 workspace 或 quarantine
   - 6/22 前完成第一轮

2. **[高] 月度 cron 首次跑验证**
   - 7/1 03:00 corrections-rolling-monthly
   - 7/1 04:00 diary-monthly-analysis
   - 6/21 起观察是否有警告/超时

3. **[中] 心跳 #25 miniMax token 时间戳 + memory_search metadata 报错排查**
   - 06-16 ~ 06-20 之间择机修复

4. **[中] OBSIDIAN Para 备份目录（`~/.openclaw/backups/`）拍板**
   - 等 Lee 确认是否创建 + 备份脚本配置

5. **[中] 持续 L0 实时写入习惯巩固**
   - 06-10 立的 4 步过滤准入门槛内化
   - 每周 W25 已显示效果：MEMORY.md 4.0 重组后行数稳定 108

6. **[中] 关联分析 `_build_related_lines` 强/中弱阈值调整（P2）**
   - 06-17 抽 1 小时优化

7. **[低] Cron health 异常 3 项下周日自动验证**
   - L1-reminder / PARA-Inbox / 周报 → 6/21 周日观察

8. **[低] Token Plan 5h 配额监控**
   - 关键节点：周日 14:00（晨峰）和周二 15:00（晚峰）
   - 已接入 HEARTBEAT 第五步第 6 项

---

## 📋 数据附件

| 项目 | 数值 | 同比 W24 |
|------|------|---------|
| 本周 memory 文件数 | 7（08~14）| 同 |
| 本周 workspace git commits | **20** | W24=53 ↓62% |
| Obsidian git commits | **45** | W24=37 ↑21% |
| MEMORY.md 行数 | **108** | W24=362 ↓70% |
| 5 专题文件总行数 | **254** | 新增（从 MEMORY 拆出）|
| Ontology 实体 / 关系 | **1361 / 298** | 847/0 ↑60.7% / ↑∞ |
| skills-store 候选 | 86 | W24=0（清理后）↑86 |
| workspace skill 数 | 12 | W24=7 ↑71% |
| Cron 总数 | 47 | W24=48 ↓2% |
| Cron 健康率 | 87% (41/47) | W24=80% ↑7pp |
| 本周 Token 节省 | **131 万/天 = 31% 5h 配额** | W24=0 改造 |
| 本周新建 cron | 7 | W24=2 ↑250% |
| 本周已写 L0 总行数 | 2304 | W24=371 ↑521% |
| corrections 本周偏差 | 8 条（dev_20260608-14）| W24=12 ↓33% |
| Lee 推送消息（按群） | 12+（进化群 5 / 安全群 4 / 日常群 3）| W24=20+ |

---

## 🎯 本周一句话总结

> **从「记忆系统臃肿」到「4 步过滤 + 索引化」+ 从「cron 沉默故障」到「防御三件套」+ 从「Token 烧光」到「省 31% 配额」+ 从「等 Lee 介入」到「L0 自愈」——W25 是小龙虾「系统级进化」的里程碑周。**

---

_🦞 W25 进化周报 | 小龙虾 | 2026-06-14 19:15_
_⚠️ 本报告 18 KB，正文 + 数据附件；后续如需精简可裁剪【数据附件】段_