# MEMORY.md — 长期记忆索引 🦞

> 本文件是索引，不是内容库。所有实质性内容都存在对应的专题文件里。
> 每条索引约 150 字符，概括主题 + 指向文件路径。
>
> **原则：少即是多。只记一次性事实，不记可推导的结论。**

---

## 用户信息
- **user**: Lee，福州台江区，Asia/Shanghai 时区，仅接受「Lee」这个称呼
- → 详见：USER.md

## 三 Agent 协作团队
- **小龙虾**（我）→ 腾讯云，OpenClaw；飞书 open_id: ou_2afb013d7a3b01d96ca4218b22e2ecd8
- **小马**（xiaoma-hermes）→ Lee 的 PC 本地（2026-06-01 从腾讯云迁移）；飞书 open_id 待补充
- **仓库**：小龙虾→xiaolongxia-openclaw / 小马→xiaoma-openclaw
- **三端分工原则**：小龙虾脚本/cron运行在服务器端，小马脚本/cron运行在PC端，Obsidian为共享数据层，两端通过GitHub共享备份
- **日记生成 cron（e44d151d）**：每日 22:00 生成 Obsidian 日记，**小龙虾负责**（2026-06-07 小马移交）；健康检查 cron（63bb338f）22:30 兜底
- **互惠约定**：发现问题主动说，不各自闷头改

## 红线规范（系统级，必须遵守）

### 任务确认流程（收到任何任务指令时）
理解 → 分解 → 步骤 → 可行性 → 建议 → **Lee 确认** → 执行 → 汇报 → 修正
- 紧急情况（服务挂了/数据丢失风险）可先做后报，但必须告知

### 收藏流程（收到文件/想法/金句/链接时）
必须走完整流程，**绝不只回不复**：提取要点 → 关联分析 → Obsidian 入库 → frontmatter 回流 → GitHub 同步 → 飞书汇报

### 删除授权
删除文件前**必须**获得 Lee 明确授权，不得擅自操作

### 日记 raw 优先规则（2026-05-25）
**生成日记必须读取 `~/Obsidian/日记/raw/微信-YYYY-MM-DD.md`，而非工作区 raw。**
Obsidian raw 是唯一真相源，工作区 raw 可能不完整。

## 飞书群推送（精确路由）

**唯一真相源：TOOLS.md**。本表为快速查询。

| 群名称 | chat_id | 用途 |
|--------|---------|------|
| 日常安排群 | `oc_ad39a8e943103c2164f1d0d9de503da5` | 日程/喝水/补剂/今日要事 |
| 学习监督群 | `oc_3fb5240d43f24be367f5bcd981a0415b` | 午间学习提醒 |
| 新闻群 | `oc_e4686fe5eb6e865b68fae7625a5ce840` | 每日 9:00 新闻简报 |
| 进化群 | `oc_8e02a9ced0671cac8413b4c98e76637a` | 进化日报/Skill安全/技术成果 |
| 内容收集群 | `oc_20875a15a62ddeb3c3573d8d23c86daa` | 书籍推荐/内容收藏 |
| 安全群 | `oc_1f77586fc34cdacac8f43a4e9733eafc` | 健康检查/备份/审计 |

**判定启发**（2026-06-03 Lee 授权自主判断）：
- 系统内部状态（HEARTBEAT/架构/规则/技能）→ 进化群
- Lee 今日行为（喝水/GNC/学习）→ 日常安排群
- 外部信息（新闻/书/文章）→ 新闻群 / 内容收集群
- 系统安全/数据 → 安全群
- 不确定时 → 进化群（兜底）

**群回复模式差异**（2026-06-10 Lee 拍板，全群免 @ 直回）：
- **所有飞书群**（学习监督/日常/新闻/进化/内容/安全）= **免 @ 直回**（Lee 17:01 拍板）
- 看倒 Lee 消息直接接，不要在群里干等 @
- 反例修正：之前 6/10 16:58 我理解成"只学习监督群免 @"，是错的，**全群都是**

