#!/usr/bin/env python3
"""
双盲测试 v2: 自动评分 + 盲评聚合 + 揭盲生成报告
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path
from collections import defaultdict

WORKDIR = Path("/root/.openclaw/workspace/proactivity/test-2026-06-03")
TASKS = {t["id"]: t for t in json.load(open(WORKDIR / "doubleblind-tasks.json"))["tasks"]}
ANSWERS = json.load(open(WORKDIR / "doubleblind-answers.json"))["results"]
REVIEWS = json.load(open(WORKDIR / "doubleblind-reviews.json"))["reviews"]

MODELS = ["minimax/MiniMax-M3", "deepseek/deepseek-v4-flash"]
SHORT = {"minimax/MiniMax-M3": "M3", "deepseek/deepseek-v4-flash": "V4-Flash"}

# ========== 自动评分 ==========
def extract_code(text):
    m = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if m: return m.group(1).strip()
    m = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if m: return m.group(1).strip()
    return None

def grade_Q1_lru(answer):
    code = extract_code(answer)
    if not code: return {"score": 0, "max": 10, "note": "未找到代码块"}
    test = """
class _Tester:
    def __init__(self):
        self.cache = LRUCache(2)
    def run(self):
        results = []
        self.cache.put(1, 1); self.cache.put(2, 2)
        results.append(self.cache.get(1))  # 1
        self.cache.put(3, 3)  # 淘汰2
        results.append(self.cache.get(2))  # -1
        self.cache.put(4, 4)  # 淘汰1
        results.append(self.cache.get(1))  # -1
        results.append(self.cache.get(3))  # 3
        results.append(self.cache.get(4))  # 4
        expected = [1, -1, -1, 3, 4]
        ok = results == expected
        print(f"RESULTS {results} expected={expected} ok={ok}")
_t = _Tester(); _t.run()
"""
    full = code + "\n\n" + test
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(full); fp = f.name
    try:
        r = subprocess.run(["python3", fp], capture_output=True, text=True, timeout=10)
        out = r.stdout + r.stderr
        m = re.search(r"RESULTS\s*\[(.*?)\]", out, re.DOTALL)
        if not m:
            return {"score": 0, "max": 10, "note": f"代码运行失败: {out[:200]}"}
        if "ok=True" in out:
            return {"score": 10, "max": 10, "note": "LRU 全部 5 步通过"}
        elif "ok=False" in out:
            return {"score": 5, "max": 10, "note": f"LRU 部分通过: {m.group(0)[:100]}"}
        return {"score": 0, "max": 10, "note": "无法判定"}
    finally:
        Path(fp).unlink(missing_ok=True)

def grade_Q2_math(answer):
    """期望 '1' = log₂8=3 + √144=12 - 25 = -10? 等下 5²=25 → 3+12-25=-10; 期望值要重算。"""
    # 重新算: log₂(8) = 3, √144 = 12, 5² = 25, 3+12-25 = -10
    text = re.sub(r"[^\d\-]", " ", answer)
    nums = re.findall(r"-?\d+", text)
    if "-10" in nums or " -10" in answer:
        return {"score": 5, "max": 5, "note": "正确答案 -10"}
    # 兼容 -10 的不同写法
    for n in nums:
        try:
            if int(n) == -10:
                return {"score": 5, "max": 5, "note": f"包含 -10"}
        except: pass
    return {"score": 0, "max": 5, "note": f"未找到 -10，候选数字: {nums[:5]}"}

def grade_Q3_capital(answer):
    expected = ["堪培拉", "渥太华", "巴西利亚", "开罗", "曼谷"]
    # 变体
    variants = {
        "堪培拉": ["堪培拉", "Canberra"],
        "渥太华": ["渥太华", "Ottawa"],
        "巴西利亚": ["巴西利亚", "巴西利亞", "Brasília"],
        "开罗": ["开罗", "開羅", "Cairo"],
        "曼谷": ["曼谷", "Bangkok"],
    }
    hits = []
    for e in expected:
        if any(v in answer for v in variants[e]):
            hits.append(e)
    return {"score": len(hits), "max": 5, "note": f"{len(hits)}/5 首都正确: {hits}"}

def grade_Q4_hats(answer):
    # 期望答案"白色"
    has_white = "白色" in answer or "白" in answer
    has_reasoning = "第3" in answer and "第2" in answer and ("听到" in answer or "听完" in answer)
    score = 0
    if has_white: score += 3
    if has_reasoning: score += 2
    return {"score": score, "max": 5, "note": f"答案={has_white}, 推理链={has_reasoning}"}

def grade_Q5_reverse(answer):
    code = extract_code(answer)
    if not code: return {"score": 0, "max": 10, "note": "未找到代码"}
    test = """
