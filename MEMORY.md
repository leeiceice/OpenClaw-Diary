# MEMORY.md — 长期记忆索引 🦞

> 本文件是索引，不是内容库。所有实质性内容都在专题文件里。
> 每条索引约 150 字符，概括主题 + 指向文件路径。

---

## 用户信息
- **user**: Lee，福州台江区，Asia/Shanghai，仅接受「Lee」
- → 详见：USER.md

## 三 Agent 协作
- **小龙虾**（我）→ 腾讯云 OpenClaw；飞书 open_id: ou_2afb013d7a3b01d96ca4218b22e2ecd8
- **小马**（xiaoma-hermes）→ Lee PC 本地；飞书 open_id 待补
- **仓库**：小龙虾 → xiaolongxia-openclaw / 小马 → xiaoma-openclaw
- **三端分工**：小龙虾跑服务器脚本/cron，小马跑 PC 端；Obsidian 共享，GitHub 备份
- **日记生成 cron（e44d151d）**：每日 22:00，**小龙虾**负责（2026-06-07 小马移交）；健康检查（63bb338f）22:30 兜底
- **互惠约定**：发现问题主动说，不各自闷头改

## 协作规范

→ 详见：**COLLAB.md**（任务确认流程 / 收藏流程 / 删除授权 / 日记 raw 优先规则 / 任务反馈规范）

## 群路由表与推送规则

→ 详见：**ROUTING.md**（精确 chat_id 表 / 判定启发 / 免 @ 直回 / chat_id 验证 / 故障排查）

## 定时任务规范与健康度

→ 详见：**CRON.md**（新建规范 / 健康度 timeout ≥600s / systemEvent 兜底 / lightContext / 模型分流 / Token Plan 参数）

## 系统架构

→ 详见：**ARCHITECT.md**（时区规则 / 三层记忆 / WAL 协议 / Gateway 端口 26301 / GitHub SSH 访问）

## MEMORY.md 维护红线

→ 详见：**MEMORY_POLICY.md**（清理频率 / 版本行规范 / 写作红线 / 4 步准入门槛）

## GitHub 协作约定

- **写前 pull**：`git pull --no-rebase origin main`（统一用法，不用 rebase）— 写入任何文件前必须先拉取远程最新状态
- **冲突处理**：检测冲突标记 → 提取冲突内容 → 追加为 `[系统/冲突待处理]` entry → 写回 → push → 告知 Lee；禁止静默覆盖
- **推送规则**：谁最后 push 谁负责解决冲突，先 rebase/fetch 再 push
- **分叉处理**：发现分叉（diverged）→ 立即 rebase → 再 push
- **增量推送**：不用 `git add -A`，精确指定文件
- 本地文件是唯一真相源，GitHub 仅作备份

## 微信读书
- **API Key**：`~/.openclaw/.env`，禁止硬编码上传 GitHub
- **.env 格式**：每 KEY 独立一行，连在一起导致解析错误
- **书名查找**：无 bookId → `/store/search?scope=10`
- **失效处理**：errcode -2010 → 微信读书 App → 我的 → 设置 → API Key 重新获取

## 每日书籍推荐
- 发送前生成卡片 → 发内容收集群
- 发送后立即 Obsidian 入库 + GitHub 同步
- **禁止**：只发送不复

## 进化里程碑

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
| 2026-06-10 | MEMORY.md 反模式纠偏（237 行）|
| 2026-06-11 | MEMORY.md 分拆 5 个专题文件；每段索引 ≤150 字符 |

**说明**：详细信息查 `git log` — MEMORY.md 只保留 anchor。

## 下次清理论目（暂搁置）

- 微信读书 API 细节 → 抽 SKILL.md
- 路由故障排查记录（5/27）→ 移 archive/
- 时区规则段（已入 ARCHITECT.md，剩余指针待验证）
- 三 Agent open_id 细节（已入本节，足够短）

---

_版本：4.0（major 结构重组）| 最后更新：2026-06-11 14:00 | by 小龙虾_
_变化：237 行 → 109 行（-54%）；拆出 COLLAB.md / ROUTING.md / CRON.md / ARCHITECT.md / MEMORY_POLICY.md_

## 每日提炼 (2026-06-11)
- timeout 600s + f7b860cc 改 8h + b9f146c4 改 4h
- f7b860cc：12 次/天 → 3 次 = 省 9×40K = **36 万 tokens/天**
- b9f146c4：24 次/天 → 6 次 = 省 18×45K = **81 万 tokens/天**
- **总节省 ~117 万 tokens/天 = 5h 配额 28%**（比 Lee 最初预期的 26 万高 4.5 倍）
- ✅ 进化群：om_x100b6d9538c6c494c018b8957533c1d
- ✅ 本日 L0 已写入
- 当前主 session（M2.7）回复是直接对话，**无法**用 lightContext
- 缺 lightContext（4）：**收集汇总报告 (287s)**、**午间记忆提炼 (201s)**、**早间记忆提炼 (177s)**、进化日报 (61s)

## 每日提炼 (2026-06-12)
- 推送安全群（chat_id=`oc_1f77586fc34cdacac8f43a4e9733eafc`），请 Lee 确认：
- 要不要建这目录 + 配置备份脚本？
- 还是备份本就在别的路径？
- 未自动创建，等 Lee 拍板（外部动作先确认，红线）
- ⏭️ `openclaw security audit`
- ⏭️ `openclaw tasks maintenance`
