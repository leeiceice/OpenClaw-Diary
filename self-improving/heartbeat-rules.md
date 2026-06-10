# Heartbeat Rules — Self-Improving 维护 🦞

> heartbeat 每小时调用一次，执行 Self-Improving 系统的日常维护。

## 规则

### 1. 检查文件变更 → 更新 index.md

```bash
# 检查 self-improving/ 下所有 .md 文件的修改时间
# 如果有文件更新时间晚于 index.md 最后更新时间 → 更新 index.md
```

**执行条件**：任何 .md 文件变更后

### 2. 压缩过大的文件

触发条件：文件 > 100KB

**待压缩目标（观察）**：
- `~/self-improving/corrections.md`（持续增长）
- `~/self-improving/memory.md`
- `~/self-improving/domains/` 下的积累型文件

### 3. 更新 heartbeat-state.md

```bash
echo "last_heartbeat: $(date -Iseconds)" >> ~/self-improving/heartbeat-state.md
```

**执行条件**：每次 heartbeat 触发

---

## 待检查问题（2026-06-02）

- [ ] corrections.md 连续 6 天无新写入 → 反馈回路断链
- [ ] graph.jsonl 连续 24h 无新数据 → ontology pipeline 空转
- [ ] scenes 12 天无新增 → L2 Scene 反馈回路断链
- [ ] heartbeat-score 46，长期低于 70 健康线

---

_版本：1.0 | 2026-06-02 | by 小龙虾（重建 heartbeat-rules.md）_