_test = []
def expect(inp, exp):
    try:
        got = reverse_str(inp)
        ok = (got == exp)
    except Exception as e:
        got = f"EXC:{type(e).__name__}"
        ok = False
    _test.append((inp, exp, got, ok))
expect("hello", "olleh")
expect("", "")
expect("a", "a")
expect("ab", "ba")
expect("12345", "54321")
print("RESULTS", _test)
"""
    full = code + "\n\n" + test
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(full); fp = f.name
    try:
        r = subprocess.run(["python3", fp], capture_output=True, text=True, timeout=10)
        out = r.stdout + r.stderr
        m = re.search(r"RESULTS\s*\[(.*)\]", out, re.DOTALL)
        if not m:
            return {"score": 0, "max": 10, "note": f"运行失败: {out[:200]}"}
        results = re.findall(r"\(([^,]+),\s*([^,]+),\s*([^,]+),\s*(True|False)\)", m.group(1))
        if not results:
            return {"score": 0, "max": 10, "note": "解析失败"}
        passed = sum(1 for r in results if r[3] == "True")
        return {"score": passed * 2, "max": 10, "note": f"{passed}/5 用例通过"}
    finally:
        Path(fp).unlink(missing_ok=True)

def grade_open(answer):
    """开放题自动给基础分（按答复长度合理性），主要靠盲评。"""
    text = re.sub(r"\s", "", answer)
    n = len(text)
    if n < 20: return {"score": 1, "max": 5, "note": f"过短 ({n}字)"}
    if n > 800: return {"score": 3, "max": 5, "note": f"过长 ({n}字)"}
    return {"score": 3, "max": 5, "note": f"长度合理 ({n}字)"}

GRADERS = {
    "Q1_lru": grade_Q1_lru, "Q2_math": grade_Q2_math, "Q3_capital": grade_Q3_capital,
    "Q4_hats": grade_Q4_hats, "Q5_reverse": grade_Q5_reverse,
    "Q6_marketing": grade_open, "Q7_analysis": grade_open,
    "Q8_poem": grade_open, "Q9_dialogue": grade_open, "Q10_classical": grade_open,
}

# 自动评分
auto = {}
for m in MODELS:
    auto[m] = {}
    for tid, task in TASKS.items():
        ans = next((r for r in ANSWERS if r["model"]==m and r["task_id"]==tid), None)
        if not ans or not ans.get("ok"):
            auto[m][tid] = {"score": 0, "max": 0, "note": "无答案"}
            continue
        try:
            g = GRADERS[tid](ans["reply"])
        except Exception as e:
            g = {"score": 0, "max": 0, "note": f"grader 异常: {e}"}
        g["latency_s"] = ans.get("latency_s")
        g["usage"] = ans.get("usage", {})
        g["reply_length"] = len(ans.get("reply",""))
        auto[m][tid] = g

# 盲评揭盲聚合
peer = defaultdict(list)  # model -> [(judge, task, overall)]
for rev in REVIEWS:
    if not rev.get("ok"): continue
    ab_map = rev["ab_map"]  # A=model, B=model
    judge = rev["judge"]
    for letter in ["A", "B"]:
        s = rev["scores"].get(letter, {})
        if not isinstance(s, dict): continue
        target = ab_map.get(letter)
        if not target: continue
        try:
            overall = float(s.get("overall", 0))
        except (TypeError, ValueError): continue
        peer[target].append({"judge": judge, "task": rev["task_id"], "overall": overall, "details": s})

# 写汇总
summary = {"auto": auto, "peer": {m: peer[m] for m in MODELS}}
for m in MODELS:
    summary["peer_avg_per_task"] = {} if "peer_avg_per_task" not in summary else summary["peer_avg_per_task"]
    summary["peer_avg_per_task"][m] = {}
    by_task = defaultdict(list)
    for p in peer[m]:
        by_task[p["task"]].append(p["overall"])
    for tid in TASKS:
        vals = by_task.get(tid, [])
        summary["peer_avg_per_task"][m][tid] = round(sum(vals)/len(vals), 2) if vals else None

# 性能
perf = {}
for m in MODELS:
    perf[m] = {}
    for tid in TASKS:
        r = next((x for x in ANSWERS if x["model"]==m and x["task_id"]==tid), None)
        if r and r.get("ok"):
            perf[m][tid] = {"latency_s": r["latency_s"], "in": r.get("usage",{}).get("input",0), "out": r.get("usage",{}).get("output",0), "len": len(r.get("reply",""))}

# ===== 生成报告 =====
md = []
md.append("# M3 vs V4-Flash 随机双盲测试报告")
md.append(f"\n**测试时间**: 2026-06-03  \n**发起**: Lee  \n**执行**: 🦞 小龙虾\n")

md.append("## 0. 测试设计")
md.append("")
md.append("**被测 2 模型**：M3 (主) vs V4-Flash (fallback)")
md.append("")
md.append("**10 任务**（5 客观 + 5 开放）：")
for tid, t in TASKS.items():
    md.append(f"- **{tid}** [{t['type']}] {t['domain']}: {t['prompt'][:80]}...")
md.append("")
md.append("**双盲机制**：")
md.append("1. 答案标 A/B 编号（按模型名 sorted 稳定映射）")
md.append("2. 裁判只看到 A/B 编号 + 答案内容，**不知道作者模型**")
md.append("3. 2 裁判（M2.7 + V4-Pro）独立盲评，互不知对方评分")
md.append("4. 揭盲后按模型聚合")
md.append("")
md.append("**评分方式**：")
md.append("- 客观题（Q1-Q5）：自动判分，跑代码 / 答案匹配 / 事实覆盖")
md.append("- 开放题（Q6-Q10）：盲评 4 维度（correctness/completeness/expression/overall）× 2 裁判")
md.append("")

md.append("## 1. 客观题自动评分（5 题满分 35）")
md.append("")
md.append("| 任务 | M3 | V4-Flash |")
md.append("|------|----|---------:|")
objective_tasks = ["Q1_lru", "Q2_math", "Q3_capital", "Q4_hats", "Q5_reverse"]
for tid in objective_tasks:
    m3g = auto["minimax/MiniMax-M3"][tid]
    v4g = auto["deepseek/deepseek-v4-flash"][tid]
    md.append(f"| **{tid}** | {m3g.get('score',0)}/{m3g.get('max',0)} ({m3g.get('note','')[:30]}) | {v4g.get('score',0)}/{v4g.get('max',0)} ({v4g.get('note','')[:30]}) |")
m3_obj = sum(auto["minimax/MiniMax-M3"][tid].get("score",0) for tid in objective_tasks)
v4_obj = sum(auto["deepseek/deepseek-v4-flash"][tid].get("score",0) for tid in objective_tasks)
md.append(f"| **小计** | **{m3_obj}/35** | **{v4_obj}/35** |")
md.append("")

md.append("## 2. 开放题盲评（5 题，2 裁判 × 5 分 = 满分 50）")
md.append("")
md.append("**每题两位裁判（M2.7 / V4-Pro）各给 1-5 分，取平均。**")
md.append("")
md.append("| 任务 | M3 (M2.7评 / V4-Pro评 / 均) | V4-Flash (M2.7评 / V4-Pro评 / 均) |")
md.append("|------|----------------------------|--------------------------------|")
open_tasks = ["Q6_marketing", "Q7_analysis", "Q8_poem", "Q9_dialogue", "Q10_classical"]
m3_open_total = 0; v4_open_total = 0
for tid in open_tasks:
    by_judge_m3 = defaultdict(list); by_judge_v4 = defaultdict(list)
    for p in peer["minimax/MiniMax-M3"]:
        if p["task"] == tid: by_judge_m3[p["judge"]].append(p["overall"])
    for p in peer["deepseek/deepseek-v4-flash"]:
        if p["task"] == tid: by_judge_v4[p["judge"]].append(p["overall"])
    def fmt(by_judge, model):
        s = ""
        for j in ["minimax/MiniMax-M2.7", "deepseek/deepseek-v4-pro"]:
            vals = by_judge.get(j, [])
            avg = sum(vals)/len(vals) if vals else None
            s += f"{avg:.1f}/" if avg is not None else "—/"
        # 总平均
        all_vals = [v for vs in by_judge.values() for v in vs]
        all_avg = sum(all_vals)/len(all_vals) if all_vals else 0
        return s.rstrip("/"), all_avg
    m3_str, m3_avg = fmt(by_judge_m3, "M3")
    v4_str, v4_avg = fmt(by_judge_v4, "V4-Flash")
    m3_open_total += m3_avg
    v4_open_total += v4_avg
    md.append(f"| **{tid}** | {m3_str} → **{m3_avg:.2f}** | {v4_str} → **{v4_avg:.2f}** |")
md.append(f"| **开放题总分 (满分 25)** | **{m3_open_total:.2f}** | **{v4_open_total:.2f}** |")
md.append("")

md.append("## 3. 性能指标")
md.append("")
md.append("| 模型 | 总延迟 (s) | 平均延迟 (s) | 总输出 token | 平均输出 token |")
md.append("|------|------------|--------------|--------------|---------------|")
for m in MODELS:
    lats = [p["latency_s"] for p in perf[m].values() if p.get("latency_s")]
    outs = [p["out"] for p in perf[m].values()]
    md.append(f"| **{SHORT[m]}** | {sum(lats):.1f} | {sum(lats)/len(lats):.2f} | {sum(outs):,} | {sum(outs)/len(outs):.0f} |")
md.append("")

# 综合
md.append("## 4. 综合评分")
md.append("")
m3_auto_total = sum(auto["minimax/MiniMax-M3"][t].get("score",0) for t in TASKS)
v4_auto_total = sum(auto["deepseek/deepseek-v4-flash"][t].get("score",0) for t in TASKS)
m3_obj = sum(auto["minimax/MiniMax-M3"][t].get("score",0) for t in objective_tasks)
v4_obj = sum(auto["deepseek/deepseek-v4-flash"][t].get("score",0) for t in objective_tasks)

# 客观 35 分 + 开放 25 分 = 60 分
m3_total = m3_obj + m3_open_total
v4_total = v4_obj + v4_open_total
md.append("| 模型 | 客观 (35) | 开放 (25) | 综合 (60) | 百分比 |")
md.append("|------|----------|----------|----------|--------|")
md.append(f"| **M3** | {m3_obj} | {m3_open_total:.2f} | **{m3_total:.2f}** | {m3_total/60*100:.1f}% |")
md.append(f"| **V4-Flash** | {v4_obj} | {v4_open_total:.2f} | **{v4_total:.2f}** | {v4_total/60*100:.1f}% |")
md.append("")
if m3_total > v4_total:
    winner = "M3"; diff = m3_total - v4_total
elif v4_total > m3_total:
    winner = "V4-Flash"; diff = v4_total - m3_total
else:
    winner = "平局"; diff = 0
md.append(f"**结论**：{winner} 胜出（差 {diff:.2f} 分 / 60）\n")

# 揭盲后观察
md.append("## 5. 揭盲后观察（不构成选型依据）")
md.append("")
md.append(f"- 客观题：M3 = {m3_obj}/35, V4-Flash = {v4_obj}/35 — {'V4-Flash 略强' if v4_obj>m3_obj else 'M3 略强' if m3_obj>v4_obj else '平局'}")
md.append(f"- 开放题盲评：M3 = {m3_open_total:.2f}/25, V4-Flash = {v4_open_total:.2f}/25 — {'V4-Flash 略强' if v4_open_total>m3_open_total else 'M3 略强' if m3_open_total>v4_open_total else '平局'}")
md.append("")
md.append("**局限**：")
md.append("- 仅 10 任务，单题差异主导排名")
md.append("- 2 裁判（M2.7/V4-Pro）样本不足，裁判自身偏好未消解")
md.append("- 客观题 Q2/Q4 答案范围窄（单数字/单字），M3/V4-Flash 都易全对或全错")
md.append("- 开放题盲评 1-5 分制粒度粗")
md.append("")

# 写文件
out_md = WORKDIR / "doubleblind-report.md"
open(out_md, "w").write("\n".join(md))
json.dump(summary, open(WORKDIR / "doubleblind-summary.json", "w"), indent=2, ensure_ascii=False)
print(f"=== 报告已生成: {out_md} ===")
print(f"长度: {len('\n'.join(md))} 字符")
print(f"\n=== 关键结果 ===")
print(f"M3:        客观 {m3_obj}/35, 开放 {m3_open_total:.2f}/25, 综合 {m3_total:.2f}/60 ({m3_total/60*100:.1f}%)")
print(f"V4-Flash:  客观 {v4_obj}/35, 开放 {v4_open_total:.2f}/25, 综合 {v4_total:.2f}/60 ({v4_total/60*100:.1f}%)")
print(f"胜出: {winner}")
