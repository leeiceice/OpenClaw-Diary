#!/usr/bin/env python3
"""
月度日记分析 — v2（完整覆盖所有日记栏目）
汇总当月所有结构化日记 → DeepSeek V4-Pro 润色生成月报 → 推送飞书 + Git push
"""

import os, fcntl, subprocess, sys, re, json, urllib.request
from datetime import datetime
from _timezone import CST
from pathlib import Path

# ============================================================
# 配置
# ============================================================
OBSIDIAN_DIARY = Path("/root/Obsidian/日记")
ANALYSIS_DIR_NAME = "月报"
FEISHU_GROUP_ID = "oc_ad39a8e943103c2164f1d0d9de503da5"
FLAG_DIR = Path("/root/.openclaw/workspace/diary/flags")
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
# 稳定性
# ============================================================
def acquire_lock():
    lock_fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        log("⏭️ 另一进程正在执行，跳过")
        sys.exit(0)

def check_already_run_this_month(year, month):
    flag_file = FLAG_DIR / f"ran_{year}-{month:02d}_monthly.flag"
    return flag_file.exists()

def mark_run_this_month(year, month):
    FLAG_DIR.mkdir(parents=True, exist_ok=True)
    flag_file = FLAG_DIR / f"ran_{year}-{month:02d}_monthly.flag"
    flag_file.write_text(datetime.now(CST).isoformat())

def ensure_dirs():
    OBSIDIAN_DIARY.mkdir(parents=True, exist_ok=True)
    (OBSIDIAN_DIARY / ANALYSIS_DIR_NAME).mkdir(parents=True, exist_ok=True)
    FLAG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 日记读取
# ============================================================
def get_month_files(year, month):
    month_dir = OBSIDIAN_DIARY / str(year) / f"{month:02d}"
    if not month_dir.exists():
        return []
    return sorted(month_dir.glob(f"{year}-{month:02d}-*.md"))

# ============================================================
# 提取日记各栏目内容
# ============================================================
def extract_section(content, section_name):
    """提取单个栏目下所有内容（支持一级和二级标题）"""
    lines = []
    in_section = False
    sub_section = False
    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        # 检测到新一级栏目时停止
        if re.match(r'^## [^#]', stripped) and not stripped.startswith(f'## {section_name}'):
            if in_section:
                break
        # 检测到二级栏目
        if re.match(r'^### ', stripped):
            if in_section:
                sub_section = True
            if section_name in stripped:
                in_section = True
            continue
        if in_section:
            if stripped.startswith('- '):
                lines.append(stripped[2:])
            elif stripped and stripped not in ['---', '（无记录）', '-（无记录）'] \
               and not stripped.startswith('_由') and not stripped.startswith('───'):
                lines.append(stripped)
    return lines

def extract_emotions(content):
    """提取情绪数据：高/中/低天数"""
    high = mid = low = 0
    for line in content.split('\n'):
        m = re.search(r'情绪.*?\*\*([高低中])\*\*|情绪.*?([高低中])(?!\*)', line)
        if m:
            val = m.group(1) or m.group(2)
            if val == '高': high += 1
            elif val == '中': mid += 1
            elif val == '低': low += 1
    return high, mid, low

def extract_one_liner(content):
    """提取「今日我的一句话」"""
    m = re.search(r'今日我的一句话[：:]\s*(.+)', content)
    return m.group(1).strip() if m else None

# ============================================================
# DeepSeek V4-Pro
# ============================================================
def call_deepseek_pro(prompt, max_tokens=1500):
    for line in Path("/root/.openclaw/.env").read_text().splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return None, "DEEPSEEK_API_KEY not found"
    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=json.dumps({
                "model": "deepseek-v4-pro",
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": "你是 Lee 的月度复盘报告助手。\n输入：当月所有日记的各栏目内容（已去重）。\n任务：生成结构完整的月度复盘报告，使用有洞见的语言，不要流水账。\n格式：严格按指定 Markdown 格式输出，每个栏目填写实在内容。\n如某栏目数据不足，写「（当月数据不足）」而非自行编造。"},
                    {"role": "user", "content": prompt}
                ]
            }).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        return None, str(e)

# ============================================================
# 去重
# ============================================================
def dedupe(items):
    seen = set()
    result = []
    for item in items:
        key = item.strip()
        if key and key not in seen and key not in ['（无记录）', '-（无记录）']:
            seen.add(key)
            result.append(key)
    return result

