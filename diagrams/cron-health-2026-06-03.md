# Cron 稳定性自查报告

**检查时间**: 2026-06-03 16:55 CST
**检查者**: 🦞 小龙虾
**检查范围**: 38 个 cron（36 enabled + 2 disabled）

---

## 1. 总览

| 指标 | 值 |
|------|-----|
| 总 cron 数 | 38 |
| enabled | 36 |
| disabled | 2 |
| model 分布 | V4-Flash: 34 / M3: 1 / (none): 3 |
| 最近 7 天失败率 | 17.3%（基于 cron-retry-monitor 历史） |

---

## 2. 健康度评分

🟡 **黄灯**（70-89分）：总体可用但有结构性问题

| 维度 | 分数 | 状态 |
|------|------|------|
| model 字段配置 | 95/100 | 3 个 cron 缺 model，1 个用了 V4-pro（已修） |
| timeout 设置 | 85/100 | 大部分 300s，少数 60-120s 可能不足 |
| 错峰执行 | 90/100 | 已错开 30 分钟 |
| 失败恢复 | 60/100 | cron-retry-monitor 自身在超时报错 |
| 推送送达 | 85/100 | 偶有 "Unsupported channel" 错误 |

---

## 3. 真实失败清单（来自 cron-retry-monitor 历史）

### 3.1 重复失败问题（高频）

**1. cron-retry-monitor 自身 4 连超时**（最近 4 次执行）
- 时间：2026-06-03 12:46~13:56
- 错误：`cron: job execution timed out (last phase: model-call-started)`
- duration：300s（timeout 顶到上限）
- 含义：DeepSeek V4-Flash 慢，300s 不够
- **影响**：这个监控如果超时，其他失败的 cron 不会被自动重试

### 3.2 偶发失败（已自动恢复）

- Session lock 冲突（5-7 次/月）：`EmbeddedAttemptSessionTakeoverError`
- Model 拼写错误（5 月一批，已修）：`deepseek-flash/deepseek-v4-flash`
- 已删除模型引用（5-6 月清理前）：`minimax-portal/MiniMax-M2.7`
- Gateway 重启中断：偶发

### 3.3 配置隐患

| Cron | 隐患 |
|------|------|
| 对话-Ontology管道 | model=(none) — 走默认路由会失败 |
| 每日Ontology图谱同步 | model=(none) — 同上 |
| 偏差传感器周扫描 | model=(none) — 同上 |

---

## 4. 修复建议

### 高优
1. **cron-retry-monitor 加 timeout 到 600s**（300s 明显不够，4 连超时）
2. **3 个 model=(none) cron 显式补 V4-Flash**
3. **每周日限流的 minimax 任务** — 5/31 周末 6 个 cron minimax 限流，要切 V4-Flash

### 中优
4. **加 cron 健康检查 cron**（weekly-cron-audit 已存在但要确认它有效）
5. **5/31 那次 minimax 套餐限流后**，所有 minimax 用法要评估是否切 V4-Flash

### 低优
6. 给 2 个 disabled cron 标注原因

---

## 5. 结论

**总体稳定但需要 1 个紧急修复**（cron-retry-monitor timeout）。其他问题都已自动恢复或在历史。

_检查完成于 2026-06-03 16:55 by 小龙虾_
