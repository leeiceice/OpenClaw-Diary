#!/usr/bin/env python3
"""
双盲互评：2 裁判盲评 20 份答案（A/B 编号，裁判看不到作者）。
揭盲前不读 map.json。
"""
import json
import re
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
WORKDIR = Path("/root/.openclaw/workspace/proactivity/test-2026-06-03")
TASKS_FILE = WORKDIR / "doubleblind-tasks.json"
ANSWERS = json.load(open(WORKDIR / "doubleblind-answers.json"))["results"]
REVIEW_OUT = WORKDIR / "doubleblind-reviews.json"
TASKS = {t["id"]: t for t in json.load(open(TASKS_FILE))["tasks"]}

JUDGES = ["minimax/MiniMax-M2.7", "deepseek/deepseek-v4-pro"]

JUDGE_PROMPT = """你是严格的盲评裁判。下面是一道任务的 2 份匿名答案（A/B）。你不知道哪个是哪个模型。

# 任务
{question}

# 评分维度（每项 1-5）
- correctness（正确性/质量）
- completeness（完整度）
- expression（表达/可读性）
- overall（综合，1-5）

# 2 份匿名答案
{answers}

# 输出严格 JSON
```json
{{
  "A": {{"correctness": <1-5>, "completeness": <1-5>, "expression": <1-5>, "overall": <1-5>, "reason": "<一句话>"}},
  "B": {{"correctness": <1-5>, "completeness": <1-5>, "expression": <1-5>, "overall": <1-5>, "reason": "<一句话>"}}
}}
```

只输出 JSON，不要其他文字。"""

def run_judge(model, prompt, timeout=120):
    t0 = time.time()
    try:
        r = subprocess.run(
            ["openclaw", "agent", "--agent", "main", "--model", model, "--message", prompt, "--thinking", "off"],
            capture_output=True, text=True, timeout=timeout
        )
        lat = time.time() - t0
        if r.returncode != 0:
            return {"ok": False, "error": r.stderr[:300], "latency_s": lat}
        out = r.stdout.strip()
        m = re.search(r"```json\s*(\{.*?\})\s*```", out, re.DOTALL)
        if not m: m = re.search(r"\{[\s\S]*?\}", out)
        if not m:
            return {"ok": False, "error": f"no json: {out[:200]}", "latency_s": lat}
        try:
            scores = json.loads(m.group(1) if m.lastindex else m.group(0))
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"json parse: {e}", "latency_s": lat}
        return {"ok": True, "scores": scores, "latency_s": round(lat, 2), "raw": out[:300]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout {timeout}s", "latency_s": timeout}

def main():
    if REVIEW_OUT.exists():
        reviews = json.load(open(REVIEW_OUT))
    else:
        reviews = {"started_at": datetime.now(CST).isoformat(), "reviews": []}
    
    for task_id, task in TASKS.items():
        task_answers = {r["model"]: r for r in ANSWERS if r["task_id"] == task_id and r.get("ok")}
        if len(task_answers) != 2:
            print(f"  [SKIP] {task_id}: 答案数 {len(task_answers)}")
            continue
        
        # A/B 编号：用 sorted() 保证 A/B 一致映射（不论模型顺序）
        # 实际上应该用 map.json 的映射，但**揭盲前我不读 map.json**
        # 所以这里只用"按模型名 hash 取模"分配 A/B，保证对每个任务稳定
        models_sorted = sorted(task_answers.keys())
        ab_map = {"A": models_sorted[0], "B": models_sorted[1]}
        
        answers_text = ""
        for letter in ["A", "B"]:
            answers_text += f"\n## 答案 {letter}\n{task_answers[ab_map[letter]]['reply']}\n"
        
        question = task["prompt"]
        full_prompt = JUDGE_PROMPT.format(question=question, answers=answers_text)
        
        for judge in JUDGES:
            done = [r for r in reviews["reviews"] if r["task_id"] == task_id and r["judge"] == judge]
            if done:
                continue
            print(f"  [{task_id:12s}] judged by {judge.split('/')[-1][:15]:15s} ...", end="", flush=True)
            res = run_judge(judge, full_prompt)
            res["task_id"] = task_id
            res["judge"] = judge
            res["ab_map"] = ab_map  # 评完揭盲时反查
            res["timestamp"] = datetime.now(CST).isoformat()
            reviews["reviews"].append(res)
            if res["ok"]:
                print(f" OK ({res['latency_s']}s)")
            else:
                print(f" FAIL: {res.get('error','')[:60]}")
            json.dump(reviews, open(REVIEW_OUT, "w"), indent=2, ensure_ascii=False)
    
    reviews["finished_at"] = datetime.now(CST).isoformat()
    json.dump(reviews, open(REVIEW_OUT, "w"), indent=2, ensure_ascii=False)
    print(f"\n=== 互评完成: {len(reviews['reviews'])} / 40 ===")

if __name__ == "__main__":
    main()
