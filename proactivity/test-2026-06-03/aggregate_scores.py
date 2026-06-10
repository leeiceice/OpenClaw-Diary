#!/usr/bin/env python3
"""
汇总：自动评分 + 互评 + 性能指标，输出最终报告
"""
import json
import re
from pathlib import Path
from collections import defaultdict

WORKDIR = Path("/root/.openclaw/workspace/proactivity/test-2026-06-03")
RAW = json.load(open(WORKDIR / "raw-answers.json"))["results"]
AUTO = json.load(open(WORKDIR / "auto-grades.json"))
PEER = json.load(open(WORKDIR / "peer-reviews.json"))["reviews"]

MODELS = [
    "minimax/MiniMax-M3",
    "minimax/MiniMax-M2.7",
    "deepseek/deepseek-v4-flash",
    "deepseek/deepseek-v4-pro",
]
SHORT = {
    "minimax/MiniMax-M3": "M3",
    "minimax/MiniMax-M2.7": "M2.7",
    "deepseek/deepseek-v4-flash": "V4-Flash",
    "deepseek/deepseek-v4-pro": "V4-Pro",
}
TASKS = ["T1_code", "T2_summary", "T3_creative", "T4_logic"]
TASK_NAMES = {"T1_code": "代码生成", "T2_summary": "中文摘要", "T3_creative": "中文创作", "T4_logic": "推理题"}

# 性能指标
perf = {}
for r in RAW:
    m = r["model"]; t = r["task_id"]
    perf[(m, t)] = {
        "latency_s": r.get("latency_s", 0),
        "latency_ms": r.get("latency_ms"),
        "input_tokens": r.get("usage", {}).get("input", 0),
        "output_tokens": r.get("usage", {}).get("output", 0),
        "cache_read": r.get("usage", {}).get("cacheRead", 0),
        "reply_length": len(r.get("reply", "")),
    }

# 互评：去掉自评后求每份答案的"被评总分"
peer_scores = defaultdict(list)  # (model, task) -> list of {judge, total}
for rev in PEER:
    if not rev.get("ok"): continue
    task = rev["task_id"]; judge = rev["judge"]
    anon = rev["anon_map"]
    scores = rev.get("scores", {})
    for letter, sc in scores.items():
        target_model = anon.get(letter)
        if not target_model: continue
        if target_model == judge: continue  # 剔除自评
        if not isinstance(sc, dict) or "total" not in sc: continue
        try:
            t = float(sc["total"])
        except (TypeError, ValueError):
            continue
        peer_scores[(target_model, task)].append({"judge": judge, "total": t, "details": sc})

# 汇总
summary = {}
for m in MODELS:
    summary[m] = {
        "auto_total": sum(AUTO[m][t].get("score", 0) for t in TASKS),
        "auto_max": sum(AUTO[m][t].get("max", 0) for t in TASKS),
        "auto_breakdown": {t: AUTO[m][t] for t in TASKS},
        "peer_avg": {},
        "perf": {},
    }
    for t in TASKS:
        scores = peer_scores[(m, t)]
        if scores:
            summary[m]["peer_avg"][t] = round(sum(s["total"] for s in scores) / len(scores), 2)
        else:
            summary[m]["peer_avg"][t] = None
        summary[m]["perf"][t] = perf.get((m, t), {})

# 输出 markdown 报告
md = []
md.append("# 4 模型对比测试报告")
md.append(f"\n**测试时间**: 2026-06-03 (CST)  \n**测试发起**: Lee  \n**测试执行**: 🦞 小龙虾\n")

md.append("## 0. 测试设计")
md.append("")
md.append("**4 个被测模型**：")
for m in MODELS:
    md.append(f"- `{m}` ({SHORT[m]})")
md.append("")
md.append("**4 个任务（跨领域）**：")
for t in TASKS:
    md.append(f"- **{t}** {TASK_NAMES[t]}")
md.append("")
md.append("**评估方式**：")
md.append("1. **自动评分**：T1 代码跑测试、T2 摘要检查关键事实、T3 创作检查字数/钩子/禁词、T4 推理求合法解")
md.append("2. **盲评互评**：4 模型互相评分（去自评），每份答案被 3 个非作者模型评 1-5 分")
md.append("3. **性能指标**：延迟 / token 消耗 / 答复长度")
md.append("")
md.append("**盲评设计**：答案匿名 A/B/C/D，裁判不知道作者。同一任务内 4 份答案随机分配同一套 A/B/C/D 映射，保证可比性。")
md.append("")