**反例**：HEARTBEAT 健康度提升 ≠ 日报（进进化群），GitHub push 成功 ≠ 任务完成（进进化群）

**chat_id 验证**：飞书 chat_id = 35 字符（`oc_` + 32 位）。`cron-chat-id-audit-daily`（每天 23:55）兜底 + 24h 去重。

## 核心系统架构

- **时区基准**：服务器UTC / 业务CST（+8），所有时间统一存储UTC，显示转换CST
- **三层记忆**：SESSION-STATE.md（短期）→ memory/YYYY-MM-DD.md（中期）→ MEMORY.md（长期）
- **Gateway 端口**：26301
- **三层记忆优先级**：长期 > 中期 > 当前会话 > 联网搜索
- **WAL 协议**：重要决策实时写入 memory/当日文件
- **MiniMax Token Plan**（2026-06-10 立）：6/5 起按 token 计费，Plus ¥49/月 = 600M/月 → 5h 周期 = 4.16M tokens。周期重置 = 00:00 / 05:00 / 10:00 / 15:00 / 20:00。实际查 `scripts/minimax_token_check.sh`。
- **token 估算公式**：要算 system prompt + bootstrap + 工具调用上下文，不能只算 chat text（实测差 2 个数量级）

## 任务执行反馈规范（2026-06-03 立）

**Lee 明确：做任务必须给完成报告才算执行结束。**

**四时点**：
1. **任务开始** → 简短确认（理解 + 步骤）
2. **长任务中间**（≥3 步 / 多次工具调用 / 外部 I/O / 预计 ≥30s）→ 状态提示
3. **任务完成** → 完成报告（做了什么 / 结果 / 推送去向）
4. **被中断或失败** → 告知（原因 / 下一步）

**反例**：安静 5 分钟只回「好的」、失败不告知、推送后不回报 ID/回执

**推送反馈**：推到飞书后必须回报 → 哪个群 / 是否成功 / ID。失败必须说明 + 尝试恢复。`deleteAfterRun` 清理的无需回报

## 时区规则（系统级铁律）

**背景**：服务器在UTC时区运行，Lee在CST（UTC+8）时区。`datetime.now()`是naive datetime，同一时间在不同Agent理解中可能是不同瞬间。

**强制规范**：
- `from _timezone import CST` — 所有脚本必须从 `_timezone.py` 导入 CST 常量
- `datetime.now(CST)` — 业务时间（日志/文件名/显示）用这个
- `datetime.now(timezone.utc).isoformat()` — 存储时间（跨Agent/持久化）用这个
- **禁止** `datetime.now()` — 会产生 naive datetime，歧义根源，发现即修

**时区语义协议**：
- 内部计算：UTC
- 用户可见：CST（+8）
- 跨Agent通信：ISO UTC
- 口头时间：默认 CST（+8），说「UTC」才用 UTC，不让对方猜

**CST 常量定义**：`CST = timezone(timedelta(hours=8))`，定义在 `scripts/_timezone.py`

## 定时任务（Cron）规范
- 新建 Cron：必须 `channel:feishu` + `to:oc_xxx`，禁止 `channel:last`
- 并发冲突：新 cron 与已有 cron 错开 ≥30 分钟
- timeout：进化日报 120s，每日简报 400s
- 任务完成后**立即删除** cron 提醒，避免重复发送
- **高频 cron（≤15min）必须 `--light-context`**（2026-06-10 立，dev_20260610_002 实测省 98% tokens）
  - OpenClaw 默认 bootstrap 加载 = 200k 字符 = ~71k tokens
  - 1min cron 跑一小时 = 4.3M tokens，超过 5h 周期额度 4.16M 的 100%
  - 修复后 jsonl 200KB → 4KB（省 50 倍）
  - 纯 shell 任务可考虑 systemEvent（更轻量），但 light-context 已够用

