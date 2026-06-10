#!/usr/bin/env python3
"""
vector_store.py — 小龙虾本地向量库
基于 sqlite-vec + SiliconFlow embedding

第一步：只索引 corrections.md + scenes/（高价值偏差内容）
第二步：扩展到 SOUL.md / AGENTS.md 等核心文件

核心链路：
  corrections.md / scenes/ → SiliconFlow embedding → sqlite-vec 存储 → RRF 混合检索
"""

import argparse
import json
import math
import os
import re
import sqlite3
import struct
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import numpy as np
    import sqlite_vec
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False
    print("❌ 需要 numpy 和 sqlite-vec: pip install numpy sqlite-vec --break-system-packages")

# ─── 配置 ────────────────────────────────────────────────
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
VEC_DB = f"{WORKSPACE}/data/vector_store.db"
SILICONFLOW_URL = "https://api.siliconflow.cn/v1/embeddings"
SILICONFLOW_KEY = None  # 运行时从 openclaw.json 读取
MODEL = "Qwen/Qwen3-Embedding-4B"
DIMENSIONS = 2560
RRF_K = 60  # RRF 融合参数


def get_api_key() -> str:
    """从 .env 读取 SILICONFLOW_API_KEY"""
    global SILICONFLOW_KEY
    if SILICONFLOW_KEY:
        return SILICONFLOW_KEY
    import os
    key = os.environ.get("SILICONFLOW_API_KEY") or os.environ.get("SILICONFLOW_KEY")
    if not key:
        env_file = os.path.expanduser("~/.openclaw/.env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("SILICONFLOW_API_KEY=") or line.startswith("SILICONFLOW_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
    if key and len(key) > 20:
        SILICONFLOW_KEY = key
        return SILICONFLOW_KEY
    raise ValueError("无法从 .env 读取 SILICONFLOW_API_KEY")

def embed_texts(texts: list[str], batch_size: int = 8) -> list[list[float]]:
    """调用 SiliconFlow embedding API（batch）"""
    import urllib.request

    key = get_api_key()
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        payload = {
            "model": MODEL,
            "input": batch,
            "dimensions": DIMENSIONS
        }
        req = urllib.request.Request(
            SILICONFLOW_URL,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(embeddings)
        except Exception as e:
            print(f"   ⚠️ API 调用失败: {e}")
            # 返回零向量作为降级
            all_embeddings.extend([[0.0] * DIMENSIONS for _ in batch])

        if i + batch_size < len(texts):
            time.sleep(0.1)  # 避免限流

    return all_embeddings


def init_db():
    """初始化 sqlite-vec 数据库"""
    conn = sqlite3.connect(VEC_DB)
    cur = conn.cursor()

    # 加载 sqlite-vec 扩展（必须先 load 才能操作 vec0 虚拟表）
    import sqlite_vec
    sqlite_vec.load(conn)

    # 创建表：文本索引（id, source, chunk_hash, text）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            chunk_hash TEXT NOT NULL UNIQUE,
            text TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建表：向量（原始 BLOB 存储，sqlite-vec 虚拟表）
    cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='vectors'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            CREATE TABLE vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chunk_id) REFERENCES chunks(id)
            )
        """)

    # 创建 sqlite-vec vec0 虚拟表（用于高效相似度检索）
    cur.execute("DROP TABLE IF EXISTS vec_chunks")
    cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(embedding float[2560])")

    conn.commit()
    return conn


def compute_hash(text: str) -> str:
    """计算文本 SHA256 前12位"""
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def extract_chunks_from_corrections() -> list[dict]:
    """从 corrections.md 提取偏差记录块"""
    corrections_path = f"{WORKSPACE}/self-improving/corrections.md"
    if not os.path.exists(corrections_path):
        return []

    content = open(corrections_path).read()
    entries = re.split(r'(?=### deviation_id: )', content)

    chunks = []
    for entry in entries:
        entry = entry.strip()
        if not re.match(r'^### deviation_id: dev_\d{8}_\d{3}', entry):
            continue
        # 提取核心内容
        subject_m = re.search(r'\*\*主题\*\*: (.+)', entry)
        desc_m = re.search(r'\*\*偏差描述\*\*: (.+)', entry)
        severity_m = re.search(r'\*\*严重程度\*\*: (.+)', entry)
        status_m = re.search(r'\*\*验证状态\*\*: (.+)', entry)

        if subject_m and desc_m:
            text = f"偏差主题：{subject_m.group(1)}\n偏差描述：{desc_m.group(1)}"
            if severity_m:
                text += f"\n严重程度：{severity_m.group(1)}"
            if status_m:
                text += f"\n验证状态：{status_m.group(1)}"

            chunks.append({
                "source": "self-improving/corrections.md",
                "text": text,
                "chunk_hash": compute_hash(text)
            })
    return chunks


def extract_chunks_from_scenes() -> list[dict]:
    """从 scenes/ 目录提取 L2 场景块"""
    scenes_dir = f"{WORKSPACE}/memory/deviations/scenes"
    if not os.path.isdir(scenes_dir):
        return []

    chunks = []
    for fname in os.listdir(scenes_dir):
        if not fname.endswith(".md"):
            continue
        fpath = f"{scenes_dir}/{fname}"
        content = open(fpath).read()

        # 按 ## 分段提取
        blocks = re.split(r'(?=^## )', content, flags=re.MULTILINE)
        for block in blocks:
            block = block.strip()
            if len(block) < 30:
                continue
            # 取第一个 ## 标题作为描述
            title_m = re.search(r'^##?\s*(.+)', block, re.MULTILINE)
            title = title_m.group(1).strip() if title_m else fname
            text = f"{fname[:-3]} — {title}\n{block[:500]}"
            chunks.append({
                "source": f"memory/deviations/scenes/{fname}",
                "text": text,
                "chunk_hash": compute_hash(text)
            })
    return chunks


def build_index(rebuild: bool = False):
    """构建向量索引"""
    print(f"📦 构建向量索引...")
    print(f"   数据库: {VEC_DB}")
    print(f"   向量维度: {DIMENSIONS}")
    print(f"   模型: {MODEL}")

    conn = init_db()
    cur = conn.cursor()

    if rebuild:
        print("   🗑️  重建模式：清空现有向量...")
        cur.execute("DELETE FROM chunks")
        try:
            cur.execute("DELETE FROM vectors")
            cur.execute("DROP TABLE IF EXISTS vec_chunks")
            import sqlite_vec
            sqlite_vec.load(conn)
            cur.execute("CREATE VIRTUAL TABLE vec_chunks USING vec0(embedding float[2560])")
        except Exception:
            pass
        conn.commit()

    # 提取文本块
    print("   📖 提取文本块...")
    chunks = []
    corrections_chunks = extract_chunks_from_corrections()
    scenes_chunks = extract_chunks_from_scenes()
    chunks.extend(corrections_chunks)
    chunks.extend(scenes_chunks)
    print(f"   corrections.md: {len(corrections_chunks)} 条")
    print(f"   scenes/: {len(scenes_chunks)} 条")
    print(f"   共计: {len(chunks)} 条")

    if not chunks:
        print("   ⚠️  没有找到文本块")
        return

    # 过滤已有向量
    existing_hashes = set()
    cur.execute("SELECT chunk_hash FROM chunks")
    for row in cur.fetchall():
        existing_hashes.add(row[0])

    new_chunks = [c for c in chunks if c["chunk_hash"] not in existing_hashes]
    print(f"   新增: {len(new_chunks)} 条（已有: {len(existing_hashes)} 条）")

    if new_chunks:
        # 批量 embedding
        texts = [c["text"] for c in new_chunks]
        print(f"   🔢 调用 SiliconFlow embedding ({len(texts)} 条)...")
        embeddings = embed_texts(texts)
        print(f"   ✅ embedding 完成")

        # 写入数据库
        print("   💾 写入向量库...")
        for chunk, embedding in zip(new_chunks, embeddings):
            # 写入 chunks 表
            cur.execute(
                "INSERT OR IGNORE INTO chunks (source, chunk_hash, text) VALUES (?, ?, ?)",
                (chunk["source"], chunk["chunk_hash"], chunk["text"])
            )
            cur.execute("SELECT id FROM chunks WHERE chunk_hash = ?", (chunk["chunk_hash"],))
            chunk_id = cur.fetchone()[0]

            # 写入 vectors 表（原始 numpy 序列化）
            vec_bytes = np.array(embedding, dtype=np.float32).tobytes()
            cur.execute(
                "INSERT INTO vectors (chunk_id, source, embedding) VALUES (?, ?, ?)",
                (chunk_id, chunk["source"], vec_bytes)
            )

            # 写入 sqlite-vec 虚拟表（使用 serialize_float32）
            try:
                import sqlite_vec
                sqlite_vec.load(conn)
                vec_bytes = sqlite_vec.serialize_float32(embedding)
                cur.execute(
                    "INSERT INTO vec_chunks (embedding) VALUES (?)",
                    (vec_bytes,)
                )
            except Exception as e:
                print(f"   ⚠️  vec_chunks 写入失败: {e}")

        conn.commit()
        print(f"   ✅ 向量写入完成")

    # 统计
    cur.execute("SELECT COUNT(*) FROM chunks")
    total = cur.fetchone()[0]
    print(f"\n   📊 向量库总计: {total} 条记录")
    conn.close()


def search(query: str, top_k: int = 5) -> list[dict]:
    """混合检索：BM25 × 向量 RRF"""
    # 1. 向量检索
    vec_results = vector_search(query, top_k * 2)

    # 2. BM25 检索（来自 memory_search.py 的 BM25）
    bm25_results = bm25_search(query, top_k * 2)

    # 3. RRF 融合
    fused = rrf_fuse(vec_results, bm25_results, top_k=top_k)
    return fused


def vector_search(query: str, top_k: int = 5) -> list[dict]:
    """向量相似度检索"""
    if not NUMPY_OK:
        return []

    conn = sqlite3.connect(VEC_DB)
    cur = conn.cursor()

    # 生成 query embedding
    embeddings = embed_texts([query])
    query_vec = np.array(embeddings[0], dtype=np.float32)

    # sqlite-vec 相似度搜索
    results = []
    try:
        rows = cur.execute(
            """
            SELECT v.id, v.chunk_id, v.source, v.embedding
            FROM vectors v
            JOIN chunks c ON c.id = v.chunk_id
            LIMIT ?
            """,
            (top_k * 3,)
        ).fetchall()

        for row in rows:
            vec = np.frombuffer(row[3], dtype=np.float32)
            # cosine similarity
            sim = float(np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec) + 1e-8))
            results.append({
                "chunk_id": row[1],
                "source": row[2],
                "vec_score": sim,
                "rank": len(results) + 1
            })
    except Exception as e:
        print(f"   ⚠️  向量搜索失败: {e}")

    conn.close()
    results.sort(key=lambda x: x["vec_score"], reverse=True)
    return results[:top_k]


def bm25_search(query: str, top_k: int = 5) -> list[dict]:
    """BM25 检索（复用 memory_search.py 的 BM25 逻辑）"""
    sys.path.insert(0, f"{WORKSPACE}/scripts")
    try:
        from memory_search import scan_memory_files, BM25, tokenize
        # 只扫描 corrections + scenes
        chunks = []
        corrections_path = f"{WORKSPACE}/self-improving/corrections.md"
        scenes_dir = f"{WORKSPACE}/memory/deviations/scenes"

        # 直接扫描
        if os.path.exists(corrections_path):
            with open(corrections_path) as f:
                content = f.read()
            entries = re.split(r'(?=### deviation_id: )', content)
            for entry in entries:
                entry = entry.strip()
                if not re.match(r'^### deviation_id: dev_\d{8}_\d{3}', entry):
                    continue
                chunks.append({"text": entry, "source": "self-improving/corrections.md"})

        if os.path.isdir(scenes_dir):
            for fname in os.listdir(scenes_dir):
                if not fname.endswith(".md"):
                    continue
                with open(f"{scenes_dir}/{fname}") as f:
                    chunks.append({"text": f.read(), "source": f"memory/deviations/scenes/{fname}"})

        if not chunks:
            return []

        texts = [c["text"] for c in chunks]
        bm25 = BM25(texts)
        query_tokens = tokenize(query)
        scores = []
        for i, doc_tokens in enumerate(bm25.tokenized_corpus):
            s = bm25.score(query_tokens, doc_tokens)
            if s > 0:
                scores.append((i, s))

        scores.sort(key=lambda x: x[1], reverse=True)
        results = []
        for rank, (i, score) in enumerate(scores[:top_k]):
            results.append({
                "source": chunks[i]["source"],
                "bm25_score": score,
                "rank": rank + 1
            })
        return results
    except Exception as e:
        print(f"   ⚠️  BM25 搜索失败: {e}")
        return []


def rrf_fuse(vec_results: list[dict], bm25_results: list[dict], top_k: int = 5) -> list[dict]:
    """RRF 融合：BM25 rank + vector rank"""
    fused = {}

    # 向量结果评分
    for r in vec_results:
        source = r["source"]
        rank = r["rank"]
        rrf_score = 1 / (RRF_K + rank)
        if source in fused:
            fused[source]["rrf_score"] += rrf_score
            fused[source]["vec_score"] = r["vec_score"]
            fused[source]["bm25_score"] = r.get("bm25_score", 0)
        else:
            fused[source] = {
                "source": source,
                "rrf_score": rrf_score,
                "vec_score": r["vec_score"],
                "bm25_score": r.get("bm25_score", 0)
            }

    # BM25 结果评分
    for r in bm25_results:
        source = r["source"]
        rank = r["rank"]
        rrf_score = 1 / (RRF_K + rank)
        if source in fused:
            fused[source]["rrf_score"] += rrf_score
            fused[source]["bm25_score"] = r["bm25_score"]
        else:
            fused[source] = {
                "source": source,
                "rrf_score": rrf_score,
                "vec_score": r.get("vec_score", 0),
                "bm25_score": r["bm25_score"]
            }

    # 按 RRF 分数排序
    sorted_results = sorted(fused.values(), key=lambda x: x["rrf_score"], reverse=True)
    return sorted_results[:top_k]


def stats():
    """向量库统计"""
    if not os.path.exists(VEC_DB):
        print("❌ 向量库不存在，先运行 build")
        return

    conn = sqlite3.connect(VEC_DB)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM chunks")
    total_chunks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM vectors")
    total_vectors = cur.fetchone()[0]

    cur.execute("SELECT source, COUNT(*) FROM chunks GROUP BY source")
    by_source = cur.fetchall()

    conn.close()

    print("📊 向量库统计：")
    print(f"   总文本块: {total_chunks}")
    print(f"   总向量数: {total_vectors}")
    print(f"   磁盘占用: {os.path.getsize(VEC_DB) / 1024:.1f} KB")
    print(f"\n   按来源分布：")
    for source, cnt in by_source:
        print(f"   - {source}: {cnt}")


def main():
    parser = argparse.ArgumentParser(description="小龙虾本地向量库")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build", help="构建向量索引")
    build_parser.add_argument("--rebuild", action="store_true", help="强制重建")

    subparsers.add_parser("stats", help="向量库统计")

    search_parser = subparsers.add_parser("search", help="混合检索")
    search_parser.add_argument("query", help="检索query")
    search_parser.add_argument("--top-k", type=int, default=5, help="返回条数")

    args = parser.parse_args()

    if args.command == "build":
        build_index(rebuild=args.rebuild)
    elif args.command == "stats":
        stats()
    elif args.command == "search":
        results = search(args.query, top_k=args.top_k)
        print(f"\n🔍 检索结果（BM25 × 向量 RRF 融合）：")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['source']}")
            print(f"     RRF: {r['rrf_score']:.4f} | Vec: {r['vec_score']:.4f} | BM25: {r['bm25_score']:.2f}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()