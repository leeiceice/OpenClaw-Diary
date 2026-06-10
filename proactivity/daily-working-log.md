# 2026-06-05 工作日志

## 🔍 [2026-06-05 22:30] 直觉系统冷启动诊断：脚本/cron 都健，数据源几乎空

- **现象**：`intuition_snapshot.py` cron 跑（22:30 daily），输出 `total_annotations=1`、四状态全 0、健康分 0/15
- **初始判定**（错）：以为是"cron 没接"，决定写"建议建 cron"
- **实际**：cron `c9310669-4881-4dfa-a426-2ec17f516036` **早就接了**（lastRun 32ms，状态 ok）
- **真正的根因**：我的回复/working log 几乎不用 `[置信度: X%]` 方括号格式，snapshot 正则扫不到
- **额外发现**：脚本有 dead code（`OBSIDIAN_RAW` / `OBSIDIAN_DIARY` / `RAW_DIR` 三个变量赋成 `WORKSPACE` 后未使用）；`next_run_hint` 文案错为"22:00"但实际 22:30
- **行动**：
  1. 删三个死变量 + 改 `next_run_hint`（A+B）
  2. 加回路规则到 `proactivity/memory.md`（查-引-调三步）
  3. 约定写入格式为 `[置信度: X%]`，不用 `**置信度**：X%`
  4. 今后写 entry 走 daily-working-log，**不造数据**
- **置信度**：[置信度: 50%]（已验证：cron 存在、脚本跑过、快照 JSON 存在、6/4 那条 entry 用了 markdown 加粗格式不匹中正则 → 路径已被锁定；30% 基础 + 20% 实测验证）
- **验证状态**：本次验证成功的 entry：0（首次记录）
- **场景适用**：未来任何"系统机制存在但健康分异常低"类问题，先看 cron 跑了没、脚本健康否，**最后**才怀疑"输入端缺失"

## 🧠 [2026-06-05 22:38] SKILL.md 写了 `/intuition verify` 但没接到实际行为（**设计 vs 实施 断层**）

- **现象**：SKILL.md 描述了完整工作流（观察→验证→/evolve 聚类→/promote 技能化），但我（小龙虾）**从没在回复中调过 `/intuition verify`**
- **诊断**：这是"机制建了但没接到调用者的行为"问题，类似 "systemEvent 跑通 ≠ 推送完成"（6/5 日报 修复 3 教训）
- **原因**：
  1. SKILL.md 是**参考文档**不是**系统指令**，不会被自动加载
  2. SOUL.md / AGENTS.md 才是每次必读 → SKILL.md 写了等于没写，除非 agent 主动看
- **行动**：回路规则放到 `proactivity/memory.md`（每次心跳/上下文会自动刷到 proactivity 相关文件）而不是 SKILL.md
- **置信度**：[置信度: 40%]（路径已验证：SKILL.md 内容未变、memory.md 写入了；30% 基础 + 10% 文档引用；还需下次真实场景触发"查-引-调"才算成功）
- **场景适用**：任何"设计完整但没生效"的机制，**先查在哪写了、谁在读**——是写入问题还是读取问题

## 🦞 [2026-06-05 22:40] "快照数据少" ≠ "脚本 bug"：32ms 跑完可能是对的

- **现象**：看到 `lastDurationMs: 32` 第一反应是"没跑就跑完了"→ 怀疑脚本空转
- **实际**：扫描范围小（3 个目录，无文件或极少文件） → 32ms 跑完是**真实**耗时
- **诊断模式**：**耗时异常低不能等同空转**——要看输入端数据量
- **反模式**：把"运行时间短"直接反推为"任务失败"
- **置信度**：[置信度: 30%]（原理性判断，未验证；推测/假设型 30% 起步）
- **场景适用**：所有 cron / pipeline 类任务，**耗时与输入数据量正相关**才健康；输入空 → 耗时极短 ≠ 异常

## 🛠 [2026-06-05 22:42] AGENTS.md 改前需授权（红线类推）—— 改 proactivity 自己的文件更稳

- **情境**：想加"直觉回路"规则到 AGENTS.md，但 AGENTS.md 是**系统级红线/规则文件**
- **原则**：MEMORY.md / SOUL.md / AGENTS.md 这类高优文件，"删除/重大修改前必须 Lee 授权"（AGENTS.md Red Lines 自带约束）
- **决策**：放 `proactivity/memory.md`，**不**污染 AGENTS.md，且 proactivity 文件会随上下文自动加载
- **置信度**：[置信度: 40%]（AGENTS.md 顶部 `Red Lines` 明确"删除操作前必须 Lee 授权"；30% 基础 + 10% 文档引用）
- **场景适用**：写"规则"前先想——这是要 Lee 必看的红线，还是我自己的纪律？前者改 AGENTS.md/SOUL.md（需授权），后者改 proactivity/ 即可

