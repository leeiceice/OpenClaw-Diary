#!/usr/bin/env python3
"""
每日记忆自动提炼脚本 v3
读取当天 memory/YYYY-MM-DD.md，提炼关键决策/教训/规范变更，写入 MEMORY.md。
去重原则：只写入 MEMORY.md 中尚不存在的内容。
"""
from pathlib import Path
from datetime import date, datetime, timezone, timedelta
from _timezone import CST, now_cst

MEMORY_DIR = Path("~/.openclaw/workspace/memory").expanduser()
MEMORY_MD  = Path("~/.openclaw/workspace/MEMORY.md").expanduser()

# 这些行几乎永远无价值（cron 过程日志），直接跳过
CRON_NOISE_STARTS = [
    'Cron:', 'cron-retry-monitor', '执行记录', '无新增',
    '结果：', '状态：', '备注：', '失败任务检查',
    '发现 1 个失败任务', '无同名任务', '距离上次失败',
    '重试已触发', '重试后状态',
    '三层记忆状态', 'Obsidian备份', 'Ontology图谱',
    '自动化Cron', '技能进化', '运行时间',
    '[',  # [时间戳] 格式的 cron 日志几乎全是噪音
]


def is_noise(line: str) -> bool:
    s = line.strip()
    for prefix in CRON_NOISE_STARTS:
        if s.startswith(prefix):
            return True
    return False


def extract_points_from_block(lines: list[str], start: int, end: int) -> list[str]:
    """从 ## 块（start 行到 end 行）中提取有效条目"""
    points = []
    for i in range(start, end):
        line = lines[i].strip()
        # 只处理顶级 - 条目（不处理子层级）
        if not line.startswith('- '):
            continue
        text = line.lstrip('- ').strip()
        # 跳过噪音和过短的内容
        if len(text) < 10 or is_noise(text):
            continue
        # 跳过包含噪音关键词的条目
        noise_in_content = any(k in text for k in [
            '执行完毕', '执行记录', 'cron', 'consecutiveErrors',
            'lastRunStatus', 'nextRunAt', '重试', 'running',
        ])
        if noise_in_content:
            continue
        if text not in points:
            points.append(text)
    return points


def extract_key_points(md_text: str) -> list[str]:
    """
    策略：识别有决策意义的 ## 块（完成项/教训/规范/授权/问题），
    从其顶级 - 条目中提取有价值的结论。
    忽略 cron 执行日志块。
    """
    lines = md_text.split('\n')
    points = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('## '):
            # 找到下一个 ## 的位置
            j = i + 1
            while j < len(lines) and not lines[j].startswith('## '):
                j += 1
            # 判断这个 ## 块是否值得提炼
            block_text = ' '.join(lines[i:j])
            valuable = any(k in block_text for k in [
                '完成项', '教训', '根本', '规范', '授权',
                '确认', '更新', '新增', '固化', '问题',
                '重构', '改进', '提炼', '优化',
            ])
            if valuable and not is_noise(line):
                extracted = extract_points_from_block(lines, i, j)
                for e in extracted:
                    if e not in points:
                        points.append(e)
            i = j
        else:
            i += 1
    return points[:8]


def read_memory_md() -> str:
    if MEMORY_MD.exists():
        return MEMORY_MD.read_text(encoding='utf-8')
    return ""


def dedup_and_append(new_points: list[str], today_str: str) -> int:
    if not new_points:
        return 0
    existing = read_memory_md()
    header = f"\n## 每日提炼 ({today_str})\n"
    new_unique = [p for p in new_points if p not in existing]
    if not new_unique:
        print("  ⏭️  所有条目已在 MEMORY.md 中，跳过")
        return 0
    items = "\n".join(f"- {p}" for p in new_unique)
    with open(MEMORY_MD, 'a', encoding='utf-8') as f:
        f.write(f"{header}{items}\n")
    print(f"  ✅ 新增 {len(new_unique)} 条（过滤 {len(new_points) - len(new_unique)} 条噪音/重复）")
    return len(new_unique)


def get_today_memory():
    today_str = datetime.now(CST).strftime('%Y-%m-%d')
    md_file = MEMORY_DIR / f"{today_str}.md"
    if md_file.exists():
        return md_file.read_text(encoding='utf-8'), md_file.name, today_str
    print(f"  ⏭️  今日 {today_str} memory 文件不存在，跳过")
    return None


def main():
    print(f"[{now_cst().strftime('%Y-%m-%d %H:%M')}] 开始每日记忆提炼...")
    result = get_today_memory()
    if not result:
        return
    content, filename, today_str = result
    print(f"  📄 读取 {filename}")
    points = extract_key_points(content)
    print(f"  🎯 提炼 {len(points)} 条关键条目")
    written = dedup_and_append(points, today_str)
    if written:
        print(f"  ✅ 已追加到 MEMORY.md")


if __name__ == "__main__":
    main()
