#!/usr/bin/env python3
"""
memory_sensor.py — 偏差传感器 CLI
小龙虾工程控制论记忆系统核心组件

功能：
1. 写入新偏差（自动检测同类主题，trigger_count +1）
2. 扫描重复偏差，N≥2 触发 L2 生成
3. 收敛检测
4. 统计与列表
5. 验证状态更新

路径：
- corrections.md: ~/.openclaw/workspace/self-improving/corrections.md
- scenes/:       ~/.openclaw/workspace/memory/deviations/scenes/
"""

import argparse
import difflib
import os
import re
import sys
from datetime import datetime
from _timezone import CST
from pathlib import Path
from typing import Optional

# ===== 路径配置 =====
WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", "~/.openclaw/workspace")).expanduser()
CORRECTIONS_PATH = WORKSPACE / "self-improving" / "corrections.md"
SCENES_DIR = WORKSPACE / "memory" / "deviations" / "scenes"
SELF_IMPROVING_DIR = WORKSPACE / "self-improving"

def ensure_dirs():
    """确保必要目录存在"""
    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    SELF_IMPROVING_DIR.mkdir(parents=True, exist_ok=True)

# ===== 偏差记录结构 =====
class Deviation:
    def __init__(self, dev_id: str, subject: str, wrong: str, right: str,
                 severity: str, trigger_count: int, status: str,
                 last_verified: str, session: str, line_start: int = 0):
        self.dev_id = dev_id
        self.subject = subject
        self.wrong = wrong
        self.right = right
        self.severity = severity
        self.trigger_count = trigger_count
        self.status = status
        self.last_verified = last_verified
        self.session = session
        self.line_start = line_start

    def to_markdown(self) -> str:
        return f"""### deviation_id: {self.dev_id}
- **主题**: {self.subject}
- **偏差描述**: 以为 {self.wrong} → 实际是 {self.right}
- **严重程度**: {self.severity}
- **触发次数**: {self.trigger_count}
- **验证状态**: {self.status}
- **最后验证**: {self.last_verified}
- **SESSION**: {self.session}"""

def parse_corrections() -> list[Deviation]:
    """解析 corrections.md，提取所有偏差记录"""
    if not CORRECTIONS_PATH.exists():
        return []

    content = CORRECTIONS_PATH.read_text()
    deviations = []

    # 匹配格式：### deviation_id: dev_YYYYMMDD_NNN ... ### deviation_id: ...
    # 按 ### deviation_id: 分隔，每个偏差记录独立解析
    # 偏差描述格式：XXX → YYY（箭头前后分别是 wrong 和 right）
    entries = re.split(r'(?=### deviation_id: )', content)

    for entry in entries:
        if not re.match(r'^### deviation_id: dev_\d{8}_\d{3}', entry.strip()):
            continue

        lines = entry.strip().split('\n')

        # 跳过格式示例（YYYYMMDD_NNN 是占位符）
        if 'YYYYMMDD' in lines[0]:
            continue

        # 2026-06-07 调低门槛：8 -> 3. 原先 8 门槛会过滤掉缺字段的简化记录.
        if len(lines) < 3:
            continue

        # 使用正则直接从 entry 文本提取各字段（更robust）
        entry_text = entry.strip()

        dev_id_m = re.search(r'### deviation_id: (dev_\d{8}_\d{3})', entry_text)
        subject_m = re.search(r'\*\*主题\*\*: ([^\n]+)', entry_text)
        # 偏差描述格式: **偏差描述**: 以为 XXX → 实际是 YYY
        # wrong / right 都取单行 (跨行 right 场景罕见, ECC 实践建议单行)
        desc_m = re.search(
            r'\*\*偏差描述\*\*:\s*([^\n]+?)\s*→\s*([^\n]+?)(?=\n|$)',
            entry_text
        )
        severity_m = re.search(r'\*\*严重程度\*\*: ([^\n]+)', entry_text)
        trigger_m = re.search(r'\*\*触发次数\*\*: (\d+)', entry_text)
        status_m = re.search(r'\*\*验证状态\*\*: ([^\n]+)', entry_text)
        last_verified_m = re.search(r'\*\*最后验证\*\*: ([^\n]+)', entry_text)
        session_m = re.search(r'\*\*SESSION\*\*: ([^\n]+)', entry_text)

        if not all([dev_id_m, subject_m, severity_m, trigger_m]):
            continue

        dev_id = dev_id_m.group(1)
        subject = subject_m.group(1).strip()
        severity = severity_m.group(1).strip()
        trigger_count = int(trigger_m.group(1))
        status = status_m.group(1).strip() if status_m else '待验证'
        last_verified = last_verified_m.group(1).strip() if last_verified_m else ''
        session = session_m.group(1).strip() if session_m else ''

        if desc_m:
            wrong = re.sub(r'^以为\s*', '', desc_m.group(1).strip())
            right = desc_m.group(2).strip()
        else:
            wrong = '(解析失败)'
            right = '(解析失败)'

        deviations.append(Deviation(
            dev_id=dev_id, subject=subject, wrong=wrong, right=right,
            severity=severity, trigger_count=trigger_count,
            status=status, last_verified=last_verified, session=session
        ))

    # === 自由格式兜底 (2026-06-07 立) ===
    # 处理 ### deviation_id 块但缺 severity / trigger_count 的情况
    # 推断：缺 severity -> L0b（偏好类），缺 trigger_count -> 1，缺 status -> '待验证'
    fallback = _parse_free_format_blocks(content)
    # 去重：跳过 dev_id 已有的
    existing_ids = {d.dev_id for d in deviations}
    for d in fallback:
        if d.dev_id not in existing_ids:
            deviations.append(d)

    return deviations

