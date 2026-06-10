#!/usr/bin/env python3
"""睡眠数据接收 API - 兼容 Health Auto Export 格式"""
from fastapi import FastAPI, Request
import json
import os
from datetime import datetime
from _timezone import CST
from collections import defaultdict

app = FastAPI()

DATA_DIR = "~/.openclaw/workspace/data"
DATA_FILE = os.path.join(DATA_DIR, "sleep-log.json")

os.makedirs(DATA_DIR, exist_ok=True)

def load_sleep_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"records": [], "stats": {}}

def save_sleep_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def min_to_hm(minutes):
    if minutes is None:
        return None
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h {m}m"

def parse_hours_to_minutes(val):
    """Health Auto Export uses hours as floats"""
    if val is None:
        return None
    return round(float(val) * 60, 1)

@app.get("/")
async def root():
    return {"status": "ok", "service": "sleep-tracker", "endpoint": "/sleep"}

@app.post("/sleep")
async def receive_sleep(request: Request):
    """接收 Health Auto Export 或简化格式的睡眠数据"""
    try:
        body = await request.body()
        data = json.loads(body)
        
        records = load_sleep_data()
        new_records = []
        
        # === Health Auto Export 格式 ===
        if "data" in data and "metrics" in data["data"]:
            metric = data["data"]["metrics"][0]
            if metric.get("name") == "sleep_analysis":
                days = metric["data"]  # 数组，多天数据
                print(f"📊 Health Auto Export: 检测到 {len(days)} 天数据")
                
                for day in days:
                    date_str = day.get("date", "")[:10]  # "2026-04-25 00:00:00 +0800"
                    
                    total_hr = day.get("totalSleep", 0)
                    deep_hr = day.get("deep", 0)
                    core_hr = day.get("core", 0)
                    rem_hr = day.get("rem", 0)
                    awake_hr = day.get("awake", 0)
                    
                    record = {
                        "date": date_str,
                        "received_at": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"),
                        "source": "health-auto-export",
                        "totalSleepMin": parse_hours_to_minutes(total_hr),
                        "totalSleepFormatted": min_to_hm(parse_hours_to_minutes(total_hr)),
                        "deepSleepMin": parse_hours_to_minutes(deep_hr),
                        "coreSleepMin": parse_hours_to_minutes(core_hr),
                        "remSleepMin": parse_hours_to_minutes(rem_hr),
                        "awakeSleepMin": parse_hours_to_minutes(awake_hr),
                        "sleepStart": day.get("sleepStart", "")[:16],
                        "sleepEnd": day.get("sleepEnd", "")[:16],
                        "bedTime": day.get("inBedStart", "")[:16],
                        "wakeTime": day.get("inBedEnd", "")[:16],
                    }
                    
                    # 计算质量评分（基于 awake ratio）
                    if total_hr > 0:
                        awake_ratio = awake_hr / total_hr
                        quality = max(1, min(5, round(5 - awake_ratio * 5, 1)))
                        record["sleepQuality"] = quality
                    
                    new_records.append(record)
                    print(f"  ✅ {date_str} | {record['totalSleepFormatted']} | 质量 {quality if total_hr > 0 else 'N/A'}")
        
        # === 简化格式（单个对象）===
        elif isinstance(data, dict) and "date" in data:
            total_min = data.get("totalSleepMin") or (float(data.get("totalSleep", 0)) * 60 if data.get("totalSleep") else None)
            
            record = {
                "date": data.get("date", datetime.now(CST).strftime("%Y-%m-%d")),
                "received_at": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"),
                "source": data.get("source", "manual"),
                "totalSleepMin": float(total_min) if total_min else None,
                "totalSleepFormatted": min_to_hm(total_min) if total_min else None,
                "deepSleepMin": data.get("deepSleepMin"),
                "lightSleepMin": data.get("lightSleepMin"),
                "sleepQuality": data.get("sleepQuality"),
                "bedTime": data.get("timeToSleep"),
                "wakeTime": data.get("wakeTime"),
            }
            new_records.append(record)
        
        if not new_records:
            print(f"⚠️ 无法解析数据格式: {str(data)[:200]}")
            return {"status": "error", "message": "无法解析数据格式"}, 400
        
        # 更新 records
        existing_dates = {r["date"] for r in records.get("records", [])}
        for r in new_records:
            if r["date"] in existing_dates:
                # 更新
                for i, old in enumerate(records["records"]):
                    if old["date"] == r["date"]:
                        records["records"][i] = r
                        break
            else:
                records["records"].append(r)
        
        records["records"].sort(key=lambda x: x["date"], reverse=True)
        save_sleep_data(records)
        
        print(f"✅ 成功保存 {len(new_records)} 条记录")
        return {"status": "ok", "saved": len(new_records), "dates": [r["date"] for r in new_records]}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}, 500

@app.get("/sleep/latest")
async def get_latest():
    records = load_sleep_data()
    if records.get("records"):
        return records["records"][0]
    return {"message": "暂无数据"}

@app.get("/sleep/week")
async def get_week():
    records = load_sleep_data()
    return {"records": records.get("records", [])[:7], "count": min(len(records.get("records", [])), 7)}

@app.get("/sleep/all")
async def get_all():
    records = load_sleep_data()
    return records

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18792, log_level="info")
