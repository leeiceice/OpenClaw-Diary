#!/usr/bin/env python3
"""
小龙虾记忆搜索 v2.0
BM25 + 意图路由 + 查询扩展 + JSON 输出
依赖:rank-bm25(pip install rank-bm25 --break-system-packages)
"""

import json, re, os, math, hashlib
from collections import Counter
from datetime import datetime, timedelta
from _timezone import CST
from pathlib import Path
from typing import List, Dict, Optional

# ─── 配置(已修正路径)───────────────────────────────
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY_DIR = f"{WORKSPACE}/memory"
SELF_IMPROVING = f"{WORKSPACE}/self-improving"

INTENT_RULES = {
    "preference": {
        "keywords": ["偏好", "喜欢", "Lee喜欢", "偏好吗", "Lee 喜欢", "Lee的喜好"],
        "files": [f"{WORKSPACE}/MEMORY.md", f"{WORKSPACE}/USER.md",
                  f"{SELF_IMPROVING}/memory.md"]
    },
    "correction": {
        "keywords": ["不要", "避免", "错误", "纠正", "不要再犯", "纠正我", "踩坑", "偏差", "同类", "收敛", "trigger_count"],
        "files": [f"{SELF_IMPROVING}/corrections.md", f"{SELF_IMPROVING}/validated.md",
                  f"{WORKSPACE}/memory/deviations/scenes"]
    },
    "pattern": {
        "keywords": ["怎么做的", "之前", "模式", "通常", "一般怎么", "通常怎么", "习惯"],
        "files": []
    },
    "status": {
        "keywords": ["现在", "还正常吗", "最近怎了", "状态", "当前"],
        "files": []
    },
    "factual": {
        "keywords": ["谁", "什么时候", "哪个", "多少", "哪一天", "哪天", "几次"],
        "files": []
    }
}

# ─── 工具函数 ─────────────────────────────────────────
def tokenize(text: str) -> List[str]:
    tokens = []
    parts = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', text.lower())
    cjk_chars = []
    for p in parts:
        if re.match(r'[\u4e00-\u9fff]$', p):
            cjk_chars.extend(list(p))
        else:
            tokens.append(p)
    # CJK: single char + bigrams from consecutive chars
    for i, c in enumerate(cjk_chars):
        tokens.append(c)
        if i < len(cjk_chars) - 1:
            tokens.append(cjk_chars[i] + cjk_chars[i+1])
    return tokens

def split_chunks(text: str, max_chars: int = 600) -> List[str]:
    chunks = []
    for block in re.split(r'\n(?=\#\#\s)|\n{2,}', text.strip()):
        block = block.strip()
        if not block or len(block) < 20:
            continue
        if len(block) <= max_chars:
            chunks.append(block)
        else:
            paras = re.split(r'\n', block)
            current = ""
            for p in paras:
                if len(current) + len(p) <= max_chars:
                    current += ("\n" if current else "") + p
                else:
                    if current:
                        chunks.append(current)
                    current = p
            if current:
                chunks.append(current)
    return [c for c in chunks if c.strip()]

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]

# ─── BM25 ─────────────────────────────────────────────
class BM25:
    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tokenized_corpus = [tokenize(doc) for doc in corpus]
        self.avg_len = sum(len(d) for d in self.tokenized_corpus) / len(corpus) if corpus else 1
        self.N = len(corpus)
        self.df = Counter()
        for doc in self.tokenized_corpus:
            for term in set(doc):
                self.df[term] += 1
        self.idf = {}
        for term, df in self.df.items():
            self.idf[term] = math.log((self.N - df + 0.5) / (df + 0.5) + 1)

    def score(self, query: List[str], doc_tokens: List[str]) -> float:
        doc_tf = Counter(doc_tokens)
        doc_len = len(doc_tokens)
        score = 0.0
        for term in query:
            tf = doc_tf.get(term, 0)
            if tf == 0:
                continue
            idf_val = self.idf.get(term, 0)
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_len)
            score += idf_val * numerator / denominator
        return score

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        query_tokens = tokenize(query)
        results = []
        for i, doc_tokens in enumerate(self.tokenized_corpus):
            s = self.score(query_tokens, doc_tokens)
            if s > 0:
                results.append((i, s))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

