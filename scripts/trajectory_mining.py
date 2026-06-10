#!/usr/bin/env python3
"""
轨迹挖掘 v3 - 精准版
只挖掘真正有价值的 patterns：真实错误、校正教训、重复失败
不抓"成功完成"等宽泛信号
"""

import re
from datetime import datetime, timedelta
from _timezone import CST
from pathlib import Path
from collections import defaultdict

SELF_IMPROVING_DIR = Path.home() / 'self-improving'
MEMORY_DIR = Path('~/.openclaw/workspace/memory').expanduser()
CORRECTIONS_FILE = SELF_IMPROVING_DIR / 'corrections.md'
LOOKBACK_DAYS = 30

# 精准错误信号（必须有具体问题描述）
ERROR_SIGNALS = [
    # 超时/性能
    (r'超时[^\w]', '超时问题'),
    (r'timed?\s*out', '超时问题'),
    # 失败
    (r'失败(?!.+成功)', '执行失败'),
    (r'failed(?!.+ok)', '执行失败'),
    (r'Error[:\s]', '执行错误'),
    # 配置/规格错误
    (r'invalid[-\s]?spec', '规格错误'),
    (r'配置.*错误|错误.*配置', '配置错误'),
    # 遗漏/疏漏
    (r'(漏过|忘记|未能|未.+?执行)', '遗漏/疏漏'),
    (r'没有.*执行|未执行', '未执行'),
    # 重复问题
    (r'重复(?!成功)', '重复问题'),
    # 代码异常
    (r'Traceback|Exception|PermissionError|FileNotFoundError', '代码异常'),
    # 任务冲突
    (r'冲突(?!成功)', '冲突问题'),
    # 权限问题
    (r'permission denied|权限不足', '权限问题'),
]

# 精准教训信号
LESSON_SIGNALS = [
    # 明确教训
    (r'教训[：:].{10,100}', '教训总结'),
    (r'经验[：:].{10,100}', '经验总结'),
    # 改进承诺（具体说明改什么）
    (r'后续.*改进|以后.*要.{10,50}|下次.*应.{10,50}|承诺.{10,50}', '改进承诺'),
    # 纠正记录（包含具体错误内容）
    (r'失误了|搞错|错在|不对是', '主动承认错误'),
]

# 重复成功模式（需要特定任务关键词，不单独出现）
TASK_SUCCESS_PATTERNS = [
    (r'定时.*成功|定时.*完成|定时.*推送', '定时任务成功'),
    (r'备份.*成功|备份.*完成', '备份成功'),
    (r'重试.*成功|重试.*完成', '重试成功'),
    (r'同步.*成功|同步.*完成', '同步成功'),
]

# 关键领域关键词
DOMAIN_MAP = {
    'skill-management': ['skill', '安装', '卸载', 'skill-vetter', '安全审查', '技能'],
    'cron-management': ['cron', '定时', '超时', '重试', 'schedule', '任务'],
    'memory-system': ['memory', 'MemOS', '同步', '向量', '记忆', '备份'],
    'content-workflow': ['收藏', '文章', '公众号', '收集', '关联'],
    'feishu': ['飞书', 'feishu', '推送', '群', '消息'],
    'book-card': ['书籍', '卡片', '排版', '金句', 'emoji'],
}

def load_memory_files():
    files = sorted(MEMORY_DIR.glob('*.md'))
    cutoff = datetime.now(CST) - timedelta(days=LOOKBACK_DAYS)
    content_by_date = {}
    for f in files:
        try:
            dt = datetime.strptime(f.stem, '%Y-%m-%d').replace(tzinfo=CST)
            if dt >= cutoff:
                content_by_date[f.stem] = f.read_text()
        except Exception:
            pass
    return content_by_date

