#!/usr/bin/env python3
"""
晨间简报生成器 v2（个性化版）
集成：天气 + 金句 + Ontology关联 + 记忆系统状态
"""

import subprocess
import json
import re
import os
from datetime import datetime
from _timezone import CST
from pathlib import Path

# ========== 配置 ==========
ONTOLOGY_GRAPH = '~/.openclaw/workspace/memory/ontology/graph.jsonl'
MEMORY_MD = '~/.openclaw/workspace/MEMORY.md'
ONTOLOGY_SCRIPT = '~/.openclaw/workspace/skills/ontology/scripts/ontology_query.py'

def get_weather(city="Fuzhou"):
    """通过 wttr.in 获取福州天气"""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "8",
             f"wttr.in/{city}?format=%l:+%c+%C,+%t,+体感%f,+湿度%h,+风速%w"],
            capture_output=True, text=True, timeout=12
        )
        raw = result.stdout.strip() if result.stdout else ""
        if not raw:
            return None
        en2zh = {
            "Clear": "晴", "Sunny": "晴", "Partly cloudy": "少云",
            "Cloudy": "多云", "Overcast": "阴", "Mist": "薄雾",
            "Fog": "雾", "Rain": "雨", "Light rain": "小雨",
            "Moderate rain": "中雨", "Heavy rain": "大雨",
            "Snow": "雪", "Light snow": "小雪",
            "Thunderstorm": "雷阵雨", "Showers": "阵雨",
        }
        for en, zh in en2zh.items():
            raw = raw.replace(en, zh)
        raw = raw.replace("fuzhou:", "福州：")
        return raw
    except Exception:
        return None

def get_quote():
    """获取每日金句"""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "10", "https://zenquotes.io/api/random"],
            capture_output=True, text=True, timeout=15
        )
        if result.stdout:
            data = json.loads(result.stdout)
            if data and len(data) > 0:
                q = data[0].get("q", "")
                a = data[0].get("a", "")
                if q and a:
                    return f"「{q}」\n—— {a}"
    except Exception:
        pass
    return None