# ─── 意图分类 ─────────────────────────────────────────
def classify_intent(query: str) -> List[str]:
    query_lower = query.lower()
    matched = []
    for intent, rule in INTENT_RULES.items():
        for kw in rule["keywords"]:
            if kw.lower() in query_lower:
                matched.append(intent)
                break
    return matched if matched else ["general"]

# ─── 查询扩展(LLM)───────────────────────────────────
def expand_query(query: str, api_key: str, model: str = "deepseek-ai/DeepSeek-V3") -> List[str]:
    prompt = (
        f"用户查询:「{query}」\n"
        "请生成5-8个相关搜索词或同义词,用 | 分隔。\n"
        "规则:包含原词、近义词、英文翻译、相关术语。\n"
        f"只输出搜索词,格式:词1 | 词2 | 词3,不要解释。"
    )
    try:
        import urllib.request
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100,
            "temperature": 0.3
        }).encode()
        req = urllib.request.Request(
            "https://api.minimaxi.chat/v1/text/chatcompletion_v2",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            expanded = result["choices"][0]["message"]["content"].strip()
            terms = [t.strip() for t in expanded.split("|") if t.strip()]
            if terms:
                return terms[:8]
    except Exception:
        pass
    return [query]

# ─── 扫描文件构建语料库 ────────────────────────────────
def scan_memory_files(intent_filter: List[str] = None, days: int = 30) -> List[Dict]:
    chunks = []
    now = datetime.now(CST)
    cutoff = now - timedelta(days=days)

    file_map = {
        f"{WORKSPACE}/MEMORY.md": "MEMORY.md",
        f"{WORKSPACE}/USER.md": "USER.md",
        f"{WORKSPACE}/SOUL.md": "SOUL.md",
        f"{SELF_IMPROVING}/memory.md": "self-improving/memory.md",
        f"{SELF_IMPROVING}/corrections.md": "self-improving/corrections.md",
    }

    domain_dir = f"{SELF_IMPROVING}/domains"
    if os.path.isdir(domain_dir):
        for fname in os.listdir(domain_dir):
            if fname.endswith(".md"):
                file_map[f"{domain_dir}/{fname}"] = f"self-improving/domains/{fname}"

    # L2 场景块(工程控制论偏差收敛后生成)
    scenes_dir = f"{WORKSPACE}/memory/deviations/scenes"
    if os.path.isdir(scenes_dir):
        for fname in sorted(os.listdir(scenes_dir)):
            if fname.endswith(".md"):
                file_map[f"{scenes_dir}/{fname}"] = f"memory/deviations/scenes/{fname}"

    # L2 场景块(工程控制论偏差收敛后生成)- 无条件加入,始终可检索
    scenes_dir = f"{WORKSPACE}/memory/deviations/scenes"
    if os.path.isdir(scenes_dir):
        for fname in sorted(os.listdir(scenes_dir)):
            if fname.endswith(".md"):
                file_map[f"{scenes_dir}/{fname}"] = f"memory/deviations/scenes/{fname}"

    if os.path.isdir(MEMORY_DIR):
        for fname in sorted(os.listdir(MEMORY_DIR)):
            if not fname.endswith(".md"):
                continue
            fpath = f"{MEMORY_DIR}/{fname}"
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    continue
            except Exception:
                pass
            file_map[fpath] = f"memory/{fname}"

    # intent 过滤:只保留 INTENT_RULES 中指定的文件(场景块不参与过滤,始终保留)
    if intent_filter and "general" not in intent_filter:
        allowed_files = set()
        for intent in intent_filter:
            if intent in INTENT_RULES and INTENT_RULES[intent]["files"]:
                for fpath in INTENT_RULES[intent]["files"]:
                    if os.path.isdir(fpath):
                        # 目录:加入目录下所有 .md 文件
                        for sub in os.listdir(fpath):
                            if sub.endswith(".md"):
                                allowed_files.add(f"{fpath}/{sub}")
                    elif os.path.isfile(fpath):
                        allowed_files.add(fpath)
        if allowed_files:
            file_map = {k: v for k, v in file_map.items() if k in allowed_files}

    for fpath, display_name in file_map.items():
        if not os.path.exists(fpath):
            continue
        try:
            content = open(fpath).read()
        except Exception:
            continue
        for chunk in split_chunks(content):
            chunks.append({
                "text": chunk,
                "source": display_name,
                "path": fpath,
                "chunk_hash": compute_hash(chunk)
            })

    return chunks

# ─── Hit 追踪(工程控制论自适应权重)────────────────
HITS_FILE = f"{WORKSPACE}/data/search_hits.json"

def load_hits() -> dict:
    """加载命中记录 {chunk_hash: {"hit_count": N, "last_hit": timestamp}}"""
    p = Path(HITS_FILE)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}

