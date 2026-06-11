---
name: "session-context-compressor"
description: "任务结束时自动压缩主 session 上下文：轻量摘要 + 超阈值时自动切 session 迁移"
---

# Session Context Compressor 🦞

自动压缩主 session 上下文，防止随时间膨胀。

## 设计

### 两层架构

| 层 | 触发条件 | 动作 | 文件 |
|----|---------|------|------|
| **L1 轻量** | 每次任务结束时 | 写结构化摘要 + 更新状态 | `compressed-state-latest.json` |
| **L2 迁移** | context > 15% (150k/1M) | spawn 新 session + 加载摘要 | `snapshot-{timestamp}.json` |

### L1 写入格式

`proactivity/session-compress/compressed-state-latest.json`:

```json
{
  "timestamp": "2026-06-11T11:25:00+08:00",
  "source_session": "agent:main:main",
  "start_ctx_ratio": 0.06,
  "end_ctx_ratio": 0.08,
  "delta": 0.02,
  "models_used": ["deepseek/deepseek-v4-flash", "minimax/MiniMax-M3"],
  "tasks_completed": [
    {
      "task": "简短描述完成任务",
      "key_decisions": ["决策1", "决策2"],
      "outputs_to": ["飞书进化群", "L0"],
      "tokens_used": {"in": 5500, "out": 644}
    }
  ],
  "pending_context": {
    "open_questions": [],
    "waiting_for_lee": []
  }
}
```

### L2 迁移流程

当 `session_status` 返回 context 占比 ≥ 15% 时：

1. **冻结快照**：写 `snapshot-{timestamp}.json` 包含完整会话摘要
2. **spawn 新 session**：挂载 snapshot 文件 + 压缩控制指令
3. **通知 Lee**：新 session 已创建，旧 session 可查看

## 集成方式

挂在 **AGENTS.md 任务收尾检查** L0 写入判断之后：

```
- [ ] **session 压缩**：任务完成后写 compressed-state-latest.json
- [ ] **context 阈值检查**：如果 context ≥ 15%，执行 L2 迁移
```

## 触发条件

**每个任务结束时自动执行**（不是每轮消息），定义见 AGENTS.md 收尾检查：

- 一个完整任务完成（比如"收集汇总报告写完了"）
- 有产出的对话段落结束（比如"方案确认了"）
- 不触发：单轮问答、闲聊、简单确认

## 文件结构

```
proactivity/session-compress/
├── compressed-state-latest.json   # L1: 当前会话状态（持续更新）
├── snapshots/                      # L2: 历史快照
│   ├── snapshot-2026-06-11T112500+0800.json
│   └── ...
└── README.md                       # 使用说明
```

## 注意事项

- L2 迁移依赖 `sessions_spawn` + 挂载文件，需测试
- context 阈值 15% 是初始值，可根据实测调整
- 旧 session 不删除，只归档可查

---

_版本：1.0 | 2026-06-11 | by 小龙虾_
