#!/usr/bin/env python3
"""Token Plan 10:00-15:00 周期分析报告生成器"""

import csv
import json
import subprocess
import re
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
LOG_FILE = "/tmp/token_plan_log.csv"
ENV_FILE = "/root/.openclaw/.env"

def read_log():
    """读取采样 CSV"""
    rows = []
    try:
        with open(LOG_FILE) as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
    except FileNotFoundError:
        return []
    return rows

def get_current_status():
    """实时查一次 Token Plan"""
    try:
        key = subprocess.run(
            f"grep MINIMAX_API_KEY {ENV_FILE} | head -1 | cut -d= -f2- | tr -d ' \\n'",
            shell=True, capture_output=True, text=True, timeout=5
        ).stdout.strip()
        if not key:
            return None
        resp = subprocess.run(
            f'curl -s --max-time 10 "https://api.minimaxi.com/v1/token_plan/remains" -H "Authorization: Bearer {key}"',
            shell=True, capture_output=True, text=True, timeout=15
        ).stdout
        data = json.loads(resp)
        r = data.get("model_remains", [{}])[0]
        return {
            "pct": r.get("current_interval_remaining_percent"),
            "used": r.get("current_interval_usage_count", 0),
            "total": r.get("current_interval_total_count", 0),
            "weekly_pct": r.get("current_weekly_remaining_percent"),
            "status": r.get("current_interval_status"),
            "cycle_start": r.get("start_time"),
            "cycle_end": r.get("end_time"),
        }
    except Exception as e:
        return {"error": str(e)}

