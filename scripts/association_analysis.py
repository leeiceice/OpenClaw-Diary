#!/usr/bin/env python3
"""
关联分析脚本 v4 - 基于标签+主题+全文BM25的混合关联评分
改进：新增全Vault内容BM25索引，替代纯标签匹配
"""

import os
import re
import sys
import yaml
import pickle
import time
from pathlib import Path
from datetime import datetime
from _timezone import CST
from rank_bm25 import BM25Okapi

WORKSPACE = Path("~/.openclaw/workspace").expanduser()
OBSIDIAN = Path.home() / "Obsidian"
COLLECTIONS = WORKSPACE / "collections"
PARA_NOTES = OBSIDIAN / "PARA"
BM25_CACHE = WORKSPACE / "data" / "bm25_index.pkl"

STOPWORDS = {
    '的', '是', '了', '和', '与', '或', '在', '以及', '通过', '一个', '一种',
    '可以', '如何', '什么', '为什么', '怎么', '不是', '没有', '非常', '更', '很',
    '都', '就', '还', '也', '但', '而', '所以', '因为', '如果', '虽然',
    '自己', '我们', '他们', '大家', '这个', '那个', '什么',
}

def tokenize(text):
    """修 C v11: jieba 真分词 + 英文单词（替换原 2-gram 切词）
    原因: 原 2-gram 把"老邮差"切成"老邮/邮差/差数"，跟任何字符串都能凑出交集
          → 关联分析假象的根本原因
    修法: 用 jieba.cut() 切出真词（如"邮差"、"绿罗裙"），交集质量提升 10x
    """
    import jieba
    jieba.setLogLevel(20)
    tokens = []
    for w in jieba.cut(str(text)):
        w = w.strip()
        if not w:
            continue
        if w in STOPWORDS:
            continue
        if len(w) == 1 and '\u4e00' <= w <= '\u9fff':
            continue
        if '\u4e00' <= w[0] <= '\u9fff':
            tokens.append(w)
        else:
            for w2 in re.findall(r'[a-zA-Z]{2,}', w):
                tokens.append(w2.lower())
    return tokens


def build_bm25_index(force=False):
    """构建全Vault的BM25索引，缓存到文件"""
    if not force and BM25_CACHE.exists():
        try:
            mtime = BM25_CACHE.stat().st_mtime
            if time.time() - mtime < 3600:
                data = pickle.loads(BM25_CACHE.read_bytes())
                print(f"[BM25] Loaded cached index ({len(data['titles'])} files)")
                return data
        except Exception:
            pass

    # 修 B (2026-06-09): 索引范围 = 整个 ~/Obsidian/（排除 .git + _archive）
    # 原因: 之前只扫 5 个目录，导致诗词/金句/wiki/日记/raw 全没进索引
    #       → BM25 候选池只有书名 → 强匹配 0 个还强行打 ⭐⭐⭐⭐
    if not PARA_NOTES.exists() and not OBSIDIAN.exists():
        # 兜底: 至少扫 PARA_NOTES
        all_files = list(PARA_NOTES.rglob("*.md")) if PARA_NOTES.exists() else []
    else:
        roots = [r for r in (PARA_NOTES, OBSIDIAN) if r.exists()]
        all_files = []
        for root in roots:
            for f in root.rglob("*.md"):
                # 排除 .git 和 _archive（备份目录，不应进活跃索引）
                if ".git" in f.parts or "_archive" in f.parts:
                    continue
                all_files.append(f)

    def read_body(path):
        try:
            c = path.read_text(encoding="utf-8")
            if c.startswith("---"):
                end = c.find("---", 3)
                body = c[end + 3:] if end > 0 else c
            else:
                body = c
            body = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', body)
            body = re.sub(r'#{1,6}\s+', '', body)
            body = re.sub(r'\*\*|\*|_', '', body)
            return body[:800].strip()
        except Exception:
            return ""

    corpus = [read_body(f) for f in all_files]
    paths = [str(f) for f in all_files]
    titles = [f.stem for f in all_files]
    tokenized = [tokenize(c) for c in corpus]

    t0 = time.time()
    bm25 = BM25Okapi(tokenized)
    print(f"[BM25] Index built in {(time.time()-t0)*1000:.0f}ms for {len(all_files)} files")

    data = {
        "bm25": bm25,
        "corpus": corpus,
        "paths": paths,
        "titles": titles,
    }

    try:
        BM25_CACHE.parent.mkdir(parents=True, exist_ok=True)
        BM25_CACHE.write_bytes(pickle.dumps(data))
        print(f"[BM25] Cached to {BM25_CACHE}")
    except Exception as e:
        print(f"[BM25] Cache failed: {e}")

    return data