---

# 2026-06-04 工作日志

## 🔧 [2026-06-04 23:03] 系统修复: 补跑 06-03/06-04 日记 + 新建 22:00 diary_daily_report cron
- **触发**：Lee 23:00 微信问「日记生成了吗？」，发现 22:30 的 diary_daily_report cron 缺失（22:30 实际跑的是 intuition_snapshot.py），06-03 和 06-04 都未生成
- **影响**：
  - 2 天微信 raw 消息未生成结构化日记
  - 月报生成会断链
  - HEARTBEAT 记忆系统维度扣分
- **修复动作**：
  1. **改 `diary_daily_report.py`**：加 `DIARY_DATE` 环境变量支持补跑历史日期；加 `DIARY_SKIP_FEISHU=1` 静默模式避免补跑打扰 Lee
  2. **补跑 06-03**（静默）：从 raw 1 条「有点疲惫，迷迷糊糊趴着睡了一会」生成 995 字节结构化日记
  3. **补跑 06-04**（静默）：从 raw 2 条（记录吧 + 大雨夜陪娃玩悬浮球）生成 1392 字节结构化日记
  4. **新建 cron `e40ffddb`**：22:00 跑 `diary_daily_report.py`，避开 22:30 intuition_snapshot 和 23:00 ontology（错开 ≥30min 规则）
  5. **失败告警**：连错 2 次 → 飞书进化群（chat: oc_8e02a9ced0671cac8413b4c98e76637a），cooldown 24h
- **置信度**：95%（已验证产物存在、cron 已启用、避开并发）
- **遗留**：未推送补跑摘要到飞书群（Lee 已睡，06-05 早间可考虑补一条说明）
- **场景适用**：未来任何「脚本存在但 cron 缺失」类问题，发现后同时补跑+建 cron+写记录

## 🔍 [2026-06-04 09:24] heartbeat-观察: intuition_snapshot 冷启动（全 0 分布）
- **现象**：cron 跑 `intuition_snapshot.py`，分布 guesses 0 / intuitions 0 / experiences 0 / knowledge 0，健康分 0/15
- **判定**：冷启动状态，不是异常——库里还没有任何直觉/猜测/经验/知识条目可快照
- **含义**：ECC 框架的「四状态分布」指标还无法产出真实信号
- **行动**：
  1. 收到 Lee 任何「我觉得…」「我猜…」「我学到一个…」这类表达时，走 `intuition_capture.py` 写一条入库
  2. 积累到一定量后，再跑快照就能看到真实分布
- **来源**：cron-实测 + Lee 飞书引用确认
- **初始置信度**：90%（冷启动是确定状态，路径清晰）
- **修复状态**：无需修复，等数据积累
- **后续**：Lee 2026-06-04 09:24 飞书确认「开始处理记录」，已写入本条；后续 `intuition_capture.py` 启动后回查

---

# 2026-06-01 工作日志

## 📝 每日纠正捕捉（2026-06-01 新增）
> 格式：`- **来源** | 日期 | 事件简述 | 教训一句话`
> 触发：被 Lee 口头纠正时 / 发现系统层异常时 / corrections 写入后补录

# 2026-05-14 工作日志
# 2026-05-13 工作日志
❌ [2026-05-13 18:03] 严重失误:今日第二次重复推送（1.中交云商cron未清理 2.AI Humanizer重复推销）→ Lee要求卸载技能并删除文件
📝 [2026-05-13 22:17] 纠正:GNC补剂提醒只推日常安排群，删除学习监督群那个(12:30)
🏥 [2026-05-14 13:49] Lee确认：三杯水（1050ml），补剂也吃了
🔧 [2026-05-14 16:06] 修复断链:删除broken symlink conversation_to_ontology.py（指向已删除的xiaolongxia/），更新HEARTBEAT.md使用ontology_auto_sync.py
📊 [2026-05-14 16:04] Ontology管道完成:新增27个日记实体(2026-04-15~05-14)，全部同步到graph.jsonl
📝 [2026-05-14 18:21] Lee纠正：我主动记录喝水行为是错的。Lee说没叫我记录时不要记录。已撤销第6杯虚假记录。

❓ [2026-05-15 09:17] 心跳检查: 无今日随手记（cron/清理任务均已在上轮处理完毕）；Ontology管道健康(6实体同步) ✅