def get_cron_runs_in_period(start_min, start_hour, end_min, end_hour):
    """获取 OpenClaw cron 列表（仅用于参照事件时间线）"""
    try:
        result = subprocess.run(
            "openclaw cron list --json 2>/dev/null",
            shell=True, capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return None
        # Try parsing as JSON from command output
        output = result.stdout.strip()
        if output.startswith('['):
            return json.loads(output)
        return None
    except:
        return None

def generate_report(rows, current):
    """生成分析报告"""
    now = datetime.now(CST)
    lines = []
    lines.append(f"🦞 Token Plan 10:00-15:00 周期分析报告")
    lines.append(f"生成时间: {now.strftime('%Y-%m-%d %H:%M:%S CST')}")
    lines.append("")
    
    # 1. 概况
    lines.append("━" * 40)
    lines.append("📊 周期概况")
    lines.append("━" * 40)
    
    if current and "error" not in current:
        if current.get("cycle_start"):
            cs = datetime.fromtimestamp(current["cycle_start"] / 1000, CST)
            ce = datetime.fromtimestamp(current["cycle_end"] / 1000, CST)
            lines.append(f"  周期: {cs.strftime('%H:%M')} - {ce.strftime('%H:%M')}")
        lines.append(f"  当前剩余: {current.get('pct', '?')}%")
        lines.append(f"  已用/总量: {current.get('used', '?')} / {current.get('total', '?')}")
        lines.append(f"  本周剩余: {current.get('weekly_pct', '?')}%")
        lines.append(f"  状态: {current.get('status', '?')} (1=充足 2=警告 3=耗尽)")
    lines.append("")
    
    # 2. 采样时间线
    lines.append("━" * 40)
    lines.append("⏱️ 采样时间线")
    lines.append("━" * 40)
    
    if rows:
        for r in rows:
            ts = r.get("timestamp", "?")
            pct = r.get("5h_remaining_pct", "?")
            used_total = f"{r.get('5h_used', '?')}"
            total = f"{r.get('total', '?')}"
            if pct != "?":
                pct_int = int(pct)
                icon = "🟢" if pct_int >= 50 else ("🟡" if pct_int >= 30 else ("🟠" if pct_int >= 10 else "🔴"))
            else:
                icon = "❓"
            lines.append(f"  {icon} {ts}  剩余 {pct}%  |  已用 {used_total}/{total}")
    else:
        lines.append("  (无采样数据)")
    lines.append("")
    
    # 3. 关键事件对齐
    lines.append("━" * 40)
    lines.append("📌 同期关键事件")
    lines.append("━" * 40)
    
    # 列出 10:00-15:00 之间跑的 M3 cron
    m3_crons = [
        ("10:00", "向量库稳定性汇报", "~135s", "单次"),
        ("10:30", "association-trigger", "~26s", "shell 脚本"),
        ("12:00", "午间学习提醒", "~131s", "推送消息"),
        ("12:00", "午间GNC补剂提醒", "~12s", "推送消息"),
        ("12:30", "午间记忆提炼", "~151s", "Python 脚本"),
        ("14:00", "association-trigger", "~26s", "shell 脚本"),
        ("14:30", "对话-Ontology管道", "~11s", "Python 脚本"),
        ("每1h", "heartbeat-maintenance", "~50s", "全链路检查"),
        ("每15min", "cron-retry-monitor", "~5s", "shell 包装, light-context"),
    ]
    for t, n, d, note in m3_crons:
        lines.append(f"  {t}  {n} ({d})")
    
    lines.append("")
    
    # 4. 消耗模式分析
    lines.append("━" * 40)
    lines.append("🔍 消耗模式分析")
    lines.append("━" * 40)
    
    if len(rows) >= 2:
        try:
            first_pct = int(rows[0].get("5h_remaining_pct", "0"))
            last_pct = int(rows[-1].get("5h_remaining_pct", "0"))
            consumed = first_pct - last_pct
            
            # 估算间隔
            first_ts = rows[0].get("timestamp", "")
            last_ts = rows[-1].get("timestamp", "")
            
            lines.append(f"  起止: {first_ts[:16]} → {last_ts[:16]}")
            lines.append(f"  消耗: {first_pct}% → {last_pct}% (= {consumed}%)")
            
            if current and "error" not in current:
                total_tokens = current.get("total", 4166667)
                used_tokens = current.get("used", 0)
                lines.append(f"  折算: {used_tokens:,}/{total_tokens:,} tokens")
                lines.append(f"  消耗率: ~{used_tokens//300:,} tokens/min")
            
            # 分段消耗
            lines.append("")
            lines.append("  分段消耗:")
            prev_pct = None
            for r in rows:
                pct_str = r.get("5h_remaining_pct", "?")
                ts = r.get("timestamp", "?")
                if pct_str != "?":
                    pct_val = int(pct_str)
                    if prev_pct is not None:
                        delta = prev_pct - pct_val
                        if delta > 0:
                            lines.append(f"    {ts[11:16]}  -{delta}% (剩余 {pct_val}%)")
                        elif delta == 0:
                            lines.append(f"    {ts[11:16]}  持平 (剩余 {pct_val}%)")
                    prev_pct = pct_val
        except (ValueError, IndexError):
            lines.append("  (数据解析异常)")
    else:
        lines.append("  (采样不足，无法分析)")
    
    lines.append("")
    
    # 5. 结论与建议
    lines.append("━" * 40)
    lines.append("💡 建议")
    lines.append("━" * 40)
    
    if current and "error" not in current:
        pct = current.get("pct", 100)
        if pct is not None and pct < 30:
            lines.append("  ⚠️ 当前周期消耗偏快，建议关注:")
            lines.append("  • heartbeat-maintenance 每小时消耗可见")
            lines.append("  • association-trigger 每2h跑一次")
            lines.append("  • 午间 12:00-12:30 是密集消耗窗口")
        elif pct is not None and pct >= 70:
            lines.append("  ✅ 消耗正常，无需干预")
        else:
            lines.append("  📊 消耗处于中等水平")
    else:
        lines.append("  (无法获取实时状态)")
    
    lines.append("")
    lines.append("— 小龙虾 🦞 Token Plan 监控系统")
    
    return "\n".join(lines)

if __name__ == "__main__":
    rows = read_log()
    current = get_current_status()
    report = generate_report(rows, current)
    print(report)