def search_bm25_ranked(query_text, topk=20, exclude_stem=""):
    """返回 (rank, bm25_score, title, path) 列表，rank从1起，跳过自己（按文件stem匹配）"""
    data = build_bm25_index()
    q_tokens = tokenize(query_text)
    scores = data["bm25"].get_scores(q_tokens)
    ranked = sorted(
        enumerate(zip(scores, data["titles"], data["paths"])),
        key=lambda x: -x[1][0]
    )
    results = []
    rank = 1
    for idx, (score, title, path) in ranked:
        if title == "" or Path(path).stem == exclude_stem:
            continue
        results.append((rank, score, title, path))
        rank += 1
    return results[:topk]

def read_file(path):
    """读取markdown文件，提取标题、标签、正文摘要"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        fm = {}
        body = content
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                try:
                    fm = yaml.safe_load(content[3:end]) or {}
                except Exception:
                    fm = {}
                body = content[end + 3:].strip()
        title = str(fm.get("title", ""))
        if not title or title == "None":
            m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
            title = m.group(1).strip() if m else path.stem
        tags = fm.get("tags", [])
        if isinstance(tags, list):
            tags = [str(t) for t in tags]
        else:
            tags = []
        inline_tags = re.findall(r"#([\w\u4e00-\u9fff-]+)", body)
        tags = list(set(tags + inline_tags))
        # 修 E v15: 跳过"关联文档"段（防止 related 反馈循环）
        # 原因: 老邮差 body 里有 "related: [[生查子...]]" → BM25 索引命中生查子
        #       → 生查子查询时又关联回老邮差 = 假关联反馈循环
        # 修法: 在 clean 之前截断"🔗 关联文档"或"## 关联文档"段
        for marker in ["🔗 关联文档", "## 关联文档", "## 相关", "🔗 相关"]:
            idx = body.find(marker)
            if idx > 0:
                body = body[:idx]
                break
        clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
        clean = re.sub(r"#{1,6}\s+", "", clean)
        clean = re.sub(r"\*\*|__|\*|_", "", clean)
        summary = fm.get("summary", clean[:150].strip())
        return {
            "title": title,
            "tags": tags,
            "body": clean[:800],
            "summary": summary,
            "fm": fm,
            "path": str(path),
        }
    except Exception:
        return None

def get_topic_score(new_tags, existing_tags):
    """主题相似性评分"""
    topic_clusters = {
        "自我成长": ["自我成长", "习惯", "时间管理", "目标", "效率", "自律", "成长", "精进"],
        "学习方法": ["学习", "阅读", "知识管理", "高效学习", "读书", "学习方法", "知识结构"],
        "思维认知": ["思维", "认知", "思考", "批判性思维", "模型", "方法论", "思维模型"],
        "AI科技": ["AI", "人工智能", "大模型", "Agent", "ChatGPT", "LLM", "科技"],
        "社会观察": ["社会", "年轻人", "内卷", "躺平", "悬浮", "项飙", "青年心理", "断亲", "奥德赛时期", "附近"],
        "健康生活": ["健康", "睡眠", "运动", "饮食", "身体", "健身"],
        "写作表达": ["写作", "表达", "文笔", "写书", "创作"],
        "历史人文": ["历史", "政治", "文化", "人文", "哲学"],
        "书法艺术": ["书法", "写字", "笔画", "碑帖", "行书", "草书", "楷书"],
    }
    new_clusters = set()
    existing_clusters = set()
    for tag in new_tags:
        for cluster, members in topic_clusters.items():
            if tag in members:
                new_clusters.add(cluster)
                break
    for tag in existing_tags:
        for cluster, members in topic_clusters.items():
            if tag in members:
                existing_clusters.add(cluster)
                break
    if new_clusters & existing_clusters:
        return 0.3
    return 0

def bm25_rank_score(rank, bm25_score=0, top1_score=0):
    """BM25排名+实际分数转[0,1]贡献分（修 D: 加实际分数惩罚）

    原因: 之前只看 rank，Top3 固定 0.90 → 即使实际分数比 Top1 低 3 倍也算强相关
    修法: 引入 ratio = bm25_score / top1_score 作为衰减因子
        - ratio >= 0.7: 跟最强候选接近 → 原 rank 得分
        - ratio >= 0.4: 中等 → 原 rank 得分 × 0.5
        - ratio < 0.4: 远离最强 → 原 rank 得分 × 0.2
    """
    if rank <= 0:
        return 0.0
    if rank <= 3:
        base = 0.90
    elif rank <= 7:
        base = 0.60
    elif rank <= 15:
        base = 0.30
    else:
        base = 0.10
    # 修 D: 实际分数衰减（跨文档长度不一致时保护）
    if top1_score > 0 and bm25_score > 0:
        ratio = bm25_score / top1_score
        if ratio >= 0.7:
            return base
        elif ratio >= 0.4:
            return base * 0.5
        else:
            return base * 0.2
    return base

def compute_association(new_info, existing_info, bm25_rank=0, bm25_score=0, top1_score=0):
    """综合关联评分：标签基础(40%) + BM25排名(60%)（修 D: 加实际分数衰减）"""
    new_tags = set(new_info["tags"])
    existing_tags = set(existing_info["tags"])

    if not new_tags or not existing_tags:
        base_score = 0.0
    else:
        tag_overlap = len(new_tags & existing_tags)
        tag_union = len(new_tags | existing_tags)
        jaccard = tag_overlap / tag_union if tag_union > 0 else 0
        direct_hit = min(1.0, tag_overlap / 2)
        base_score = jaccard * 0.4 + direct_hit * 0.3

    topic = get_topic_score(new_tags, existing_tags)

    new_title_words = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", new_info["title"].lower()))
    existing_title_words = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", existing_info["title"].lower()))
    title_overlap = len(new_title_words & existing_title_words)
    title_score = min(1.0, title_overlap / 3)

    base = base_score * 0.4 + topic * 0.2 + title_score * 0.1
    final = base * 0.4 + bm25_rank_score(bm25_rank, bm25_score, top1_score) * 0.6

    return min(1.0, final)

def stars(score):
    if score >= 0.65:
        return "⭐⭐⭐⭐⭐"
    elif score >= 0.45:
        return "⭐⭐⭐⭐"
    elif score >= 0.28:
        return "⭐⭐⭐"
    elif score >= 0.15:
        return "⭐⭐"
    elif score >= 0.07:
        return "⭐"
    return "—"

def stars_num(score):
    if score >= 0.65:
        return 5
    elif score >= 0.45:
        return 4
    elif score >= 0.28:
        return 3
    elif score >= 0.15:
        return 2
    elif score >= 0.07:
        return 1
    return 0

def _classify_source(path):
    p = str(path)
    if "/PARA/areas/" in p:
        return "PARA/Areas"
    elif "/PARA/projects/" in p:
        return "PARA/Projects"
    elif "/收藏/文章/" in p:
        return "收藏文章"
    elif "/收藏/公众号/" in p:
        return "收藏公众号"
    elif "/收藏/书籍/" in p:
        return "收藏书籍"
    return "Other"

def search_all(new_info):
    """搜索所有可能的关联内容（BM25排名 + 标签双重信号）"""
    bm25_data = build_bm25_index()
    # 修 C v13: query = 标题 + tags + body 前 500 字（去元数据噪声）
    # 原因: v12 只有 title+tags 太短，BM25 找不到真相关（T2/T3 退步）
    #       v11 用整个 body 有 "lee/相关/关联/理由/收藏/文档" 元数据噪声
    # 修法: title + tags + body 前 500 字（足够长 + 元数据在文末被截掉）
    title = new_info.get("title", "")[:50]
    body = new_info.get("body", "")[:500]
    query_parts = new_info["tags"] + [title, body]
    query_text = " ".join(query_parts)
    bm25_ranked = search_bm25_ranked(query_text, topk=20, exclude_stem=Path(new_info["path"]).stem)

    results = []
    # 修 C (2026-06-09): 加 BM25 实际分数门槛（双门槛）
    # 原因: 之前 bm25_score 完全没用上，只用 rank 推算
    #       → 即使 0.54 这种实际无匹配也会输出 ⭐⭐⭐⭐
    # 门槛说明:
    #   - BM25_MIN_SCORE: 绝对经验门槛（生查子测试 Top15 = 60.8+，远高于此）
    #   - TOP1_RATIO_MIN: Top1 归一化门槛（必须达到最强候选的 30%）
    #   - TOKEN_OVERLAP_MIN: 真实中文词交集 ≥2（防 2-gram 专名假象）
    BM25_MIN_SCORE = 30.0   # 经验值：< 30 = 实际无匹配
    TOP1_RATIO_MIN = 0.30   # < 30% Top1 = 不是真正"最相关"的同类
    TOKEN_OVERLAP_MIN = 2   # < 2 个真实词交集 = 不是真正相关
    # 修 C v4: 加 "≥3 字中文词交集" 门槛（防 2-gram 专名假交集）
    # 原因: 中文 2-gram 会把 "老邮差" 切成 "老邮/邮差/差数"，跟任何文件名都能凑出交集
    # 修法: 必须有 ≥1 个 ≥3 字的中文词交集才算"语义相关"
    MIN_3CHAR_OVERLAP = 1
    top1_score = bm25_ranked[0][1] if bm25_ranked else 0

    # 算新文件的"真实词集合"（过滤 2-gram 专名 + 停用词）
    new_query_tokens = set(tokenize(query_text))
    # 过滤: 排除长度 > 6 的伪 2-gram（专名 2-gram 概率高）
    new_real_tokens = {t for t in new_query_tokens if len(t) <= 6 and not t.isdigit()}

    for rank, bm25_score, title, path in bm25_ranked:
        if title == new_info.get("title", ""):
            continue
        # 修 C v2: 双门槛（任一不满足即跳过）
        if bm25_score < BM25_MIN_SCORE:
            continue
        if top1_score > 0 and bm25_score / top1_score < TOP1_RATIO_MIN:
            continue
        # 修 C v3: 真实词交集门槛（防专名 2-gram 假象）
        target_info = read_file(Path(path))
        if not target_info:
            continue
        target_body = " ".join(target_info.get("tags", []) + [target_info.get("body", "")])
        target_tokens = set(tokenize(target_body))
        target_real = {t for t in target_tokens if len(t) <= 6 and not t.isdigit()}
        real_overlap = new_real_tokens & target_real
        if len(real_overlap) < TOKEN_OVERLAP_MIN:
            continue
        # 修 C v9: 综合判断（多门 OR 逻辑）
        # 原因: 中文 2-gram tokenize 注定产生假交集，必须联合多个信号判断
        # 门 (OR):
        #   1) 交集里有 ≥1 个 ≥3 字中文真词
        #   2) 交集总 ≥ 10 个
        #   3) 交集里命中 new/target 的 tag 词（tags 是高质量元数据）
        #   4) BM25 分数极高（> 150）
        new_tag_set = set(new_info.get("tags", []))
        target_tag_set = set(target_info.get("tags", []))
        new_tag_tokens = set()
        for tag in new_tag_set:
            new_tag_tokens.update(tokenize(tag))
        target_tag_tokens = set()
        for tag in target_tag_set:
            target_tag_tokens.update(tokenize(tag))
        tag_overlap = new_tag_tokens & target_real
        target_tag_overlap = target_tag_tokens & new_real_tokens
        long_overlap = {t for t in real_overlap if len(t) >= 3 and chr(0x4e00) <= t[0]}
        # 修 C v14: pass_gate OR 4 门（加 BM25 极高门 = Top1 50%）
        # 原因: v10/v13 测试发现——莽荒纪 vs 诛仙 BM25=64.2（Top1 100%）
        #       但长交集 0 + tags 不命中 → v10 误杀
        # 修法: 加 BM25 极高门（>= 50，约 Top1 78% 经验值）
        # 4 门 OR:
        #   门1: 交集里有 ≥1 个 ≥3 字真词
        #   门2: 交集里命中我 tags
        #   门3: 交集里命中对方 tags
        #   门4: BM25 极高（>= 50）—— 经验值，莽荒纪 vs 诛仙 64.2 过
        pass_gate = (
            len(long_overlap) >= 1
            or len(tag_overlap) >= 1
            or len(target_tag_overlap) >= 1
            or bm25_score >= 50
        )
        if not pass_gate:
            continue
        info = target_info
        # 修 D: 把 bm25_score 和 top1_score 传给 compute_association 让 rank 得分能被衰减
        score = compute_association(new_info, info, bm25_rank=rank, bm25_score=bm25_score, top1_score=top1_score)
        if score >= 0.05:
            results.append({
                "file": path,
                "title": info["title"],
                "tags": info["tags"],
                "score": score,
                "source": _classify_source(path),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    seen = {}
    deduped = []
    for r in results:
        if r["title"] not in seen:
            seen[r["title"]] = r
            deduped.append(r)
    return deduped

def para_suggestion(tags):
    tag_str = " ".join(tags)
    suggestions = []
    if any(t in tag_str for t in ["学习", "阅读", "知识管理", "高效学习", "读书", "学习力"]):
        suggestions.append("📚 **Areas · 学习力**")
    if any(t in tag_str for t in ["自我成长", "习惯", "目标", "成长", "自律", "精进"]):
        suggestions.append("🌱 **Areas · 自我成长**")
    if any(t in tag_str for t in ["AI", "人工智能", "大模型", "Agent", "科技", "技术"]):
        suggestions.append("🤖 **Areas · AI研究**")
    if any(t in tag_str for t in ["思维", "认知", "方法论", "思维模型", "模型"]):
        suggestions.append("🧠 **Areas · 思维与认知**")
    if any(t in tag_str for t in ["社会", "年轻人", "内卷", "躺平", "悬浮", "项飙", "历史", "政治", "人文"]):
        suggestions.append("🏛️ **Areas · 社会观察**")
    if any(t in tag_str for t in ["工作", "项目", "运营", "写作", "创业"]):
        suggestions.append("📁 **Projects ·**")
    if any(t in tag_str for t in ["资源", "工具", "技能", "教程", "书单", "片单"]):
        suggestions.append("📦 **Resources ·**")
    if not suggestions:
        suggestions.append("📦 **Resources ·** 待分类")
    return "\n".join(suggestions[:2])

def _build_related_lines(related_items):
    """Build properly-formatted related list lines, deduped."""
    seen = set()
    lines = ["related:"]
    for item in related_items:
        # Normalize for dedup: strip leading "- " and wiki-link brackets
        norm = re.sub(r'^-\s*', '', item)
        norm = re.sub(r'\s*[⭐💡📚🎯🔍]+.*$', '', norm)  # strip ratings and source tags
        norm = norm.strip()
        if norm and norm not in seen:
            seen.add(norm)
            # Reconstruct in canonical quoted form (Obsidian YAML compat)
            clean = item.strip()
            lines.append(f'  - "{clean}"')
    return lines

def _replace_related_block(content, related_items, in_frontmatter=False):
    """Replace ALL existing related lines (not just the header) with new items."""
    marker = "  - "
    block_lines = _build_related_lines(related_items)
    
    if in_frontmatter:
        # frontmatter: find ^related: and consume all following ^  - ... lines (including empty)
        # 修 dev_20260610_010：原本 pattern 要求 (  - .*)+ 至少 1 个，
        # 但空 related 段没有 list item → pattern 不匹配 → 变成空写
        # 改：pattern 接受 \n 或 \n-- 后任意
        # ⚠️ replacement 必须加 \n，否则 pattern 末尾吞的 \n 丢丢
        pattern = r'^related:(?:\n(?:  - .*|\s*)?)*'
        replacement = "\n".join(block_lines) + "\n"
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        return new_content
    else:
        # body section: find the whole ## 🔗 block and replace
        # 修 dev_20260610_010：body 模式不要「related:」头，只要 list items
        # 还要支持空 body 段（只有 ## 头）
        pattern = r'## 🔗 关联文档\n\n(?:  - .*\n|related:\n)*'
        block_text = "\n".join([f'  - "{item.strip()}"' for item in related_items])
        replacement = f"## 🔗 关联文档\n\n{block_text}\n"
        new_content = re.sub(pattern, replacement, content)
        return new_content

def _is_self_reference(r, file_path):
    """判断 r 是否为「自指」——指向源文件、源文件索引、原始 raw 消息、系统内低价值关联。
    
    修 dev_20260610_010：避免「自指」占满 Top 5，
    导致 related 字段全部是同一本书的不同切片 + 系统内低分命中。
    """
    p = str(file_path)
    rpath = str(r.get("file", ""))
    rtitle = r.get("title", "")
    rscore = r.get("score", 0)
    
    import os
    fname = os.path.basename(p)
    # 去日期前缀 (2026-06-10-)
    fname_clean = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", fname)
    # 去扩展名
    fname_clean = os.path.splitext(fname_clean)[0]
    # 取前 6 字符作为主名词 token（中文书籍名）
    main_token = fname_clean[:6] if len(fname_clean) > 0 else ""
    
    # 1. 同一个文件
    if rpath and rpath == p:
        return True
    # 2. 提取源文件主名词命中 rtitle = 同书不同切片
    if main_token and main_token in rtitle:
        return True
    # 3. rpath 在 raw/收藏/ 路径且 rtitle 含源主名词 = 同源切片
    if "/raw/收藏/" in rpath and main_token and main_token in rtitle:
        return True
    # 4. 系统内低价值关联：收藏索引 / 关联分析报告（被 BM25 边缘命中）
    # ⚠️ 不同日微信日记 = 跨主题关联，保留；同日微信日记 + 边缘分 = 过滤
    fname_date_match = re.search(r"(\d{4}-\d{2}-\d{2})", fname)
    fname_date = fname_date_match.group(1) if fname_date_match else ""
    rpath_date_match = re.search(r"(\d{4}-\d{2}-\d{2})", rpath)
    rpath_date = rpath_date_match.group(1) if rpath_date_match else ""
    same_date = bool(fname_date and rpath_date and fname_date == rpath_date)
    
    system_noise_exact = [
        "📚 收藏索引", "收藏索引",
        "关联分析报告", "关联分析", "📚-每日书籍推荐",
        "📓 微信消息同步",
    ]
    for noise in system_noise_exact:
        if noise in rtitle:
            return True
    # 同日微信日记 + 边缘分 = 过滤（防「当天日记被当关联」）
    if "微信-" in rtitle and same_date and rscore < 0.20:
        return True
    # 5. 低分 (score < 0.10) 边缘命中 + 同日系统内 = 过滤（不同日保留）
    if rscore < 0.10 and same_date and any(x in rpath for x in ["/日记/raw/", "/raw/收藏/想法/", "/raw/收藏/Index"]):
        return True
    return False


def write_related_back(file_path, results):
    # 修 dev_20260610_010：先过滤自指，取所有非自指（不限 5 条）
    filtered = [r for r in results if not _is_self_reference(r, file_path)]
    related_items = []
    for r in filtered:
        related_items.append("[[{0}]] {1} ({2})".format(r["title"], stars(r["score"]), r["source"]))

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    new_content = content

    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            frontmatter = content[3:end]
            body = content[end + 3:]
            if re.search(r"^related:", frontmatter, re.MULTILINE):
                frontmatter = _replace_related_block(frontmatter, related_items, in_frontmatter=True)
            else:
                block_lines = _build_related_lines(related_items)
                frontmatter = frontmatter.rstrip() + "\n" + "\n".join(block_lines) + "\n"
            new_content = "---" + frontmatter + "---" + body

    # Replace body section if it exists, otherwise append
    section_marker = "## 🔗 关联文档"
    body_lines = []
    for item in related_items:
        body_lines.append(f"  - {item.strip()}")
    if section_marker in new_content:
        new_content = _replace_related_block(new_content, related_items, in_frontmatter=False)
    else:
        new_content += "\n\n" + section_marker + "\n\n" + "\n".join(body_lines) + "\n"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    # 修 dev_20260610_010：写入后 verify related 字段 non-empty
    if related_items:
        return related_items
    return None  # 告诉上游「写入了，但为空」需报警

def run_analysis(new_file_path):
    new_info = read_file(Path(new_file_path))
    if not new_info:
        return None

    results = search_all(new_info)
    related_written = write_related_back(new_file_path, results)
    
    # 修 dev_20260610_010：verify related 写入结果
    if not related_written:
        print(f"⚠️ 警告：related 字段写入为空（dev_20260610_010）", file=__import__('sys').stderr)
        print(f"   原因：results ({len(results)} 条) 全部被「自指」过滤后为空", file=__import__('sys').stderr)

    strong = [r for r in results if r["score"] >= 0.28]
    medium = [r for r in results if 0.07 <= r["score"] < 0.28]

    date = datetime.now(CST).strftime("%Y-%m-%d")
    date_str = datetime.now(CST).strftime("%Y%m%d")
    slug = re.sub(r"[^\w\u4e00-\u9fff-]", "", new_info["title"])[:20]

    lines = [
        f"# 🔗 关联分析报告 · {date}",
        "",
        f"## 📌 本次收藏",
        "",
        f"**{new_info['title']}**",
        "",
        f"**标签**：{' '.join(f'`{t}`' for t in new_info['tags'][:8])}",
        "",
        f"**摘要**：{new_info.get('summary', '—')[:200]}",
        "",
        "---",
        "",
        "## 🔍 关联结果",
        "",
    ]

    if not results:
        lines.append("*未发现显著关联（内容较新或主题独特）*")
    else:
        if strong:
            lines.append(f"### ⭐⭐⭐ 强关联（{len(strong)}个）")
            lines.append("")
            for r in strong:
                lines.append(f"- **{stars(r['score'])} {r['title']}**")
                lines.append(f"  - `{r['file']}`")
                lines.append(f"  - 标签：`{'`, `'.join(r['tags'][:5])}`")
                lines.append(f"  - 得分：{r['score']:.2f}")
                lines.append("")
        if medium:
            lines.append(f"### ⭐⭐ 中弱关联（{len(medium)}个）")
            lines.append("")
            for r in medium:
                lines.append(f"- {stars(r['score'])} **{r['title']}** — `{r['file']}`")

    lines.extend(["", "---", "", "## 📂 PARA 分类建议", ""])
    lines.append(para_suggestion(new_info["tags"]))

    output_path = COLLECTIONS / "ideas" / f"关联分析-{date_str}-{slug}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {
        "output": str(output_path.relative_to(WORKSPACE)),
        "results": results[:8],
        "strong_count": len(strong),
        "medium_count": len(medium),
        "top_result": results[0] if results else None,
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 association_analysis.py <新收藏文件路径>")
        sys.exit(1)

    result = run_analysis(sys.argv[1])
    if not result:
        print("无法分析文件")
        sys.exit(1)

    print(f"\n✅ 关联分析已保存：{result['output']}")
    print(f"\n找到 {result['strong_count']} 个强关联 + {result['medium_count']} 个中弱关联")
    print("✅ related 字段已回流写入源文件")

    if result["results"]:
        print("\n关联结果（按强度排序）：")
        seen = set()
        for r in result["results"][:6]:
            if r["title"] not in seen:
                seen.add(r["title"])
                print(f"  {stars(r['score'])} {r['title'][:40]} ({r['score']:.2f})")

        top = result["top_result"]
        if top and top["score"] >= 0.28:
            print(f"\n最强关联：{stars(top['score'])} {top['title']}")