def save_hits(hits: dict):
    Path(HITS_FILE).write_text(json.dumps(hits, ensure_ascii=False, indent=2))

def record_hit(chunk_hash: str, boost: float = 1.0):
    """记录一次命中,增加 hit_count 并更新 last_hit"""
    hits = load_hits()
    if chunk_hash in hits:
        hits[chunk_hash]["hit_count"] += 1
        hits[chunk_hash]["last_hit"] = datetime.now(CST).isoformat()
        # confidence += 0.02 per hit
        hits[chunk_hash]["confidence"] = min(1.0, hits[chunk_hash].get("confidence", 0.5) + 0.02 * boost)
    else:
        hits[chunk_hash] = {
            "hit_count": 1,
            "last_hit": datetime.now(CST).isoformat(),
            "confidence": 0.5 + 0.02 * boost
        }
    save_hits(hits)

def get_hit_metadata(chunk_hash: str) -> dict:
    """获取某 chunk 的命中元数据"""
    hits = load_hits()
    return hits.get(chunk_hash, {"hit_count": 0, "confidence": 0.5, "last_hit": None})

def apply_hit_boost(results: List[Dict], hits: dict) -> List[Dict]:
    """对搜索结果应用 hit_count 加权和 confidence_score"""
    for item in results:
        chunk_hash = item.get("chunk_hash", "")
        meta = hits.get(chunk_hash, {"hit_count": 0, "confidence": 0.5})
        # RRF-inspired boost: hit_count 贡献一个 log 因子
        hit_boost = (1 + meta.get("hit_count", 0)) ** 0.3 - 1
        item["_hit_count"] = meta.get("hit_count", 0)
        item["_confidence"] = meta.get("confidence", 0.5)
        item["score"] = item["score"] * (1 + hit_boost * meta.get("confidence", 0.5))
    return results

