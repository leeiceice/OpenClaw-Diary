#!/usr/bin/env python3
"""
日常安排日报生成脚本 v2.0
从多个数据源生成增强版日报：
- memory/YYYY-MM-DD.md → 完成事项
- water-log.json → 喝水追踪
- mtdb_health_check.py → 记忆系统状态
- cron 执行记录 → 定时任务
- self-improving → 今日纠正/模式积累
- collections/ → 今日收藏
"""

import json
import os
import sqlite3
import subprocess
from datetime import datetime, timedelta
from _timezone import CST
from pathlib import Path

DATE = datetime.now(CST).strftime("%Y-%m-%d")
YESTERDAY = (datetime.now(CST) - timedelta(days=1)).strftime("%Y-%m-%d")
WORKSPACE = Path("~/.openclaw/workspace").expanduser()
DATA = WORKSPACE / "data"
MEMORY_DIR = Path("~/.openclaw/workspace/memory").expanduser()
MEMORY_FILE = MEMORY_DIR / f"{DATE}.md"
WATER_LOG_FILE = DATA / "water-log.json"
MTDB_HEALTH = WORKSPACE / "scripts/mtdb_health_check.py"
MTDB_DATA = Path("~/.openclaw/memory-tdai").expanduser()
VECTOR_DB = WORKSPACE / "data" / "vector_store.db"
COLLECTIONS = WORKSPACE / "collections"
OBSIDIAN_PATH = Path.home() / "Obsidian"

def section(title, content):
    """生成带标题的板块"""
    if not content.strip():
        return ""
    return f"■ {title}\n{content}\n"

def check_memory_system_status():
    """记忆系统状态：L0缺口 + 向量库状态"""
    lines = []
    
    # L0 对话录制检查（同时检查 workspace/memory/ 和 Obsidian 日记，使用 rglob 递归子目录）
    obsidian_dir = Path.home() / "Obsidian/日记"
    
    # 收集两边的文件（递归搜索子目录）
    workspace_files = set([f.stem for f in MEMORY_DIR.glob("*.md")]) if MEMORY_DIR.exists() else set()
    obsidian_files = set([f.stem for f in obsidian_dir.rglob("*.md")]) if obsidian_dir.exists() else set()
    
    all_existing = workspace_files | obsidian_files
    
    missing = []
    for i in range(7):
        d = (datetime.now(CST) - timedelta(days=i)).strftime("%Y-%m-%d")
        if d not in all_existing:
            missing.append(d)
    
    if missing:
        lines.append(f"  ⚠️ L0 录制缺口：{', '.join(missing)}")
    else:
        lines.append(f"  ✅ L0 对话录制正常（最近：{sorted(all_existing)[-1]}）")
    
    # 向量库状态（使用 data/vector_store.db）
    db_path = VECTOR_DB
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM vectors")
            l1_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cur.fetchone()[0]
            conn.close()
            lines.append(f"  📊 向量库：{l1_count}条向量 | {chunk_count}条chunks")
        except Exception as e:
            lines.append(f"  ⚠️ 向量库状态：查询失败 ({e})")
    else:
        lines.append(f"  ⚠️ 向量库：文件不存在")
    
    return "\n".join(lines) if lines else None

def load_water_summary():
    """喝水追踪图形化汇总"""
    if not WATER_LOG_FILE.exists():
        return None
    try:
        with open(WATER_LOG_FILE) as f:
            data = json.load(f)
        if data.get('today') != DATE:
            return None
        total = data.get('total_ml', 0)
        goal = data.get('goal_ml', 2000)
        cups = data.get('cup_count', 0)
        goal_cups = 6
        pct = min(100, int(total / goal * 100))
        filled = int(pct / 10)
        bar = '█' * filled + '░' * (10 - filled)
        cup_filled = total // 350
        cup_bar = '💧' * cup_filled + '⚪' * (goal_cups - cup_filled)
        emoji = '🎉' if total >= goal else '💧'
        return f"""  {emoji} 今日累计：{total}ml / {goal}ml
  ▕{bar}▏ {pct}%
  {cup_bar}  {cups}杯 / {goal_cups}杯
  {'🎉 今日2L目标达成！' if total >= goal else '继续加油，每天6杯 💪'}"""
    except:
        return None

