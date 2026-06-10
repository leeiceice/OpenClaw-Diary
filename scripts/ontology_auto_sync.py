#!/usr/bin/env python3
"""
Ontology 自动同步脚本
检查 memory/ 目录下的每日日记，自动将新的日记实体注册到 ontology graph。

运行：每日 cron 或按需
"""
import json
import re
from pathlib import Path
from datetime import datetime
from _timezone import CST

MEMORY_DIR = Path("~/.openclaw/workspace/memory").expanduser()
GRAPH_FILE = Path("~/.openclaw/workspace/memory/ontology/graph.jsonl").expanduser()

def load_graph():
    """加载现有 graph"""
    entities, relations = {}, []
    if GRAPH_FILE.exists():
        with open(GRAPH_FILE) as f:
            for line in f:
                r = json.loads(line.strip())
                if r.get("op") == "create":
                    entities[r["entity"]["id"]] = r["entity"]
                elif r.get("op") == "relate":
                    relations.append(r)
    return entities, relations

def save_graph_op(op_type, entity=None, relation=None):
    """追加操作到 graph 文件"""
    if op_type == "create" and entity:
        with open(GRAPH_FILE, "a") as f:
            f.write(json.dumps({"op": "create", "entity": entity}, ensure_ascii=False) + "\n")
    elif op_type == "relate" and relation:
        with open(GRAPH_FILE, "a") as f:
            f.write(json.dumps({"op": "relate", **relation}, ensure_ascii=False) + "\n")

def extract_topics(md_text: str) -> list[str]:
    """从日记提取主题关键词"""
    topics = []
    for line in md_text.split('\n'):
        line = line.strip()
        # 提取二级标题主题
        if line.startswith('### '):
            topics.append(line.replace('### ', '').strip())
    return topics[:3]

def main():
    entities, _ = load_graph()
    existing_ids = set(entities.keys())
    
    # 找所有日记文件
    daily_files = list(MEMORY_DIR.glob("????-??-??.md"))
    new_count = 0
    
    for md_file in daily_files:
        date_str = md_file.stem  # YYYY-MM-DD
        entity_id = f"daily_{date_str.replace('-', '')}"
        
        if entity_id in existing_ids:
            continue
        
        # 新日记文件 → 添加到 graph
        content = md_file.read_text(encoding='utf-8')
        topics = extract_topics(content)
        
        entity = {
            "id": entity_id,
            "type": "Document",
            "properties": {
                "name": date_str,
                "file": str(md_file),
                "topics": ", ".join(topics) if topics else "日常记录"
            }
        }
        
        save_graph_op("create", entity=entity)
        save_graph_op("relate", relation={
            "from": entity_id,
            "rel": "has_daily_memory",
            "to": "file_memory_md"
        })
        new_count += 1
        print(f"  ✅ 新增: {entity_id} ({', '.join(topics) if topics else '日常记录'})")
    
    if new_count == 0:
        print("  ⏭️  无新增日记实体")
    else:
        print(f"  📊 共新增 {new_count} 个日记实体到 ontology")

if __name__ == "__main__":
    print(f"[{datetime.now(CST).strftime('%Y-%m-%d %H:%M')}] 开始 ontology 自动同步...")
    main()