def fuse_bm25_and_vector(bm25_results: List[Dict], vec_sources: List[dict], k: int = 60) -> List[Dict]:
    """BM25 结果与向量结果的 RRF 融合
    
    vec_sources: 从 vector_store 返回的 [{source, vec_score, bm25_score}, ...]
    BM25 结果字段用 path（不是 source）
    """
    # 短路：vec_sources 为空时直接返回 BM25 结果，不套 RRF（否则所有结果会被拉平为 ~0.015）
    if not vec_sources:
        for r in bm25_results:
            r["_bm25_rrf"] = round(r["score"], 4)
            r["_vec_rrf"] = 0.0
            r["_fused_by"] = "bm25-only"
        return bm25_results
    
    # 构建 source → vec_score 映射
    vec_scores = {r["source"]: r["vec_score"] for r in vec_sources}
    
    # 按 source 聚合，融合 BM25 和向量分数
    fused = {}
    
    for r in bm25_results:
        src = r["path"]  # BM25 用 path，向量用 source
        vec_s = vec_scores.get(src, 0.0)
        if src in fused:
            fused[src]["bm25_score"] = r["score"]
            fused[src]["vec_score"] = vec_s
        else:
            fused[src] = {
                "path": src,
                "source": src,
                "snippet": r["snippet"],
                "bm25_score": r["score"],
                "vec_score": vec_s,
                "chunk_hash": r.get("chunk_hash", "")
            }
    
    # 补充只有向量分没有 BM25 分的结果
    for r in vec_sources:
        if r["source"] not in fused:
            fused[r["source"]] = {
                "path": r["source"],
                "source": r["source"],
                "snippet": "",
                "bm25_score": 0.0,
                "vec_score": r["vec_score"],
                "chunk_hash": ""
            }
    
    # 计算 RRF 分数
    for src, item in fused.items():
        # BM25 rank
        sorted_bm25 = sorted(bm25_results, key=lambda x: x["score"], reverse=True)
        bm25_rank = next((i+1 for i, r in enumerate(sorted_bm25) if r["path"] == src), len(sorted_bm25) + 1)
        bm25_rrf = 1 / (k + bm25_rank)
        
        # vec rank
        sorted_vec = sorted(vec_sources, key=lambda x: x["vec_score"], reverse=True)
        vec_rank = next((i+1 for i, r in enumerate(sorted_vec) if r["source"] == src), len(sorted_vec) + 1)
        vec_rrf = 1 / (k + vec_rank)
        
        # 融合分数 = BM25 RRF + Vec RRF
        # RRF 分数仅用于排序，score 字段保留真实信号以方便读取
        item["_rrf_score"] = round(bm25_rrf + vec_rrf, 4)
        item["score"] = round(item["bm25_score"] + item["vec_score"], 4)
        item["_bm25_rrf"] = round(bm25_rrf, 4)
        item["_vec_rrf"] = round(vec_rrf, 4)
        item["_fused_by"] = "rrf"
        # 保留 path 以兼容现有字段
        item["citation"] = src
        item["rank"] = 0
    
    return sorted(fused.values(), key=lambda x: x["_rrf_score"], reverse=True)

# ─── 主搜索函数 ────────────────────────────────────────
def search(query: str, use_expansion: bool = True, top_k: int = 5,
           api_key: str = None, intent_filter: List[str] = None,
           record_hits: bool = True) -> Dict:
    import time as time_module
    t0 = time_module.perf_counter()
    intents = classify_intent(query)
    chunks = scan_memory_files(intent_filter=intents)

    if not chunks:
        return {"results": [], "query": query, "intents": intents,
                "error": "no memory files found"}

    texts = [c["text"] for c in chunks]
    bm25_index = BM25(texts)

    expanded_terms = []
    if use_expansion and api_key:
        expanded_terms = expand_query(query, api_key)
    else:
        expanded_terms = [query]

    seen_hashes = set()
    all_results = []

    for term in expanded_terms:
        term_results = bm25_index.search(term, top_k=top_k)
        for rank, (idx, score) in enumerate(term_results):
            chunk = chunks[idx]
            if chunk["chunk_hash"] in seen_hashes:
                continue
            seen_hashes.add(chunk["chunk_hash"])
            snippet = chunk["text"][:200].strip()
            if len(chunk["text"]) > 200:
                snippet += "..."

            item = {
                "path": chunk["source"],
                "snippet": snippet,
                "score": round(score, 4),
                "textScore": round(score, 4),
                "citation": f"{chunk['source']}",
                "rank": len(all_results) + 1,
                "query_term": term,
                "chunk_hash": chunk["chunk_hash"]
            }
            all_results.append(item)

    all_results.sort(key=lambda x: x["score"], reverse=True)
    all_results = all_results[:top_k]

    # ─── 向量检索补充(RRF 融合)───────────────────────
    vec_sources = []
    try:
        import sys
        sys.path.insert(0, f"{WORKSPACE}/scripts")
        import vector_store
        vec_results = vector_store.search(query, top_k=top_k)
        vec_sources = [{
            "source": r["source"],
            "vec_score": r.get("vec_score", 0),
            "bm25_score": 0
        } for r in vec_results]
    except Exception:
        # 向量库不可用时静默降级为纯 BM25
        vec_sources = []

    # 融合 BM25 和向量结果（统一调用，函数内部会处理 vec_sources 为空的情况）
    all_results = fuse_bm25_and_vector(all_results, vec_sources)
    all_results = all_results[:top_k]

    # 应用 hit boost(工程控制论自适应权重)
    hits = load_hits()
    all_results = apply_hit_boost(all_results, hits)
    all_results.sort(key=lambda x: x["score"], reverse=True)

    # 记录本次命中(供下次检索使用)
    if record_hits:
        for item in all_results:
            chunk_hash = item.get("chunk_hash", "")
            if chunk_hash:
                record_hit(chunk_hash)

    latency_ms = round((time_module.perf_counter() - t0) * 1000, 1)
    # 记录性能数据
    record_query_stats(latency_ms, len(all_results), len(vec_sources) > 0)
    return {
        "results": all_results,
        "query": query,
        "expanded_terms": expanded_terms,
        "intents": intents,
        "total_indexed": len(chunks),
        "has_vector_results": len(vec_sources) > 0,
        "latency_ms": latency_ms,
        "timestamp": datetime.now(CST).isoformat()
    }

