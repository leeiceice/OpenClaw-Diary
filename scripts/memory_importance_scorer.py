#!/usr/bin/env python3
"""
每日记忆重要性评分脚本 v2
对 memory/YYYY-MM-DD.md 中的每个 ## 块智能打分，决定是否值得固化到 MEMORY.md。
"""
from pathlib import Path
from datetime import date, datetime, timezone, timedelta
from _timezone import CST, now_cst
import re

MEMORY_DIR = Path("~/.openclaw/workspace/memory").expanduser()
MEMORY_MD  = Path("~/.openclaw/workspace/MEMORY.md").expanduser()

CRON_NOISE_HEADERS = [
    'cron-retry-monitor', 'Cron 运行', '执行记录', '系统事件',
    'Heartbeat', '健康检查', 'MemOS 同步', ' ontology',
]

CRON_NOISE_LINES = [
    'HEARTBEAT_OK', 'none -> last', 'no route', 'will fail-closed',
    '代码 0', 'code 0', 'consecutiveErrors', 'lastRunStatus',
    '无失败任务', '无新增', '无同名任务', '成功触发',
    'Cron:', 'cron-retry-monitor', '执行记录',
    '距离上次失败', '重试已触发', '重试后状态',
    '结果：', '状态：', '备注：', '失败任务检查',
    '发现 1 个失败任务',
]

# === 评分维度 ===
SCORING_RULES = [
    # Lee 直接反馈 → 立即固化
    {'score': 90, 'header': None, 'keywords': ['Lee.*反馈', 'Lee.*说', '没看记忆', '漏过.*回复', '同步数据给你'], 'weight': 'max'},
    # 待办/问题 → 高价值
    {'score': 70, 'header': ['待补充事项', '待处理', '问题定位', '需要检查'], 'keywords': [], 'weight': 'header'},
    # 规范/规则变更 → 高价值
    {'score': 75, 'header': ['规范', '规则', '策略', '协议'], 'keywords': ['写入', '补充', '固化', '修改', '已.*规则'], 'weight': 'header'},
    # 技能/系统配置变更 → 高价值
    {'score': 80, 'header': ['技能', '系统配置', '插件', 'cron.*新建', 'cron.*删除'], 'keywords': ['安装', '卸载', '升级', '禁用', '启用'], 'weight': 'header'},
    # 决策/确认 → 高价值
    {'score': 85, 'header': None, 'keywords': ['确认：', '就这样', '没问题', '可以', '好的', '同意', '授权', '按方案'], 'weight': 'keyword'},
    # 错误/纠正 → 高价值
    {'score': 80, 'header': None, 'keywords': ['纠正', '错.*是', '教训', '踩坑', '已.*漏过', '漏过.*审查', '规则.*冲突'], 'weight': 'keyword'},
    # 完成项（如果内容有价值）
    {'score': 30, 'header': ['完成项', '已完成', '成果'], 'keywords': [], 'weight': 'header'},
]

NO_VALUE_KEYWORDS = [
    'HEARTBEAT_OK', 'none -> last', 'no route', 'will fail-closed',
    '代码 0', 'code 0', 'Cron:', 'cron-retry-monitor',
]


def is_noise_line(line: str) -> bool:
    s = line.strip()
    for kw in NO_VALUE_KEYWORDS:
        if kw in s:
            return True
    for prefix in CRON_NOISE_LINES:
        if s.startswith(prefix):
            return True
    if re.match(r'^\[.*\]$', s):  # 时间戳日志
        return True
    return False


