# Successful Operation Patterns
> Extracted from last 7 days of active sessions (2026-05-17 ~ 2026-05-24)
> Source: 18 non-cron sessions + 50 cron sessions, 68 total active sessions, 2.25M tokens

---

## 📊 Top-Level Numbers

| Metric | Value |
|--------|-------|
| Total active sessions (7d) | 68 |
| Non-cron sessions | 18 |
| Cron sessions | 50 |
| Total tokens consumed | 2,251,741 |
| Avg tokens / session | 38,823 |
| Main session tokens | 127,901 |
| Highest-token session | Main (127.9K) / Feishu direct (117.8K) |

---

## 🔧 Session Profile

### Non-Cron Sessions (18)

| Type | Count | Typical Tokens | Notes |
|------|-------|---------------|-------|
| Main (微信/飞书桥) | 1 | 127,901 | 主要工作会话，含两个 dashboard 交互 |
| Dashboard sessions | 2 | 51K + 106K | 控制台操作 |
| Feishu DM (ou_e7a...) | 1 | 117,836 | Lee 飞书私聊 |
| Feishu DM (weixin bridge) | 1 | 39,085 | 微信群→飞书桥 |
| Feishu Groups | 6 | 23K-40K | 各目标群被动消息 |
| Subagents (spawned) | 4 | 20K-21K | 隔离任务执行 |
| Feishu DM (news/security) | 3 | 0 (passive) | 仅接收，无工具调用 |

### Cron Sessions (50)

~73% 为正常运行（每个 ~37K tokens），集中在晨报/日报/进化日报/健康检查/记忆提炼/Ontology同步等任务。

---

## ✅ 本周新增/确认的成功模式

### 1. Gateway 进程冲突诊断与修复（全新模式）

**触发**：systemd 管理的 Gateway 反复 crash loop（旧进程抢占端口）

**模式**：
```
诊断: 检查日志 → 发现 old PID + port conflict → 确认 systemd 外部遗留进程
修复: kill 旧进程 → systemd restart gateway → 验证稳定运行
```

**效果**：一次诊断解决持续数天的 crash loop ✅

**可复用**：任何端口冲突类故障 → 先杀旧进程再重启 systemd

---

### 2. 废弃插件全量清理 SOP（固化模式）

**触发**：memos-local-openclaw-plugin 已弃用

**模式**：
```
发现 → 全盘搜索残留文件 → 分类清理清单 → 分区删除 → 确认零残留
```

**效果**：从 `/usr/local/bin/openclaw` 到 `pnpm node_modules` 全面清理，无残留 ✅

---

### 3. Systemd Gateway 部署固化（全新模式）

**触发**：旧 wrapper 脚本改为 systemd 托管

**模式**：
```
诊断: systemd 失败因为是 wrapper 脚本而非二进制 → 改用直接路径
环境变量: systemd 没有 PATH 中的 node → 需要绝对路径或 EnvironmentFile
冲突处理: 旧进程占端口 → 杀旧进程再重启
```

**效果**：Gateway 由 systemd 稳定管理，自动重启 ✅

---

### 4. 子会话 (Subagent) 批量执行模式（已确认）

**触发**：多篇收藏文章需要并行处理

**模式**：
```
sessions_spawn × 4（每个子会话处理不同文章）
所有子会话用 deepseek-flash（低成本）
主会话通过 Memory Dreaming 合并结果
```

**效果**：4 个子会话 × 20K tokens 每个，总 token 比单会话处理更经济 ✅

---

### 5. Cron 任务 Token 稳定性（延续）

**每日 Cron 稳定消耗**：
- 晨报/日报/健康检查：~37K tokens/次
- 记忆提炼 + Ontology 同步：~38K tokens/次
- 书籍推荐：~28K tokens/次

**模式**：DeepSeek Flash 用于所有 cron 任务（配置固化），消耗稳定，无 Token 爆炸 ✅

---

### 6. 知识库连续编译（新模式）

**模式**：Wiki 编译持续推进，sources/ 38 个卡片，concepts/ 7 个概念卡片
**效果**：每月进步，无需额外资源投入 ✅

---

## 🏗️ 持续运行的工作流模式

### 🅰️ 公众号收藏模式
```
微信收到文章 → 自动收藏入库 → 关联分析 → Obsidian → GitHub
```
本周继续正常运行。

### 🅱️ 群聊被动响应模式
```
6 个飞书群 → 被动消息接收 → 仅群聊上下文回复 → 不主动推送
```
各群独立 session，不交叉污染。

### 🅲 日常 Cron 自动化环
```
07:00 晨报 → 09:30 书籍推荐 → 定时健康检查 → 12:30/23:30 记忆提炼
→ Ontology 同步（每8h）→ Obsidian 02:30 备份
```
全链路稳定运行。

---

## ⚠️ 可改进点（本周发现）

| # | 问题 | 根因 | 建议方案 |
|---|------|------|---------|
| 1 | **Gateway crash loop** | 旧进程残留 + systemd 端口冲突 | 部署时先杀旧进程 |
| 2 | **废弃残留** | memos 等弃用插件未及时清理 | 建立「废弃→全量清理」自动化脚本 |
| 3 | **message 存档被遗漏** | 微信消息存档承诺未执行 | 确认存档脚本正常触发（非 ~ 标记的消息也存档） |
| 4 | **session_miner.sh 脚本陈旧** | 尝试用 CLI 获取 history 失败 | 升级为直接解析 JSONL + sessions.json 元数据 |

---

## 📈 行为改进跟踪

| 行为 | 状态 | 本周表现 |
|------|------|---------|
| 回复前 memory_search | ✅ 固化 | 主 session 正常执行 |
| 任务先复述再确认 | ✅ 固化 | Gateway 诊断流程验证 |
| 飞书推送不硬编码 | ✅ 固化 | 从 TOOLS.md 读取 |
| ~ 消息立即存档 | ❌ 有遗漏 | 05-23 非存档 msg 未自动存档 |
| 主动检查 → 发现问题 → 修复 | ✅ 固化 | Gateway crash loop 诊断 |
| DeepSeek 仅 cron 使用 | ✅ 遵循 | 所有 cron 用 DeepSeek Flash |

---

*Generated: 2026-05-24 19:00 (weekly session miner, W24)*
