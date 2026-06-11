---
name: openclaw-diary
description: OpenClaw-Daily AI学习日记生成流程（21:10 cron）— GitHub API + HTML 结构 + 第一人称 AI 视角
trigger: "提问涉及 OpenClaw-Daily 日记 / 学习日记 / AI 日记生成 / index.html entry 结构相关"
---

# OpenClaw-Daily AI学习日记生成流程

## 执行时间
每日 21:10 CST，cron `0eaef122-1e3a-4751-98d9-a6191033bd46`

## 生成内容结构
- 第一人称 AI 视角（小龙虾）
- 板块：核心感悟 / 技术产出 / 反思 / 自我进化日报 / 最终教训
- 必用 `<h2>` 分大块 + `<ul><li>` 列点 + `<code>` 包路径 + `<strong>` 关键判断
- 不读 Lee 日记、不暴露私人信息

## 执行步骤
1. 读 MEMORY.md 了解今日记忆
2. 读 `memory/$(date +%Y-%m-%d).md` 今日工作流
3. 读 `proactivity/daily-working-log.md` 随手记
4. 读 `self-improving/corrections.md` 自动修偏差
5. 生成符合 OpenClaw-Diary index.html entry 结构的 HTML
6. GET `https://api.github.com/repos/leeiceice/OpenClaw-Diary/contents/index.html` 拿 SHA
7. PUT 提交更新（Token 从 ~/.openclaw/.env GITHUB_TOKEN）
8. 完成后 DM Lee 飞书（ou_e7a18238e21dede810d2e55ac91d3165）

## cron 参数
- 时间：每日 21:10 CST
- 模型：minimax/MiniMax-M3
- fallback：deepseek/deepseek-v4-flash
- timeout：1200s（2026-06-10 21:25 Lee 拍板从 600→1200，600s 跑 21:10 时卡死）
- lightContext：true（bootstrap 不注入）
- 推送目标：直接 DM Lee

## 故障记录
- 2026-06-10 21:10：原 timeout 600s 卡死（model-call-started），当日 entry 缺位
  修复：timeout→1200s，Lee 拍板加长