✅ [2026-05-15 19:00] cron提醒推送:苹果手表钢带→日常安排群

## 12:10 Lee 指令：research-context-compressor 留着，有需要时提醒加入使用

- 当前状态：已安装，未整合进搜索系统（两者层面不同）
- 结合时机：未来建本地文件 embedding 向量检索时，作为「项目索引层」接入
- 下次提醒 Lee 的触发条件：启动本地文件向量检索相关讨论时

## 11:53 - 关联分析方案A已确立为永久标准

Lee 确认：关联分析脚本 `association_analysis.py` 已升级为 v4，BM25全文检索替代纯标签匹配。
- **已废弃**：纯标签Jaccard匹配
- **新标准**：全Vault BM25索引（76文件）+ 标签双重信号，BM25排名权重60%
- **自匹配过滤**：按文件stem排除
- **适用场景**：所有书籍/文章收藏后的关联分析
- **缓存**：BM25索引缓存1小时，数据文件 `data/bm25_index.pkl`

已推送GitHub（commit 1cc4c12）。

## Git 协作规范更新（2026-05-28）
- **来源**：Lee 口述，小马操作示范
- **标准流程**：fetch → pull --no-rebase → push
- **原因**：保留远程日记备份等 commits 的历史
- **我要学**：以后合并分叉时也用 `git pull --no-rebase`，不再用普通 `git pull`

🦞 小龙虾补充随手记（2026-05-29 08:01）
---
**待办：明早（2026-05-30）找苹果手表钢带**
- 来源：Lee 飞书提醒
- 优先级：待确认

10:17 CST - 飞书安全群推送失败（Channel unavailable），心跳记录已写入 heartbeat-state.json

🦞 [2026-05-30 08:00] 系统事件: 苹果手表钢带提醒触发 (feishu → Lee个人chat)
📌 Lee提醒：明早（2026-05-31）找苹果手表钢带
🦞 [2026-05-31 10:17] 小马文件迁移完成：/root/.hermes-xiaoma/，2.6GB，17处路径修正，GitHub已推送
🦞 [2026-05-31 18:09] 系统决策：systemd PATH 问题 later 处理，但升级Node版本前必须先修复gateway service

🦞 [2026-05-31 18:46] 小马Hermes部署完成
- 根因：Hermes读取`HERMES_HOME`环境变量来确定config位置，默认`~/.hermes`（即`/root/.hermes`），但小马config在`/root/.hermes-xiaoma/`
- 修复：systemd service直接设`HERMES_HOME=/root/.hermes-xiaoma`，不依赖EnvironmentFile
- 教训：hermes-agent和OpenClaw不同，OpenClaw用`config.yaml`，Hermes用`HERMES_HOME`目录下的config.yaml
- Feishu已连接：wss://msg-frontier.feishu.cn

🦞 [2026-05-31 20:53] 双Agent同机运行确认
- 腾讯云服务器同时跑小龙虾和小马
- 小龙虾: Node.js (OpenClaw) PID=3946358 端口26301 内存534MB
- 小马: Python (hermes-gateway) PID=4072951 内存351MB
- 总内存占用: 1.5Gi / 3.6Gi，可用2.1Gi
- 磁盘: 39G/59G (68%)
🦞 [2026-06-01 11:15] 飞书群路由修复（requireMention → false）
- 根因：groupPolicy="open" 的群默认需要 @mention 才响应
- 修复：对所有 6 个飞书群设置 `channels.feishu.groups.{chat_id}.requireMention = false`
- 验证：Lee 确认 2026-06-01 11:15 修复成功

🦞 [2026-06-01 12:00] HERMES_HOME 路径修复（小马workspace）
- 小马 workspace（/root/.hermes-xiaoma/skills/）大量文件硬编码 /home/admin/.hermes
- 实际应为 /root/.hermes-xiaoma
- 小马执行替换：12个文件，0残留
- 小马同时告知小龙虾 openclaw 路径（/home/admin/.openclaw → /root/.openclaw）

## 观察 [2026-06-01T18:16:00+08:00]
- 内容：小马反馈ECC框架已借鉴落地，置信度85%，框架逻辑扎实与现有机制高度兼容
- 来源：文档-引用（小马飞书转发）
- 初始置信度：85%（来源高质量文档+双马独立验证）
- 修复状态：无需修复，闭环确认
- 备注：ECC框架双马落地完成

