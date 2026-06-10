#!/usr/bin/env python3
"""
PARA Inbox 处理器
自动从收藏目录读取新内容，生成 PARA 路由建议

触发：每周日 19:30（Self-Improving 周报前）或手动运行
输入：collections/ 目录下新收藏的文章
输出：Obsidian inbox 草稿 + 路由建议

用法：
  python3 scripts/para_inbox_processor.py [--dry-run] [--limit 5]
"""

import json
import re
import os
from datetime import datetime, timedelta
from _timezone import CST
from pathlib import Path

COLLECTIONS_DIR = '~/.openclaw/workspace/collections'
OBSIDIAN_PARA = Path.home() / 'Obsidian' / 'PARA'
OBSIDIAN_INBOX = OBSIDIAN_PARA / 'inbox'
OBSIDIAN_AREAS = OBSIDIAN_PARA / 'areas'
OBSIDIAN_PROJECTS = OBSIDIAN_PARA / 'projects'
OBSIDIAN_RESOURCES = OBSIDIAN_PARA / 'resources'

# AREAS 索引（与实际目录对应）
AREAS = {
    'AI学习': OBSIDIAN_AREAS / 'AI学习.md',
    '认知科学': OBSIDIAN_AREAS / '认知科学.md',
    '中国历史': OBSIDIAN_AREAS / '中国历史.md',
    '物理学': OBSIDIAN_AREAS / '物理学.md',
}

# 关键词 → Area 映射
TOPIC_KEYWORDS = {
    'AI学习': [
        'ai', 'agent', 'llm', 'gpt', 'openai', '大模型', '人工智能', 'copilot',
        '知识管理', '笔记系统', 'obsidian', 'notion', '第二大脑',
        '提示词', 'prompt', '工作流', 'automation', '工具',
    ],
    '认知科学': [
        '认知', '思维', '学习', '记忆', '注意力', '元认知',
        '心理学', '行为', '决策', '偏差', '认知偏差',
    ],
    '中国历史': [
        '中国历史', '古代史', '近代史', '史纲', '政治史', '经济史',
        '文化史', '王朝', '帝王', '革命', '中国政治',
    ],
    '物理学': [
        '物理', '量子', '相对论', '力学', '热力学', '电磁', '天体',
    ],
}

# 已归档文件记录（避免重复处理）
STATE_FILE = '~/.openclaw/workspace/scripts/.para_inbox_state.json'

def load_state():
    if Path(STATE_FILE).exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'archived': [], 'last_run': None}

def save_state(state):
    state['last_run'] = datetime.now(CST).isoformat()
    Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def scan_collections(since_days=7):
    """扫描最近收藏的文章"""
    state = load_state()
    cutoff = datetime.now(CST) - timedelta(days=since_days)
    
    new_articles = []
    
    for subdir in ['articles', 'wechat', 'ideas']:
        subpath = Path(COLLECTIONS_DIR) / subdir
        if not subpath.exists():
            continue
        
        for md_file in subpath.glob('*.md'):
            # 跳过已处理的
            if md_file.name in state['archived']:
                continue
            
            # 检查修改时间
            mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
            if mtime > cutoff:
                content = md_file.read_text()
                new_articles.append({
                    'file': md_file,
                    'name': md_file.name,
                    'mtime': mtime,
                    'content': content[:500],  # 只读前500字符做分析
                    'full_path': str(md_file),
                })
    
    return new_articles

def infer_area(content: str) -> list[str]:
    """根据内容推断最匹配的 Area（可能多个）"""
    content_lower = content.lower()
    scores = {}
    for area, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in content_lower)
        if score > 0:
            scores[area] = score
    return sorted(scores.items(), key=lambda x: -x[1])

def extract_metadata(content: str) -> dict:
    """从文章内容提取元信息"""
    meta = {'title': '', 'author': '', 'date': '', 'tags': []}
    
    # 标题（第一个 # 或文件名）
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        meta['title'] = title_match.group(1).strip()
    
    # 日期
    date_match = re.search(r'(\d{4}[-/]\d{2}[-/]\d{2})', content)
    if date_match:
        meta['date'] = date_match.group(1)
    
    # 标签
    tags = re.findall(r'tags?[:\s]+([^\n]+)', content, re.IGNORECASE)
    if tags:
        meta['tags'] = [t.strip() for t in tags[0].split(',')]
    
    return meta

