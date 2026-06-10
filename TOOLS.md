# TOOLS.md 🦞 - 本地配置

Skills define _how_ tools work. This file is for _your_ specifics - the stuff that's unique to your setup.

## 响应规则（Lee 强制确认）

**回复前必须：**
1. `memory_search(query="简短查询")` — 先搜记忆
2. 有依据 → 组织回答
3. 依据不足 → 联网搜索
4. **禁止**：无记忆依据的乱回答

## 飞书推送目标（单一真相源）

| 类型 | 群名称 | chat_id |
|------|--------|---------|
| 日常安排/工作/健康 | 日常安排群 | `oc_ad39a8e943103c2164f1d0d9de503da5` |
| 学习提醒/监督 | 学习监督群 | `oc_3fb5240d43f24be367f5bcd981a0415b` |
| 新闻简报 | 新闻群 | `oc_e4686fe5eb6e865b68fae7625a5ce840` |
| 进化日报/周报/Skill安全 | 进化群 | `oc_8e02a9ced0671cac8413b4c98e76637a` |
| 内容收藏/书籍推荐 | 内容收集群 | `oc_20875a15a62ddeb3c3573d8d23c86daa` |
| 系统健康/备份/安全 | 安全群 | `oc_1f77586fc34cdacac8f43a4e9733eafc` |

> 所有推送目标必须从此处读取，禁止硬编码。

## 收藏流程规范（红线）

收到文件/想法/金句/链接 → 必须走完整收藏流程，**绝不只回不复**：

1. 提取核心要点（3-5 bullet）在文档开头
2. 关联分析 → 找 Obsidian 中相关已有文档
3. 回流写入 → `related:` 字段回写到源文件 frontmatter
4. 同步 Obsidian + git push
5. 推送飞书汇报：`📥 收藏完成！「标题」已入库，核心要点：...`

详见：收藏系统 skill（TOOLS.md 不重复记录流程）

## 脚本路径速查

| 任务 | 脚本路径 | 关键参数 |
|------|---------|---------|
| 喝水追踪（主） | `scripts/water_tracker.py` | `<文本> --card` → 返回文字+图片 |
| 喝水卡片生成 | `scripts/water_card_generator.py` | 输入数据文件，输出图片 |
| 晨报 | `scripts/morning_briefing.py` | 发送到新闻群 |
| 日报 | `scripts/generate_daily_arrangement_report.py` | 发送到日常安排群 |
| 进化日报 | `scripts/generate_evolution_daily_report.py` | 发送到进化群 |
| 书籍推荐图 | `scripts/generate_book_card_hd.py` | 直接生成，路径固定 |
| Ontology同步 | `scripts/conversation_to_ontology.py` | 自动运行 |
| 关联分析 | `scripts/association_analysis.py` | `<文件路径>` → 星级报告 |

## 数据存储

| 项目 | 路径 |
|------|------|
| 收藏目录 | `/root/.openclaw/workspace/collections/` |
| Obsidian 仓库 | `~/Obsidian/` |
| 收藏文章 | `~/Obsidian/收藏/文章/` |
| 收藏公众号 | `~/Obsidian/收藏/公众号/` |
| PARA | `~/Obsidian/wiki/_archive/2026-05-para-backup/` |

## 喝水追踪系统

| 项目 | 值 |
|------|-----|
| 数据文件 | `/root/.openclaw/workspace/data/water-log.json` |
| 目标 | 每日 2000ml = 6杯 × 350ml/杯 |
| 杯容量 | 350ml |
| 数量歧义 | "第X杯"=1杯，"X杯"=X杯；不明确时先问 Lee |

---

_版本：2.1 | 最后更新：2026-06-01 10:15 | by 小龙虾（版本号规范整理）_


## 回归测试
- **[回归测试] dev_20260605_001 验证 datetime 不再重复 strftime** — 触发: Lee 11:01 拍板跑 A 组 4 条 → A1 wal_protocol.py datetime bug 回归 → bug 已修，line 19/26 都只 strftime 一次