def get_ontology_insight():
    """查询 Ontology 图谱，返回今日关联知识"""
    try:
        if not os.path.exists(ONTOLOGY_GRAPH):
            return None
        result = subprocess.run(
            ["python3", ONTOLOGY_SCRIPT,
             "--graph", ONTOLOGY_GRAPH,
             "--query", "知识 记忆 系统"],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout.strip()
        # 解析输出中的实体（找 📌 开头的行）
        lines = [l.strip() for l in output.split('\n') if '📌' in l or '•' in l]
        if not lines:
            # 没有特殊标记时取第二行正文
            all_lines = [l.strip() for l in output.split('\n') if l.strip() and not l.strip().startswith(('Found', 'Query', '🔎'))]
            lines = all_lines[:3]
        if lines:
            insights = []
            for line in lines[:3]:
                line = re.sub(r'^[\s\S]*?•\s*', '', line)
                line = re.sub(r'\s*\[Concept\]|\s*\[Document\]', '', line)
                line = line.strip()
                if line and len(line) > 3:
                    insights.append(line)
            if insights:
                return " → ".join(insights[:2])
    except Exception:
        pass
    return None

def get_last_night_sleep():
    """读取最近一次记录的睡眠数据，检测数据是否过旧（超过72小时）"""
    sleep_file = '~/.openclaw/workspace/data/sleep-log.json'
    try:
        with open(sleep_file) as f:
            data = json.load(f)
        records = data.get('records', [])
        if not records:
            return None
        
        # records 按上传时间倒序排列，取第一条（最近一次）
        latest = records[0]
        
        # 检查数据是否太旧（超过72小时），需要标注
        from datetime import datetime as dt_cls
        wake_ts = latest.get('wakeTime', '')
        try:
            wake_dt = dt_cls.strptime(wake_ts, '%Y-%m-%d %H:%M')
            age_hours = (dt_cls.now() - wake_dt).total_seconds() / 3600
            if age_hours > 72:
                latest['_stale'] = True
        except:
            pass
        
        date = latest.get('date', 'N/A')
        dur = latest.get('totalSleepFormatted', 'N/A')
        quality = latest.get('sleepQuality', 0)
        deep = latest.get('deepSleepMin', 0)
        rem = latest.get('remSleepMin', 0)
        awake = latest.get('awakeSleepMin', 0)
        bed = latest.get('bedTime', 'N/A')
        wake = latest.get('wakeTime', 'N/A')
        total_min = latest.get('totalSleepMin', 0)
        stars = "★" * int(round(quality)) + "☆" * (5 - int(round(quality)))
        
        tips = []
        if total_min < 360:
            tips.append("⚠️ 睡眠不足，建议今晚提前30分钟就寝")
        elif total_min >= 420:
            tips.append("✅ 睡眠充足，继续保持")
        if deep < 60:
            tips.append("💤 深睡偏少，睡前避免使用电子设备")
        if awake > 30:
            tips.append("🌙 夜间觉醒次数偏多，注意睡前放松")
        if not tips:
            tips.append("🌟 睡眠质量良好")
        
        # 格式化就寝时间为 HH:MM
        bed_short = bed[11:16] if len(bed) >= 16 else bed
        wake_short = wake[11:16] if len(wake) >= 16 else wake
        
        return {
            'date': date, 'duration': dur, 'quality': quality,
            'stars': stars, 'deep': deep, 'rem': rem,
            'awake': awake, 'bedTime': bed_short, 'wakeTime': wake_short,
            'tips': '\n'.join(tips)
        }
    except Exception:
        return None

def get_memory_status():
    """从 MEMORY.md 提取待办事项"""
    try:
        with open(MEMORY_MD) as f:
            text = f.read()
        # 提取未完成的待办事项
        todo_match = re.search(r'待办/未完成事项[\s\S]+?(?=\n##\s|\Z)', text)
        if todo_match:
            block = todo_match.group(0)
            items = re.findall(r'-\s*\[.\]\s*(.+)', block)
            return items[:3]
    except Exception:
        pass
    return []

def generate_morning_briefing():
    now = datetime.now(CST)
    weekday_map = {
        'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三',
        'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'
    }
    weekday_cn = weekday_map.get(now.strftime('%A'), now.strftime('%A'))
    date_str = now.strftime('%Y年%m月%d日')

    weather = get_weather("Fuzhou")
    quote = get_quote()
    ontology = get_ontology_insight()
    focus_items = get_memory_status()

    # 构建个性化今日待办
    if focus_items:
        personalized_priority = "\n".join([f"◇ {item.strip()}" for item in focus_items[:3]])
    else:
        personalized_priority = ("① ___________________________\n"
                                 "② ___________________________\n"
                                 "③ ___________________________")

    sleep = get_last_night_sleep()

    sleep_display = "（暂无睡眠数据）"
    if sleep:
        stale_tag = " ⚠️ 数据较旧" if sleep.get('_stale') else ""
        sleep_display = (f"{sleep['date']}{stale_tag} · {sleep['duration']} · {sleep['stars']}\n"
                         f"  入睡{sleep['bedTime']} → 起床{sleep['wakeTime']}\n"
                         f"  深睡{int(sleep['deep'])}min · REM {int(sleep['rem'])}min · 清醒{int(sleep['awake'])}min\n"
                         f"  {sleep['tips']}")

    sections = [
        ("🌅 早安启动", "新的一天开始了。聚焦目标，从容行动。"),
        ("☔ 福州天气", weather if weather else "请出门前确认天气。"),
        ("💤 昨晚睡眠", sleep_display),
        ("💬 每日金句", quote if quote else "生活就像海洋，只有意志坚强的人才能到达彼岸。"),
        ("🧠 知识关联", ontology if ontology else "（今日暂无新关联）"),
        ("🎯 今日待办", personalized_priority),
        ("✅ 今日习惯",
         "□ 晨间例程（运动/冥想/日志）\n"
         "□ 饮水目标（8杯水）\n"
         "□ 学习时间（30分钟阅读/课程）\n"
         "□ 晚间复盘"),
        ("💚 自我关爱",
         "• 每小时离开屏幕休息5分钟\n"
         "• 保持水分\n"
         "• 适时休息，不过度消耗"),
        ("🌙 晚间复盘（提醒）",
         "睡前完成：\n"
         "① 今天完成了什么？\n"
         "② 感恩什么？\n"
         "③ 哪里可以更好？\n"
         "④ 明天最重要的一件事？"),
    ]

    lines = [
        f"📅 {date_str} {weekday_cn} · 晨间简报",
        "═" * 32,
        ""
    ]
    for title, content in sections:
        lines.append(f"{title}")
        lines.append(str(content))
        lines.append("")

    return "\n".join(lines)

if __name__ == '__main__':
    briefing = generate_morning_briefing()
    print(briefing)