def _parse_free_format_blocks(content: str) -> list[Deviation]:
    """对 `### deviation_id: dev_YYYYMMDD_NNN` 开头的块但缺标准字段的进行兑底解析。

    仅在 parse_corrections 主逻辑跳过的块上调用，填补：
    - 缺 severity -> L0b
    - 缺 trigger_count -> 1
    - 缺 status -> '待验证'
    - 缺偏差描述 -> 误填 '(自由格式记录)'
    """
    result = []
    blocks = re.split(r'(?=### deviation_id: )', content)

    for block in blocks:
        if not re.match(r'^### deviation_id: dev_\d{8}_\d{3}', block.strip()):
            continue
        if 'YYYYMMDD' in block.split('\n')[0]:
            continue
        if len(block.strip().split('\n')) < 3:
            continue

        # 主解析需要的字段
        dev_id_m = re.search(r'### deviation_id: (dev_\d{8}_\d{3})', block)
        subject_m = re.search(r'\*\*主题\*\*: ([^\n]+)', block)
        severity_m = re.search(r'\*\*严重程度\*\*: ([^\n]+)', block)
        trigger_m = re.search(r'\*\*触发次数\*\*: (\d+)', block)
        status_m = re.search(r'\*\*验证状态\*\*: ([^\n]+)', block)
        last_verified_m = re.search(r'\*\*最后验证\*\*: ([^\n]+)', block)
        session_m = re.search(r'\*\*SESSION\*\*: ([^\n]+)', block)
        # 偏差描述格式: **偏差描述**: 以为 XXX → 实际是 YYY (单行)
        desc_m = re.search(
            r'\*\*偏差描述\*\*:\s*([^\n]+?)\s*→\s*([^\n]+?)(?=\n|$)',
            block
        )

        # 字段齐全的主解析会处理，这里只处理缺字段的
        if all([dev_id_m, subject_m, severity_m, trigger_m]):
            continue

        if not all([dev_id_m, subject_m]):
            continue  # 连 dev_id + subject 都没有，不算偏差记录

        # 猜测今天作为最后验证
        today = datetime.now(CST).strftime("%Y-%m-%d")
        result.append(Deviation(
            dev_id=dev_id_m.group(1),
            subject=subject_m.group(1).strip(),
            wrong='(自由格式记录)' if not desc_m else re.sub(r'^以为\s*', '', desc_m.group(1).strip()),
            right='(需人工补全)' if not desc_m else desc_m.group(2).strip(),
            severity=severity_m.group(1).strip() if severity_m else 'L0b',
            trigger_count=int(trigger_m.group(1)) if trigger_m else 1,
            status=status_m.group(1).strip() if status_m else '待验证',
            last_verified=last_verified_m.group(1).strip() if last_verified_m else today,
            session=session_m.group(1).strip() if session_m else '',
        ))

    return result

def extract_keywords(text: str) -> set:
    """提取关键词（支持中英文混合）
    - 英文按空格/连字符分词
    - 中文按字符 bigram（2-gram）提取
    """
    keywords = set()
    # English words
    en_words = re.findall(r'[a-zA-Z0-9]{2,}', text.lower())
    keywords.update(en_words)
    # Chinese bigrams
    cn_chars = re.findall(r'[\u4e00-\u9fff]', text)
    for i in range(len(cn_chars) - 1):
        bigram = cn_chars[i] + cn_chars[i+1]
        keywords.add(bigram)
    return keywords