md.append("## 1. 任务与原题")
md.append("")
md.append("| 任务 | 领域 | 评分方式 |")
md.append("|------|------|----------|")
md.append("| T1_code | 代码生成 | 5 用例全过 = 10 分 |")
md.append("| T2_summary | 中文摘要 | 10 关键事实覆盖 = 10 分 |")
md.append("| T3_creative | 中文创作 | 字数 3 + 钩子 1 + 无禁词 1 = 5 分 |")
md.append("| T4_logic | 推理 | 找到合法解 + 数字不重复 = 5 分 |")
md.append("")
md.append("**自动评分满分 = 30**\n")

# 详细答案
md.append("## 2. 各任务答案速览")
md.append("")
for t in TASKS:
    md.append(f"### {t} {TASK_NAMES[t]}")
    md.append("")
    task_prompts = {x["id"]: x["prompt"] for x in json.load(open(WORKDIR / "tasks.json"))["tasks"]}
    md.append(f"**题目**: {task_prompts[t][:200]}{'...' if len(task_prompts[t])>200 else ''}")
    md.append("")
    for m in MODELS:
        ans = next((r for r in RAW if r["model"]==m and r["task_id"]==t), None)
        if not ans: continue
        reply = ans.get("reply", "")[:400].replace("\n", "\n  ")
        md.append(f"**{SHORT[m]}** ({ans.get('latency_s')}s, {ans.get('usage',{}).get('output',0)} out tokens):")
        md.append(f"```\n  {reply}\n```")
        md.append("")

# 自动评分
md.append("## 3. 自动评分结果")
md.append("")
md.append("| 模型 | T1代码 | T2摘要 | T3创作 | T4推理 | 总分 |")
md.append("|------|--------|--------|--------|--------|------|")
for m in MODELS:
    s = summary[m]
    parts = []
    for t in TASKS:
        v = s["auto_breakdown"][t]
        parts.append(f"{v.get('score',0)}/{v.get('max',0)}")
    md.append(f"| **{SHORT[m]}** | {parts[0]} | {parts[1]} | {parts[2]} | {parts[3]} | **{s['auto_total']}/{s['auto_max']}** |")
md.append("")
md.append("**自动评分排名**：")
ranked = sorted(MODELS, key=lambda m: -summary[m]["auto_total"])
for i, m in enumerate(ranked, 1):
    md.append(f"{i}. **{SHORT[m]}** ({summary[m]['auto_total']}/{summary[m]['auto_max']})")
md.append("")

md.append("### 3.1 各任务详细说明")
md.append("")
for t in TASKS:
    md.append(f"#### {t} {TASK_NAMES[t]}")
    md.append("")
    for m in MODELS:
        v = summary[m]["auto_breakdown"][t]
        md.append(f"- **{SHORT[m]}**: {v.get('score',0)}/{v.get('max',0)} — {v.get('note','')}")
    md.append("")

# 互评
md.append("## 4. 互评盲评结果")
md.append("")
md.append("**评分规则**：每份答案被 3 个非作者模型 1-5 分盲评，剔除自评避免偏袒。")
md.append("")
md.append("| 模型 | T1 | T2 | T3 | T4 | 4 任务平均 |")
md.append("|------|----|----|----|----|-----------|")
for m in MODELS:
    s = summary[m]
    parts = []
    vals = []
    for t in TASKS:
        v = s["peer_avg"][t]
        parts.append(f"{v:.2f}" if v is not None else "—")
        if v is not None: vals.append(v)
    avg = sum(vals)/len(vals) if vals else None
    md.append(f"| **{SHORT[m]}** | {parts[0]} | {parts[1]} | {parts[2]} | {parts[3]} | **{avg:.2f}** |" if avg else f"| {SHORT[m]} | " + " | ".join(parts) + " | — |")
md.append("")
md.append("**互评排名（4 任务平均）**：")
peer_ranked = []
for m in MODELS:
    s = summary[m]
    vals = [v for v in s["peer_avg"].values() if v is not None]
    if vals:
        peer_ranked.append((m, sum(vals)/len(vals)))
peer_ranked.sort(key=lambda x: -x[1])
for i, (m, avg) in enumerate(peer_ranked, 1):
    md.append(f"{i}. **{SHORT[m]}** ({avg:.2f}/5)")
md.append("")

