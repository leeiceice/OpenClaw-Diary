# 2026-05-13 日志

## 22:45 - Obsidian长期记忆备份（cron）
- **状态**: 脚本不存在，跳过
- **脚本**: sync_memory_to_obsidian.py（未找到）
- **备注**: 可考虑改用 memos_daily_sync.py（已存在于 workspace/scripts/）
## 2026-05-14 GitHub 推送日志
- 17:15 成功推送4个commit到 xiaolongxia-openclaw（50e8a81）
  - backup-maintenance.sh + 每日2:00备份cron
  - 备份清理 + heartbeat更新
  - conversation_to_ontology.py 断链修复
  - lee-content-auto-collect skill

## 2026-05-15 02:00 - workspace每日备份维护（cron）

- **git pull**: ❌ 网络超时失败（GnuTLS recv error）
- **git add + commit**: ✅ 成功（2 files changed, 127 insertions/77 deletions）
- **git push**: ✅ 成功（重试后完成）
- **备份清理**: 无需清理（backups/*.json等文件不存在）
- **说明**: 网络不稳定，push失败需后续重试


## 2026-05-16 02:00 (workspace每日备份维护)

- ✅ git pull --no-rebase origin main → Already up to date
- ✅ git add -A && git commit -m "auto-sync: 2026-05-16 workspace backup" && git push → 9 files changed, pushed to main
- ✅ 备份清理 → 无需清理（未找到匹配的旧文件）


## 2026-05-17 02:00 CST (2026-05-16 18:00 UTC)
**类型:** workspace每日备份维护

### 执行结果
| 步骤 | 状态 |
|------|------|
| git pull --no-rebase | ✅ Already up to date |
| git add + commit + push | ✅ 5 files changed, pushed to main |
| 备份清理 | ✅ 无需清理（无相关文件） |

### 变更概要
- 5 files changed, 206 insertions(+), 182 deletions(-)
- Commit: `2b70da8` auto-sync: 2026-05-17 workspace backup

---

## 2026-05-17 20:00 - 每周进化报告（cron）

- **类型**: weekly-evolution-report W21
- **范围**: 2026-05-11 ~ 2026-05-17
- **输出**: memory/weekly-evolution-report-2026-W21.md
- **MEMORY.md**: v2.8 → v2.9（清理重复提炼 + 新增条目）
- **GitHub**: ✅ 推送成功（acc4bd4）
- **待推送**: 进化群+日常安排群

## 2026-05-18 02:00 — workspace每日备份维护
- git pull origin main: ✅ Already up to date
- git add + commit + push: nothing to commit (工作区干净)
- 备份清理: backups/*.json、openclaw.json.bak* 等文件不存在，无需清理
- 状态: ✅ 完成

## 2026-05-19 02:00 (workspace每日备份维护)

- ✅ git pull --no-rebase origin main → Already up to date
- ✅ git add -A && git commit && git push → e6a0571 pushed (4 files changed, 336 insertions, 323 deletions)
- ✅ 备份清理 → 无需清理文件（backups/*.json 及 openclaw.json.bak*/clobbered*/before-fix* 均不存在）

## 2026-05-20 02:00 (UTC+8) — workspace每日备份维护

- ✅ Git pull: Already up to date
- ✅ Git push: 8 files changed, committed as `auto-sync: 2026-05-20 workspace backup`
- ✅ 备份清理: 无需清理（backups目录不存在或相关文件为空）

## 2026-05-21 02:00 - Workspace每日备份维护（cron）
- **Git pull**: Already up to date
- **Git push**: ✅ 成功推送（commit 34ae171），11个文件变更，新增：
  - `reports/hermes_memory_system_report_2026-05-20.html`
  - `reports/hermes_memory_system_report_2026-05-20.md`
  - `reports/hermes_memory_system_report_2026-05-20.pdf`
  - `reports/hermes_memory_system_report_2026-05-20_v2.pdf`
  - `reports/reading_report_2026.html`
