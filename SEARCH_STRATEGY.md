# 联网搜索工具使用规范 🦞

> 本规范定义：当记忆库（L0/L1/L2）查不到时，各搜索工具的优先级和使用场景

---

## 搜索工具矩阵

| 工具 | 用途 | API依赖 | 响应速度 | 适用场景 |
|------|------|---------|---------|---------|
| **记忆库** | 查历史对话/记忆 | 无 | 最快 | 已知事实、历史决策、已讨论过的内容 |
| **tavily_search** | 全网语义搜索 | Tavily API Key | 中 | 实事、新闻、技术文档、公开信息 |
| **web_fetch** | 抓取单个页面 | 无 | 中 | 已知 URL，直接抓取文章/文档 |
| **agent-reach** | 结构化平台搜索 | 无 | 慢 | 特定平台内容（微信/小红书/GitHub等） |
| **tavily_extract** | JS 渲染页面提取 | Tavily API Key | 慢 | 需要渲染的动态页面 |

---

## 搜索优先级（遇到不确定问题时执行顺序）

### 场景 1：记忆库已有 → 直接用，不重复搜索

```
记忆库搜索 → 命中 → 回复
```

### 场景 2：记忆库没有 → 查 Tavily 全网搜索

```
记忆库搜索 → 未命中 → tavily_search → 命中 → 回复 + 补充说明来源
```

### 场景 3：Tavily 搜不到 → 针对性抓取

```
tavily_search → 未命中 → web_fetch / tavily_extract → 抓到 → 回复
```

### 场景 4：特定平台内容 → agent-reach

```
微信文章  → agent-reach 微信公众号渠道
B站/YouTube → agent-reach 视频渠道
GitHub    → agent-reach GitHub 渠道
小红书    → agent-reach 小红书渠道
```

### 场景 5：所有都失败 → 承认不知道 + 建议 Lee 提供更多信息

```
所有工具 → 均未命中 → "这个问题我目前无法确认，建议 Lee 提供链接或补充说明"
```

---

## 搜索质量规范

1. **搜索词精简**：不超过 5 个关键词，避免口语化
2. **来源标注**：搜索到的信息要标注来源 URL（简短形式）
3. **不拼接记忆**：联网结果和记忆内容分开，不混为一谈
4. **时效性判断**：新闻类主动注明时间，不确定时说"可能有更新"
5. **敏感信息**：不搜索/传播个人隐私信息

---

## 各工具调用示例

```python
# Tavily 全网搜索
tavily_search(query="OpenClaw memory plugin comparison", max_results=3)

# Tavily 提取页面内容
tavily_extract(urls=["https://example.com/article"], query="key information")

# 抓取已知URL
web_fetch(url="https://docs.openclaw.ai/configuration", maxChars=3000)
```

---

_版本：1.0 | 最后更新：2026-05-20 18:05 | by 小龙虾_