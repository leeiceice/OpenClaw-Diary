# Cron 管理领域经验

> 来源：自 2026-05-15 以来 cron 维护过程中的踩坑与规范提炼。
> 写入时间：2026-06-05 15:35（小龙虾）

---

## 1. 路径 Path("~/...") 不展开陷阱（2026-06-05 立）

**症状**：脚本里写 `Path("~/.openclaw/workspace/memory")`，永远找不到文件，脚本一直说"⏭️ 文件不存在"。

**根因**：`Path("~/...")` 把 `~` 当成普通目录名，**不会自动调用 `expanduser()`**。

**证据**：
```python
>>> p = Path("~/.openclaw/workspace/memory")
>>> p.parts
('~', '.openclaw', 'workspace', 'memory')  # ~ 是普通目录！
>>> p.resolve()
/cwd/scripts/~/.openclaw/workspace/memory  # 实际指向 cwd 下的 `~/` 子目录
```

**修法**：永远用 `Path("~/...").expanduser()`，或直接用绝对路径。

**触发条件**：所有用 `Path()` 拼接路径的脚本（不只是 cron）都要查一遍。

**状态**：
- ✅ `scripts/memory_importance_scorer.py`（修）
- ✅ `scripts/memory_auto_refine.py`（修）
- ⏳ 其他脚本待巡检：`grep -rn 'Path("~/' /root/.openclaw/workspace/scripts/`

---

## 2. systemEvent 调 shell 脚本的隐含陷阱（2026-06-05 立）

**症状**：cron 跑通 `lastRunStatus: ok`，但飞书群没收到消息。

**根因**：systemEvent 只把 stdout/系统输出注入主会话，**不投递消息**。shell 脚本如果只 echo 不调 `openclaw message send` / `curl feishu`，**永远不送达**。

**反直觉**：`lastDeliveryStatus: "not-requested"` 在 systemEvent 模式下是**正常状态**，**不等于"消息已送达"**。

**正例**（自包含推送）：
```bash
MSG=$(bash /root/.openclaw/workspace/scripts/daily-briefing.sh 2>&1)
openclaw message send --channel feishu \
  --target chat:oc_xxx --message "$MSG"
```

**反例**（只生成不推送）：
```bash
bash /root/.openclaw/workspace/scripts/daily-briefing.sh  # 只 echo
```

**验证步骤**：
1. 改完 cron，先 `cat <script> | tail -20` 看脚本末尾是否有发送动作
2. 没有 → 加 `openclaw message send` 或 `curl` 调飞书
3. 有 → `cron run` 手动触发，看飞书群

---

## 3. cron 失败的 4 类根因（2026-06-05 整理）

| 类别 | 表现 | 修法 |
|------|------|------|
| **prompt 过短** | agentTurn 14s 退出，consecutiveErrors 6+ | 补全 20+ 行任务指令 |
| **model 拼写错** | `Unknown model: xxx` | 改回 `deepseek/deepseek-v4-flash` |
| **timeout 不足** | `cron: job execution timed out` (600s) | 改 systemEvent 或 timeout≥600s |
| **shell 脚本无推送** | lastDeliveryStatus not-requested | 加 `openclaw message send` |

**诊断顺序**（Lee 早上教的）：
1. 看 `lastRunStatus` 是不是 `error`
2. 看 `lastError` 字符串 → 命中 4 类哪一类
3. 看 `lastDiagnostics` 详细堆栈
4. 必要时翻 `memory/cron-retry.log` 看批量失败

---

## 4. 看到批量失败不要立刻反推（2026-06-05 立）

**反面案例**：早上看到 `cron-retry.log` 里 `FailoverError: Token Plan 限流` → 反推"记忆系统崩了"。
**实际**：那些是别的 cron（Self-Improving 周报、PARA-Inbox）的历史错误，**与每日记忆无关**。

**教训**：
- 看到 `cron-retry.log` 大量错误时，**先列涉及哪些 cron**
- 不要一句话反推为"全系统崩"
- 同一份 log 里的错误可能来自不同根因

---

## 5. 记忆提炼 cron 的健康指标（2026-06-05 立）

| 指标 | 健康值 | 异常表现 |
|------|--------|----------|
| `memory/YYYY-MM-DD.md` 文件存在 | 每天有 | 缺失 |
| `memory/YYYY-MM-DD.md` 文件大小 | 当天有大事时 1K-8K | 全天 < 200B |
| MEMORY.md 每月新增条目 | ≥5 条 | 0 条 |
| `memory_auto_refine.py` 退出码 | 0 | 1 |

**关键认知**：
- memory 文件**不是每天机械生成** — 没新教训/规范/决策时**就该是空的**
- 6/2 写满 1.4K、6/3 写满 8K 是因为**真有大事件**
- 6/4、6/5 缺失 = 那天**没东西可记**，不是出 bug
- 但**有东西的时候必须主动记**（不是等 Lee 质问）

---

## 6. cron 修改的正确姿势（沿用 MEMORY.md v3.4）

- ✅ 用 `openclaw cron update` 工具
- ❌ 不要直接编辑 `jobs.json`（runtime store 不会自动同步）
- 验证：改完后 `cron get <id>` 看 `updatedAtMs` 是否变化