def scan_content(text):
    """只返回真正有价值的 findings"""
    findings = []
    
    # 精准错误扫描
    for pattern, label in ERROR_SIGNALS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 100)
            ctx = text[start:end].replace('\n', ' ').strip()
            findings.append({
                'type': 'error',
                'label': label,
                'context': ctx,
                'pattern': pattern,
                'priority': 'high'
            })
    
    # 教训扫描
    for pattern, label in LESSON_SIGNALS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, m.start() - 50)
            end = min(len(text), m.end() + 150)
            ctx = text[start:end].replace('\n', ' ').strip()
            findings.append({
                'type': 'lesson',
                'label': label,
                'context': ctx,
                'pattern': pattern,
                'priority': 'high'
            })
    
    # 有任务前缀的成功才记录
    for pattern, label in TASK_SUCCESS_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, m.start() - 50)
            end = min(len(text), m.end() + 80)
            ctx = text[start:end].replace('\n', ' ').strip()
            findings.append({
                'type': 'success',
                'label': label,
                'context': ctx,
                'pattern': pattern,
                'priority': 'low'
            })
    
    return findings

def infer_domain(context):
    text_lower = context.lower()
    scores = {}
    for domain, keywords in DOMAIN_MAP.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[domain] = score
    return max(scores, key=scores.get) if scores else 'general'

def deduplicate(findings, existing_text):
    """基于上下文相似度去重"""
    seen = set()
    unique = []
    for f in findings:
        # 用 context 前 100 字符作为去重 key
        key = f['context'][:100].lower()
        # 去除空白和标点
        key = re.sub(r'[\s\W]', '', key)
        if key and key not in seen and key not in existing_text:
            seen.add(key)
            unique.append(f)
    return unique

def main():
    print(f"🔍 轨迹挖掘 v3（精准版，{LOOKBACK_DAYS}天回溯）")
    print("=" * 50)
    
    memory_contents = load_memory_files()
    print(f"📅 覆盖 {len(memory_contents)} 天的 memory 日志")
    
    # 加载已有 corrections 内容用于去重
    existing_text = ''
    if CORRECTIONS_FILE.exists():
        existing_text = CORRECTIONS_FILE.read_text()
    
    all_findings = []
    for date in sorted(memory_contents.keys()):
        findings = scan_content(memory_contents[date])
        for f in findings:
            f['date'] = date
            f['domain'] = infer_domain(f['context'])
        all_findings.extend(findings)
        if findings:
            print(f"📌 {date}: {len(findings)} 条")
    
    # 去重
    unique = deduplicate(all_findings, existing_text)
    print(f"\n{'=' * 50}")
    print(f"✅ 去重后：{len(unique)} 条（总计 {len(all_findings)} 条）")
    
    if unique:
        # 只输出有价值的（去掉 low priority 的宽泛成功）
        valuable = [f for f in unique if f['priority'] == 'high']
        print(f"   高价值：{len(valuable)} 条")
        
        # 写入
        lines = [f"\n## 轨迹挖掘 v3（{datetime.now(CST).strftime('%Y-%m-%d')}）\n"]
        lines.append(f"*从 {LOOKBACK_DAYS} 天 memory 日志精准挖掘，高价值 {len(valuable)} 条*\n\n")
        
        errors = [f for f in valuable if f['type'] == 'error']
        lessons = [f for f in valuable if f['type'] == 'lesson']
        
        if errors:
            lines.append("### ❌ 错误/教训\n\n")
            for f in errors[:20]:  # 最多 20 条
                lines.append(f"- **{f['label']}** [{f['domain']}]：{f['context'][30:180]}...\n")
            lines.append("\n")
        
        if lessons:
            lines.append("### 🔧 改进/教训\n\n")
            for f in lessons[:10]:
                lines.append(f"- **{f['label']}** [{f['domain']}]：{f['context'][30:180]}...\n")
            lines.append("\n")
        
        entry = ''.join(lines)
        with open(CORRECTIONS_FILE, 'a') as fc:
            fc.write(entry)
        print(f"📝 已追加到 {CORRECTIONS_FILE}")
        
        domain_count = defaultdict(int)
        for f in valuable:
            domain_count[f['domain']] += 1
        print(f"\n📊 领域分布：")
        for d, c in sorted(domain_count.items(), key=lambda x: -x[1]):
            print(f"   {d}: {c}条")
    else:
        print("未发现新的高价值 patterns")
    
    return unique

if __name__ == '__main__':
    main()
