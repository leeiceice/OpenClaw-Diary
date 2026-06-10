#!/usr/bin/env python3
"""
memory-tencentdb 向量重建脚本
从 records/*.jsonl 读取 L1 记忆，调用 SiliconFlow 生成 Qwen3-Embedding-4B 向量，
写入 vectors.db 的 l1_vec / l1_vec_chunks 表。
"""

import argparse
import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("❌ 需要 requests: pip install requests")
    raise SystemExit(1)


def embed_texts(texts: list[str], api_key: str, model: str, base_url: str, dimensions: int, timeout: int = 30) -> Optional[list[list[float]]]:
    """调用 SiliconFlow embedding API"""
    url = f"{base_url.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "input": texts,
        "dimensions": dimensions
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code != 200:
        print(f"   ⚠️ API 错误 {resp.status_code}: {resp.text[:200]}")
        return None
    data = resp.json()
    if "data" not in data:
        print(f"   ⚠️ 返回异常: {data}")
        return None
    # API 返回已按 index 排序，直接取出 embedding 列表
    embeddings = [item["embedding"] for item in data["data"]]
    return embeddings


def load_records(records_dir: Path) -> list[tuple[str, str]]:
    """加载所有 L1 记录，返回 [(record_id, content), ...]"""
    records = []
    for f in sorted(records_dir.glob("*.jsonl")):
        with open(f, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    record_id = rec.get("record_id") or rec.get("id")
                    content = rec.get("content", "")
                    if record_id and content:
                        records.append((record_id, content))
                except json.JSONDecodeError:
                    continue
    return records


def main():
    parser = argparse.ArgumentParser(description="重建 memory-tencentdb L1 向量")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--model", default="Qwen/Qwen3-Embedding-4B")
    parser.add_argument("--base-url", default="https://api.siliconflow.cn/v1")
    parser.add_argument("--dimensions", type=int, default=2560)
    parser.add_argument("--db-path", default="~/.openclaw/memory-tdai/vectors.db")
    parser.add_argument("--records-dir", default="~/.openclaw/memory-tdai/records")
    parser.add_argument("--batch-size", type=int, default=10, help="每批embedding条数")
    parser.add_argument("--dry-run", action="store_true", help="仅统计，不写入")
    args = parser.parse_args()

    records_dir = Path(args.records_dir)
    db_path = Path(args.db_path)

    print(f"加载 L1 记录: {records_dir} ...")
    records = load_records(records_dir)
    print(f"共 {len(records)} 条 L1 记录")

    if args.dry_run:
        print("✅ dry-run 模式，仅统计")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    total = len(records)
    success = 0
    errors = 0
    batch_size = args.batch_size

    for i in range(0, total, batch_size):
        batch = records[i:i + batch_size]
        texts = [r[1][:5000] for r in batch]
        ids = [r[0] for r in batch]

        print(f"  处理 {i+1}–{i+len(batch)}/{total} ...", end="", flush=True)
        vecs = embed_texts(texts, args.api_key, args.model, args.base_url, args.dimensions)

        if vecs is None:
            errors += len(batch)
            print(" ❌")
            continue

        for record_id, vec in zip(ids, vecs):
            vec_json = json.dumps(vec, separators=(",", ":"))
            cur.execute(
                "INSERT OR REPLACE INTO l1_vec (record_id, vec_contents) VALUES (?, ?)",
                (record_id, vec_json)
            )
            cur.execute(
                "INSERT OR REPLACE INTO l1_vec_chunks (record_id, chunks) VALUES (?, ?)",
                (record_id, "[]")
            )

        conn.commit()
        success += len(batch)
        print(f" ✅ ({success} 成功, {errors} 错误)")
        time.sleep(0.3)

    cur.execute("SELECT COUNT(*) FROM l1_vec WHERE vec_contents != '[]' AND vec_contents != ''")
    written = cur.fetchone()[0]
    print(f"\n✅ 完成: {success}/{total} 条向量已写入 vectors.db")
    print(f"   l1_vec 表有效记录: {written} 条")

    cur.execute("INSERT OR REPLACE INTO embedding_meta (key, value) VALUES ('embedding_dimensions', ?)", (str(args.dimensions),))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()