def find_similar_subject(subject: str, deviations: list[Deviation]) -> Optional[Deviation]:
    """查找同类主题的偏差（模糊匹配 + 关键词重叠）
    
    匹配策略：
    1. 精确包含（互为子串）
    2. fuzzy ratio ≥ 0.65（difflib similarity）
    3. 关键词重叠 ≥2 个，且包含共同核心词（英文词或重复 bigram 频率高的中文词）
    """
    subject_lower = subject.lower()
    subject_keywords = extract_keywords(subject_lower)
    
    best_match = None
    best_score = 0.0
    
    for dev in deviations:
        dev_lower = dev.subject.lower()
        
        # 策略1：精确包含
        if subject_lower in dev_lower or dev_lower in subject_lower:
            return dev
        
        # 策略2：fuzzy ratio
        ratio = difflib.SequenceMatcher(None, subject_lower, dev_lower).ratio()
        if ratio >= 0.65 and ratio > best_score:
            best_score = ratio
            best_match = dev
            continue
        
        # 策略3：关键词重叠（中文 bigram + 英文词）
        dev_keywords = extract_keywords(dev_lower)
        overlap = subject_keywords & dev_keywords
        if len(overlap) >= 2:
            # 英文词重叠权重更高（语义更强）
            en_overlap = overlap & set(re.findall(r'[a-zA-Z0-9]{2,}', subject_lower)) & set(re.findall(r'[a-zA-Z0-9]{2,}', dev_lower))
            score = len(overlap) + len(en_overlap) * 0.5  # 英文词加权
            if score > best_score:
                best_score = score
                best_match = dev
    
    return best_match

def generate_dev_id() -> str:
    """生成新的 dev_id"""
    today = datetime.now(CST).strftime("%Y%m%d")
    existing = [d for d in parse_corrections() if d.dev_id.startswith(f"dev_{today}")]
    next_num = len(existing) + 1
    return f"dev_{today}_{next_num:03d}"

def write_deviation(subject: str, wrong: str, right: str,
                   severity: str = "L0b", session: str = "") -> str:
    """写入一条新偏差"""
    ensure_dirs()

    deviations = parse_corrections()
    today = datetime.now(CST).strftime("%Y-%m-%d")
    dev_id = generate_dev_id()

    # 检测同类主题
    similar = find_similar_subject(subject, deviations)
    if similar:
        # 更新触发次数
        similar.trigger_count += 1
        similar.last_verified = today
        # 更新偏差描述为最新
        similar.wrong = wrong
        similar.right = right
        update_corrections([d for d in deviations if d.dev_id != similar.dev_id], deviations)
        action = f"同类主题触发 +1，trigger_count: {similar.trigger_count}"
        dev_id = similar.dev_id
    else:
        # 新增
        new_dev = Deviation(
            dev_id=dev_id, subject=subject, wrong=wrong, right=right,
            severity=severity, trigger_count=1,
            status="待验证", last_verified=today,
            session=session or f"manual:{today}"
        )
        deviations.append(new_dev)
        append_to_corrections(new_dev)
        action = "新偏差写入"

    print(f"✅ {action}")
    print(f"   dev_id: {dev_id}")
    print(f"   subject: {subject}")

    # === 写入验证 (2026-06-07 立) ===
    # 防止 WORKSPACE 路径 bug 复发：类似 memory_sensor.py WORKSPACE=Path('~/...') 未 .expanduser() 会导致写入到字面 '~' 路径
    verify_ok, verify_msg = verify_write(CORRECTIONS_PATH, dev_id)
    print(f"   {'✅' if verify_ok else '❌'} 写入验证: {verify_msg}")
    if not verify_ok:
        raise RuntimeError(f"写入验证失败: {verify_msg}")

    # 检查是否触发 L2 生成
    if similar and similar.trigger_count >= 2:
        generate_l2_scene(similar)
        print(f"   🔔 N≥2 触发 L2 场景块生成")

    return dev_id