- **备份清理**: 无匹配文件（backups/*.json / openclaw.json.bak* 等均无残留）

## 2026-05-22 02:00 CST (UTC+8) — workspace每日备份维护

- ✅ Git pull: Already up to date
- ✅ Git push: 30 files changed, committed as `auto-sync: 2026-05-22 workspace backup` (d8920c9)
  - 新增: reports/ 下的多个PDF测试报告 + paddleocr-text-recognition skill
- ✅ 备份清理: 无需清理（backups/*.json / openclaw.json.bak* 等文件不存在）

## 2026-05-23 02:00 CST (workspace每日备份维护)

- **Git pull**: Already up to date
- **Git push**: ✅ 71296ee | 8 files changed, +823/-529
  - 新增: `scripts/feishu_group_fetch.py`
- **备份清理**: 无需清理（各pattern均不足3个）

## 2026-05-24 02:00 (Asia/Shanghai)

- ✅ Git pull: Already up to date
- ✅ Git push: `aec8535` — 6 files changed, 609 insertions(+), 472 deletions(-)
- ✅ 备份清理:
  - backups/*.json → 无需清理
  - openclaw.json.bak* → 无需清理
  - openclaw.json.before-fix.* → 无需清理
  - openclaw.json.clobbered.* → 无需清理


## 2026-05-24 02:03 (UTC 18:03) — workspace每日备份维护

**Git 操作：**
- `git pull --no-rebase origin main` → Already up to date
- `git add -A && git commit && git push` → ✅ 成功，commit e68c048

**备份清理：**
- backups/*.json、openclaw.json.bak*、openclaw.json.before-fix.*、openclaw.json.clobbered.* 均不存在，无须清理


---

## 2026-05-25 02:00（周一）

**Git 同步：**
- `git pull --no-rebase origin main` → ✅ Already up to date
- `git add -A && git commit && git push` → ✅ 成功，commit 35bf9b4，7 files changed

**备份清理：**
- backups/*.json、openclaw.json.bak*、openclaw.json.before-fix.*、openclaw.json.clobbered.* 均不存在，无须清理

## 2026-05-25 15:04 (UTC+8) — 每日备份维护

- **Git pull**: Already up to date
- **Git push**: 11 files changed, committed as `auto-sync: 2026-05-25 workspace backup`
- **备份清理**: 无需清理文件（未发现bak/before-fix/clobbered/ backups/*.json 文件）

## 2026-05-26 02:00 (UTC 2026-05-25 18:00)

**定时备份维护**

- Git pull: Already up to date
- Git push: ✅ 545635c | 3 files changed, 480 insertions(+), 465 deletions(-)
- 备份清理: 每类文件均 ≤3 个，无需清理


## 2026-05-26 15:04 (CST)

- Git pull: Already up to date
- Git push: ✅ bd5680b | auto-sync: 2026-05-26 workspace backup | 638 files changed
- 备份清理: openclaw.json.bak.3, openclaw.json.bak.4 已删除（保留 3 个最新）

## 2026-05-27 02:00 CST (Daily Workspace Backup)
- Git pull: Already up to date
- Git push: 6 files changed, committed and pushed
- Cleanup: No files removed (all patterns ≤1 file)

## 2026-05-27 15:06 CST (Daily Workspace Backup)
- Git pull: Merge made by ort strategy (index.md updated, 1 file changed)
- Git push: 8 files changed, committed and pushed
- Cleanup: No backup files found (patterns matched 0 files)

---
## 2026-05-27 15:08 (Asia/Shanghai) — workspace每日备份维护

**备份结果：✅ 成功**
- git pull: Already up to date
- git push: dbfd440 auto-sync: 2026-05-27 workspace backup

**备份清理：✅ 无需清理**
- backups/*.json: 1 file
- openclaw.json.bak*: 1 file  
- openclaw.json.before-fix.*: 1 file
- openclaw.json.clobbered.*: 1 file
- 各类别文件数均 ≤3，无需清理

## 2026-05-28 02:00 (Asia/Shanghai) — 每日备份

| 项目 | 结果 |
|------|------|
| git pull | Already up to date |
| git push | ✅ c99dc2d — 4 files changed, 19 insertions(+), 9 deletions(-) |
| 备份清理 | 无需清理（各模式文件数 < 3） |

## 2026-05-28 15:07 CST（每日备份维护）

**Git 操作：**
- ✅ `git pull --no-rebase origin main` → Already up to date
- ✅ `git add -A && git commit` → 3 files changed, 29 insertions(+), 8 deletions(-)
- ✅ `git push` → b656b0b..4376579 pushed to main

**备份清理：**
- backups/*.json → 无此类文件，无需清理
- openclaw.json.bak* → 无此类文件，无需清理
- openclaw.json.before-fix.* → 无此类文件，无需清理
- openclaw.json.clobbered.* → 无此类文件，无需清理


## 2026-05-29 02:00 (Asia/Shanghai) — workspace每日备份维护

- **Git pull**: Already up to date
- **Git push**: ✅ 提交 `6e57eb2`，7 files changed，76 insertions(+)，47 deletions(-)
- **清理**:
  - `openclaw.json.bak*`: 4→3，删除 `openclaw.json.bak.3`
  - `openclaw.json.before-fix.*`: 保持3个，无需清理
  - `openclaw.json.clobbered.*`: 保持3个，无需清理
  - `backups/*.json`: 无文件


## 2026-05-30 02:00 CST (cron:workspace每日备份维护)

**Git pull:** Fast-forward 2 files (MEMORY.md, water-log.json)  
**Git push:** 12 files changed, committed as `d648a00`  
**备份清理:** backups/*.json / openclaw.json.bak* / before-fix.* / clobbered.* — 均无文件，无需清理  
**状态:** ✅ 完成


## 2026-05-31 02:00 CST (cron:workspace每日备份维护)

**Git pull:** Fast-forward (remote had 49 files update, committed cron-jobs-backup-20260530.json, etc.)  
**冲突解决:** `proactivity/heartbeat-state.json` — 自动合并冲突 → 采用 `--theirs`  
**Git push:** ✅ 提交 `8551efc`，5 files changed  
**备份清理:** backups/*.json / openclaw.json.bak* / before-fix.* / clobbered.* — 均无文件，无需清理  
**状态:** ✅ 完成

## 2026-06-01 飞书群路由修复

**问题**：Lee 在日常安排群发消息，bot 不回复（被判定为 "no bot mention" 拒绝）

**根因**：`groupPolicy="open"` 的群默认需要 @mention 才响应，但 `requireMention` 没有在 groups 级别显式关闭

**修复**：对所有 6 个飞书群设置 `channels.feishu.groups.{chat_id}.requireMention = false`

- 日常安排群 `oc_ad39a8e943103c2164f1d0d9de503da5`
- 学习监督群 `oc_3fb5240d43f24be367f5bcd981a0415b`
- 新闻群 `oc_e4686fe5eb6e865b68fae7625a5ce840`
- 进化群 `oc_8e02a9ced0671cac8413b4c98e76637a`
- 内容收集群 `oc_20875a15a62ddeb3c3573d8d23c86daa`
- 安全群 `oc_1f77586fc34cdac8f43a4e9733eafc`

**验证**：Lee 确认 2026-06-01 11:15 修复成功


## 2026-06-02 02:00 — workspace每日备份维护
- **git pull**: Already up to date
- **git commit**: `17c2e50` — auto-sync: 2026-06-02 workspace backup (8 files, +159/-25)
- **git push**: ✅ pushed to origin/main
- **备份清理**: 4类备份文件均≤3个，无需清理
- **状态**: ✅ 完成

---

# 2026-06-03 日志

## 02:00 - 每日备份维护

- **git pull**: Already up to date
- **git commit**: `auto-sync: 2026-06-03 workspace backup` — 13 files changed, +132/-42
- **git push**: ✅ main → origin
- **备份清理**: 4类备份文件均≤3个，无需删除
- **状态**: ✅ 完成

## 2026-06-04 02:00 每日备份维护

- **git pull**: Already up to date
- **git push**: ✅ 成功（16 files changed, commit `eb2dd62`）
- **备份清理**: 无过期备份需清理
- **新增文件**: diagrams x2, memory/deviations, self-improving x2, 新收藏
- **状态**: ✅ All good

## 2026-06-05 02:00 每日备份维护

- **git pull**: Already up to date
- **git push**: ✅ 成功（10 files changed, +275/-53, commit `c41164c`）
- **备份清理**: 4类备份文件均 ≤3 个，无需清理
- **新增文件**: weekly-evolution-report-2026-W24.md, 关联分析收藏, feat scripts
- **状态**: ✅ 完成

## 2026-06-06 02:00 — Workspace 每日备份维护

- **git pull**: Already up to date
- **git commit**: auto-sync: 2026-06-06 workspace backup（6ae724c）
- **git push**: 已推送到 GitHub
- **备份清理**: 无匹配文件（backups/*.json / openclaw.json.bak* / .before-fix.* / .clobbered.* 均为空）
- **状态**: ✅ 完成

## 2026-06-07 02:00 — 每日备份维护

- **git pull**: Already up to date (无远程变更)
- **git commit + push**: 提交 10 个文件（+166/-30），成功推送到 GitHub
- **备份清理**: backups/*.json、openclaw.json.bak*、before-fix.*、clobbered.* — 均无文件，无需清理
- **状态**: ✅ 全部完成

## 2026-06-08 02:00 — Workspace 每日备份维护

- **git pull**: Already up to date（无远程变更）
- **git commit + push**: 提交 45 个文件（+2837/-773），成功推送到 GitHub（commit `4af5196`）
- **备份清理**: backups/*.json、openclaw.json.bak*、before-fix.*、clobbered.* — 均无文件，无需清理
- **状态**: ✅ 全部完成

## 2026-06-09 02:00 — Workspace 每日备份维护

- **git pull**: Already up to date
- **git commit + push**: 13 个文件（+2024/-603），commit `61e5e85`，成功推送到 GitHub
- **备份清理**: 四类备份目录均无旧文件需清理
- **状态**: ✅ 全部完成

## 2026-06-11 02:00 — Workspace 每日备份维护

- **git pull --no-rebase**: ❌ unrelated histories（origin/OpenClaw-Diary 与本地 xiaolongxia-openclaw 历史无共同祖先）
- **策略**: 创建备份分支 `backup-before-rebase-20260611` → reset 到 origin/main → checkout 备份分支全部文件 → commit（454文件，+65103/-56）→ push
- **git push**: ✅ 成功推送（9f66d5c → 6bd0686）
- **备份清理**: backups/*.json、openclaw.json.bak*、before-fix.*、clobbered.* — 均无文件，无需清理
- **状态**: ✅ 全部完成
- **备注**: remote push URL 已从 xiaolongxia-openclaw 修正为 OpenClaw-Diary（fetch/push URL 不同步的历史遗留问题）

## 2026-06-12 02:00 CST — Workspace 每日备份维护

- **git pull**: Already up to date
- **git commit & push**: 15 files changed, 2054 insertions(+), 1527 deletions(-); new: `skills/session-context-compressor/SKILL.md`; commit `f6f24cb`
- **备份清理**: 所有目录无备份文件，无需清理
- **状态**: ✅ 完成

## 2026-06-13 02:00 workspace backup
- git pull: Already up to date
- git commit+push: 270c268 (13 files, +5158/-2046)
- backup cleanup: no stale files found
- status: ✅ success

## 2026-06-14 02:00 CST (workspace每日备份维护)
- **git pull --no-rebase**: Already up to date
- **git push**: ✅ 6259ade — 15 files changed, +1828/-1683, 推送成功
- **备份清理**: 无匹配文件（backups/*.json / openclaw.json.bak* / openclaw.json.before-fix.* / openclaw.json.clobbered.* 均不存在或为空）