def generate_inbox_entry(article: dict, areas: list) -> str:
    """生成 Inbox 条目"""
    meta = extract_metadata(article['content'])
    title = meta['title'] or article['name'].replace('.md', '')
    area_tags = ', '.join([f'[[{a}]]' for a, _ in areas[:2]])
    
    entry = f"""## {title}
- **来源**: `{article['full_path']}`
- **日期**: {meta['date'] or article['mtime'].strftime('%Y-%m-%d')}
- **建议 Area**: {area_tags}
- **Tags**: {', '.join(meta['tags']) if meta['tags'] else '待定'}

> {meta['title'] if meta['title'] else title}

---
"""
    return entry

def append_to_area(area_path: Path, article: dict, area_name: str):
    """追加文章引用到 Area 文件"""
    meta = extract_metadata(article['content'])
    title = meta['title'] or article['name'].replace('.md', '')
    date = meta['date'] or article['mtime'].strftime('%Y-%m-%d')
    
    # 生成 Obsidian 内部链接
    # 把收藏路径转为 Obsidian 路径（假设同步到 Obsidian）
    # 实际链接需要根据实际 Obsidian 同步路径调整
    link_path = f"收藏/公众号/{title}" if 'wechat' in article['full_path'] else f"收藏/文章/{title}"
    
    new_entry = f"\n- **{title}** ({date}) — [[{link_path}]]\n"
    
    with open(area_path, 'a') as f:
        f.write(new_entry)

def run_dry_run(limit=5):
    """预览模式：只显示路由建议，不实际写入"""
    articles = scan_collections(since_days=7)
    print(f"🔍 发现 {len(articles)} 篇新文章（近7天）")
    
    if not articles:
        print("✅ 无新内容，Inbox 无需更新")
        return
    
    for article in articles[:limit]:
        areas = infer_area(article['content'])
        meta = extract_metadata(article['content'])
        title = meta['title'] or article['name'].replace('.md', '')
        
        print(f"\n📄 {title}")
        print(f"   文件: {article['name']}")
        if areas:
            print(f"   → 建议路由: {' | '.join([a for a, _ in areas[:2]])}")
        else:
            print(f"   → 建议路由: 待定（建议放进 Resources）")
    
    if len(articles) > limit:
        print(f"\n... 还有 {len(articles) - limit} 篇")

def run_processor():
    """完整处理流程"""
    state = load_state()
    articles = scan_collections(since_days=7)
    
    if not articles:
        print("✅ PARA Inbox：无新内容")
        return {'processed': 0, 'routed': {}}
    
    print(f"📥 PARA Inbox 处理：{len(articles)} 篇新文章")
    
    OBSIDIAN_INBOX.mkdir(parents=True, exist_ok=True)
    inbox_file = OBSIDIAN_INBOX / f"inbox-{datetime.now(CST).strftime('%Y-%m-%d')}.md"
    
    routed = {}
    inbox_entries = []
    
    for article in articles:
        areas = infer_area(article['content'])
        entry = generate_inbox_entry(article, areas)
        inbox_entries.append(entry)
        
        # 写入 inbox
        with open(inbox_file, 'a') as f:
            f.write(entry)
        
        # 追加到 Area（如果匹配度高）
        if areas and areas[0][1] >= 1:
            top_area = areas[0][0]
            area_path = AREAS.get(top_area)
            if area_path and area_path.exists():
                append_to_area(area_path, article, top_area)
                routed[top_area] = routed.get(top_area, 0) + 1
        
        # 标记为已处理
        state['archived'].append(article['name'])
    
    # 保持 state 精简（只保留最近 200 条）
    if len(state['archived']) > 200:
        state['archived'] = state['archived'][-200:]
    
    save_state(state)
    
    print(f"\n✅ 处理完成：{len(articles)} 篇")
    if routed:
        print("📬 路由分布：")
        for area, count in sorted(routed.items()):
            print(f"   {area}: {count}篇")
    print(f"📁 Inbox 草稿：{inbox_file}")
    
    return {'processed': len(articles), 'routed': routed}

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=5)
    args = parser.parse_args()
    
    if args.dry_run:
        run_dry_run(limit=args.limit)
    else:
        run_processor()
