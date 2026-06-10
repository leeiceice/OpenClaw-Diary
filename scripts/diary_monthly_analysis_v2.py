#!/usr/bin/env python3
"""
月度日记分析 — 最终优化版
汇总当月所有结构化日记 → 生成月报 → 推送飞书 + Git push
"""

import subprocess
from datetime import datetime
from _timezone import CST
from pathlib import Path

# ============================================================
# 配置
# ============================================================
OBSIDIAN_DIARY = Path(__import__('os').expanduser("~/Obsidian/日记"))
FEISHU_GROUP_ID = "oc_ad39a8e943103c2164f1d0d9de503da5"
LOG_FILE = "/tmp/diary_monthly.log"
LOCK_FILE = "/tmp/diary_monthly.lock"

# ============================================================
# 日志
# ============================================================
def log(msg):
    print(msg, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(f"{datetime.now(CST).strftime('%H:%M:%S ')}{msg}\n")

# ============================================================
# 月度汇总
# ============================================================
def get_month_files(year, month):
    prefix = f"{year}-{month:02d}"
    return sorted(OBSIDIAN_DIARY.glob(f"{prefix}-*.md"))

def extract_bullet_items(content, section_name):
    """提取日记中指定 section 的列表项内容"""
    lines = []
    in_section = False
    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('## ') and not stripped.startswith('### '):
            if in_section:
                break
            if section_name in stripped:
                in_section = True
                continue
        elif stripped.startswith('### '):
            continue
        if in_section:
            if stripped.startswith('- '):
                lines.append(stripped[2:])
            elif stripped and stripped not in ['-（无记录）', '（无记录）']:
                lines.append(stripped)
    return lines

def generate_monthly_report(year, month, diaries):
    month_display = f"{year}年{month}月"

    all_events = []
    all_thoughts = []
    all_reflections = []
    all_actions = []

    for date_str, content in diaries:
        all_events.extend((date_str, e) for e in extract_bullet_items(content, "今天发生了什么"))
        all_thoughts.extend((date_str, t) for t in extract_bullet_items(content, "我在想什么"))
        all_reflections.extend((date_str, r) for r in extract_bullet_items(content, "今日收获"))
        all_actions.extend((date_str, a) for a in extract_bullet_items(content, "明日行动"))

    # 去重（保留顺序）
    def dedupe(items):
        seen = set()
        result = []
        for date_str, item in items:
            key = item.strip()
            if key and key not in ['（无记录）', '-（无记录）'] and key not in seen:
                seen.add(key)
                result.append(f"**{date_str}**: {key}")
        return result

    events = dedupe(all_events)[:20]
    thoughts = dedupe(all_thoughts)[:15]
    reflections = dedupe(all_reflections)[:15]
    actions = dedupe(all_actions)[:10]

    return f"""# 📊 {month_display} 月度复盘报告

## 📅 本月概况
- 记录天数：**{len(diaries)}** 天
- 生成时间：{datetime.now(CST).strftime("%Y-%m-%d %H:%M")}

---

## 🔥 本月关键事件
{chr(10).join(f"- {e}" for e in events) if events else "-（无记录）"}

---

## 💭 本月思考
{chr(10).join(f"- {t}" for t in thoughts) if thoughts else "-（无记录）"}

---

## 🌟 本月沉淀
{chr(10).join(f"- {r}" for r in reflections) if reflections else "-（无记录）"}

---

## 🎯 下月行动
{chr(10).join(f"- {a}" for a in actions) if actions else "-（无记录）"}

---

_由 OpenClaw 自动生成 | {month_display}_
"""

def save_monthly_report(report, year, month):
    OBSIDIAN_DIARY.mkdir(parents=True, exist_ok=True)
    path = OBSIDIAN_DIARY / f"{year}-{month:02d}月报.md"
    path.write_text(report, encoding='utf-8')
    log(f"✅ 月报已保存: {path}")
    return path

def push_obsidian_git(year, month):
    path = OBSIDIAN_DIARY / f"{year}-{month:02d}月报.md"
    if not path.exists():
        return
    try:
        subprocess.run(["git", "-C", str(OBSIDIAN_DIARY), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(OBSIDIAN_DIARY), "commit", "-m", f"月报自动同步 {year}-{month:02d}"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(OBSIDIAN_DIARY), "push"], check=True, capture_output=True)
        log(f"✅ 月报已 Git push")
    except subprocess.CalledProcessError as e:
        log(f"⚠️ Git push 失败: {e}")

def push_feishu(year, month):
    msg = f"📊 {year}年{month}月 月度复盘报告已生成\n完整月报请查看 Obsidian"
    try:
        result = subprocess.run(
            ["openclaw", "message", "send",
             "-t", FEISHU_GROUP_ID,
             "-m", msg],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            log(f"✅ 飞书月报推送成功")
        else:
            log(f"⚠️ 飞书月报推送失败: {result.stderr}")
    except Exception as e:
        log(f"⚠️ 飞书月报推送异常: {e}")

# ============================================================
# 主流程
# ============================================================
def main():
    now = datetime.now(CST)
    year, month = now.year, now.month

    # 默认分析上月
    if month == 1:
        year, month = year - 1, 12
    else:
        month = month - 1

    log(f"=== 月报生成开始 {year}-{month:02d} ===")

    files = get_month_files(year, month)
    log(f"📥 读取到 {len(files)} 篇日记")

    if not files:
        log(f"⚠️ 无日记记录，跳过月报生成")
        return

    diaries = [(f.stem, f.read_text(encoding='utf-8')) for f in files]
    report = generate_monthly_report(year, month, diaries)

    save_monthly_report(report, year, month)
    push_obsidian_git(year, month)
    push_feishu(year, month)

    log(f"=== 月报生成完成 ===")

if __name__ == "__main__":
    main()