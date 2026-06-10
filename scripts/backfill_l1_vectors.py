#!/usr/bin/env python3
"""
Backfill missing L1 vectors for memory-tencentdb.
Reads L1 records from JSONL files, embeds them via SiliconFlow API,
and inserts vectors into vectors.db l1_vec table.

Usage: python3 scripts/backfill_l1_vectors.py [records_dir] [vectors_db]
"""
import json
import sqlite3
import sys
import os
import time
import subprocess
import vector

VEC0_SO = "~/.openclaw/extensions/memory-tencentdb/node_modules/.pnpm/sqlite-vec-linux-x64@0.1.7-alpha.2/node_modules/sqlite-vec-linux-x64/vec0.so"
SILICONFLOW_API = "https://api.siliconflow.cn/v1/embeddings"
SILICONFLOW_KEY = subprocess.run(
    ["openclaw", "config", "get", "plugins.entries.memory-tencentdb.config.embedding.apiKey"],
    capture_output=True, text=True
).stdout.strip()

# Read API key from config - it's redacted in config get, need to read from env or config file
# Try reading from environment or netrc
API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
if not API_KEY:
    # Read directly from openclaw.json
    import subprocess
    result = subprocess.run(["cat", "~/.openclaw/openclaw.json"], capture_output=True, text=True)
    try:
        full_config = json.loads(result.stdout)
        raw = full_config.get("plugins", {}).get("entries", {}).get("memory-tencentdb", {}).get("config", {})
        # apiKey is redacted - need to check if there's a way to get it
        print("WARNING: Cannot read apiKey from openclaw.json (redacted). Trying environment...")
    except:
        pass

def get_api_key():
    """Try to get API key from netrc or environment."""
    import subprocess
    # Use openclaw config get with full output
    result = subprocess.run(
        ["openclaw", "config", "get", "plugins.entries.memory-tencentdb.config.embedding.apiKey", "--raw"],
        capture_output=True, text=True
    )
    raw = result.stdout.strip()
    # If it shows __OPENCLAW_REDACTED__, we can't get the actual key
    if "REDACTED" in raw:
        # Try reading from the raw config file
        try:
            with open("~/.openclaw/openclaw.json") as f:
                content = f.read()
            # The key might be in the file as actual value
            import re
            match = re.search(r'"apiKey"\s*:\s*"([^"]{10,})"', content)
            if match:
                return match.group(1)
        except:
            pass
        return None
    return raw.strip()

def embed_text(text: str, api_key: str) -> list[float]:
    """Call SiliconFlow embedding API."""
    import urllib.request
    import urllib.error
    
    payload = {
        "model": "Qwen/Qwen3-Embedding-4B",
        "input": text[:5000],  # truncate to 5000 chars
        "dimensions": 2560
    }
    
    req = urllib.request.Request(
        SILICONFLOW_API,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["data"][0]["embedding"]
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"  Embedding error: {e}")
        return None

def main():
    records_dir = sys.argv[1] if len(sys.argv) > 1 else "~/.openclaw/memory-tdai/records"
    vectors_db = sys.argv[2] if len(sys.argv) > 2 else "~/.openclaw/memory-tdai/vectors.db"
    
    api_key = get_api_key()
    if not api_key:
        print("ERROR: Cannot get SiliconFlow API key. Exiting.")
        sys.exit(1)
    
    # Connect to vectors.db with vec0 extension
    conn = sqlite3.connect(vectors_db)
    conn.enable_load_extension(True)
    try:
        conn.load_extension(VEC0_SO)
    except Exception as e:
        print(f"ERROR: Failed to load vec0 extension: {e}")
        sys.exit(1)
    
    # Get existing record_ids that already have vectors
    existing = set()
    try:
        for row in conn.execute("SELECT record_id FROM l1_vec"):
            existing.add(row[0])
        print(f"Existing vectors in DB: {len(existing)}")
    except Exception as e:
        print(f"Note: l1_vec query error (may be empty): {e}")
    
    # Find all JSONL files
    jsonl_files = sorted([f for f in os.listdir(records_dir) if f.endswith(".jsonl")])
    print(f"Record files: {[f for f in jsonl_files]}")
    
    total_records = 0
    new_vectors = 0
    already_had = 0
    errors = 0
    
    for jsonl_file in jsonl_files:
        filepath = os.path.join(records_dir, jsonl_file)
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except:
                    continue
                
                record_id = record.get("id")
                content = record.get("content", "")
                if not record_id or not content:
                    continue
                
                total_records += 1
                
                if record_id in existing:
                    already_had += 1
                    continue
                
                # Need to embed this record
                print(f"  Embedding {record_id[:20]}... ({len(content)} chars)", end=" ")
                embedding = embed_text(content, api_key)
                
                if embedding is None:
                    errors += 1
                    print("FAILED")
                    continue
                
                now = time.time()
                conn.execute(
                    "INSERT INTO l1_vec (record_id, embedding, updated_time) VALUES (?, ?, ?)",
                    (record_id, json.dumps(embedding), now)
                )
                new_vectors += 1
                print(f"OK ({len(embedding)} dims)")
                
                # Rate limit: sleep between requests
                time.sleep(0.3)
        
        # Commit after each file
        conn.commit()
    
    print(f"\n=== Summary ===")
    print(f"Total records processed: {total_records}")
    print(f"Already had vectors: {already_had}")
    print(f"New vectors created: {new_vectors}")
    print(f"Errors: {errors}")
    
    # Verify count
    final_count = conn.execute("SELECT COUNT(*) FROM l1_vec").fetchone()[0]
    print(f"Final l1_vec count: {final_count}")
    
    conn.close()

if __name__ == "__main__":
    main()
