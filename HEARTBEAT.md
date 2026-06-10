# Heartbeat — 全链路记忆系统健康检查 🦞

## 心跳检查顺序

### 第一步：Self-Improving 维护

运行 `~/self-improving/heartbeat-rules.md` 中的规则：
- 检查文件变更，更新 index.md
- 压缩过大的文件
- 更新 heartbeat-state.md

### 第二步：L0 当日记录存在性检查（2026-06-07 立）

```bash
TODAY=$(date +%Y-%m-%d)
if [ ! -f "memory/${TODAY}.md" ]; then
  echo "⚠️ L0 缺失: memory/${TODAY}.md"
  # 推安全群
else
  echo "✅ L0 存在: memory/${TODAY}.md"
fi
```

**判定逻辑**：
- 文件不存在 → ⚠️ 推安全群 `oc_1f77586fc34cdacac8f43a4e9733eafc`：「🦞 L0 缺口预警：${TODAY} 未写」
- 文件存在但 < 200 字节 → ⚠️ 同上（可能只是个空模板）
- 文件存在且 ≥ 200 字节 → ✅ 静默

**24h 去重**：同一日期只推一次，避免心躁。

**为什么要这一步**：
- 2026-06-06、06-07 连续 L0 缺口
- 根因："实时写入" 全靠手动，无任何机制保证
- L1 修复：心跳时强制检查 + 推送提醒（被动召回我写）

### 第三步：随手记抽查（每3次心跳一次）

检查 `proactivity/daily-working-log.md` 是否有今日事件：
- 有内容 → 确认是否需要合并到 memory
- 无内容 → 可选提醒 Lee 养成随手记习惯

**⚠️ 随手记不是 cron 的替代，是实时记忆工具。**

### 第四步：Cron 状态健康检查（2026-06-09 新增）

**调用**：`bash scripts/cron_health_check.sh`（已嵌入 l0_watchdog.sh，L0 正常路径顺带跑）

**检查维度**：
- `consecutiveSkipped > 3` → 静默跳过超阈值
- `lastError == "disabled"` → main session 入口冻结（dev_20260609_003 同源问题）
- `consecutiveErrors > 0` → 上一次执行失败

**输出**：
- 正常 → 静默通过（exit 0）
- 异常 → 写 `/tmp/cron_health_state_${TODAY}.json`，exit 1（l0_watchdog 拿到信号，HEARTBEAT 评分扣分）

**未动推送**：错报风险高（脚本容易出边界 bug），推送由独立 cron `cron-disabled-audit-daily` 每天 0:30 跑（严格 24h 去重）

**为什么这么设计**：
- HEARTBEAT 是高频检查（每小时），轮查用读、跳静默
- cron-disabled-audit-daily 是低频推送（每天一次），由 shell 脚本独立推送，严格 24h 去重
- 两层机制互不依赖、互不覆盖

**修复历史**：
- 2026-06-09 dev_20260609_003：发现 6 个 cron（ec85def5/5a222ec4/f7b860cc/c9310669/ab150a93/69e9d850）被 main session 入口冻结，全部静默跳过，failureAlert 不告警。**根因 = main session 不该作为 cron 入口**。

### 第五步：数据链路健康检查

依次检查以下路径是否通畅：

**A. 对话 → Ontology**
```bash
python3 scripts/conversation_to_ontology.py --dry-run
```
检查是否有新实体被提取。

**B. 本地向量搜索健康检查**

1. 向量 pipeline 畅通性：检查 `memory/ontology/graph.jsonl` 是否有新实体，24小时内有更新则向量索引需同步。（2026-06-09 修正：原 `graph.jsonl` 路径不全，实际是 `memory/ontology/graph.jsonl`）

2. L2 Scene 反馈回路：检查 `memory/deviations/scenes/` 是否有最近生成的 scene 块（24小时内）：
   - 有 scene → 确认 scene 状态已反写到 memory_search 的 confidence 评分
   - 无 scene → 确认 memory_search.py 内嵌的 scan 已正常调度

3. memory_sensor 活跃度：检查 `self-improving/corrections.md` 是否有新增记录，有则 L2 反馈正常。
   （2026-06-07 修正：原 `memory/deviations/corrections.md` 是孤儿文件，memory_sensor.py 写的是 `self-improving/corrections.md`）

4. BM25×vector RRF 融合：确认本地向量排序是否正常（vs 降级纯 BM25），检查 `scripts/memory_search.py` 配置。

   **RRF 健康判据**（2026-06-05 Lee 决策：加脚本级检测）
   - 跑 `python3 scripts/check_memory_search_health.py`（纯读 3 用例）
   - **score 字段 < 1.0 = RRF 拉平 bug**（立即标 ❌）
   - **所有结果 _fused_by=bm25-only 但 has_vector=true = 向量库异常**（标 ⚠️）
   - **任何用例失败 → 推安全群**（oc_1f77586fc34cdacac8f43a4e9733eafc）
   - 详见：`self-improving/domains/memory-search-health.md` 第 4 节

