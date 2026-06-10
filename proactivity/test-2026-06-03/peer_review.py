#!/usr/bin/env python3
"""
互评（盲评）：4 个模型互评 4 个任务的答案。
- 答案匿名（A/B/C/D 编号，不显示原模型）
- 每个模型不能评自己的答案
- 评分 1-5 + 简短理由
"""
import json
import random
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
WORKDIR = Path("/root/.openclaw/workspace/proactivity/test-2026-06-03")
RAW = json.load(open(WORKDIR / "raw-answers.json"))["results"]
TASKS = {t["id"]: t for t in json.load(open(WORKDIR / "tasks.json"))["tasks"]}
OUT = WORKDIR / "peer-reviews.json"

MODELS = [
    "minimax/MiniMax-M3",
    "minimax/MiniMax-M2.7",
    "deepseek/deepseek-v4-flash",
    "deepseek/deepseek-v4-pro",
]

JUDGE_PROMPT = """你是严格的代码/文本质量评审。下面是一道任务的 4 份匿名答案（A/B/C/D）。

# 任务
{question}

# 评分维度（1-5 分）
- 正确性：答案是否解决了任务
- 完成度：是否覆盖任务要求的所有方面
- 表达质量：组织/可读性/无废话
- 鲁棒性：边界情况处理、是否考虑反例
- 总分（1-5）：综合评价

# 4 份匿名答案
{answers}

# 输出格式（严格按此 JSON）
```json
{{
  "A": {{"correctness": <1-5>, "completeness": <1-5>, "expression": <1-5>, "robustness": <1-5>, "total": <1-5>, "reason": "<一句话>"}},
  "B": {{...同上...}},
  "C": {{...同上...}},
  "D": {{...同上...}}
}}
```

只输出 JSON，不要其他文字。"""

def run_judge(model, prompt, timeout=120):
    t0 = time.time()
    try:
        result = subprocess.run(
            ["openclaw", "agent", "--agent", "main", "--model", model, "--message", prompt, "--thinking", "off"],
            capture_output=True, text=True, timeout=timeout
        )
        latency = time.time() - t0
        out = result.stdout.strip()
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr[:300], "latency_s": latency}
        # 提取 JSON
        import re
        m = re.search(r"```json\s*(\{.*?\})\s*```", out, re.DOTALL)
        if not m:
            m = re.search(r"\{[\s\S]*?\}", out)
        if not m:
            return {"ok": False, "error": f"未找到 JSON: {out[:200]}", "latency_s": latency}
        try:
            scores = json.loads(m.group(1) if m.lastindex else m.group(0))
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"JSON 解析失败: {e}\n{m.group(0)[:200]}", "latency_s": latency}
        return {"ok": True, "scores": scores, "latency_s": round(latency, 2), "raw": out[:500]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout {timeout}s", "latency_s": timeout}

def main():
    if OUT.exists():
        reviews = json.load(open(OUT))
    else:
        reviews = {"started_at": datetime.now(CST).isoformat(), "reviews": []}
    
    random.seed(42)  # 固定 shuffle，保证可复现
    
    for task_id, task in TASKS.items():
        # 找该任务 4 个模型的答案
        task_answers = {r["model"]: r for r in RAW if r["task_id"] == task_id and r.get("ok")}
        if len(task_answers) != 4:
            print(f"  [SKIP] {task_id}: 答案数 {len(task_answers)} != 4")
            continue
        
        # 匿名：给 4 个模型答案随机分配 A/B/C/D
        models_list = list(task_answers.keys())
        random.shuffle(models_list)  # 同一个 task 内部 shuffle
        # 记录映射
        anon_map = {chr(65+i): m for i, m in enumerate(models_list)}  # A->model
        # 让 4 个裁判都看到**同一套** A/B/C/D 映射（保证可比）
        
        # 拼 prompt
        answers_text = ""
        for letter in ["A", "B", "C", "D"]:
            ans = task_answers[anon_map[letter]]["reply"]
            answers_text += f"\n## 答案 {letter}\n{ans}\n"
        question = task["prompt"]
        full_prompt = JUDGE_PROMPT.format(question=question, answers=answers_text)
        
        for judge_model in MODELS:
            # 跳过自评
            if judge_model == anon_map["A"] and judge_model == anon_map["B"] and judge_model == anon_map["C"] and judge_model == anon_map["D"]:
                continue  # 防御性，不会发生
            # 简化：如果 judge 是答案提供方之一 → 跳过
            if judge_model in anon_map.values():
                # 还是要评的，去掉 judge 自己那份的 A/B/C/D 编号？
                # 简单处理：让 judge 评全 4 份，事后剔除自评
                pass
            
            # 跳过已评
            done = [r for r in reviews["reviews"] if r["task_id"] == task_id and r["judge"] == judge_model]
            if done:
                print(f"  [SKIP] {task_id} judged by {judge_model} (已有)")
                continue
            
            print(f"  [RUN]  {task_id} judged by {judge_model} ...", end="", flush=True)
            res = run_judge(judge_model, full_prompt)
            res["task_id"] = task_id
            res["judge"] = judge_model
            res["anon_map"] = anon_map  # A=哪个模型
            res["timestamp"] = datetime.now(CST).isoformat()
            reviews["reviews"].append(res)
            if res["ok"]:
                print(f" OK ({res['latency_s']}s)")
            else:
                print(f" FAIL: {res.get('error','')[:60]}")
            json.dump(reviews, open(OUT, "w"), ensure_ascii=False, indent=2)
    
    reviews["finished_at"] = datetime.now(CST).isoformat()
    json.dump(reviews, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"\n=== 互评完成: {len(reviews['reviews'])} 次评审 ===")

if __name__ == "__main__":
    main()
