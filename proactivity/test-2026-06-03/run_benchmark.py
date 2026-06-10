#!/usr/bin/env python3
"""
Model benchmark runner.
Calls each model × each task via `openclaw agent --model`, saves raw answers.
"""
import json
import subprocess
import time
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
WORKDIR = Path("/root/.openclaw/workspace/proactivity/test-2026-06-03")
TASKS_FILE = WORKDIR / "tasks.json"
RAW_FILE = WORKDIR / "raw-answers.json"

MODELS = [
    "minimax/MiniMax-M3",
    "minimax/MiniMax-M2.7",
    "deepseek/deepseek-v4-flash",
    "deepseek/deepseek-v4-pro",
]

def run_one(model, prompt, timeout=180):
    """Call openclaw agent and return dict with response, latency, token info."""
    t0 = time.time()
    try:
        result = subprocess.run(
            [
                "openclaw", "agent",
                "--agent", "main",
                "--model", model,
                "--message", prompt,
                "--thinking", "off",
                "--json",
            ],
            capture_output=True, text=True, timeout=timeout
        )
        latency = time.time() - t0
        out = result.stdout.strip()
        err = result.stderr.strip()
        if result.returncode != 0:
            return {"ok": False, "error": f"exit {result.returncode}: {err[:500]}", "latency_s": latency}
        # 解析 JSON 输出
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return {"ok": False, "error": f"non-json output", "stdout": out[:500], "latency_s": latency}
        # 提取答复文本和 token
        result_obj = data.get("result", {})
        payloads = result_obj.get("payloads", [])
        reply = payloads[0].get("text", "") if payloads else ""
        meta = result_obj.get("meta", {})
        agent_meta = meta.get("agentMeta", {})
        usage = agent_meta.get("lastCallUsage") or agent_meta.get("usage") or {}
        return {
            "ok": True,
            "reply": reply,
            "latency_s": round(latency, 2),
            "latency_ms": meta.get("durationMs"),
            "usage": usage,
            "model_id": agent_meta.get("model", model),
            "provider": agent_meta.get("provider", ""),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s", "latency_s": timeout}

def main():
    data = json.load(open(TASKS_FILE))
    tasks = data["tasks"]
    
    if RAW_FILE.exists():
        raw = json.load(open(RAW_FILE))
    else:
        raw = {"started_at": datetime.now(CST).isoformat(), "results": []}
    
    # 跑所有 16 个组合
    for model in MODELS:
        for task in tasks:
            # 跳过已跑过的
            done = [r for r in raw["results"]
                    if r["model"] == model and r["task_id"] == task["id"]]
            if done:
                print(f"  [SKIP] {model} × {task['id']} (已有结果)")
                continue
            print(f"  [RUN]  {model} × {task['id']} ...", end="", flush=True)
            res = run_one(model, task["prompt"])
            res["model"] = model
            res["task_id"] = task["id"]
            res["timestamp"] = datetime.now(CST).isoformat()
            raw["results"].append(res)
            if res["ok"]:
                print(f" OK ({res['latency_s']}s, {len(res.get('reply',''))} 字)")
            else:
                print(f" FAIL: {res.get('error','')[:80]}")
            # 每条都保存
            json.dump(raw, open(RAW_FILE, "w"), ensure_ascii=False, indent=2)
    
    raw["finished_at"] = datetime.now(CST).isoformat()
    json.dump(raw, open(RAW_FILE, "w"), ensure_ascii=False, indent=2)
    print(f"\n=== 完成: {len(raw['results'])} 条结果 ===")
    ok = sum(1 for r in raw["results"] if r["ok"])
    print(f"成功 {ok} / 失败 {len(raw['results'])-ok}")

if __name__ == "__main__":
    main()
