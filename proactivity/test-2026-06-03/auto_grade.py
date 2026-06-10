#!/usr/bin/env python3
"""自动评分（v2）：T1 代码 / T2 摘要 / T3 创作 / T4 数字谜题"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

WORKDIR = Path("/root/.openclaw/workspace/proactivity/test-2026-06-03")
RAW = WORKDIR / "raw-answers.json"
TASKS = json.load(open(WORKDIR / "tasks.json"))["tasks"]
ANSWERS = {f"{r['model']}__{r['task_id']}": r for r in json.load(open(RAW))["results"]}

def extract_code(text):
    m = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if m: return m.group(1).strip()
    m = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if m: return m.group(1).strip()
    return None

def grade_T1(answer):
    code = extract_code(answer)
    if not code:
        return {"score": 0, "max": 10, "note": "未找到 Python 代码块"}
    test_cases = """
_test_results = []
_expected = [(2, True), (17, True), (1, False), (-7, False), (100, False)]
for inp, exp in _expected:
    try:
        got = is_prime(inp)
        ok = (got == exp)
    except Exception as e:
        got = f"EXC:{type(e).__name__}"
        ok = False
    _test_results.append((inp, exp, got, ok))
print("RESULTS", _test_results)
"""
    full = code + "\n\n" + test_cases
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(full); fp = f.name
    try:
        r = subprocess.run(["python3", fp], capture_output=True, text=True, timeout=10)
        out = r.stdout + r.stderr
        m = re.search(r"RESULTS\s*\[(.*)\]", out, re.DOTALL)
        if not m:
            return {"score": 0, "max": 10, "note": f"代码运行失败: {out[:200]}"}
        results = re.findall(r"\((\-?\d+),\s*(True|False),\s*('?[^,]+'?(?:\:[^,]+)?),\s*(True|False)\)", m.group(1))
        if not results:
            return {"score": 0, "max": 10, "note": f"解析结果失败: {m.group(1)[:200]}"}
        passed = sum(1 for r in results if r[3] == "True")
        return {"score": passed * 2, "max": 10, "note": f"{passed}/5 用例通过", "details": results}
    finally:
        Path(fp).unlink(missing_ok=True)

def grade_T2(answer):
    must = ["小李", "深圳", "StarFeather", "1万", "30天", "100KB", "22%", "3家上市公司", "v2.0", "2026年第四季度"]
    variants = {
        "1万": ["1万", "10000", "一万"],
        "30天": ["30天", "三十天"],
        "100KB": ["100KB", "100kb", "100 KB", "100 kb"],
        "22%": ["22%", "22 %"],
        "3家上市公司": ["3家上市公司", "3家上市", "三家上市公司", "三家"],
        "2026年第四季度": ["2026年第四季度", "2026 Q4", "2026年Q4", "2026年底", "Q4 2026", "2026年 第四季度"],
    }
    hits, misses = [], []
    for fact in must:
        candidates = variants.get(fact, [fact])
        if any(c in answer for c in candidates):
            hits.append(fact)
        else:
            misses.append(fact)
    char_count = len(re.sub(r"\s", "", answer))
    # 字数合规：≤150 字（按题目要求）
    length_ok = 0 <= char_count <= 160  # 给点容差
    return {
        "score": len(hits),
        "max": 10,
        "note": f"{len(hits)}/10 关键事实；字数 {char_count} ({'合规' if length_ok else '超'})",
        "hits": hits, "misses": misses, "length_ok": length_ok,
    }

def grade_T3(answer):
    text = re.sub(r"\s", "", answer)
    chars = len(text)
    in_range = 150 <= chars <= 200
    has_hook = bool(re.search(r"[？?！!]|[你]知道吗|想象|如果|猜", text))
    forbidden = ["大家好", "欢迎收听", "今天我们", "我是"]
    bad = [f for f in forbidden if f in text]
    # 评分细则
    score = 0
    if in_range: score += 3
    if has_hook: score += 1
    if not bad: score += 1
    return {
        "score": score, "max": 5,
        "note": f"字数 {chars} ({'合规' if in_range else '不合规 150-200'}); 钩子={has_hook}; 禁词={bad}",
    }

def grade_T4(answer):
    """数字谜题：找 abc 三数，求和=999，每个数字 1-9 用且只用一次"""
    # 提取三个三位数
    nums = re.findall(r"\b([1-9]\d{2})\b", answer)
    # 去重
    seen = set()
    unique_nums = []
    for n in nums:
        if n not in seen:
            seen.add(n); unique_nums.append(n)
    # 找三数 a+b+c=999
    found = None
    for i in range(len(unique_nums)):
        for j in range(i+1, len(unique_nums)):
            for k in range(j+1, len(unique_nums)):
                a, b, c = int(unique_nums[i]), int(unique_nums[j]), int(unique_nums[k])
                if a + b + c == 999:
                    # 检查 9 数字不重复
                    digits = str(a) + str(b) + str(c)
                    if len(digits) == 9 and len(set(digits)) == 9 and '0' not in digits:
                        found = (a, b, c); break
            if found: break
        if found: break
    if found:
        return {"score": 5, "max": 5, "note": f"找到 {found[0]}+{found[1]}+{found[2]}=999，9 数字不重复", "found": found}
    else:
        return {"score": 0, "max": 5, "note": f"未找到合法解 (候选: {unique_nums[:6]})"}

GRADERS = {"T1_code": grade_T1, "T2_summary": grade_T2, "T3_creative": grade_T3, "T4_logic": grade_T4}

results = {}
for model in ["minimax/MiniMax-M3", "minimax/MiniMax-M2.7", "deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro"]:
    results[model] = {}
    for task in TASKS:
        key = f"{model}__{task['id']}"
        ans = ANSWERS[key]
        if not ans.get("ok"):
            results[model][task["id"]] = {"error": ans.get("error"), "score": 0, "max": 0}
            continue
        grader = GRADERS[task["id"]]
        try:
            g = grader(ans["reply"])
        except Exception as e:
            g = {"score": 0, "max": 0, "note": f"grader 异常: {e}"}
        g["reply_preview"] = ans["reply"][:200]
        g["latency_s"] = ans.get("latency_s")
        g["usage"] = ans.get("usage", {})
        g["reply_length"] = len(ans.get("reply", ""))
        results[model][task["id"]] = g

out = WORKDIR / "auto-grades.json"
json.dump(results, open(out, "w"), indent=2, ensure_ascii=False)
print(f"=== 自动评分完成 ===\n")
print(f"{'模型':<28} {'T1代码':>10} {'T2摘要':>10} {'T3创作':>10} {'T4推理':>10} {'总分':>10}")
totals = {}
for m, ts in results.items():
    parts = []
    s = 0
    for t in ["T1_code", "T2_summary", "T3_creative", "T4_logic"]:
        v = ts[t]
        parts.append(f"{v.get('score',0):>3}/{v.get('max',0):<2}")
        s += v.get("score", 0)
    totals[m] = s
    print(f"{m:<28} {parts[0]:>10} {parts[1]:>10} {parts[2]:>10} {parts[3]:>10} {s:>10}")
print()
print("排名：")
for i, (m, s) in enumerate(sorted(totals.items(), key=lambda x: -x[1]), 1):
    print(f"  {i}. {m}: {s}/30")
