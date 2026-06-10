# 🦞 交接：飞书 IM 卡片 SVG 架构图绘制任务

> **交接时间**：2026-06-08 11:07 CST
> **交接方**：小龙虾（OpenClaw, model=minimax/MiniMax-M3）
> **接手方**：CC / Codex（按 Lee 指示）
> **任务状态**：3 版尝试 + 1 版测试，均未达 Lee 要求，**整体移交**
> **优先级**：🔴 高（Lee 显式说"效率太低"）

---

## 一、任务原始诉求

Lee 要求绘制 **2 张 SVG 架构图**，通过 OpenClaw message 工具发到飞书 DM（chat: `oc_8dd77f85fc71a5691e915184515d0cb2`，owner: `ou_e7a18238e21dede810d2e55ac91d3165`）。

### 图 1：5 个常驻核心框架骨干图
- **场景**：任务生命周期闭环
- **5 个核心框架**（按 Lee 06-08 筛选）：
  1. 任务确认红线（来源 SOUL.md）
  2. 反信息茧房 3 条（来源 AGENTS.md 05-22）
  3. 三层记忆（来源 MEMORY.md）
  4. 任务收尾 3 项（来源 AGENTS.md 06-07）
  5. 飞书推送路由（来源 MEMORY.md 06-03）
- **结构诉求**：闭环（Lee 问 → 处理 → 回报 → 沉淀 → 回到 Lee 问），不是平铺

### 图 2：搜索/检索架构图
- **场景**：5 层金字塔 + 评估反馈闭环
- **5 层**：
  1. L1 路由分发（关键词/语义/外部判断）
  2. L2 三路并行（A 本地记忆 / B 联网搜索 / C 外部资源）
  3. L3 子引擎（BM25 + Vector + tavily + web_search + web_fetch + feishu + Obsidian）
  4. L4 融合/汇总
  5. L5 评估反馈层（HEARTBEAT 4 步）
- **结构诉求**：3 路并行 + 横向支撑层（顶部路由、底部评估）

---

## 二、🪨 已踩的坑（务必避开）

### 坑 1：飞书 IM 卡片渲染管道 ≠ 浏览器 HTML 渲染

**症状**：在 OpenClaw message 工具发送的 SVG 附件，飞书 IM 卡片显示时**会丢内容**。
**已知表现**（按发生概率排序）：

| 元素 | 飞书 IM 卡片渲染 | 浏览器渲染 | 建议 |
|------|-----------------|-----------|------|
| 中文 `<text>` | ✅ 正常 | ✅ 正常 | 用 |
| `font-family="Microsoft YaHei"` | ✅ 正常 | ✅ 正常 | 用 |
| `font-family="PingFang SC"` | ❌ 乱码 | ✅ 正常 | **别用** |
| emoji 字符（🦞🔍📊） | ❌ 乱码 | ✅ 正常 | **别用** |
| `&#x1Fxxx;` Unicode 转义 | ❌ 乱码 | ✅ 正常 | **别用** |
| `<line marker-end>` 箭头 marker | ❌ 看不到 | ✅ 正常 | **别用 marker** |
| 复杂多层 `<g>` 嵌套 | ❌ 容易乱 | ✅ 正常 | **极简结构** |
| 长文字（>10 字/块） | ✅ 但臃肿 | ✅ | **极简文字** |
| `<polygon>` 直接画三角 | 🟡 待验证 | ✅ | **可试** |
| 文字箭头字符 `→` | 🟡 待验证 | ✅ | **可试** |

**根因推测**：飞书 IM 卡片走的是**图片预览压缩**或**简化 SVG 渲染器**，不支持 SVG 高级特性（marker、symbol、use 等）和部分字体。

### 坑 2：emoji 在飞书 IM 卡片里 100% 失败

**v1 错** → 把 emoji 全删了（Lee 不满意）
**v2 错** → 改用 `&#x1Fxxx;` 转义（Lee 看到还是乱码）
**正确做法** → emoji 在 SVG `<text>` 里**根本不能用**，必须去掉

### 坑 3：marker-end 箭头渲染器不支持

**v1-v3 三版都用了** `<line marker-end="url(#arrow)">` 画箭头
**Lee 反馈**：完全看不到箭头
**正确做法**：用 `→` 字符做箭头，或用 `<polygon>` 直接画三角形

### 坑 4：文字超过 ~10 字/块就臃肿

**v2 错** → Lee 说"没有箭头 + 描述臃肿"
**v2 错** → 我反而加了一堆详细说明框（每块 30+ 字）
**正确做法** → 每块 ≤ 8 字，关键信息用箭头标签承载

### 坑 5：小尺寸的 `<text>` 会被裁切

**测试图 v1** → 块 C 框宽 60px，"块 C" 文字显示成 "C"（被裁切）
**正确做法** → 框宽 ≥ 100px，文字居中留 padding

---

## 三、📁 相关文件位置

### OpenClaw 工作区
```
/root/.openclaw/workspace/
├── diagrams/
│   ├── skeleton-frameworks-2026-06-08.svg    # 图 1（v1/v2/v3 都在这里，Lee 都说不合格）
│   ├── search-architecture-2026-06-08.svg    # 图 2（同上）
│   └── test-minimal.svg                       # 最小测试图（块 A/块 B 中文 OK，箭头看不到）
├── handoffs/
│   └── handoff-svg-diagrams-2026-06-08.md   # 本文件
└── memory/2026-06-08.md                       # 今日 L0，含完整时间线
```