# ─── 性能监控（稳定性追踪）──────────────────────────────
STATS_FILE = f"{WORKSPACE}/data/vector_store_stats.json"

def record_query_stats(latency_ms: float, hit_count: int, has_vector: bool, error: str = None):
    """记录每次查询的性能数据（用于稳定性追踪）"""
    import json
    from datetime import datetime, timedelta
    p = Path(STATS_FILE)
    stats = json.loads(p.read_text()) if p.exists() else {"queries": [], "last_clean": datetime.now(CST).isoformat()}
    entry = {
        "ts": datetime.now(CST).isoformat(),
        "latency_ms": round(latency_ms, 1),
        "hit_count": hit_count,
        "has_vector": has_vector,
        "error": error
    }
    stats["queries"].append(entry)
    # Keep last 7 days
    cutoff = datetime.now(CST) - timedelta(days=7)
    stats["queries"] = [q for q in stats["queries"] if datetime.fromisoformat(q["ts"]).replace(tzinfo=CST) > cutoff]
    p.write_text(json.dumps(stats, ensure_ascii=False, indent=2))

def get_stability_report() -> dict:
    """获取稳定性报告"""
    import json
    from datetime import datetime, timedelta
    p = Path(STATS_FILE)
    if not p.exists():
        return {"error": "暂无性能数据"}
    stats = json.loads(p.read_text())
    queries = stats.get("queries", [])
    if not queries:
        return {"error": "暂无性能数据"}
    latencies = sorted(q["latency_ms"] for q in queries)
    n = len(latencies)
    errors = [q for q in queries if q.get("error")]
    has_vec = sum(1 for q in queries if q.get("has_vector"))
    return {
        "total_queries": n,
        "avg_ms": round(sum(latencies) / n, 1),
        "p50_ms": latencies[int(n * 0.50)],
        "p95_ms": latencies[int(n * 0.95)],
        "p99_ms": latencies[int(n * 0.99)],
        "max_ms": max(latencies),
        "vector_hit_rate": f"{has_vec}/{n}",
        "error_count": len(errors),
        "recent_errors": errors[-5:] if errors else []
    }

# ─── CLI ────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="小龙虾记忆搜索 v2.0")
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--no-expand", action="store_true", help="禁用查询扩展")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--api-key", default=os.environ.get("MINIMAX_API_KEY", ""))
    args = parser.parse_args()

    if not args.query:
        print("用法: python3 memory_search.py <查询词> [--no-expand] [--top-k 5]")
        exit(0)

    result = search(args.query, use_expansion=not args.no_expand,
                    top_k=args.top_k, api_key=args.api_key)
    print(json.dumps(result, ensure_ascii=False, indent=2))