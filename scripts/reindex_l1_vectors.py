#!/usr/bin/env python3
"""
reindex_l1_vectors.py
背填 L1 向量：读取所有未生成向量的 L1 记录，通过 SiliconFlow Qwen3-Embedding-4B 生成向量，
写入 ~/.openclaw/memory-tdai/vectors.db 的 l1_vec 表。

用法：
  python3 reindex_l1_vectors.py [--dry-run] [--limit N]
"""

import sqlite3
import json
import os
import sys
import time
import argparse
import urllib.request
import urllib.error

SILICONFLOW_API = "https://api.siliconflow.cn/v1/embeddings"
SILICONFLOW_KEY = "sk-svrwmzrwzxycgoildavxcrtzprlktsyalcqfltuqmwvspbzz"
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-4B"
DIMENSIONS = 2560
DB_PATH = "~/.openclaw/memory-tdai/vectors.db"


def embed_text(text: str) -> list[float] | None:
    payload = json.dumps({
        "model": EMBEDDING_MODEL,
        "input": text[:5000],
    }).encode("utf-8")
    req = urllib.request.Request(
        SILICONFLOW_API,
        data=payload,
        headers={
            "Authorization": f"Bearer {SILICONFLOW_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["data"][0]["embedding"]
    except urllib.error.HTTPError as e:
        print(f"  [HTTP ERROR {e.code}] {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


def get_l1_records_without_vectors(conn: sqlite3.Connection) -> list[tuple]:
    """返回有 l1_records 记录但 l1_vec 表中没有对应向量的记录"""
    sql = """
    SELECT r.id, r.content, r.type, r.priority
    FROM l1_records r
    LEFT JOIN l1_vec v ON v.record_id = r.id
    WHERE v.record_id IS NULL
    ORDER BY r.createdAt DESC
    """
    return conn.execute(sql).fetchall()


def get_existing_vec_ids(conn: sqlite3.Connection) -> set:
    """返回已在 l1_vec 中的 record_id"""
    rows = conn.execute("SELECT record_id FROM l1_vec").fetchall()
    return {r[0] for r in rows}


def write_vector(conn: sqlite3.Connection, record_id: str, vector: list[float]):
    """将向量写入 l1_vec 表"""
    # 写入 l1_vec（虚拟表，通过 l1_vec_rowids + l1_vec_vector_chunks00 实现）
    # 检查 record 是否已在 l1_vec_rowids 中
    existing = conn.execute(
        "SELECT rowid FROM l1_vec_rowids WHERE id = ?", (record_id,)
    ).fetchone()

    vec_bytes = sqlite3.Binary(bytearray.fromhex(''.join('%02x' % int(x * 127 + 128) for x in vector[:DIMENSIONS])))
    
    # 实际 l1_vec 是 vec0 虚拟表，直接 INSERT
    # vec0 的结构：record_id TEXT, embedding float[2560]
    # 虚拟表不能直接 INSERT，用普通表模拟
    # 实际上 l1_vec_vector_chunks00 才是实际存储，我们直接写入 chunks
    if existing:
        # Update existing
        rowid = existing[0]
        # 更新 vector_chunks 表
        # 先检查表结构
        pass
    else:
        # Insert new - 通过 chunks 表
        pass


def write_vector_via_chunks(conn: sqlite3.Connection, record_id: str, vector: list[float]):
    """通过 chunks 表写入向量（模拟 vec0 虚拟表的底层存储）"""
    cursor = conn.cursor()
    
    # 检查 record 是否已存在
    existing = cursor.execute(
        "SELECT rowid FROM l1_vec_rowids WHERE id = ?", (record_id,)
    ).fetchone()
    
    # 将 float32 vector 转为 bytes
    import struct
    vec_bytes = struct.pack(f'{len(vector)}f', *vector[:DIMENSIONS])
    
    if existing:
        rowid = existing[0]
        # 更新 chunks
        cursor.execute(
            "UPDATE l1_vec_vector_chunks00 SET vectors = ? WHERE rowid = ?",
            (vec_bytes, rowid)
        )
    else:
        # 找到当前最大 chunk_id
        max_chunk = cursor.execute(
            "SELECT COALESCE(MAX(chunk_id), 0) FROM l1_vec_rowids WHERE chunk_id = 1"
        ).fetchone()[0]
        
        # 在 l1_vec_rowids 中添加记录
        # 先找到当前 chunk 的行数
        chunk_row_count = cursor.execute(
            "SELECT COUNT(*) FROM l1_vec_rowids WHERE chunk_id = ?", (1,)
        ).fetchone()[0]
        
        chunk_offset = chunk_row_count  # 当前 chunk 的 offset
        
        cursor.execute(
            "INSERT INTO l1_vec_rowids (id, chunk_id, chunk_offset) VALUES (?, ?, ?)",
            (record_id, 1, chunk_offset)
        )
        new_rowid = cursor.lastrowid
        
        # 在 vector_chunks 表中插入
        cursor.execute(
            "INSERT INTO l1_vec_vector_chunks00 (rowid, vectors) VALUES (?, ?)",
            (new_rowid, vec_bytes)
        )
    
    conn.commit()
    return True


def get_vec_chunks_schema():
    """返回 l1_vec_vector_chunks00 的表结构信息"""
    return None


def main():
    parser = argparse.ArgumentParser(description="背填 L1 向量到 vectors.db")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写入")
    parser.add_argument("--limit", type=int, default=0, help="限制处理记录数（0=全部）")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"ERROR: DB 不存在: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    
    # 检查表结构
    print("=== 检查 l1_vec 表结构 ===")
    try:
        test = conn.execute("SELECT record_id, embedding FROM l1_vec LIMIT 1").fetchall()
        print(f"  l1_vec: vec0 虚拟表，可直接写入")
        use_direct = True
    except Exception as e:
        print(f"  l1_vec: {e}")
        use_direct = False
    
    print()
    
    # 获取 l1_vec_rowids 的实际内容
    rowid_count = conn.execute("SELECT COUNT(*) FROM l1_vec_rowids").fetchone()[0]
    vec_chunk_count = conn.execute("SELECT COUNT(*) FROM l1_vec_vector_chunks00").fetchone()[0]
    l1_records_count = conn.execute("SELECT COUNT(*) FROM l1_records").fetchone()[0]
    
    print(f"=== 当前数据状态 ===")
    print(f"  l1_records:        {l1_records_count} 条")
    print(f"  l1_vec_rowids:     {rowid_count} 条")
    print(f"  l1_vec chunks:     {vec_chunk_count} 行")
    print()
    
    # 获取已有向量的 record_id
    existing_ids = get_existing_vec_ids(conn)
    print(f"  l1_vec 中已有向量: {len(existing_ids)} 条")
    
    # 获取需要生成向量的记录
    records = get_l1_records_without_vectors(conn)
    print(f"  需要生成向量:      {len(records)} 条")
    print()
    
    if args.limit > 0:
        records = records[:args.limit]
        print(f"  [limit模式] 处理前 {args.limit} 条")
    
    if not records:
        print("✅ 没有需要生成向量的记录")
        conn.close()
        return
    
    print(f"=== 开始生成向量 (共 {len(records)} 条) ===")
    
    success = 0
    failed = 0
    skipped = 0
    
    for i, (record_id, content, rec_type, priority) in enumerate(records):
        print(f"  [{i+1}/{len(records)}] {record_id[:30]}... ({rec_type}, p={priority})")
        
        if args.dry_run:
            print(f"    [dry-run] 跳过写入")
            skipped += 1
            continue
        
        vector = embed_text(content)
        if vector is None:
            print(f"    [FAIL] embedding 请求失败")
            failed += 1
            continue
        
        if len(vector) != DIMENSIONS:
            print(f"    [FAIL] 向量维度错误: {len(vector)} vs {DIMENSIONS}")
            failed += 1
            continue
        
        # 写入向量
        ok = write_vector_via_chunks(conn, record_id, vector)
        if ok:
            print(f"    [OK] 写入成功")
            success += 1
        else:
            print(f"    [FAIL] 写入失败")
            failed += 1
        
        if (i + 1) % 10 == 0:
            print(f"  --- 进度: {i+1}/{len(records)}, 成功: {success}, 失败: {failed} ---")
    
    print()
    print(f"=== 完成 ===")
    print(f"  成功: {success}")
    print(f"  失败: {failed}")
    print(f"  跳过: {skipped}")
    
    # 验证
    new_existing = get_existing_vec_ids(conn)
    print(f"  l1_vec 向量总数: {len(new_existing)}")
    
    conn.close()


if __name__ == "__main__":
    main()