# ============================================================
# 阅读记录读取
# ============================================================
def read_reading_log(year, month):
    """从 PARA/areas/阅读成长.md 提取当月阅读记录"""
    reading_file = Path("/root/Obsidian/wiki/_archive/2026-05-para-backup/areas/阅读成长.md")
    if not reading_file.exists():
        return []
    content = reading_file.read_text(encoding='utf-8')

    # 提取书名（从 ## 标题）
    book_match = re.search(r'## 《([^》]+)》', content)
    book_name = book_match.group(1) if book_match else ''

    # 匹配日期行（排除表头）
    pattern = re.compile(r'(\d{1,2}月\d{1,2}日)')
    lines = content.split('\n')
    records = []
    for line in lines:
        m = pattern.search(line)
        if m and '日期' not in line and '---' not in line:
            date_part = m.group(1)
            mm = int(date_part.split('月')[0])
            if mm == month:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                # cells[0]=日期, cells[1]=章节, cells[2]=页码, cells[3]=核心事件
                if len(cells) >= 2:
                    chapter = cells[1] if len(cells) > 1 else ''
                    pages = cells[2] if len(cells) > 2 else ''
                    note = cells[3] if len(cells) > 3 else ''
                    record = f"{date_part} {book_name} {chapter} {pages}"
                    if note:
                        record += f"。{note}"
                    records.append(record.strip())
    return records

# ============================================================
# 生成月报
# ============================================================
def generate_monthly_prompt(year, month, diaries):
    month_display = f"{year}年{month}月"
    total_days = len(diaries)

    # 按栏目聚合
    events, thoughts, reflections, insights = [], [], [], []
    key_events, improvements, actions = [], [], []
    one_liners, tomorrow_actions = [], []
    high = mid = low = 0

    # 原始日记数据（供 LLM 参考完整上下文）
    diary_full_text = []
    for date_str, content in diaries:
        diary_full_text.append(f"=== {date_str} ===\n{content}")
    full_data = "\n\n".join(diary_full_text)

    for date_str, content in diaries:
        events.extend(extract_section(content, "今天发生了什么"))
        thoughts.extend(extract_section(content, "我在想什么"))
        reflections.extend(extract_section(content, "今日收获"))
        insights.extend(extract_section(content, "值得沉淀的洞察"))
        key_events.extend(extract_section(content, "关键事件"))
        improvements.extend(extract_section(content, "待改进"))
        actions.extend(extract_section(content, "明日行动"))
        tomorrow_actions.extend(extract_section(content, "明天一件小事"))
        ol = extract_one_liner(content)
        if ol:
            one_liners.append(f"{date_str}: {ol}")
        h, m, l = extract_emotions(content)
        high += h; mid += m; low += l

    events = dedupe(events)[:20]
    thoughts = dedupe(thoughts)[:15]
    reflections = dedupe(reflections)[:15]
    insights = dedupe(insights)[:10]
    key_events = dedupe(key_events)[:10]
    improvements = dedupe(improvements)[:10]
    actions = dedupe(actions)[:10]
    tomorrow_actions = dedupe(tomorrow_actions)[:10]
    one_liners = dedupe(one_liners)[:10]
    reading_log = read_reading_log(year, month)

    total_emotion = high + mid + low
    high_pct = round(high / total_emotion * 100) if total_emotion else 0
    mid_pct = round(mid / total_emotion * 100) if total_emotion else 0
    low_pct = round(low / total_emotion * 100) if total_emotion else 0

    prompt = f"""请为 {month_display} 生成月度复盘报告。

{'='*60}
每篇日记的完整内容如下：
{full_data}
{'='*60}

各维度数据汇总（已去重）：
- 记录天数：{total_days} 天
- 今天发生了什么：{chr(10).join(events) if events else '（无记录）'}
- 我在想什么：{chr(10).join(thoughts) if thoughts else '（无记录）'}
- 关键事件：{chr(10).join(key_events) if key_events else '（无记录）'}
- 今日收获：{chr(10).join(reflections) if reflections else '（无记录）'}
- 值得沉淀的洞察：{chr(10).join(insights) if insights else '（无记录）'}
- 待改进：{chr(10).join(improvements) if improvements else '（无记录）'}
- 明日行动：{chr(10).join(actions) if actions else '（无记录）'}
- 明天一件小事：{chr(10).join(tomorrow_actions) if tomorrow_actions else '（无记录）'}
- 今日我的一句话：{chr(10).join(one_liners) if one_liners else '（无记录）'}
- 情绪分布：高 {high}天 / 中 {mid}天 / 低 {low}天
- 本月阅读记录：{chr(10).join(reading_log) if reading_log else '（当月无阅读打卡记录）'}

请生成以下格式的月度复盘报告（中文，流畅有洞见，不要流水账）：

# 📊 {month_display} 月度复盘报告

## 📅 本月概况
（简述本月整体状态，涵盖工作/生活/健康/社交/成长五个维度，2-3句话）

## 😶 本月情绪分布
| 情绪状态 | 天数 | 占比 |
|---------|------|------|
| 高 | {high} 天 | {high_pct}% |
| 中 | {mid} 天 | {mid_pct}% |
| 低 | {low} 天 | {low_pct}% |
（描述情绪整体趋势，高高低低的转折点）

## 🔥 本月关键事件
（从「今天发生了什么」+「关键事件」提炼，不按日列举，合并同类项，3-5件大事。每条格式：序号 + **加粗标题** + 换行 + 缩进描述，四级结构，不要把标题和描述写在一行里）

1. **（事件标题）**

   （描述，1-2句话，不与其它条重复）

2. **（事件标题）**

   （描述）

3. ...

## 💭 本月思考
（从「我在想什么」提炼1-3个核心主题或思维模式）

## 🌟 本月沉淀
（从「今日收获」提炼1-3条最重要的成长或认知更新）

## 💡 本月洞察
（从「值得沉淀的洞察」提炼2-4条有价值的规律/模式/真理）

## 🔧 本月待改进
（从「待改进」提炼1-3个最重要的改进方向）

## 📚 阅读/学习
（当月读过的书、学习的新知识，从阅读打卡记录和日记内容中提炼。格式：书名 + 章节/主题 + 一句话感想。无数据写「（当月无阅读记录）」）
（当月阅读记录：{chr(10).join(reading_log) if reading_log else '（当月无打卡记录）'}）

## 🌱 下月行动
（从「明日行动」+「明天一件小事」提炼1-3个具体的下月可执行动作）

## 💎 本月金句
（从「今日我的一句话」中选出1-3句最打动人的）

## 🎯 下月主题
（基于本月总结，提炼1个下月聚焦主题/方向，1句话）

---
_由 OpenClaw + DeepSeek 自动生成 | {month_display}_
"""
    return call_deepseek_pro(prompt)