🔍 [2026-06-01 22:19] heartbeat-观察: corrections.md 已 146h（6天）无新写入，自我修正反馈回路断链
- 来源：heartbeat-实测
- 初始置信度：30%
- 修复状态：待观察（cron 排程是否仍在跑？memory_sensor 活跃度？）

🔍 [2026-06-01 23:17] heartbeat-观察: 评分 53（与上轮持平）；corrections.md 仍 6 天断链；graph.jsonl 24h 无新数据（ontology 干跑）
- 来源：heartbeat-实测
- 初始置信度：30%
- 修复状态：未处理（Lee 关注点在小马迁移本地 PC）

## 系统状态 [2026-06-02 21:24 CST]
- Lee 评估：小龙虾系统稳定性严重不足，需持续调整
- 后续计划：用思维导图画出常用系统框架
- 优先级：高（稳定性问题是系统级问题）

## 系统修复 [2026-06-07T15:55+08:00] ✅ 3个持续问题一次性修复

**触发**: Lee 说"执行"后立即动手

**修复内容**:
1. **ontology pipeline 17天空转** (conversation_to_ontology.py:263)
   - 根因: mtime naive vs cutoff aware 的 TypeError 被 except:pass 吞
   - 修法: fromtimestamp(..., tz=CST)
   - 效果: graph.jsonl 1992→2094 行，96+5 个新实体入库
2. **memory_sensor WORKSPACE 路径 bug** (额外发现)
   - 根因: WORKSPACE = Path("~/...") 字面构造，read_text/write_text 走字面路径
   - 修法: 加 .expanduser()
   - 清理: 删除字面 ~ 路径下的所有垃圾文件
3. **corrections.md 双文件分裂**
   - 真相源: self-improving/corrections.md
   - 孤儿: memory/deviations/corrections.md
   - 合并: 6/2 5条观察转 ECC 格式 (dev_20260602_001~005)
   - 归档: 孤儿移到 _archive_2026-06-07/

**附带修复**:
- HEARTBEAT.md 路径统一指向 self-improving/corrections.md
- wiki/vector-search-architecture.md 同步修正

**未修**:
- 5/21 和 6/5 两条历史偏差用自由格式（非ECC），parse_corrections 跳过
- 等 Lee 决定是否重写为 ECC 格式

**验证**:
- memory_sensor list: 13 条 (修复前 1 条) ✅
- ontology graph: 2094 行 (修复前 1992 行) ✅
- 3 个 cron (f7b860cc 2h, ab150a93 23:00, d0518b66 10:00) 下次自动跑会正常

**commit**: f7e9c7a pushed to origin/main

## 观察启动 [2026-06-07T16:16+08:00] Lee 授权持续观察

**Lee 16:16 原话**：「好的，请持续观察！」

**观察范围**（4 个修复点）:

| 修复 | cron 验证时机 | 验证指标 | 当前基线 |
|------|--------------|---------|---------|
| ontology TypeError 修复 | f7b860cc 2h/次 (18:00, 20:00) | graph.jsonl +N 行 | 2102 行 |
| ontology 23:00 全量同步 | ab150a93 23:00 | mtime 23:00 附近 | 6/5 23:00 |
| memory_sensor 双文件 | 周日 d0518b66 10:00 | 16+ 条仍能解析 | 16 条 |
| cron 产物 mtime 监控 | 5a222ec4 4h/次 (18:00) | 7/7 通过 | 待首次跑 |

**触发主动推送的条件**:
- ontology cron 跑通但 graph.jsonl 0 新增 → 立即推安全群
- memory_sensor verify_write 抛出 RuntimeError → 立即推安全群
- cron 产物 mtime 监控 high severity 失败 → 自动查 cron runs + 推送
- 系统稳定性降到 < 70 持续 24h → 推安全群

**主动推送路由**（按 MEMORY 路由原则）:
- 技术成果 / 系统观察 → 进化群
- 健康度异常 → 安全群

**静默条件**（不推送）:
- 同类问题 24h 内已推送
- 修复点持续稳定运行 7 天
- 监控本身（cron 产物）首次跑通

**下次主动推送窗口**:
- 6/7 18:00 ontology 2h 跑后 (5min 内)
- 6/7 18:00 cron 产物监控首次跑后
- 6/8 07:00 daily-health-check (例行)
- 6/14 10:00 偏差传感器周扫描


## 观察 [2026-06-07 17:06] heartbeat #93

### 4 项修复后系统状态
- E1 memory_search: 3/3 ✅
- E2 cron error: 3 个 (新增 d376d8dc 是 gateway restart 造成)
- E3 idle: 2 个 (没到点)
- E4+E5: drift 7→1, integrity 9→2
- 3 channel: 全 ON/OK
- gateway: pid 3547325 active