def load_completed_from_memory():
    """从当日memory文件提取完成事项"""
    if not MEMORY_FILE.exists():
        return None
    with open(MEMORY_FILE) as f:
        content = f.read()
    lines = content.split("\n")
    completed = []
    current_section = ""
    for line in lines:
        line = line.strip()
        if not line or line.startswith("# ") or line.startswith("===") or line.startswith("---"):
            continue
        if line.startswith("## "):
            current_section = line.replace("## ", "").strip()
            continue
        if current_section and line:
            keywords = ["完成", "✅", "已确认", "已修复", "已处理", "已设置", "已创建", "已更新", "已同步", "已提交", "已配置"]
            if any(k in line for k in keywords):
                cleaned = line.replace("✅", "■").strip()
                if cleaned.startswith("■"):
                    cleaned = "  • " + cleaned[1:].strip()
                elif not cleaned.startswith("•"):
                    cleaned = "  • " + cleaned
                else:
                    cleaned = "  " + cleaned
                completed.append(cleaned)
    return completed[:15] if completed else ["  • 系统正常运行，无显著完成事项"]

def check_cron_execution():
    """检查今日 cron 执行情况"""
    cron_file = MEMORY_DIR / f"{DATE}.md"
    if not cron_file.exists():
        return "  （无今日memory文件）"
    
    try:
        with open(cron_file) as f:
            content = f.read()
        cron_keywords = ["cron", "定时", "执行", "任务"]
        lines_content = content.split("\n")
        results = []
        for line in lines_content:
            if any(k in line.lower() for k in cron_keywords):
                clean = line.strip()
                if clean and len(clean) > 10:
                    results.append(f"  • {clean[:80]}")
        if len(results) > 10:
            results = results[:10]
    except:
        pass
    
    # 检查 self-improving cron 结果
    state_file = WORKSPACE / "scripts/.conversation_ontology_state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
            last_run = state.get("last_run", "")
            if DATE in last_run:
                results.append(f"  • Ontology管道执行：{last_run[:16]}")
        except:
            pass
    
    return "\n".join(results) if results else "  无显著cron执行记录"

def check_self_improving():
    """检查今日 Self-improving 更新"""
    corrections_file = Path("/root/self-improving/corrections.md")
    patterns_file = Path("/root/self-improving/successful-patterns.md")
    today_prefix = f"## {DATE}"
    
    lines = []
    
    if corrections_file.exists():
        with open(corrections_file) as f:
            content = f.read()
        # 简单检查今日是否有新条目（通过时间戳或日期标记）
        # 读取最后几行检查日期
        file_lines = content.split("\n")
        today_entries = [l for l in file_lines if DATE in l or f"[{DATE}" in l]
        if today_entries:
            lines.append(f"  📝 corrections.md：今日有更新")
        else:
            lines.append(f"  📝 corrections.md：无新增")
    
    if patterns_file.exists():
        with open(patterns_file) as f:
            content = f.read()
        file_lines = content.split("\n")
        today_entries = [l for l in file_lines if DATE in l or f"[{DATE}" in l]
        if today_entries:
            lines.append(f"  🌟 patterns.md：今日有更新")
        else:
            lines.append(f"  🌟 patterns.md：无新增")
    
    return "\n".join(lines) if lines else None

def check_collections():
    """检查今日收藏（小龙虾本地 collections/ 目录）"""
    if not COLLECTIONS.exists():
        return None
    
    collections_found = []
    
    for subdir in ["articles", "wechat", "ideas"]:
        subpath = COLLECTIONS / subdir
        if not subpath.exists():
            continue
        for f in subpath.iterdir():
            if f.is_file() and f.stat().st_mtime >= datetime.now(CST).timestamp() - 86400:
                collections_found.append(f"  • {f.name[:40]}")
    
    return "\n".join(collections_found[:5]) if collections_found else None

