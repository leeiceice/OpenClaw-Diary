#!/usr/bin/env python3
"""
记忆 + 搜索系统健康检查脚本（纯读测试）

来源：2026-06-05 16:30 Lee 决策（方案 B：脚本级、半自动）
被调用方：heartbeat-maintenance (52f5f99e) 每小时

设计原则：
- 纯读：不动 MEMORY.md、不写测试数据、不推送飞书
- 3 个独立用例：RRF 拉平检测 / 已知问题命中 / 跨文件命中
- 失败立即退出 + 输出 JSON，HEARTBEAT 检测到再决定推哪个群
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 强制从 _timezone 导入
sys.path.insert(0, str(Path(__file__).parent))
from _timezone import CST

WORKSPACE = Path("~/.openclaw/workspace").expanduser()
WORKSPACE_SCRIPTS = WORKSPACE / "scripts"

# ── 测试用例（与 memory-search-health.md 规范保持一致）──
TEST_CASES = [
    {
        "name": "RRF 拉平检测（应 score > 10）",
        "query": "Path expanduser 脚本 bug",
        "expect_path": "self-improving/domains/cron-management.md",
        "expect_score_min": 10.0,
    },
    {
        "name": "systemEvent 推送动作（应在 cron-management / corrections / memory-search-health）",
        "query": "is_requested 不等于",
        "expect_paths": [
            "self-improving/domains/cron-management.md",
            "self-improving/corrections.md",
            "self-improving/domains/memory-search-health.md",
        ],
        "expect_score_min": 1.0,
    },
    {
        "name": "Token Plan 限流（应在 corrections 或 weekly-evolution-report）",
        "query": "Token Plan 限流",
        "expect_score_min": 1.0,
    },
]

# ── 失败阈值（参考 memory-search-health.md 第 4 节）──
RRF_LAMINATED_SCORE_MAX = 1.0  # score < 1 即被压扁特征
HEALTH_SCORE_MIN = 5.0  # 真实 BM25 命中应 > 5


def run_memory_search(query: str) -> dict:
    """调 memory_search.py 拿 JSON 结果"""
    import subprocess
    try:
        result = subprocess.run(
            ["python3", str(WORKSPACE_SCRIPTS / "memory_search.py"), query],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {"error": f"exit_code={result.returncode}", "stderr": result.stderr[:500]}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"error": "timeout_30s"}
    except json.JSONDecodeError as e:
        return {"error": f"json_decode_failed: {e}"}
    except Exception as e:
        return {"error": f"exception: {type(e).__name__}: {e}"}


def check_rrf_laminated(results: list) -> tuple[bool, str]:
    """检查 RRF 是否被压扁（score 全在 0.01-0.04）"""
    if not results:
        return False, "no_results"
    top = results[0]
    score = top.get("score", 0)
    fused_by = top.get("_fused_by", "unknown")
    if score < RRF_LAMINATED_SCORE_MAX:
        return False, f"score={score:.4f} 被压扁（RRF 拉平 bug 特征），_fused_by={fused_by}"
    return True, f"score={score:.4f} 健康"


def check_test_case(tc: dict) -> dict:
    """跑单个测试用例"""
    result = run_memory_search(tc["query"])
    if "error" in result:
        return {
            "name": tc["name"],
            "ok": False,
            "reason": f"search 失败: {result['error']}",
            "query": tc["query"],
        }

    results = result.get("results", [])
    if not results:
        return {
            "name": tc["name"],
            "ok": False,
            "reason": "无 results 返回",
            "query": tc["query"],
        }

    # RRF 拉平检测（对所有用例统一）
    rrf_ok, rrf_msg = check_rrf_laminated(results)
    if not rrf_ok:
        return {
            "name": tc["name"],
            "ok": False,
            "reason": f"RRF 拉平: {rrf_msg}",
            "query": tc["query"],
            "top": results[0].get("path"),
            "score": results[0].get("score"),
        }

    top = results[0]
    top_path = top.get("path", "")
    top_score = top.get("score", 0)

    # path 命中检查
    if "expect_path" in tc:
        if top_path != tc["expect_path"]:
            return {
                "name": tc["name"],
                "ok": False,
                "reason": f"第一名 path={top_path}，期望 {tc['expect_path']}",
                "query": tc["query"],
                "top": top_path,
                "score": top_score,
            }

    # paths 白名单检查
    if "expect_paths" in tc:
        if top_path not in tc["expect_paths"]:
            return {
                "name": tc["name"],
                "ok": False,
                "reason": f"第一名 path={top_path}，不在白名单 {tc['expect_paths']}",
                "query": tc["query"],
                "top": top_path,
                "score": top_score,
            }

    # score 阈值检查
    score_min = tc.get("expect_score_min", 1.0)
    if top_score < score_min:
        return {
            "name": tc["name"],
            "ok": False,
            "reason": f"score={top_score:.4f} < 期望 {score_min}",
            "query": tc["query"],
            "top": top_path,
            "score": top_score,
        }

    return {
        "name": tc["name"],
        "ok": True,
        "query": tc["query"],
        "top": top_path,
        "score": top_score,
        "_fused_by": top.get("_fused_by", "unknown"),
    }


def main() -> int:
    """主入口，返回 0=健康 / 1=异常"""
    timestamp = datetime.now(CST).isoformat()
    cases = []

    for tc in TEST_CASES:
        cases.append(check_test_case(tc))

    all_ok = all(c["ok"] for c in cases)
    failed = [c for c in cases if not c["ok"]]

    output = {
        "timestamp": timestamp,
        "ok": all_ok,
        "total": len(cases),
        "passed": sum(1 for c in cases if c["ok"]),
        "failed_count": len(failed),
        "cases": cases,
    }

    # 输出 JSON 到 stdout
    print(json.dumps(output, ensure_ascii=False, indent=2))

    # 健康时静默（stdout JSON 仍输出，给 HEARTBEAT 看）
    # 异常时输出到 stderr 显眼提示
    if not all_ok:
        print(f"\n❌ {len(failed)}/{len(cases)} 用例失败", file=sys.stderr)
        for c in failed:
            print(f"  - {c['name']}: {c['reason']}", file=sys.stderr)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