## 微信读书
- **API Key**：存储于 `~/.openclaw/.env`，禁止硬编码上传 GitHub
- **.env 格式**：每个 KEY 独立一行，连在一起会导致解析错误（如 `FEISHU_BOT_TOKEN=xxxDEEPSEEK_API_KEY=sk-xxx` 错位）
- **书名查找**：无 bookId → `/store/search?scope=10` 拿 bookId
- **失效处理**：errcode -2010 → Lee 在微信读书 App → 我的 → 设置 → API Key 重新获取

## 每日书籍推荐
- 发送前：生成卡片 → 发内容收集群
- 发送后：立即 Obsidian 入库 + GitHub 同步
- **禁止**：只发送不复

## 模型安全规则
- DeepSeek v4 Flash：**仅限** cron 定时任务使用，禁止主动调用
- 主会话主力：MiniMax-M3（M2.7 → fb1）
- cron 任务：`minimax/MiniMax-M3`（2026-06-07 反转，原 V4-Flash 降 fb3）
- cron 以外需要 DeepSeek：必须立即通知 Lee 或获得授权
- **DeepSeek 填充安全**：无内容写「（当日未记录）」，不编造

## GitHub 协作约定（系统级）
- **写前 pull 标准**：`git pull --no-rebase origin main`（统一，不用 rebase）— 写入任何文件前必须先拉取远程最新状态
  - **2026-06-07 修正**：历史记忆写的是 `master`，但本仓库从创建（2026-05-14）就用 `main`，GitHub 默认分支也是 `main`，无 master 分支
- **冲突处理**：检测到冲突标记 → 提取冲突内容 → 追加为 `[系统/冲突待处理]` entry → 写回 → push → 告知 Lee；禁止静默覆盖
- **推送规则**：谁最后 push 谁负责解决冲突，先 rebase/fetch 再 push
- **分叉处理**：发现分叉（diverged）→ 立即 rebase → 再 push
- **增量推送**：不用 `git add -A`，精确指定文件
- 本地文件是唯一真相源，GitHub 仅作备份

---

## Cron 健康度规范（2026-06-03 立）

### 根因
- OpenClaw cron agentTurn 默认 timeout=300s，但实际很多任务（多次模型调用+工具+飞书推送）需 5-10 分钟
- 全量 4481 次运行中 401 次 timeout（占失败 48%），其中 cron-retry-monitor 自己 152 次
- 救命稻草也是病人 → 兜底机制失灵

### 强制规范
- **agentTurn 任务 timeoutSeconds ≥ 600s**（任何含 1 次以上工具调用的任务）
- **救命稻草类 cron 必须用 systemEvent 或纯 shell**（不依赖模型调用）
- **OpenClaw cron update patch 不支持局部字段** → 必须传完整 payload（kind/message/model/timeoutSeconds）

### 验证
- 实际耗时参考：6e9478c2 晨间简报 12s、52f5f99e heartbeat 22s、81f34340 备份 389s（最长的 6.5min）
- timeout 设 600s 后这些任务都不会被杀

## 进化里程碑

**架构调整与制度建立时间点**（会复用的 anchor）：

| 日期 | 里程碑 |
|------|---------|
| 2026-04-28 | 书卡系统 + MEMORY 精简 + Obsidian 备份 |
| 2026-05-02 | Token 消耗降 99.94%；双轨记忆打通 |
| 2026-05-12 | 三 Agent 协作确立；GitHub 仓库重建 |
| 2026-05-22 | 反信息茧房三条；HEARTBEAT 向量检查 |
| 2026-05-23 | MEMORY 版本行规范；GitHub SSH 推送规范 |
| 2026-05-29 | Git 写前 pull+冲突处理机制 |
| 2026-05-31 | 飞书群聊路由故障修复 |
| 2026-06-01 | Cron 模型切换 |
| 2026-06-03 | Cron 健康度规范建立 |
| 2026-06-07 | PARA vs Wiki 分工原则 |
| 2026-06-10 | MEMORY.md 反模式纠偏（v3.11→3.14，699→237 行） |

