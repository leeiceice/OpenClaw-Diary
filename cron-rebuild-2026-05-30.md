# 小龙虾 Cron 重建清单

> 由小马根据 Lee 确认生成（2026-05-30）
> 状态：待执行

## 已知事实
- openclaw.json 已修：端口从 26301 → 18789
- 认证 token: `fqf4U7npBp2Eruk4mNgvGg6BtWZ2SQXhIC4temIQzQg`（operator token）
- Gateway: `http://localhost:18789`
- 飞书路由：
  - 新闻群: `oc_e4686fe5eb6e865b68fae7625a5ce840`
  - 日常安排群: `oc_ad39a8e943103c2164f1d0d9de503da5`
  - 进化群: `oc_8e02a9ced0671cac8413b4c98e76637a`
  - 内容收集群: `oc_20875a15a62ddeb3c3573d8d23c86daa`
  - 安全群: `oc_1f77586fc34cdac8f43a4e9733eafc`

## 执行步骤

### Step 1: 测试 CLI 连通性
```bash
OPENCLAW_TOKEN=fqf4U7npBp2Eruk4mNgvGg6BtWZ2SQXhIC4temIQzQg OPENCLAW_GATEWAY=http://localhost:18789 openclaw cron list
```
期望输出: `No cron jobs.`

### Step 2: 创建 6 个 Cron Job

**Job 1: 每日晨报**
```bash
OPENCLAW_TOKEN=fqf4U7npBp2Eruk4mNgvGg6BtWZ2SQXhIC4temIQzQg OPENCLAW_GATEWAY=http://localhost:18789 openclaw cron add \
  --name "每日晨报" \
  --cron "0 9 * * *" \
  --channel feishu \
  --to "oc_e4686fe5eb6e865b68fae7625a5ce840" \
  --message "你是 Lee 的新闻助理。搜索今日重大新闻，生成3-5条简明摘要，推送到飞书新闻群。内容要有时效性，每条附来源。" \
  --expect-final \
  --timeout-seconds 120
```

**Job 2: 每日简报（17:00）**
```bash
OPENCLAW_TOKEN=fqf4U7npBp2Eruk4mNgvGg6BtWZ2SQXhIC4temIQzQg OPENCLAW_GATEWAY=http://localhost:18789 openclaw cron add \
  --name "每日简报" \
  --cron "0 17 * * *" \
  --channel feishu \
  --to "oc_ad39a8e943103c2164f1d0d9de503da5" \
  --message "总结今日重要事项，推送到日常安排群。内容包括：今日完成、明日待办、任何需要 Lee 注意的事项。" \
  --expect-final \
  --timeout-seconds 300
```

**Job 3: 进化日报（17:30，与简报错开）**
```bash
OPENCLAW_TOKEN=fqf4U7npBp2Eruk4mNgvGg6BtWZ2SQXhIC4temIQzQg OPENCLAW_GATEWAY=http://localhost:18789 openclaw cron add \
  --name "进化日报" \
  --cron "30 17 * * *" \
  --channel feishu \
  --to "oc_8e02a9ced0671cac8413b4c98e76637a" \
  --message "总结今日 AI 学习/进化进展，推送到进化群。内容包括：今日学到了什么、有哪些反思、下一步计划。" \
  --expect-final \
  --timeout-seconds 120
```

**Job 4: 进化周报（周一 09:30）**
```bash
OPENCLAW_TOKEN=fqf4U7npBp2Eruk4mNgvGg6BtWZ2SQXhIC4temIQzQg OPENCLAW_GATEWAY=http://localhost:18789 openclaw cron add \
  --name "进化周报" \
  --cron "30 9 * * 1" \
  --channel feishu \
  --to "oc_8e02a9ced0671cac8413b4c98e76637a" \
  --message "生成周度进化报告，发送到进化群。总结本周进化进展、关键决策、教训与下周计划。" \
  --expect-final \
  --timeout-seconds 180
```

**Job 5: 每日书籍推荐（15:00）**
```bash
OPENCLAW_TOKEN=fqf4U7npBp2Eruk4mNgvGg6BtWZ2SQXhIC4temIQzQg OPENCLAW_GATEWAY=http://localhost:18789 openclaw cron add \
  --name "每日书籍推荐" \
  --cron "0 15 * * *" \
  --channel feishu \
  --to "oc_20875a15a62ddeb3c3573d8d23c86daa" \
  --message "从微信读书书架中选一本值得推荐的书，推送到内容收集群。格式：书名+作者+推荐理由+适合人群。" \
  --expect-final \
  --timeout-seconds 120
```

**Job 6: 每日备份（02:00，本地）**
```bash
OPENCLAW_TOKEN=fqf4U7npBp2Eruk4mNgvGg6BtWZ2SQXhIC4temIQzQg OPENCLAW_GATEWAY=http://localhost:18789 openclaw cron add \
  --name "每日备份" \
  --cron "0 2 * * *" \
  --channel feishu \
  --to "oc_1f77586fc34cdac8f43a4e9733eafc" \
  --message "执行 workspace 每日备份：git add + commit + push 到 xiaolongxia-openclaw。备份完成后简短汇报。" \
  --expect-final \
  --timeout-seconds 300
```

### Step 3: 验证
```bash
OPENCLAW_TOKEN=fqf4U7npBp2Eruk4mNgvGg6BtWZ2SQXhIC4temIQzQg OPENCLAW_GATEWAY=http://localhost:18789 openclaw cron list
```
期望: 看到 6 个 job

## 注意
- 喝水提醒：Lee 确认不需要，不建
- 如果 CLI 连不上（pairing 问题），尝试用 gateway token：
  `OPENCLAW_TOKEN=36433a0a81b82f0fbe816f01e787cf1bf116f283d8d3e3ef`
