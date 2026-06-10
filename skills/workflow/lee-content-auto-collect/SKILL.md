---
name: lee-content-auto-collect
description: Lee 发来的想法/文件/金句/文章/链接自动收藏流程。触发后必须走完全套：收藏→关联→Obsidian入库→GitHub同步→飞书推送（匹配话题时）。禁止只回复不存档。
---

# Lee 内容自动收藏流程（小龙虾版）

> ⚠️ **强制执行，不可跳过。Lee 已两次提醒（2026-05-13、2026-05-14）。最高优先级工作流。**

## 触发条件

Lee 发送以下任一内容时，立即执行完整流程：
- 💡 想法、观点、金句、摘录
- 📄 文件（.md、.txt、.pdf 等附件或粘贴内容）
- 📰 文章（纯文字，非 URL）
- 🔗 任何 Lee 认为值得收藏的内容

**触发后绝对禁止**：只回复分析/感想，不做任何收藏操作。

## 关键区别

| 触发类型 | 参考流程 |
|---------|---------|
| **URL 链接 + "收藏"** | → 使用 TOOLS.md「Content Collector」流程（URL 抓取） |
| **想法/文件/文字** | → 使用本 skill 流程（本文件） |

## 完整流程

### Step 1: 判断内容类型并收藏

| 内容类型 | 收藏路径 | 命名 |
|---------|---------|------|
| 想法/观点 | `~/Obsidian/收藏/想法/` | `YYYY-MM-DD-{内容摘要≤15字}.md` |
| 金句/摘录 | `~/Obsidian/收藏/金句/` | `YYYY-MM-DD-{内容摘要≤15字}.md` |
| 文章/长文 | `~/Obsidian/收藏/文章/` | `YYYY-MM-DD-{内容摘要≤15字}.md` |
| 文件附件 | `~/Obsidian/收藏/文件/` | 原始文件名 |

### Step 2: 关联分析（强制）

运行关联分析脚本，为新内容找到 ≥3 个最相关的已有文档：

```bash
python3 /root/.openclaw/workspace/scripts/association_analysis.py <收藏文件路径>
```

输出星级报告（⭐至⭐⭐⭐⭐⭐），在源文件 frontmatter 写入 `related:` 字段（Top5）。

### Step 3: 同步到 Obsidian GitHub

⚠️ 推送前先 fetch + 检查差异，避免覆盖 Lee 的编辑：

```bash
cd ~/Obsidian
git fetch origin
# 对比是否有冲突
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)
if [ "$LOCAL" != "$REMOTE" ]; then
  git pull --rebase || echo "⚠️ 拉取有冲突，请手动处理"
fi
# 只 add 本次收藏文件
git add "收藏/{新文件名}.md"
git commit -m "收藏: {新文件名}"
git push origin master
```

### Step 4: 飞书推送（匹配话题时）

匹配以下话题则推送到对应群：

| 话题类型 | 目标群 | chat_id |
|---------|-------|---------|
| AI/大模型/科技/研究 | 进化群 | `oc_8e02a9ced0671cac8413b4c98e76637a` |
| 书籍/学习相关 | 内容收集群 | `oc_20875a15a62ddeb3c3573d8d23c86daa` |
| 日常/工作/健康 | 日常安排群 | `oc_ad39a8e943103c2164f1d0d9de503da5` |

### Step 5: 记录到中期记忆

在当天 `memory/YYYY-MM-DD.md` 写入收藏记录：

```markdown
### 收藏
- 📄 {文件名} → {收藏路径}
  - 关联: {关联文档1}、{关联文档2}、{关联文档3}
  - 推送: {目标群}
```

## 流程图

```
Lee 发送内容（非URL）
    │
    ▼
┌─────────────────┐
│ Step 1: 收藏    │ → 判断类型，存入 Obsidian 收藏目录
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 2: 关联    │ → association_analysis.py，≥3 个关联
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 3: 同步GH  │ → Obsidian git push（先 fetch 检查冲突）
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 4: 飞书    │ → 匹配话题则推送对应群
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 5: 记录    │ → memory/YYYY-MM-DD.md
└─────────────────┘
```

## 验证清单

触发后自检：
- [ ] 文件已保存到 Obsidian 收藏目录
- [ ] association_analysis.py 已运行，≥3 个关联
- [ ] Obsidian 已 git push
- [ ] memory/YYYY-MM-DD.md 已写入收藏记录
- [ ] （如匹配话题）飞书推送已完成

## 常见错误

- ❌ 只回复分析，不收藏 → 违反强制规则，Lee 已两次提醒
- ❌ 收藏后不关联 → 关联分析是强制步骤
- ❌ 关联后不 git push → Obsidian 和 GitHub 必须同步
- ❌ 忘记写 memory/YYYY-MM-DD.md → 收藏记录必须可追溯

## 路径速查

| 用途 | 路径 |
|------|------|
| 收藏根目录 | `~/Obsidian/收藏/` |
| 关联分析脚本 | `/root/.openclaw/workspace/scripts/association_analysis.py` |
| 收集群 | `oc_20875a15a62ddeb3c3573d8d23c86daa` |
| 进化群 | `oc_8e02a9ced0671cac8413b4c98e76637a` |
| 日常安排群 | `oc_ad39a8e943103c2164f1d0d9de503da5` |
| 内容收集群 | `oc_20875a15a62ddeb3c3573d8d23c86daa` |

## 参考

- TOOLS.md「Content Collector」— URL 收藏流程（本 skill 处理非 URL 内容）
- TOOLS.md「话题订阅推送机制」— 推送匹配逻辑
- `scripts/association_analysis.py` — 关联分析脚本
