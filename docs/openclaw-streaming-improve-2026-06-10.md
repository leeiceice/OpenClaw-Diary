# 🦞 OpenClaw vs hermes-lark-streaming 改进报告

**日期**：2026-06-10 00:35 CST
**对比对象**：OpenClaw（小龙虾/腾讯云） vs hermes-lark-streaming（小马/Lee PC）
**文档依据**：小马技术文档 v1.0（13.7KB）+ OpenClaw docs/feishu.md

---

## 一、现状对比

### OpenClaw 飞书流式（小龙虾这边）
| 功能 | 状态 | 说明 |
|------|------|------|
| 飞书流式卡片 | ✅ `streaming: true` | 开/关，1 个参数 |
| blockStreaming | ❌ 默认关 | 等 complete block 再 flush |
| 工具调用实时显示 | ❌ 无 | 看不到"正在调用 XXX" |
| 思考过程显示 | ❌ 无 | 看不到 thinking/reasoning |
| CardKit 错误重试 | ❌ 无 | 1663/300000 直接失败 |
| 消息队列/follow-up | ❌ 无 | 连续消息行为不确定 |
| hook 系统 | ❌ 无 | 不支持自定义注入点 |
| Cron 静态卡 | ✅ 有 | `on_cron_deliver` 类型 |
| 卡片去重 | ❌ 无 | 同 chat_id 可能重复投 |

### 小马 hermes-lark-streaming（Lee PC 端）
| 功能 | 状态 | 说明 |
|------|------|------|
| 13 个 lifecycle hook | ✅ | AST 注入到 `run.py` |
| ANSWER 打字机 | ✅ | 100ms FlushController 节流 |
| TOOL 工具调用图标 | ✅ | 实时显示调用中/完成/失败 |
| THINKING/REASONING | ✅ | 显示思考过程 |
| FOLLOWUP_COMPLETE/RESULT | ✅ | queue 模式 |
| CardKit 错误重试 | ✅ | 1663/300000 |
| Cron 卡片去重 | ✅ | 同 chat_id 去重 |
| 三件套安装/验证 | ✅ | uninstall → install → verify |

---

## 二、架构差距根因

**不是"功能少"的问题，是架构设计不同**：

| 维度 | OpenClaw | 小马 hermes-lark-streaming |
|------|---------|---------------------------|
| **设计目标** | 多 Agent 通用 gateway | 单用户流式体验优化 |
| **定制方式** | config 参数（streaming: bool）| AST 注入 +13 hook |
| **可观测性** | 黑盒（config 只剩 true/false）| 白盒（13 个可观测注入点）|
| **平台** | 跨平台（Linux/Windows/macOS）| Windows only（Hermes）|
| **升级影响** | config稳定 | Hermes update 冲 markers |

**核心差距**：OpenClaw 的 feishu streaming 是一个 **"开关"**（true/false），小马的 是一个 **"系统"**（13 个可编程 hook）。

---

## 三、改进优先级

### 🔴 P0 — 能做且影响大

#### P0#1：CardKit 瞬态错误重试（1663 / 300000）
**现状**：CardKit API报 1663/300000 直接失败，用户看不到消息
**小马方案**：错误 → 等待 → 重试 → 最多 3 次
**OpenClaw 能不能做**：需要查 OpenClaw 飞书 connector 的 CardKit 调用代码
**实现位置**：`openclaw/plugins/feishu-connector/` 或 channel 实现层
**工作量**：中（找到 CardKit 调用位置，加 try-catch + retry）

#### P0#2：工具调用实时显示（TOOL hook 等效功能）
**现状**：工具调用期间用户在飞书看不到任何反应，感觉"死了"
**小马方案**：`controller.on_tool_update()` → 显示"🔧 调用 XXX 工具中..." → 完成/失败
**OpenClaw 能不能做**：需要流式卡片支持 **多消息块同时更新**（一张卡，toolCall 块动态变化）
**工作量**：大（OpenClaw 卡片模型需要支持"工具状态更新"这个新块类型）
**注意**：飞书 CardKit v2 支持在同一个 card message 上 PATCH 更新——技术可行

---

### 🟡 P1 — 能做但影响有限

#### P1#1：Cron 卡片去重（同 chat_id + content 哈希）
**现状**：cron 推送如果失败重试，可能重复投到同一个群
**小马方案**：`_deliver_result` 里加 dedup map，相同 `(chat_id, content_hash)` 跳过
**OpenClawa 能不能做**：能做，工作量小
**工作量**：小（加一个 dedup 缓存就行）

#### P1#2：blockStreaming 增强（completed-block flush）
**现状**：`blockStreaming: false`，等完整回复才发
**小马方案**：有 thinking块时先显示 thinking，等 ANSWER 开始再切换
**OpenClaw 能不能做**：当前 `blockStreaming: true` 已经支持部分场景，但缺少"thinking 先显示"的逻辑
**工作量**：中（需要在流式处理层识别 thinking block，先单独发一个 card）

---

### 🟢 P2 — 做了更好但非必须

#### P2#1：飞书卡片 streaming 状态指示器
**现状**：流式打字中，用户不知道是"在输入中"还是"卡了"
**小马方案**：打字机效果本身提供了状态，不需要额外 UI
**评估**：打字机效果已足够，不需要额外改进

#### P2#2：13 hook 系统
**评估**：架构改动太大（需要重新设计 gateway hook系统），投入产出比低
**建议**：如果未来 OpenClaw 要做，应该用 **插件机制** 而不是 AST 注入（AST 注入跟 Hermes 耦合太紧）

---

## 四、不适合 OpenClaw 的（小马特有）

以下功能**不适合**移植到 OpenClaw：

| 功能 | 原因 |
|------|------|
| AST 注入到 `run.py` | OpenClaw 是跨平台多 channel，AST 注入跟 Hermes 耦合 |
| FOLLOWUP_COMPLETE/RESULT | 需要 Hermes queue 模式，OpenClaw 无对应架构 |
| 三件套（certifi+AST+editable）| Windows/Hermes 特定，OpenClaw 是 Linux |
| MSYS bash grep workaround | Windows 特定问题 |

---

## 五、务实结论

**能快速做**（1-2h）：
- Cron 卡片去重（P1#1）

**值得做但需要开发**（1-2 天）：
- CardKit 错误重试（P0#1）
- blockStreaming thinking 先显示（P1#2）

**架构改动太大**（不建议）：
- 13 hook 系统（P2#2）
- TOOL 实时显示（P0#2）— 技术可行但工作量大

**最值得做的 1 件**：
**CardKit 瞬态错误重试（P0#1）**——投入小（1-2h），直接解决"流式消息突然中断"的高频投诉场景。

---

## 六、反信息茧房自检

- **我没有 Hermes 安装**——改进报告基于文档分析，不是"我会做"
- **"能做"不等于"我要做"**——需要 Lee 拍板才执行
- **架构差距是设计选择，不是缺陷**——OpenClaw 通用 vs 小马单用户优化，不能直接比
- **P0#2 TOOL 显示投入产出比低**——我主动降级为 P2，避免过度承诺
- **务实结论**——只推1 件（P0#1 CardKit 重试），不列一堆"可以做"