### 源文件参考
- `MEMORY.md` v3.8 — 三层记忆、推送路由、5 框架索引
- `SOUL.md` — 任务确认红线
- `AGENTS.md` — 反信息茧房 3 条 + 任务收尾 3 项
- `HEARTBEAT.md` — 4 步健康检查

### 关键纠正记录
- `self-improving/corrections.md` → `dev_20260608_001`（emoji 误判）
- `self-improving/corrections.md` → `dev_20260608_002`（emoji 二次误判 + 臃肿）
- `self-improving/corrections.md` → `dev_20260608_003`（emoji 三次失败 + marker 失败 + 效率低）

---

## 四、🎯 Lee 验收硬标准（CC/Codex 必达）

| 维度 | 硬要求 |
|------|--------|
| **乱码** | 飞书 IM 卡片显示**完全无乱码**（文字/符号/箭头）|
| **箭头** | 每两块之间**必须**有显式箭头（带或不带文字标签都行）|
| **文字精简** | 每块描述 ≤ 8 个中文字 |
| **结构清晰** | 图 1 必须显式画"Lee 问 → 处理 → 回报 → 沉淀 → 回到 Lee 问"闭环 |
| **结构清晰** | 图 2 必须显式画"3 路并行 + 顶部路由 + 底部评估" |
| **emoji** | **完全不用**（在飞书 IM 卡片里 100% 失败）|
| **字体** | `font-family="Microsoft YaHei, SimHei, Arial, sans-serif"`（这是唯一验证过的）|
| **文件命名** | `diagrams/skeleton-frameworks-{日期}.svg` 和 `diagrams/search-architecture-{日期}.svg` |
| **发送方式** | OpenClaw message 工具，filePath 字段 |

---

## 五、💡 推荐技术路线（CC/Codex 自选）

### 路线 A：纯 SVG + 文字箭头（最简，最可能成功）
- 用 `→` Unicode 字符（不在 BMP 平面，**未验证**，可能也不行）做箭头
- 或者在 `<line>` 末端**直接画 `<polygon>` 三角形**（不依赖 marker）

### 路线 B：SVG 转 PNG（最稳，但需要工具）
- 用 `image_generate` 工具（model=openai/gpt-image-2 可选）重做图
- PNG 100% 在飞书显示
- 缺点：可能改不了 SVG 那种"矢量精确"风格

### 路线 C：HTML/SVG 双版（最稳+最灵活）
- 先在 SVG 调试清楚
- 发送时附 PNG 预览（用 `screenshot` 或 `image_generate`）

### 路线 D：用 Mermaid/PlantUML 渲染
- Mermaid 文本 → SVG → 转换时可能仍踩同样的坑
- PlantUML 同理

---

## 六、🧪 验证步骤（务必先做）

**在画完整图前，先做这个最小测试**（已存在 `diagrams/test-minimal.svg`，可重做）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 200" font-family="Microsoft YaHei, SimHei, Arial, sans-serif">
  <rect width="600" height="200" fill="#0f1419"/>
  <rect x="50" y="70" width="120" height="60" rx="6" fill="#1f6feb"/>
  <text x="110" y="105" text-anchor="middle" fill="#ffffff" font-size="14" font-weight="bold">块 A</text>
  <!-- 方案 1：直接画三角，不依赖 marker -->
  <line x1="170" y1="100" x2="270" y2="100" stroke="#58a6ff" stroke-width="2"/>
  <polygon points="270,94 282,100 270,106" fill="#58a6ff"/>
  <rect x="282" y="70" width="120" height="60" rx="6" fill="#3fb950"/>
  <text x="342" y="105" text-anchor="middle" fill="#ffffff" font-size="14" font-weight="bold">块 B</text>
</svg>
```

**Lee 验收**：
- 块 A 文字清晰？
- 块 A → 块 B 的箭头**带三角形**能看到吗？

**如果 polygon 三角能看到** → 用这个路线画完整图
**如果连 polygon 都看不到** → 飞书 IM 卡片对 SVG 渲染限制更大，**必须换 PNG 路线**

---

## 七、📞 联系/继续

- **OpenClaw 工作区**：`/root/.openclaw/workspace/`
- **Lee 时区**：Asia/Shanghai (UTC+8)
- **飞书 chat_id**：`oc_8dd77f85fc71a5691e915184515d0cb2`（DM with Lee）
- **Lee 的 open_id**：`ou_e7a18238e21dede810d2e55ac91d3165`
- **小马 xiaoma-hermes**：Lee 的 PC 本地主 Agent，飞书 open_id 待补充（06-08 当前状态）

---

## 八、🦞 小龙虾反思

- **效率问题**：连改 3 版 + 测试 1 张图，最终还在排查基础渲染问题——**超出"快速画图"能力**
- **早该交接的时机**：**第 1 次发现 emoji + marker 都有渲染问题**的时候就该提出，而不是死磕
- **判断偏差模式**：连续 3 次把"相关性 = 因果"——emoji 跨平台不稳 ≠ emoji 在飞书不行
- **任务复杂度误判**：把"画图"当简单任务，没意识到**飞书 IM 卡片渲染管道**是隐藏变量

---

_版本：1.0 | 2026-06-08 11:07 CST | by 小龙虾_
_交接方：minimax/MiniMax-M3 → 接手方：CC / Codex_
