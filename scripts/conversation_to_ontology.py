#!/usr/bin/env python3
"""
Ontology 会话级实体提取脚本 v2.1
从 session JSONL 文件中提取实体，追加到 ontology graph。

优化：
- CronJob 名称从 jobs.json 解析可读名
- 新增 Lee/小马 等关键人物实体
- 清理超长/无意义概念名
- 移除 MemOS 同步依赖
"""
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from _timezone import CST

WORKSPACE = Path("/root/.openclaw/workspace")
GRAPH_FILE = WORKSPACE / "memory/ontology/graph.jsonl"
STATE_FILE = WORKSPACE / "scripts/.conversation_ontology_state.json"
SESSIONS_DIR = Path("~/.openclaw/agents/main/sessions").expanduser()
CRON_JOBS_FILE = Path("~/.openclaw/cron/jobs.json").expanduser()

# 预定义关键人物实体（不依赖 emoji）
KEY_PERSONS = {
    "Lee": {"name": "Lee", "id": "person_lee"},
    "小马": {"name": "小马", "id": "person_xiaoma"},
    "小龙虾": {"name": "小龙虾", "id": "person_xiaolongxia"},
    "CC": {"name": "Claude Code", "id": "person_cc"},
}

def load_cron_names():
    """从 jobs.json 加载 cron 任务名称映射"""
    cron_map = {}
    if CRON_JOBS_FILE.exists():
        try:
            with open(CRON_JOBS_FILE) as f:
                d = json.load(f)
            for job in d.get("jobs", []):
                job_id = job.get("id", "")
                name = job.get("name", "")
                if job_id and name:
                    # 提取 UUID 部分（去掉连字符）
                    uuid_part = job_id.replace("-", "")
                    cron_map[job_id.lower()] = name
                    cron_map[uuid_part.lower()] = name
                    # 也存简化版（前8位）
                    if len(job_id) > 8:
                        cron_map[job_id[:8].lower()] = name
        except Exception:
            pass
    return cron_map