5. **Vector store mtime 陈旧检查**（2026-06-09 新增）：
   - 调用：`bash scripts/check_vector_store_freshness.sh`（已嵌入 l0_watchdog.sh）
   - 阈值：`mtime > 3 天` → 标 ⚠️
   - 输出：写 `/tmp/vector_store_freshness_state.json`，exit 1
   - **修复历史**：2026-06-09 dev_20260609_006 发现 vector_store.db 8 天未更新，根因 = `vector_store.py build` 无 cron 配套
   - 已有 cron `vector-store-daily-build` (id: `3502982c`)，`30 3 * * *` 每天 3:30 跑

6. **MiniMax Token Plan 5h 剩余检查**（2026-06-10 新增）：
   - 调用：`bash scripts/minimax_token_check.sh --quiet`（已嵌入 l0_watchdog.sh）
   - API：`GET https://www.minimaxi.com/v1/token_plan/remains`
   - 阈值：5h 剩余 < 50% 标 🟡 / < 30% 标 🟠 / < 10% 标 🔴
   - 输出：写 `/tmp/minimax_token_state.json` + `/tmp/minimax_token_alert.txt`
   - 推算公式：Plus ¥49/月 = 600M tokens/月，每 5h 周期 = 4.16M tokens
   - **使用场景**：Lee 23:55 反馈"5h/1500 次用光"，接入真实 API 查证

**C. Self-improving → Obsidian 归档**
检查 `self-improving/corrections.md` 最近是否有新增（24小时内）。

### 第六步：主动推送评估

如果发现以下情况，主动向 Lee 推送：

| 情况 | 推送目标 | 内容 |
|------|---------|------|
| 发现高频错误模式（同一错误3次/天） | 进化群 | "🦞 发现新错误模式：XXX，今天出现3次，建议..." |
| Ontology 新增实体超过 10 个/小时 | （静默） | — |
| 记忆系统状态异常 | 安全群 | "⚠️ 记忆系统检查未通过，请检查" |
| Lee 待办项有进展 | 进化群 | "📌 Lee 今天完成了：..." |
| 自我进化承诺未兑现（24h 内） | 进化群 | "🔄 还在等待 Lee 确认的事项：..." |

**同一问题不重复推送（24小时去重）**

更新心跳状态：
```bash
echo "last_heartbeat: $(date -Iseconds)" >> ~/self-improving/heartbeat-state.md
```

---

## 评分闭环（v3.0 新增）

每次心跳执行 **健康评分（0-100）**，并记录趋势：

### 评分维度

| 维度 | 分值 | 评分规则 |
|------|------|---------|
| **数据链路** | 30分 | Ontology + 向量 + BM25×vector RRF 全部通畅 |
| **Self-improving** | 20分 | `self-improving/corrections.md` 有新增记录得20分；机制完整但无新错误（6天以上空闲）得15分；机制损坏或文件丢失得0分 |
| **记忆系统** | 20分 | MEMORY.md / memory/ 索引正常，无过期条目 |
| **直觉状态** | 15分 | 直觉（30-59%）占比≥50% 得15分；经验（60-84%）占比≥30% 得15分 |
| **自我进化** | 15分 | 7天内有新的 skill 或规则更新 |

### 评分标准

| 分数 | 状态 | 行动 |
|------|------|------|
| **90-100** | 🟢 优秀 | 静默，记录到 heartbeat-state.json |
| **70-89** | 🟡 良好 | 静默，发现问题记录但不推送 |
| **50-69** | 🟠 警告 | 推送到安全群，建议检查 |
| **< 50** | 🔴 危急 | 立即推送到安全群，需 Lee 介入 |

### 评分记录格式

写入 `proactivity/heartbeat-state.json`：

```json
{
  "timestamp": "2026-05-27T08:00:00+08:00",
  "score": 85,
  "dimensions": {
    "data_pipeline": 30,
    "self_improving": 15,  // 机制完整，无新错误=空闲状态（正常）
    "memory_system": 20,
    "intuition_health": 15,
    "self_evolving": 0
  },
  "trend": "stable",
  "issues": []
}
```

### 置信度反馈回路（ECC 框架）

每次 HEARTBEAT 检查后，按以下流程处理：

**发现异常 → 记录为观察条目**（写入 `proactivity/daily-working-log.md`）：
```markdown
## 观察 [timestamp]
- 内容：[问题描述]
- 来源：heartbeat-实测
- 初始置信度：30%
- 修复状态：待验证
```

**修复后 → 更新置信度**（按 ECC 算法）：
- 成功修复 → 置信度 +15%（最高 70%）
- 失败 → 置信度 -20%（最低 10%）
- 实测验证来源 → 额外 +20%（已达知识级别可写 MEMORY.md）


**置信度 ≥ 60%** → 触发 /evolve 聚类检查
**置信度 ≥ 85%** → 触发 /promote 技能化检查

---

_版本：3.2 | 最后更新：2026-06-01 10:55 | by 小龙虾（置信度反馈回路对接ECC框架）_