def check_obsidian_git_updates():
    """读取 Obsidian git 仓库自昨日以来的所有 commit，提取入库内容"""
    if not OBSIDIAN_PATH.exists():
        return None
    
    import re
    
    try:
        # 获取自昨日以来的所有 commit，用 | 分隔符避免 datetime 空格问题
        result = subprocess.run(
            ["git", "log", f"--since={YESTERDAY} 00:00:00", "--until=tomorrow 00:00:00",
             "--format=%h|%ai|%s"],
            cwd=str(OBSIDIAN_PATH),
            capture_output=True,
            text=True,
            timeout=10
        )
        if not result.stdout.strip():
            return None
        
        lines = result.stdout.strip().split("\n")
        entries = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) < 3:
                continue
            _short_hash, _dt, subject = parts[0], parts[1], parts[2]
            
            # 提取书籍名
            book_match = re.findall(r'《([^》]+)》', subject)
            # 提取收藏标题
            quote_match = re.findall(r'收藏 "([^"]+)"', subject)
            
            if book_match:
                for book in book_match:
                    entries.append(f"  📚 {book}")
            elif quote_match:
                for q in quote_match:
                    entries.append(f"  💡 {q[:30]}")
            else:
                # 通用模式：去掉 emoji/prefix，过滤无意义 backup commit
                clean = subject.strip()
                for prefix in ["feat:", "fix:", "vault backup:"]:
                    if clean.startswith(prefix):
                        clean = clean[len(prefix):].strip()
                # 去除所有 emoji
                clean = re.sub(r'[\U00010000-\U0010ffff\u2600-\u2B55\U0001F300-\U0001F9FF]', '', clean).strip()
                # 过滤无意义的纯时间 commit
                if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$', clean):
                    continue
                if clean.startswith("自动推送") or clean.startswith("推送"):
                    # 提取时间
                    t = re.search(r'\d{2}:\d{2}', clean)
                    if t:
                        clean = f"自动推送 {t.group()}"
                if clean:
                    entries.append(f"  • {clean[:35]}")
        
        if not entries:
            return None
        # 去重保留顺序
        seen = set()
        unique = []
        for e in entries:
            if e not in seen:
                seen.add(e)
                unique.append(e)
        return "\n".join(unique[:8])
    except Exception as e:
        return f"  ⚠️ 读取 Obsidian git 失败: {e}"

def generate_report():
    today_str = datetime.now(CST).strftime("%Y-%m-%d")
    
    # 各板块数据收集
    memory_system = check_memory_system_status()
    water = load_water_summary()
    completed = load_completed_from_memory()
    cron_log = check_cron_execution()
    self_improving = check_self_improving()
    collections = check_collections()
    obsidian_updates = check_obsidian_git_updates()
    
    # 组装报告
    parts = []
    parts.append(f"【📋 日常安排日报】 {today_str}\n")
    
    if water:
        parts.append(section("💧 喝水追踪", water))
    
    if memory_system:
        parts.append(section("🧠 记忆系统状态", memory_system))
    
    if completed:
        parts.append(f"■ 📝 今日完成事项：\n" + "\n".join(completed) + "\n")
    
    if cron_log:
        parts.append(section("⏰ 定时任务", cron_log))
    
    if self_improving:
        parts.append(section("🛠️ Self-improving", self_improving))
    
    if obsidian_updates:
        parts.append(section("📚 Obsidian 入库（小马/CC/小龙虾）", obsidian_updates))
    
    if collections:
        parts.append(section("📥 今日收藏（小龙虾本地）", collections))
    
    parts.append(f"\n■ 📅 明日待办：待补充")
    
    return "\n".join(parts)

if __name__ == "__main__":
    print(generate_report())