def load_state():
    """加载状态文件"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"processed_sessions": {}, "last_run": None}

def save_state(state):
    """保存状态文件"""
    state["last_run"] = datetime.now(CST).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_graph():
    """加载现有 graph"""
    entities, relations = {}, []
    if GRAPH_FILE.exists():
        with open(GRAPH_FILE) as f:
            for line in f:
                try:
                    r = json.loads(line.strip())
                    if r.get("op") == "create":
                        entities[r["entity"]["id"]] = r["entity"]
                    elif r.get("op") == "relate":
                        relations.append(r)
                except:
                    pass
    return entities, relations

def save_graph_op(op_type, entity=None, relation=None):
    """追加操作到 graph 文件"""
    if op_type == "create" and entity:
        with open(GRAPH_FILE, "a") as f:
            f.write(json.dumps({"op": "create", "entity": entity}, ensure_ascii=False) + "\n")
    elif op_type == "relate" and relation:
        with open(GRAPH_FILE, "a") as f:
            f.write(json.dumps({"op": "relate", **relation}, ensure_ascii=False) + "\n")

def extract_text_from_message(msg: dict) -> str:
    """从消息对象中提取纯文本"""
    text_parts = []

    # 处理 OpenClaw JSONL 格式：content 在 msg.content 中
    content = msg.get("content", [])
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    text_parts.append(item["text"])
                elif item.get("type") == "tool_result" and item.get("content"):
                    text_parts.append(str(item["content"]))
                elif item.get("type") == "tool_use" and item.get("name"):
                    # 工具调用名也可能是实体
                    text_parts.append(f"`{item['name']}`")

    # 处理带 reasoning 的消息
    if msg.get("reasoning"):
        text_parts.append(str(msg["reasoning"]))

    return " ".join(text_parts)

def clean_concept_name(name: str) -> str:
    """清理概念名：移除超长内容、句子级别的文本"""
    # 移除包含句号过多或长度超过60字符的概念
    if len(name) > 60:
        # 取前40字符 + "..."
        name = name[:40] + "..."
    # 移除含有执行手册、完成等完整句子痕迹的内容
    if re.search(r'[\u4e00-\u9fff]{20,}', name):
        # 中文长句，取前20字符
        name = name[:20] + "..."
    return name.strip()

def extract_entities_from_text(text: str, cron_map: dict) -> list[dict]:
    """从文本中提取实体"""
    entities = []
    seen = set()

    # 提取被[[ ]]包围的概念（Obsidian双向链接格式）
    wiki_links = re.findall(r'\[\[([^\]]+)\]\]', text)
    for link in wiki_links:
        if link not in seen and len(link) > 1:
            seen.add(link)
            clean_name = clean_concept_name(link)
            if len(clean_name) > 2:  # 过滤掉过短的
                entities.append({
                    "id": f"concept_{clean_name.replace(' ', '_').replace('/', '_')}",
                    "type": "Concept",
                    "properties": {"name": clean_name}
                })

    # 提取代码/工具名称（如 `skill_name`, python, git 等）
    code_refs = re.findall(r'`([a-z_-]+)`', text, re.IGNORECASE)
    for ref in code_refs:
        ref_lower = ref.lower()
        if ref_lower not in seen and len(ref_lower) > 2:
            seen.add(ref_lower)
            entities.append({
                "id": f"tool_{ref_lower}",
                "type": "Tool",
                "properties": {"name": ref}
            })

    # 提取带 emoji 的人名模式（如 👤 Lee）
    name_patterns = re.findall(r'[\U0001F464\U0001F474]\s+([A-Za-z\u4e00-\u9fff]{2,30})', text)
    for name in name_patterns:
        if name not in seen:
            seen.add(name)
            entities.append({
                "id": f"person_{name}",
                "type": "Person",
                "properties": {"name": name}
            })

    # 提取关键人物（不依赖 emoji）
    for person_name, person_info in KEY_PERSONS.items():
        if person_name in text and person_info["id"] not in seen:
            seen.add(person_info["id"])
            entities.append({
                "id": person_info["id"],
                "type": "Person",
                "properties": {"name": person_info["name"]}
            })

    # 提取技能名称（如 skill-name, skill_name）
    skill_refs = re.findall(r'(?:skill[_-]?)([a-z][a-z0-9_-]{1,30})', text, re.IGNORECASE)
    for skill in skill_refs:
        skill_lower = skill.lower()
        if skill_lower not in seen and len(skill_lower) > 2:
            seen.add(skill_lower)
            entities.append({
                "id": f"skill_{skill_lower}",
                "type": "Skill",
                "properties": {"name": skill}
            })

    # 提取脚本路径（如 scripts/xxx.py）
    script_paths = re.findall(r'scripts/([\w_-]+\.py)', text)
    for script in script_paths:
        script_lower = script.lower()
        if script_lower not in seen:
            seen.add(script_lower)
            entities.append({
                "id": f"script_{script_lower}",
                "type": "Script",
                "properties": {"name": script}
            })

    # 提取 cron 任务名并解析为可读名称
    cron_refs = re.findall(r'cron[:/]?([a-z0-9_-]+)', text, re.IGNORECASE)
    for cron in cron_refs:
        cron_lower = cron.lower()
        # 先尝试从 cron_map 获取可读名称
        readable_name = cron_map.get(cron_lower, cron)
        entity_id = f"cron_{readable_name.replace(' ', '_').replace('-', '_').lower()}"
        if entity_id not in seen:
            seen.add(entity_id)
            entities.append({
                "id": entity_id,
                "type": "CronJob",
                "properties": {"name": readable_name}
            })

    return entities

def extract_entities_from_session_file(session_path: Path, cron_map: dict) -> list[dict]:
    """从单个 session JSONL 文件提取实体"""
    all_entities = []
    seen_in_file = set()

    try:
        with open(session_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                except:
                    continue

                if event.get("type") == "message":
                    msg_obj = event.get("message", {})
                    role = msg_obj.get("role")
                    if role in ("user", "assistant"):
                        text = extract_text_from_message(msg_obj)
                        if text:
                            entities = extract_entities_from_text(text, cron_map)
                            for ent in entities:
                                if ent["id"] not in seen_in_file:
                                    seen_in_file.add(ent["id"])
                                    all_entities.append(ent)

    except Exception as e:
        pass

    return all_entities

def get_recent_session_files(state: dict, max_age_days: int = 7) -> list[Path]:
    """获取最近活跃的 session 文件"""
    if not SESSIONS_DIR.exists():
        return []

    cutoff = datetime.now(CST) - timedelta(days=max_age_days)
    recent = []

    for session_file in SESSIONS_DIR.iterdir():
        name = session_file.name
        if not (name.endswith('.deleted') or '.deleted.' in name or
                '.reset.' in name or '.checkpoint.' in name or
                name.endswith('.trajectory.jsonl')):
            if name.endswith('.jsonl'):
                try:
                    # 必须带 tz=CST，否则 mtime 是 naive，跟 aware 的 cutoff 比较会 TypeError
                    mtime = datetime.fromtimestamp(session_file.stat().st_mtime, tz=CST)
                    if mtime > cutoff:
                        session_key = session_file.stem
                        recent.append((session_file, session_key))
                except:
                    pass

    return recent

def main():
    print(f"[{datetime.now(CST).strftime('%Y-%m-%d %H:%M')}] 开始会话级实体提取 (v2.1)...")

    cron_map = load_cron_names()
    print(f"  📋 已加载 {len(cron_map)} 个 cron 任务名称")

    state = load_state()
    existing_entities, _ = load_graph()
    existing_ids = set(existing_entities.keys())

    sessions_to_process = get_recent_session_files(state)
    new_count = 0

    for session_file, session_key in sessions_to_process:
        entities = extract_entities_from_session_file(session_file, cron_map)

        for entity in entities:
            if entity["id"] not in existing_ids:
                save_graph_op("create", entity=entity)
                existing_ids.add(entity["id"])
                new_count += 1
                print(f"  ✅ 新增实体: {entity['id']} ({entity['type']})")

        state["processed_sessions"][session_key] = datetime.now(CST).isoformat()

    save_state(state)

    if new_count == 0:
        print("  ⏭️  无新增会话实体")
    else:
        print(f"  📊 共新增 {new_count} 个会话实体到 ontology")

if __name__ == "__main__":
    main()