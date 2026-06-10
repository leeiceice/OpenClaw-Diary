# 内容收集与关联系统

## 收藏工作流（强制）
收到文章/链接 → 一次做完整：
1. 判断类型：公众号（mp.weixin.qq.com）vs 普通网页
2. 提取：标题/作者/日期/摘要/核心观点/关键数据/金句
3. 存入 collections/articles/ 或 collections/wechat/
4. 生成阅读摘要（## 阅读摘要章节）
5. 运行关联分析脚本：`python3 /root/.openclaw/workspace/scripts/association_analysis.py <文件路径>`
6. 展示星级报告（⭐至⭐⭐⭐）
7. 同步 Obsidian（~/Obsidian/收藏/文章/ 或 /公众号/）
8. 更新 index.md + tags.md + 双向链接

## 目录结构
```
/workspace/collections/
  articles/    ← 普通网页文章
  wechat/      ← 微信公众号（粘贴正文）
  ideas/       ← 关联分析输出
```

## 关联分析脚本
- 路径：scripts/association_analysis.py
- 输出：星级（0-5）+ 关联对象 + PARA建议分类
- 保存位置：collections/ideas/

## PARA 分类
- `notes/projects/` — 有截止日期的主动项目
- `notes/areas/` — 持续责任领域
- `notes/resources/` — 参考资料/研究素材
- `notes/archive/` — 已完成/不活跃内容

## 关联强度星级
| 星级 | 强度 |
|------|------|
| ⭐⭐⭐⭐⭐ | 极强，主题完全吻合，多次关联 |
| ⭐⭐⭐⭐ | 强，核心主题相关，概念重叠 |
| ⭐⭐⭐ | 中等，领域相关，部分关键词重叠 |
| ⭐⭐ | 弱，间接相关，仅关键词匹配 |
| ⭐ | 极弱，勉强相关，单一关键词 |

## 收集群
- 飞书群：oc_20875a15a62ddeb3c3573d8d23c86daa
- 触发：发到群里的任何内容实时分析处理

---

## ⚠️ 踩坑记录（从 memory/ 日志提炼）


### 微信公众号抓取失效（2026-04-22）
- **问题**：browser 超时 + 镜像搜索失败，公众号文章无法自动抓取
- **教训**：微信公众号有验证码拦截，web_fetch/browser 方案不稳定
- **解决**：Lee 粘贴正文 → 小龙虾整理成收藏格式（已验证可行）
- **待解决**：SOGO 微信验证码绕过方案待探索

### 全网文章收集未完成（2026-04-22）
- **问题**：browser 超时导致文章收集中途失败
- **教训**：browser 类任务要给足够 timeout，建议 120s+
- **解决**：收集任务分阶段，确认每阶段完成后再继续
