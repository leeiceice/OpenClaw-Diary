# Cron 管理经验

## 核心规则
- 新建 cron 必须检查时间冲突，同一时间点只能一个推送
- 物理隔离：同一群同时间点至少隔 5 分钟
- 推送失败必须通知 Lee，不静默失败
- failureAlert.after 设为 9999（不重复推送，靠 monitor 重试）

## 超时处理
- lightclawbot 路由延迟 + 新闻脚本执行 → 需要较大 timeout
- 晨间简报：300s → 400s
- 健康检查：300s
- 进化日报提醒：30s → 120s

## 重试机制
- `cron-retry-monitor` 每 15 分钟检查所有 cron 状态
- 检测到 `lastRunStatus=error` 且 `consecutiveErrors>=1` → 等待 15 分钟后自动重试
- 重试延迟目的：避免与还在运行的原任务冲突

## 推送渠道（按群分类）
| 群 | 用途 |
|----|------|
| 日常安排群 | 晨间简报、日报提醒、日常安排 |
| 新闻群 | 新闻简报 |
| 学习监督群 | 午间学习提醒 |
| 进化群 | 进化日报、周报、Skill安全周报 |
| 安全群 | 健康检查、备份、月报 |
| 内容收集群 | 收集网页文章 |

## 新建 cron 清单
- [ ] 检查时间是否与现有 cron 冲突
- [ ] 确认推送群和用途
- [ ] 设置合理的 timeout
- [ ] 设置 failureAlert.after = 9999
- [ ] 测试触发一次确认正常

---

## ⚠️ 踩坑记录（从 memory/ 日志提炼）

### Cron 超时问题（2026-04-16）
- **问题**：多个 cron 任务 timeout（进化日报30s、晨间简报300s）
- **根因**：lightclawbot 路由延迟 + 新闻脚本执行时间不确定
- **教训**：cron 任务要给足够 timeout，新闻类任务至少 180s
- **解决**：晨间简报调至 400s，健康检查 300s，进化日报 120s

### Cron 推送失败一次性故障（2026-04-16）
- **问题**：日报提醒失败，显示 "Message failed"
- **根因**：一次性传输故障，非配置问题
- **教训**：先判断是持续性故障还是偶发故障，再决定是否调整配置
- **解决**：重新触发一次验证即可

### 多 cron 时间冲突（2026-04-16）
- **问题**：多个 cron 同时跑导致超时
- **教训**：同一群同时间点至少隔 5 分钟，物理隔离
- **解决**：日报 17:10，进化日报 17:20（错开 10 分钟）

### 升级后配置被覆盖（2026-04-15~16）
- **问题**：升级版本后配置文件每次被覆盖，plugins.entries 丢失
- **根因**：`lastTouchedVersion` 与当前版本不匹配，openclaw doctor 未正确执行
- **教训**：升级前必须备份，升级后必须验证 lastTouchedVersion
- **解决**：备份脚本 + SOP 流程

### 复用旧 cron 时的 channel 陷阱（2026-05-10）
- **问题**：cron-retry-monitor 复制的 cron 有 delivery: none + channel: last，但 lightclawbot 启用后多 channel 环境导致 "Channel is required" 错误
- **受影响的 cron**：喝水记录每日重置（20h+未运行）、openclaw-config-daily-backup（17h+未运行）
- **修复**：改 delivery 为 announce + 明确指定 channel:feishu + to:oc_xxx
- **预防**：新建 cron 时用 --announce --channel feishu --to oc_xxx；修改旧 cron 时优先检查 delivery.mode 是否为 none
- **教训**：openclaw cron edit 不验证 delivery 有效性，error 状态只在下一次 run 时才暴露