def verify_write(path: Path, dev_id: str) -> tuple[bool, str]:
    """验证写入是否成功（防路径 bug 复发）

    验证要点：
    1. 路径不含字面 '~'
    2. 文件存在
    3. 文件 mtime 在过去 60 秒内
    4. 文件内容包含 dev_id
    """
    path_str = str(path)
    if "~" in path_str:
        return False, f"路径含字面 '~': {path_str}"

    if not path.exists():
        return False, f"文件不存在: {path_str}"

    # mtime 检查
    mtime = path.stat().st_mtime
    now = datetime.now(CST).timestamp()
    if now - mtime > 60:
        return False, f"文件 mtime 过旧 ({now-mtime:.0f}s 前)"

    # 内容检查
    try:
        content = path.read_text(encoding="utf-8")
        if dev_id not in content:
            return False, f"文件内容不含 dev_id={dev_id}"
    except Exception as e:
        return False, f"读取文件失败: {e}"

    return True, f"路径={path} mtime={mtime:.0f}"

def append_to_corrections(dev: Deviation):
    """追加偏差到 corrections.md"""
    with open(CORRECTIONS_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n.deviation_id: {dev.dev_id}\n")
        f.write(dev.to_markdown() + "\n")

def update_corrections(old_deviations: list[Deviation], new_deviations: list[Deviation]):
    """重写 corrections.md（用于更新触发次数）"""
    lines = ["# corrections.md — 偏差记录 🦞\n",
             "> 钱学森工程控制论记忆系统核心：偏差是控制的起点。",
             "> 存储不是目的，控制系统才是目的。\n",
             "---",
             "\n## 格式说明\n"]
    
    # ... 保留格式说明 ...
    format_text = """```markdown
### deviation_id: dev_YYYYMMDD_NNN
- **主题**: 偏差所属主题
- **偏差描述**: 以为 XXX → 实际是 YYY
- **严重程度**: L0a / L0b / L1 / L2
- **触发次数**: N
- **验证状态**: 待验证 / 收敛中 / 已收敛
- **最后验证**: YYYY-MM-DD
- **SESSION**: 相关会话标识
```

### 严重程度分级

| 等级 | 含义 | 处理时机 |
|------|------|---------|
| L0a | 立刻修正 | 明显事实错误（工具名、API参数等） |
| L0b | 会话末修正 | 偏好类（沟通风格、语气） |
| L1 | 积分验证 | 框架性问题，放入 L1 积分队列 |
| L2 | 长期聚合 | 跨次验证的聚合认知 |

### 收敛判断

- trigger_count ≥ 3 → **已收敛**
- trigger_count = 2 → **收敛中**
- trigger_count = 1 → **待验证**

---

## 偏差记录

"""
    lines.append(format_text)

    for dev in new_deviations:
        lines.append(dev.to_markdown() + "\n")

    lines.append(f"\n_版本：1.0 | 最后更新：{datetime.now(CST).strftime('%Y-%m-%d')} | by 小龙虾（工程控制论偏差传感器）_")

    CORRECTIONS_PATH.write_text("\n".join(lines), encoding="utf-8")

def generate_l2_scene(dev: Deviation) -> Path:
    """生成 L2 场景块"""
    ensure_dirs()

    slug = re.sub(r'[^\w]+', '-', dev.subject.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')
    scene_path = SCENES_DIR / f"{slug}.md"

    # 获取所有同类偏差
    all_deviations = parse_corrections()
    similar_devs = [d for d in all_deviations
                   if dev.subject.lower() in d.subject.lower()
                   or d.subject.lower() in dev.subject.lower()]

    # 构建偏差模式列表
    deviation_patterns = []
    for d in similar_devs:
        status_icon = "✅" if d.trigger_count >= 3 else "🔄"
        deviation_patterns.append(
            f"- [{d.dev_id}] 以为 {d.wrong} → 实际是 {d.right} "
            f"({status_icon} 触发:{d.trigger_count}次)"
        )

    scene_content = f"""# 场景块：{dev.subject}

**生成日期**: {datetime.now(CST).strftime("%Y-%m-%d")}
**偏差来源**: {len(similar_devs)} 次独立校正

## 核心认知

经多次验证，Lee 的真实偏好/认知：
- {dev.right}

## 偏差模式

{chr(10).join(deviation_patterns)}

## 置信度

- **触发次数**: {dev.trigger_count}
- **状态**: {"已收敛" if dev.trigger_count >= 3 else "收敛中"}
- **置信度**: {"高" if dev.trigger_count >= 3 else "中"}

_版本：1.0 | 最后更新：{datetime.now(CST).strftime("%Y-%m-%d")} | by 小龙虾（工程控制论偏差传感器）_
"""

    scene_path.write_text(scene_content, encoding="utf-8")
    print(f"📝 L2 场景块已生成: {scene_path}")
    return scene_path

def scan_for_l2() -> int:
    """扫描所有偏差，N≥2 触发 L2 生成"""
    deviations = parse_corrections()
    count = 0

    for dev in deviations:
        if dev.trigger_count >= 2:
            scene_path = generate_l2_scene(dev)
            count += 1

    return count

def convergence_check() -> dict:
    """收敛检测（v2 — 优先按 status 字段分类，trigger_count 仅作交叉验证）

    历史 bug（dev_20260609_001）：
      原版用 `trigger_count<2` 当"待验证"，完全忽略 status 字段
      → 14 条状态已写"已收敛"但 trigger=1 的偏差被误报为"待验证"
      → 数字虚高 140%，误导回归测试排期

    v2 行为：
      - 已收敛：status=='已收敛' → 真值优先
      - 收敛中：status=='收敛中' → 真值优先
      - 待验证：status=='待验证' → 真值优先
      - 其他：按 trigger_count 兜底（trigger≥3 → 已收敛，=2 → 收敛中）
    """
    deviations = parse_corrections()
    stats = {"total": len(deviations), "converged": 0, "converging": 0, "pending": 0}

    for dev in deviations:
        # 1. status 字段是真值源（人工/系统维护）
        # 注意：status 字段可能带注释（"已收敛（X+Y+Z）"），需用 startswith 模糊匹配
        s = dev.status.strip()
        if s.startswith("已收敛") or s.startswith("已修复"):
            stats["converged"] += 1
        elif s.startswith("收敛中"):
            stats["converging"] += 1
        elif s.startswith("待验证"):
            stats["pending"] += 1
        else:
            # 2. status 缺失/异常时，按 trigger_count 兜底
            if dev.trigger_count >= 3:
                stats["converged"] += 1
            elif dev.trigger_count == 2:
                stats["converging"] += 1
            else:
                stats["pending"] += 1

    return stats

def list_deviations():
    """列出所有偏差"""
    deviations = parse_corrections()

    if not deviations:
        print("📭 暂无偏差记录")
        return

    print(f"📊 共 {len(deviations)} 条偏差记录：\n")
    for dev in deviations:
        s = dev.status.strip()
        if s.startswith("已收敛") or s.startswith("已修复"):
            status_icon = "✅"
        elif s.startswith("收敛中"):
            status_icon = "🔄"
        elif s.startswith("待验证"):
            status_icon = "⏳"
        else:
            status_icon = "❓"
        print(f"{status_icon} [{dev.dev_id}] {dev.subject}")
        print(f"   触发: {dev.trigger_count}次 | 严重: {dev.severity}")
        print()

def stats():
    """统计偏差分布"""
    deviations = parse_corrections()
    conv_stats = convergence_check()

    print("📊 偏差统计：")
    print(f"   总计: {conv_stats['total']}")
    print(f"   ✅ 已收敛: {conv_stats['converged']}")
    print(f"   🔄 收敛中: {conv_stats['converging']}")
    print(f"   ⏳ 待验证: {conv_stats['pending']}")

    # 按严重程度分布
    severity_counts = {}
    for dev in deviations:
        severity_counts[dev.severity] = severity_counts.get(dev.severity, 0) + 1

    print("\n按严重程度：")
    for sev, cnt in sorted(severity_counts.items()):
        print(f"   {sev}: {cnt}")

def main():
    parser = argparse.ArgumentParser(description="小龙虾偏差传感器 CLI")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # write
    write_parser = subparsers.add_parser("write", help="写入新偏差")
    write_parser.add_argument("--subject", required=True, help="偏差主题")
    write_parser.add_argument("--wrong", required=True, help="错误认知")
    write_parser.add_argument("--right", required=True, help="正确认知")
    write_parser.add_argument("--severity", default="L0b", help="严重程度")
    write_parser.add_argument("--session", default="", help="会话标识")

    # scan
    subparsers.add_parser("scan", help="扫描重复偏差，触发 L2 生成")

    # convergence
    subparsers.add_parser("convergence", help="运行收敛检测")

    # list
    subparsers.add_parser("list", help="列出所有偏差")

    # stats
    subparsers.add_parser("stats", help="统计偏差分布")

    args = parser.parse_args()

    if args.command == "write":
        write_deviation(args.subject, args.wrong, args.right,
                       args.severity, args.session)
    elif args.command == "scan":
        count = scan_for_l2()
        print(f"✅ 扫描完成，生成 {count} 个 L2 场景块")
    elif args.command == "convergence":
        conv_stats = convergence_check()
        stats()
    elif args.command == "list":
        list_deviations()
    elif args.command == "stats":
        stats()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()