# 记忆 + 搜索系统健康规范

> 来源：2026-06-05 下午 Lee「向量库、记忆系统、搜索系统，一定要及时保证健康运行」+ 当日 E2E 协作修复实践
> 写入时间：2026-06-05 16:12（小龙虾）

---

## 1. 三大系统覆盖范围

| 系统 | 主要脚本 | 跑通标志 | 数据源 |
|------|----------|----------|--------|
| **向量库** | `scripts/vector_store.py` | `stats` 跑通 + 实体数 ≥ 昨日 95% | `data/vector_store.db` |
| **记忆系统**（写入层）| `scripts/memory_importance_scorer.py` + `scripts/memory_auto_refine.py` | 不抛异常 + 写入 MEMORY.md | `MEMORY.md` + `memory/YYYY-MM-DD.md` |
| **搜索系统**（协作层）| `scripts/memory_search.py` | E2E 命中真实信号 | MEMORY.md / memory/* / self-improving/* |

**核心原则**：三个系统是**串联协作**的 — 写入 → 索引 → 搜索。任何一环坏掉，agent 拿到的是错误信号。

---

## 2. 写入层（memory_importance_scorer + memory_auto_refine）

### 健康指标
- ✅ 跑通不抛异常
- ✅ 能识别高价值块（scorer 输出有 "## ..." 计数）
- ✅ 能追加到 MEMORY.md（refine 报 "已追加 N 条"）
- ✅ 自动去重（"所有条目已在 MEMORY.md 中，跳过"）

### 常见故障
| 症状 | 根因 | 修法 |
|------|------|------|
| `⏭️ 今日 memory 文件不存在` | `Path("~/...")` 不展开（2026-06-05 修）| `.expanduser()` 或绝对路径 |
| 脚本 AttributeError | 写时区用 `datetime.now()`（naive）| `datetime.now(CST)` from `_timezone` |
| MEMORY.md 无限增长 | 没去重 | 提炼前查 hash；refine 已有 hash 跳过 |

### 自检方法
```bash
# 1. 任意 cwd 跑（验证 Path 修对了）
cd /tmp && python3 /root/.openclaw/workspace/scripts/memory_importance_scorer.py
cd /tmp && python3 /root/.openclaw/workspace/scripts/memory_auto_refine.py
# 2. 预期：输出"已追加 N 条" 或 "所有条目已在，跳过"
```

---

## 3. 向量库（vector_store）

### 健康指标
- ✅ `stats` 跑通
- ✅ 实体数 ≥ 昨日 95%（允许 5% 漂移）
- ✅ `vector_store.db` 大小稳定（< 100MB）
- ✅ `search(query)` 返回 `vec_score > 0` 的真实值

### 常见故障
| 症状 | 根因 | 修法 |
|------|------|------|
| `Unknown model: xxx` | API Key 失效或模型名错 | 查 `.env` 重新配 |
| `stats` 卡住 | index 损坏 | 删 `vector_store.db` 重建 |
| 实体数突掉 50% | cron 没跑 / sync 脚本挂 | 看 `cron-retry.log` |

### 自检方法
```bash
python3 /root/.openclaw/workspace/scripts/vector_store.py stats
# 预期：返回 { entities: N, relationships: M, db_size: X MB }
```

---

## 4. 搜索系统（memory_search — 端到端协作层）

### 健康指标
- ✅ E2E 测试通过：写 unique marker → 搜 → 命中真实 snippet
- ✅ score 字段有意义（BM25 真实分 1-30 范围，不是 0.01-0.04 拉平值）
- ✅ RRF 融合层有 `_rrf_score` 字段记录排序用分
- ✅ `fused_by` 字段标识融合路径（`rrf` / `bm25-only`）

### 已知 Bug 与修法（2026-06-05 立）

#### 🐛 Bug 1: RRF 把 score 压扁
- **症状**：所有结果 score 都在 0.01-0.04，agent 无法区分真命中 vs fallback
- **根因**：`fuse_bm25_and_vector()` 始终套 RRF 公式 `1/(60+rank)`
- **修法**：
  - RRF 分数进 `_rrf_score`（仅用于排序）
  - `score` 字段保留 `BM25 + vec_score` 真实加权
  - `score` 排序也按 `_rrf_score`（保持 RRF 排序优势）

#### 🐛 Bug 2: vec_sources=空时还套 RRF
- **症状**：即使向量库静默失败，所有结果都走 `rrf` 路径
- **修法**：`fuse_bm25_and_vector` 函数开头短路 — `vec_sources=[]` 时直接返回 BM25 结果，加 `_fused_by: bm25-only`

#### 🐛 Bug 3: 字段不一致
- **症状**：vec 路径有 `bm25_score/vec_score/_bm25_rrf/_vec_rrf`；BM25-only 路径没有
- **修法**：统一字段，两个路径都返回完整字段集

### E2E 测试方法（必跑，每周一次）

**测试用例 1 — 唯一 marker 命中：**
```python
import subprocess, json
# 1. 写唯一 marker
marker = f"e2e_test_qzx_{datetime.now(CST).strftime('%Y%m%d_%H%M')}"
with open('MEMORY.md', 'a') as f:
    f.write(f"\n## [E2E-TEST] {marker}\n  - 验证内容：搜索系统能识别刚写入的内容\n")
# 2. 搜
result = json.loads(subprocess.check_output(
    ['python3', 'scripts/memory_search.py', marker]
))
# 3. 验证第一名
top = result['results'][0]
assert top['path'] == 'MEMORY.md', f"未命中 MEMORY.md: {top['path']}"
assert top['score'] > 5, f"score 过低（{top['score']}）— RRF 拉平 bug 重现"
# 4. 清理
subprocess.run(['python3', '-c', f"import re; ..."])
```

**测试用例 2 — 已知问题命中：**
```python
# 搜 <RRF_QUERY> (Path expanduser 脚本 bug) → 第一名应该是 cron-management.md
```

**测试用例 3 — 跨文件命中：**
```python
# 搜 <DELIVERY_QUERY> (is_requested 不等于) → 第一名应该在 cron-management.md
```

### 失败应对
| 症状 | 行动 |
|------|------|
| 写 marker 后搜不到 | 看 `total_indexed` 是否增加；不增 → 索引同步问题，重建 |
| 第一名 score < 1 | RRF bug 重现 → 检查 `fuse_bm25_and_vector` 是否还走 RRF |
| `fused_by=bm25-only` 但 vec 应有结果 | 向量库挂了 → `vector_store.py stats` 排查 |

---

## 5. 监控与护栏 cron

| 频率 | 工具 | 触发 | 推送 | 状态 |
|------|------|------|------|------|
| **每小时** | `52f5f99e heartbeat-maintenance` | 0 * * * * | 静默（异常才推安全群）| ✅ 已有 |
| **每天 7:30** | `bc0ff9bf daily-health-check` | openclaw status | 静默（异常才推进化群）| ✅ 已有 |
| **每天 8:00 / 12:30** | `823a779c / f92708f2` 记忆提炼 | memory_*.py | 静默 | ✅ 已有 |
| **每天 9:00** | `c1f98636 向量库稳定性汇报` | vector_store.py stats | 静默 | ✅ 已有 |
| **每周一 10:00** | `7a4d0ef9 weekly-cron-audit` | cron 列表健康 | 推安全群 | ✅ 已有（6-5 修推送）|
| **每周日 18:00** | `memory_search_e2e_weekly`（**新建**）| E2E 3 用例 | 推进化群 | 🆕 2026-06-05 立 |

---

## 6. 出问题的标准动作

1. **看到 3 个系统任何一个跑不通**：
   - 不立刻反推根因
   - **先列最近 24h 涉及哪些 cron / session**
   - 看 `memory/cron-retry.log` 批量错误
   - 用 `git log --since=24h` 看最近改动

2. **修完后必须 E2E 验证**：
   - 写测试数据 → 跑相关脚本 → 验证真实输出
   - 不只看"没报错" = 健康

3. **把新发现的 bug 模式写进本文件**：
   - 不重复犯同一个错
   - 修法 + 触发条件 + 验证步骤

---

## 7. 待定项（Lee 16:09 待讨论）

- ⏸️ **HEARTBEAT.md 的 "BM25 RRF 全 0.5 → 短路检查" 规则**：
  - 决定是否在 HEARTBEAT 文档加这一条
  - 决定心跳脚本是否自动检测 `_fused_by` 字段
  - Lee 16:09 说"前两项处理完再讨论"，**未执行**

---

_版本：1.0 | 最后更新：2026-06-05 16:12 | by 小龙虾（首次立规范）_
