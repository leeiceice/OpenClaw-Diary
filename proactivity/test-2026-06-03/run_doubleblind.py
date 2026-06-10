#!/usr/bin/env python3
"""
双盲测试 v2: 收集 2 模型 × 10 任务 = 20 份答案，生成 A/B 随机映射（不存到模型可见处）。
"""
import json
import random
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
WORKDIR = Path("/root/.openclaw/workspace/proactivity/test-2026-06-03")
TASKS_FILE = WORKDIR / "doubleblind-tasks.json"
ANSWERS = WORKDIR / "doubleblind-answers.json"
MAP_FILE = WORKDIR / "doubleblind-map.json"  # 揭盲用，答案收集阶段不读

MODELS = ["minimax/MiniMax-M3", "deepseek/deepseek-v4-flash"]

def run_one(model, prompt, timeout=180):
    t0 = time.time()
    try:
        result = subprocess.run(
            ["openclaw", "agent", "--agent", "main", "--model", model, "--message", prompt, "--thinking", "off", "--json"],
            capture_output=True, text=True, timeout=timeout
        )
        latency = time.time() - t0
        out = result.stdout.strip()
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr[:300], "latency_s": latency}
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return {"ok": False, "error": "non-json", "raw": out[:200], "latency_s": latency}
        result_obj = data.get("result", {})
        payloads = result_obj.get("payloads", [])
        reply = payloads[0].get("text", "") if payloads else ""
        meta = result_obj.get("meta", {})
        am = meta.get("agentMeta", {})
        usage = am.get("lastCallUsage") or am.get("usage") or {}
        return {"ok": True, "reply": reply, "latency_s": round(latency, 2), "latency_ms": meta.get("durationMs"), "usage": usage, "model_id": am.get("model", model)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "latency_s": timeout}

def main():
    tasks = json.load(open(TASKS_FILE))["tasks"]
    if ANSWERS.exists():
        data = json.load(open(ANSWERS))
    else:
        data = {"started_at": datetime.now(CST).isoformat(), "results": []}
    
    # 双盲映射：每个任务内 2 模型 → A/B（每次独立 shuffle，但 seed 固定可复现）
    # 映射表生成一次，写到独立文件
    if not MAP_FILE.exists():
        random.seed(20260603)  # 固定 seed 保证可复现
        map_data = {"created_at": datetime.now(CST).isoformat(), "seed": 20260603, "mapping": {}}
        for task in tasks:
            labels = ["A", "B"]
            shuffled = labels.copy()
            random.shuffle(shuffled)
            map_data["mapping"][task["id"]] = dict(zip(shuffled, MODELS))  # {"A": "model1", "B": "model2"}
        json.dump(map_data, open(MAP_FILE, "w"), indent=2, ensure_ascii=False)
        print(f"映射表已生成: {MAP_FILE}")
    
    # 跑所有 20 个
    for model in MODELS:
        for task in tasks:
            done = [r for r in data["results"] if r["model"] == model and r["task_id"] == task["id"]]
            if done:
                continue
            print(f"  [{model.split('/')[-1][:15]:15s}] × {task['id']:12s} ...", end="", flush=True)
            res = run_one(model, task["prompt"])
            res["model"] = model
            res["task_id"] = task["id"]
            res["timestamp"] = datetime.now(CST).isoformat()
            data["results"].append(res)
            if res["ok"]:
                print(f" OK ({res['latency_s']}s, {len(res.get('reply',''))}字)")
            else:
                print(f" FAIL: {res.get('error','')[:60]}")
            json.dump(data, open(ANSWERS, "w"), indent=2, ensure_ascii=False)
    
    data["finished_at"] = datetime.now(CST).isoformat()
    json.dump(data, open(ANSWERS, "w"), indent=2, ensure_ascii=False)
    print(f"\n=== 收集完成: {len(data['results'])} 条 ===")

if __name__ == "__main__":
    main()