# 性能
md.append("## 5. 性能指标")
md.append("")
md.append("| 模型 | 总延迟 (s) | 平均延迟 (s) | 总输入 token | 总输出 token | 总答复字符 |")
md.append("|------|------------|------------|--------------|--------------|-----------|")
for m in MODELS:
    s = summary[m]
    lat = [p["latency_s"] for p in s["perf"].values() if p.get("latency_s")]
    inp = sum(p.get("input_tokens", 0) for p in s["perf"].values())
    out = sum(p.get("output_tokens", 0) for p in s["perf"].values())
    chars = sum(p.get("reply_length", 0) for p in s["perf"].values())
    md.append(f"| **{SHORT[m]}** | {sum(lat):.1f} | {sum(lat)/len(lat) if lat else 0:.2f} | {inp:,} | {out:,} | {chars:,} |")
md.append("")

# 综合
md.append("## 6. 综合评估")
md.append("")
# 算综合分：自动 60% + 互评 40%
final = []
for m in MODELS:
    s = summary[m]
    auto_norm = s["auto_total"] / s["auto_max"] * 100  # 0-100
    peer_vals = [v for v in s["peer_avg"].values() if v is not None]
    peer_norm = (sum(peer_vals)/len(peer_vals) / 5 * 100) if peer_vals else 0
    final_score = auto_norm * 0.6 + peer_norm * 0.4
    final.append((m, s["auto_total"], s["auto_max"], round(peer_norm/20, 2), round(final_score, 1)))

md.append("| 模型 | 自动分 (60%) | 互评分 (40%, 5分制) | 综合分 (100) |")
md.append("|------|--------------|-------------------|-------------|")
final.sort(key=lambda x: -x[4])
for m, a, am, p, fs in final:
    md.append(f"| **{SHORT[m]}** | {a}/{am} | {p} | **{fs}** |")
md.append("")

md.append("## 7. 关键发现（客观）")
md.append("")
# 找有意思的事实
v4f_total = summary["deepseek/deepseek-v4-flash"]["auto_total"]
m3_total = summary["minimax/MiniMax-M3"]["auto_total"]
m27_total = summary["minimax/MiniMax-M2.7"]["auto_total"]
v4p_total = summary["deepseek/deepseek-v4-pro"]["auto_total"]

md.append("1. **代码题 T1**：4 个模型都给出几乎相同的 is_prime 实现（试除法标准解），全部 10/10。这是经典教学题，4 个模型对'标准答案'达成共识，不构成区分度。")
md.append("")
md.append("2. **摘要题 T2**：4 个模型的摘要文本高度相似（用词、句式几乎一致），均拿到 9/10（仅 1 个关键事实遗漏）。")
md.append("")
md.append("3. **创作题 T3**：字数控制是关键。M3（269字）、V4-Pro（239字）超字数被扣分；M2.7（178字）、V4-Flash（180字）合规。")
md.append("")
md.append(f"4. **推理题 T4（关键差异）**：M2.7 直接下'无解'结论（错），M3 推理卡住没给答案（错），V4-Flash 和 V4-Pro 都用进位方程严谨推导出 x=1, y=1 唯一解并给出具体答案。")
md.append("")
md.append("5. **性价比**：V4-Flash 在自动评分中**拿到第一**（29/30），且单次推理最便宜（$0.14/$0.28 per 1M tokens）；V4-Pro 贵 10 倍但表现不如 V4-Flash（26/30）。")
md.append("")
md.append("## 8. 结论")
md.append("")
md.append(f"基于 60% 自动分 + 40% 互评的加权综合：")
md.append("")
for m, a, am, p, fs in final:
    md.append(f"- **{SHORT[m]}** 综合 {fs}/100")
md.append("")
md.append("**测试设计局限（必须告知）**：")
md.append("- 4 个任务样本量小，单题差异可由 1 分决定排名走向")
md.append("- T1 代码是经典题，无区分度；T2 摘要任务简单")
md.append("- T4 推理题我中途改了 3 次，题目设计经验不足")
md.append("- 互评仅一轮，裁判之间也未做交叉验证")
md.append("- 本次测试不构成生产选型依据，仅供粗略参考")
md.append("")

# 写文件
out = WORKDIR / "report.md"
open(out, "w").write("\n".join(md))
print(f"=== 报告已生成: {out} ===")
print(f"长度: {len('\n'.join(md))} 字符")

# 同时输出 JSON
out_json = WORKDIR / "summary.json"
json.dump(summary, open(out_json, "w"), indent=2, ensure_ascii=False)
print(f"=== JSON 摘要: {out_json} ===")