# ============================================================
# 推送
# ============================================================
def save_report(report, year, month):
    ANALYSIS_DIR = OBSIDIAN_DIARY / str(year) / ANALYSIS_DIR_NAME
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    path = ANALYSIS_DIR / f"{year}-{month:02d}月报.md"
    path.write_text(report, encoding='utf-8')
    log(f"✅ 月报已保存: {path}")
    return path

def push_git(year, month):
    try:
        subprocess.run(["git", "-C", str(OBSIDIAN_DIARY), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(OBSIDIAN_DIARY), "commit", "-m", f"月报自动同步 {year}-{month:02d}"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(OBSIDIAN_DIARY), "push", "origin", "master"], check=True, capture_output=True)
        log("✅ Git push 完成")
    except subprocess.CalledProcessError as e:
        log(f"⚠️ Git push 失败: {e}")

def push_feishu(year, month):
    msg = f"📊 {year}年{month}月 月度复盘报告已生成\n完整月报请查看 Obsidian"
    try:
        result = subprocess.run(
            ["openclaw", "message", "send", "--channel", "feishu",
             "--target", FEISHU_GROUP_ID, "--message", msg],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            log("✅ 飞书推送成功")
        else:
            log(f"⚠️ 飞书推送失败: {result.stderr}")
    except Exception as e:
        log(f"⚠️ 飞书推送异常: {e}")

# ============================================================
# 主流程
# ============================================================
def main():
    now = datetime.now(CST)
    year, month = now.year, now.month
    if month == 1:
        year, month = year - 1, 12
    else:
        month = month - 1

    log(f"=== 月报生成开始 {year}-{month:02d} ===")
    ensure_dirs()
    acquire_lock()

    if check_already_run_this_month(year, month):
        log(f"⏭️ {year}年{month}月月报已生成过，跳过")
        return

    files = get_month_files(year, month)
    log(f"📥 读取到 {len(files)} 篇日记")
    if not files:
        log("⚠️ 无日记记录，跳过")
        return

    diaries = [(f.stem, f.read_text(encoding='utf-8')) for f in files]
    report, err = generate_monthly_prompt(year, month, diaries)
    if err or not report:
        log(f"⚠️ DeepSeek 失败: {err}")
        return

    save_report(report, year, month)
    push_git(year, month)
    push_feishu(year, month)
    mark_run_this_month(year, month)
    log(f"=== 月报生成完成 ===")

if __name__ == "__main__":
    main()