### 新发现
- d376d8dc 17:00 error = 364s 后 abort, 我 17:06 重启 gateway 打断
- 不是持续问题, 下次跑 (明天 17:00) 会自动恢复

### 评分
- 升级前: 56
- 4 修复后: 72 (+16)
- trend: up

## 观察 [2026-06-08 02:05] heartbeat #102（每3次抽查）

（此后 28 次心跳无新观察条目，沉默 25h，本轮 HB-130 强制抽查记录于此）

## 观察 [2026-06-09 03:04] heartbeat #130（每3次抽查，补登）

### HB-102→HB-130 状态对比（28 次心跳跨度）
- run_count: 102 → 130（+28，沉默期未漏跑，每小时都在跑）
- L0 watchdog: 清醒窗口外 03:04 静默 ✅（按设计 08:00 后才回报）
- ontology: HB-130 新增 14 实体（concept_生查子·春山烟欲收、tool_search_dirs 等），说明对话有新增内容
- memory-search: 3/3 ✅
- corrections.md: 45.9K → 48.3K（+2.4K 增长，仍 < 100K）
- index.md: 23:03 → 03:04 本轮重建（因 corrections 03:00 已更新）
- size-check: 全部 < 100K，最大 48.3K
- self-improving/ 5 个文件，结构稳定

### 沉默期观察（25h 无新 entry）
- run_count 在涨（每跑一次 +1），说明 cron 健康
- 但没触发任何"值得记录"的偏差/发现
- 可能原因：清醒窗口外跑的 HB 都静默，无 Lee 介入，无新事件
- **置信度**：[置信度: 70%]（从 run_count 增长 + 文件无突变推断，无直接证据表明"应该有事但漏了"）

### 趋势
- score: 75 → 75（持续稳定）
- 持续遗留：scenes 停滞、score < 80

### 行动
- 无紧急行动
- 继续静默观察

### 评分
- score: 75（稳定）
- trend: stable

### HB-101→HB-102 状态对比
- run_count: 101 → 102
- L0 watchdog: 清醒窗口外（00:00-08:00）静默 ✅
- ontology dry-run: 无新增会话实体（135 cron 已加载）✅
- memory-search: 3/3 ✅（RRF 拉平、systemEvent 推送、Token Plan 限流全过）
- graph.jsonl: 2182 → 2188 行（+6 实体）
- self-improving 文件: 最大 20.2K（corrections.md），全部 < 100KB，无需压缩
- index.md: 00:03 生成，corrections.md 23:26（index 已最新，无需重建）
- daily-working-log: 17:07 后无新条目（沉默 9 小时），但 heartbeat 一直在跑无异常

### 待观察
- 02:04 清醒窗口外，本轮静默
- 下次心跳：02:04 → 03:04

### 评分
- score: 75 → 75（稳定）

## 观察 [2026-06-09 20:04] heartbeat #147（每3次抽查，本轮触发）

### HB-130→HB-147 状态对比（17 次心跳跨度）
- run_count: 130 → 147（+17，沉默期未漏跑）
- L0 watchdog: 清醒窗口内 20:04 静默 ✅（19:00-23:00 静默设计）
- l0_watchdog.sh 同源输出：L0 正常 15913 字节；3/50 cron 风险（同源 timeout/abort）
- datetime_naive_scanner: pass（内嵌在 l0_watchdog.sh）
- memory-search: 3/3 ✅
- ontology dry-run: 无新增会话实体（150 cron 已加载，6/9 18:07 同步后无新对话）
- graph.jsonl: 2294 → 2295 行（+1，cron 自动 sync 产物）
- corrections.md: 8KB < 100KB
- index.md: 19:04 最新，corrections.md 17:33（index 新于 corrections，无需重建）
- self-improving 5 个文件，结构稳定
- daily-log 上次 mtime 03:05，本轮抽查写入

### 沉默期观察（17h 无 entry）
- 17:04 → 20:04，无 Lee 主动交互触发新事件
- run_count +17 持续增长
- L0/data/memory 链路全静默稳定
- 主流反面是：cron 跑了不等于 Lee 信息在持续沉淀。沉默 17h 是常态，**不是漏报**
- **置信度**：[置信度: 75%]（从 run_count、文件 mtime、heartbeat-state.json 三处交叉验证）

### 评分
- score: 75 → 75（稳定）
- trend: stable

### 行动
- 无紧急行动
- 下次抽查：HB-150（每 3 次）