def score_block(header: str, lines: list[str]) -> tuple[int, str, list[str]]:
    """对整个块打分，返回 (总分, 理由, 有效条目列表)"""
    score = 0
    reasons = []
    valid_items = []

    # 噪音标题直接返回0
    for noise in CRON_NOISE_HEADERS:
        if noise in header:
            return 0, '', []

    block_text = ' '.join(lines)

    # 应用评分规则
    for rule in SCORING_RULES:
        matched = False
        score_val = rule['score']

        # 检查标题匹配
        if rule['header']:
            for h in rule['header']:
                if h in header:
                    matched = True
                    reasons.append(f'标题含「{h}」')
                    break

        # 检查关键词匹配
        if rule['keywords']:
            for kw in rule['keywords']:
                if re.search(kw, block_text):
                    matched = True
                    reasons.append(f'内容含「{kw}」')
                    break

        if matched:
            if rule['weight'] == 'max':
                score = max(score, score_val)
            else:
                score += score_val

    # 内容去噪 + 提取有效条目
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('#'):
            continue
        if is_noise_line(stripped):
            continue
        if len(stripped) < 10:
            continue
        # 清理 `- ` 前缀
        clean = stripped.lstrip('- ').strip()
        if len(clean) < 5:
            continue
        if is_noise_line(clean):
            continue
        valid_items.append(clean)

    return min(score, 100), ' + '.join(reasons), valid_items


def parse_blocks(md_text: str) -> list[tuple[str, list[str]]]:
    """将 markdown 文本解析为 (标题, 块内容行列表)"""
    lines = md_text.split('\n')
    blocks = []
    current_header = '## 全文'
    current_lines = []

    for line in lines:
        if line.startswith('## '):
            if current_lines:
                blocks.append((current_header, current_lines))
            current_header = line.lstrip('#').strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        blocks.append((current_header, current_lines))

    return blocks


def get_today_memory():
    import os
    # Use CST (Asia/Shanghai) for date
    os.environ['TZ'] = 'Asia/Shanghai'
    try:
        import time as _time
        _time.tzset()
    except:
        pass
    today_cst = datetime.now(CST).strftime("%Y-%m-%d")
    today = today_cst
    md_file = MEMORY_DIR / f"{today}.md"
    if md_file.exists():
        return md_file.read_text(encoding='utf-8'), md_file.name, today
    return None, None, None


def main():
    print(f"[{now_cst().strftime('%Y-%m-%d %H:%M')}] 开始记忆重要性评分...")

    content, filename, today_str = get_today_memory()
    if not content:
        print("  ⏭️  今日 memory 文件不存在")
        return

    print(f"  📄 读取 {filename}")

    blocks = parse_blocks(content)
    results = {'critical': [], 'high': [], 'medium': [], 'low': []}

    for header, lines in blocks:
        score, reason, items = score_block(header, lines)
        if score == 0 or not items:
            continue

        if score >= 80:
            bucket = 'critical'
        elif score >= 50:
            bucket = 'high'
        elif score >= 25:
            bucket = 'medium'
        else:
            bucket = 'low'

        results[bucket].append({
            'header': header,
            'score': score,
            'reason': reason,
            'items': items,
        })

    # 输出报告
    total = sum(len(items) for items in results.values())
    print(f"\n  📊 评分结果（共 {total} 条有效条目）：")
    print(f"  🔴 紧急固化(80+): {len(results['critical'])} 个块")
    print(f"  🟠 高价值(50-79): {len(results['high'])} 个块")
    print(f"  🟡 中等(25-49): {len(results['medium'])} 个块")
    print(f"  🟢 日常(<25): {len(results['low'])} 个块")

    for bucket_name, bucket_key in [('🔴', 'critical'), ('🟠', 'high')]:
        if results[bucket_key]:
            print(f"\n  {bucket_name} {bucket_key}：")
            for block in results[bucket_key]:
                print(f"    [{block['score']}分|{block['reason']}] {block['header']}")
                for item in block['items'][:3]:
                    print(f"      - {item[:80]}")

    # 写入 MEMORY.md
    new_for_memory = results['critical'] + results['high']
    if new_for_memory:
        existing = MEMORY_MD.read_text(encoding='utf-8') if MEMORY_MD.exists() else ""

        new_items_text = []
        for block in new_for_memory:
            for item in block['items']:
                if item not in existing and item not in '\n'.join(new_items_text):
                    new_items_text.append(item)

        if new_items_text:
            header = f"\n## 每日提炼 ({today_str})\n"
            items_str = "\n".join(f"- {p}" for p in new_items_text)
            with open(MEMORY_MD, 'a', encoding='utf-8') as f:
                f.write(f"{header}{items_str}\n")
            print(f"\n  ✅ 已追加 {len(new_items_text)} 条到 MEMORY.md")


if __name__ == "__main__":
    main()