**说明**：详细信息查 `git log`（commit history）— MEMORY.md 只保留 anchor，**不重复时间线**。

## 维护规范

### 清理频率
- MEMORY.md 精简：**每月一次**，结合当月教训归档一起做
- 教训索引：>3个月且不再适用的规则移入 `memory/archive.md`
- 里程碑：**永久保留**（时间线是资产）

### 版本行规范
- 格式：`版本：X.X | 最后更新：YYYY-MM-DD HH:MM | by 作者`
- patch（Bug修正）/ minor（新增章节）/ major（结构重组）

### MEMORY.md 写作红线（2026-06-10 立，防 06/08-06/10 全文照抄反模式）
- **不全文照抄 L0**——L0 是中期过程记录，MEMORY.md 是长期索引
- **每条索引 150 字符**——只概括主题 + 指向文件路径，不记详情
- **不记"什么会进 MEMORY"**——不写"本次会议纪要 / 今日发生 / 临时状态"
- **不记消息 ID / commit hash**——查时走 git log / 飞书 API
- **会复用的规则** vs **一次性事件**：规则进 MEMORY.md，事件进 L0

### MEMORY.md 准入门槛（4 步过滤，2026-06-10 立，Lee 反问 4 次后形成）

**逐项检查，遇否就拦**：

1. **会复用规则吗？** — 否 → 不进 MEMORY（只进 L0）
   - 例外：里程碑 anchor（首次落地时间点）→ 留 11 条短行，详细查 `git log`
2. **已升级到 SOUL/AGENTS/其他段了吗？** — 是 → MEMORY 里只留指针（“→ 升级到 X 段”），不重复列
3. **是技术细节且会复用？**（.env 格式 / weread 查找 / DeepSeek 填充安全）— 是 → 可留为技术细节段
4. **里程碑 / 时间线：** 1 个 milestone = 1 行 anchor（< 30 字符），不写详情

**反例**（不该在 MEMORY）：
- ❌ 5/27 那天修了 L0 路径（历史事件）→ 只进 L0
- ❌ 本次会议纪要（临时状态）→ 只进 SESSION-STATE
- ❌ “cron 今天跳 3 次，原因是 X”（事件）→ 只进 L0
- ❌ 里程碑 “Skills 107→40 精简”（事件）→ 删，留“精简原则”进对应段

**正例**（该在 MEMORY）：
- ✅ L0 实时写入（非 cron 补跑）= 规则
- ✅ Token Plan 5h 周期 = 4.16M tokens = 会复用的参数
- ✅ git pull --no-rebase origin main = 规则
- ✅ "全交班" 发生时在该日加个 anchor = 里程碑

---


## GitHub 访问方式（系统级）
- **腾讯云服务器**：必须用 SSH（git@github.com:xxx），HTTPS 会超时
- **SSH URL 格式**：`git@github.com:leeiceice/仓库名.git`
- **设置 upstream**：`git push --set-upstream origin main`（一次性）
---

## 飞书群聊路由故障排查（2026-05-27）
- **症状**：群消息被路由成 DM，bot 在群里无响应
- **根因**：`channels.feishu.groups.{chat_id}.requireMention` 等 per-group 配置与全局 allowlist 冲突
- **修复**：`openclaw config unset channels.feishu.groups.{chat_id}` + 重启
- **预防**：per-group 配置要慎用，加完必须在群里实际 @ 机器人测试



---

_版本：3.15 | 最后更新：2026-06-10 15:50 | by 小龙虾（精简第二阶段：删 legacy 8 段共 109 行 + 3 技术细节合并到对应段，-32%；累计 699→237 行 -66%；事件流水留 L0 memory/2026-06-10.md）_
