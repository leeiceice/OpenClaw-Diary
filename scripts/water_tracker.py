#!/usr/bin/env python3
"""
喝水追踪处理脚本
Lee 发送喝水消息 → 记录 → 生成视觉化卡片 → 推送到飞书（自动）

推送目标：飞书「日常安排群」 oc_ad39a8e943103c2164f1d0d9de503da5
（强制约束：喝水记录必须文字+图片一起发，缺一不可 —— 2026-06-08 事故后固化）
"""

import argparse
import json
import subprocess
import sys
import re
from datetime import date, datetime, timezone, timedelta
from _timezone import CST
from pathlib import Path

# 飞书推送目标（与 TOOLS.md 同步，禁止硬编码）
FEISHU_CHANNEL = "feishu"
FEISHU_DAILY_CHAT_ID = "oc_ad39a8e943103c2164f1d0d9de503da5"
FEISHU_DAILY_CHAT_TARGET = f"chat:{FEISHU_DAILY_CHAT_ID}"

LOG_FILE = Path("~/.openclaw/workspace/data/water-log.json").expanduser()
WORKSPACE = Path("~/.openclaw/workspace").expanduser()
HISTORY_FILE = Path("~/.openclaw/workspace/data/water-history.jsonl").expanduser()  # 2026-06-14 Lee 拍 A+A：历史永不清空

WATER_KEYWORDS = [
    "喝了一杯", "一杯", "一杯水", "喝了一杯水",
    "两杯", "三杯", "四杯", "五杯", "六杯", "喝两杯", "喝三杯", "喝四杯", "喝五杯",
    "喝了350ml", "350ml", "喝了水", "喝水", "补水",
    "喝了一罐", "喝了瓶", "喝了一瓶", "喝了杯水",
    "🍵", "💧", "☕", "🫖",
    # 序数词（累计杯数）
    "第一杯", "第二杯", "第三杯", "第四杯", "第五杯", "第六杯",
]

CN_NUM_MAP = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'两':2}

def load_log():
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return {"today": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"), "total_ml": 0, "cup_count": 0, "goal_ml": 2000, "cup_ml": 350, "records": []}

def save_log(data):
    with open(LOG_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def append_history(data: dict, mode: str, override_cups: int = 0) -> dict:
    """
    追加一条到 data/water-history.jsonl（2026-06-14 Lee 拍 A+A）
    - 覆盖模式：写 1 条（今日总量 = override_cups × cup_ml）
    - 追加模式：写 1 条（本次增量的 ml）
    返回：{ok, line, path}
    """
    now = datetime.now(CST)
    last_record = data['records'][-1] if data.get('records') else {}
    entry = {
        "ts": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "ml": data['total_ml'] if mode == 'override' else last_record.get('ml', 0),
        "cups_total": data['cup_count'],
        "ml_total": data['total_ml'],
        "mode": mode,  # 'append' | 'override'
        "note": last_record.get('note', ''),
    }
    if mode == 'override':
        entry['override_cups'] = override_cups
    line = json.dumps(entry, ensure_ascii=False)
    try:
        with open(HISTORY_FILE, 'a') as f:
            f.write(line + '\n')
        return {"ok": True, "line": line, "path": str(HISTORY_FILE)}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": str(HISTORY_FILE)}

def backfill_history_if_needed(log: dict) -> dict:
    """
    启动自愈：检测 log 里的 records 是否都已同步进 history.jsonl
    2026-06-15 Lee 拍板：防 log 已有但 history 缺失的失同步（如 6/14 覆盖补录漏写 bug）
    - 用 records 里每条的 (date, ml, note) 元组比对
    - 缺失的自动回填 1 条/每条
    返回：{checked, missing_count, backfilled: [lines]}
    """
    if not log.get('records'):
        return {"checked": 0, "missing_count": 0, "backfilled": []}

    # 读 history 现存条目
    existing = set()
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                    # 用 (date, ml_total) 作为去重 key
                    existing.add((e.get('date'), e.get('ml_total'), e.get('note', '')))
                except Exception:
                    continue

    backfilled = []
    for rec in log['records']:
        # 从 rec['time'] 拆 date（"2026-06-14 16:42" → "2026-06-14"）
        rec_date = rec.get('time', '').split(' ')[0] if rec.get('time') else log.get('today')
        rec_ml_total = rec.get('ml', 0)  # 单条记录的 ml（覆盖模式是总量，追加模式是增量）
        rec_note = rec.get('note', '')
        key = (rec_date, rec_ml_total, rec_note)
        if key in existing:
            continue
        # 缺失 → 回填 1 条（最简形式，标 mode=backfill 避免和正常 append 混淆）
        now_iso = datetime.now(CST).isoformat()
        # rec 的真实时间（从 "YYYY-MM-DD HH:MM" 拼 ISO）
        rec_dt = rec.get('time', '')
        if rec_dt and len(rec_dt) >= 16:
            try:
                rec_ts = datetime.strptime(rec_dt, "%Y-%m-%d %H:%M").replace(tzinfo=CST).isoformat()
            except Exception:
                rec_ts = now_iso
        else:
            rec_ts = now_iso
        entry = {
            "ts": rec_ts,
            "date": rec_date,
            "time": rec_dt.split(' ')[1] if ' ' in rec_dt else '',
            "ml": rec_ml_total,
            "cups_total": log.get('cup_count', 0),  # 近似值
            "ml_total": rec_ml_total,
            "mode": "backfill",
            "note": f"[自愈补录] {rec_note}" if rec_note else "[自愈补录]",
        }
        line = json.dumps(entry, ensure_ascii=False)
        try:
            with open(HISTORY_FILE, 'a') as f:
                f.write(line + '\n')
            backfilled.append(line)
            existing.add(key)
        except Exception as e:
            print(f"[backfill] ⚠️ 写入失败:{e}", file=sys.stderr)
    return {"checked": len(log['records']), "missing_count": len(backfilled), "backfilled": backfilled}

def is_water_message(text: str) -> bool:
    text_lower = text.lower()
    keywords = ["喝了一杯", "一杯", "一杯水", "两杯", "三杯", "四杯", "五杯", "六杯",
                "喝了350ml", "350ml", "喝了水", "喝水", "补水",
                "🍵", "💧", "☕", "🫖", "瓶", "罐", "第", "第杯"]
    # 阿拉伯数字+杯
    if re.search(r'\d+\s*杯', text):
        return True
    return any(kw in text_lower for kw in keywords)

def process_messages(text: str) -> int:
    """
    喝水意图解析。重要：不同分支必须互斥，不能叠加。
    优先级（取最高者）：
      A. 「喝了第X杯」 → 累计为第X杯，本次增量 = X - 现有 cup_count
      B. 「喝了X杯水」 → 本次+1杯，忽略X中的数量（X 仅是修饰词）
         例：'喝了一杯水' = 喝了 1 杯 = +350ml
         例：'喝了两杯水' = 喝了 2 杯 = +700ml （X 是动作数量）
      C. 「第X杯」 （无"喝了"前缀）→ 当作累计X杯，增量 = X - cup_count
      D. 「X杯水」 （纯中文/数字）→ 本次=X杯，增量 = X
      E. 其他喝水意图 → 默认为 +1 杯（350ml）
    """
    if not is_water_message(text):
        return 0

    has_drunk = '喝了' in text
    current_cup_count = 0
    try:
        log = load_log()
        if log.get('today') == datetime.now(CST).strftime("%Y-%m-%d"):
            current_cup_count = log.get('cup_count', 0)
    except Exception:
        pass

    # A + C：包含「第X杯」 → 按累计语义
    ordinal_match = re.search(r'第([一二三四五六七八九十]+|[0-9]+)\s*杯', text)
    if ordinal_match:
        cn = ordinal_match.group(1)
        target_cups = CN_NUM_MAP.get(cn, 0) or int(cn) if cn.isdigit() else 0
        if target_cups > 0:
            delta = target_cups - current_cup_count
            return max(0, delta) * 350

    # B：包含「喝了X杯」 → 本次+1杯
    # 2026-06-14 Lee 拍板 B：含 override 关键词 → 走覆盖模式
    override_keywords_b = ['共', '漏', '补', '总共', '一共', '今天', '今早', '了']  # 「我喝了」= 事实陈述，可能是补录
    drank_match = re.search(r'喝了[一二三四五六七八九十两0-9]+\s*杯', text)
    if drank_match or has_drunk:
        # 抽 X 作为修饰（默认1）
        num_match = re.search(r'喝了([一二三四五六七八九十两0-9]+)\s*杯', text)
        cups = 1
        if num_match:
            cn = num_match.group(1)
            cups = CN_NUM_MAP.get(cn, 0) or (int(cn) if cn.isdigit() else 1) or 1
        # 覆盖语义检查：含「共/漏/补/今天」等 → 重置当日为 X 杯
        if any(kw in text for kw in override_keywords_b):
            return ('OVERRIDE', cups)
        return cups * 350

    # D：纯「X杯」 → 直接量（追加 X 杯）
    # 2026-06-14 Lee 拍板 B：增加「共/漏/补/了」覆盖语义关键词
    #   例：「我喝了两杯」「漏记了一杯」「补两杯」「今天共三杯」「今日 2 杯」 → 覆盖当日记录为 X 杯
    #   例：「再来一杯」「再喝一杯」 → 追加 1 杯（D 旧行为）
    override_keywords = ['共', '漏', '补', '总共', '一共', '今天', '今早', '了', '是', '已']
    is_override = any(kw in text for kw in override_keywords)

    direct_match = re.search(r'([一二三四五六七八九十两]+|\d+)\s*杯', text)
    if direct_match:
        cn = direct_match.group(1)
        cups = CN_NUM_MAP.get(cn, 0) or (int(cn) if cn.isdigit() else 0) or 0
        if cups > 0:
            if is_override:
                # 覆盖模式：返回特殊标记，让 save_log 识别并重置当日
                return ('OVERRIDE', cups)
            return cups * 350

    # E：其他喝水意图 → +1
    return 350

def is_duplicate_recent(data: dict, seconds: int = 120) -> bool:
    if not data.get('records'):
        return False
    last = data['records'][-1]
    try:
        last_time = datetime.strptime(last['time'], "%Y-%m-%d %H:%M")
        diff = (datetime.now(CST) - last_time).total_seconds()
        return diff < seconds and last.get('ml', 0) == 350
    except:
        return False

def generate_card():
    """生成喝水视觉化卡片,返回路径"""
    sys.path.insert(0, str(WORKSPACE / 'scripts'))
    from water_card_generator import load_data, generate_card as gen_card
    from pathlib import Path
    OUTPUT = Path('/tmp/water_card.png')
    data = load_data()
    gen_card(data, OUTPUT)
    return str(OUTPUT)


def push_to_feishu(message: str, card_path: str) -> dict:
    """
    异步推送文字+卡片到飞书「日常安排群」。
    背景：openclaw CLI 启动 ~50s（包含 plugin 扫描 + 飞书 connector 鉴权），
          同步推送会超时长任务超时。改用 nohup 异步推 + 日志文件。
    原理：写入待推送 payload → spawn 后台进程跑 openclaw message send
          → 推送结果写入日志。
    返回：{"ok": bool, "mode": "async", "log_path": str, "error": str|None}
    """
    if not Path(card_path).exists():
        return {"ok": False, "error": f"card_not_found:{card_path}", "mode": "async"}

    # 待推送队列：每条一个文件，文件名为时间戳。消费者是后台 single-flight worker。
    queue_dir = Path("/tmp/water_push_queue")
    queue_dir.mkdir(exist_ok=True)
    log_dir = Path("/tmp/water_push_logs")
    log_dir.mkdir(exist_ok=True)

    ts = datetime.now(CST).strftime("%Y%m%d_%H%M%S_%f")
    payload_file = queue_dir / f"push_{ts}.json"
    log_file = log_dir / f"push_{ts}.log"

    payload = {
        "channel": FEISHU_CHANNEL,
        "target": FEISHU_DAILY_CHAT_TARGET,
        "message": message,
        "card_path": str(card_path),
        "log_file": str(log_file),
        "enqueued_at": datetime.now(CST).isoformat(),
    }
    payload_file.write_text(json.dumps(payload, ensure_ascii=False))

    # spawn 一个 short-lived 进程等推送完成（这里用 nohup + disown，脱离父进程）
    worker_script = WORKSPACE / "scripts" / "water_push_worker.sh"
    try:
        subprocess.Popen(
            [str(worker_script), str(payload_file)],
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,  # 脱离父进程
        )
    except Exception as e:
        return {"ok": False, "error": f"spawn_failed:{e}", "mode": "async"}

    return {
        "ok": True,
        "mode": "async",
        "log_path": str(log_file),
        "payload_file": str(payload_file),
    }

def format_reply(data: dict) -> str:
    total = data['total_ml']
    goal = data['goal_ml']
    cups = data['cup_count']
    goal_cups = 6
    pct = min(100, int(total / goal * 100))
    filled = int(pct / 10)
    bar = '█' * filled + '░' * (10 - filled)
    cup_filled = total // 350
    cup_total = 6
    cup_bar = '💧' * cup_filled + '⚪' * (cup_total - cup_filled)
    emoji = '🎉' if total >= goal else '💧'
    return (
        f"{emoji} 喝水记录更新!\n\n"
        f"今日累计:{total}ml / {goal}ml\n"
        f"▕{bar}▏ {pct}%\n\n"
        f"{cup_bar}  {cups}杯 / {goal_cups}杯\n\n"
        f"{'🎉 今日2L目标达成!' if total >= goal else '继续加油,每天6杯 💪'}"
    )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="喝水追踪 → 记录 → 生成卡片 → 推送飞书（默认自动推送）"
    )
    parser.add_argument('text', nargs='+', help='喝水消息文本')
    parser.add_argument('--push', action='store_true', default=True,
                        help='推送到飞书日常安排群（默认 True）')
    parser.add_argument('--no-push', dest='push', action='store_false',
                        help='不推送，只在本地记录+生成卡片')
    parser.add_argument('--dry-run', action='store_true',
                        help='只记录不推送也不生成卡片（调试用）')
    parser.add_argument('--stdout-only', action='store_true',
                        help='保持旧行为：只打印文字+__CARD_PATH__，不推送（不推荐）')
    args = parser.parse_args()

    text = ' '.join(args.text)
    parse_result = process_messages(text)

    # 2026-06-14 Lee 拍板 B：OVERRIDE 模式（覆盖当日记录）
    is_override_mode = isinstance(parse_result, tuple) and parse_result[0] == 'OVERRIDE'
    if is_override_mode:
        override_cups = parse_result[1]
        ml = override_cups * 350
        print(f"解析结果:[OVERRIDE] {override_cups}杯 = {ml}ml（覆盖当日记录）")
    else:
        ml = parse_result
        print(f"解析结果:{ml}ml")

    if ml == 0:
        print("未识别到喝水量,忽略")
        sys.exit(0)

    log = load_log()
    today = datetime.now(CST).strftime("%Y-%m-%d")

    # 2026-06-15 Lee 拍板：启动自愈——log 有但 history 没的 records 自动回填
    bres = backfill_history_if_needed(log)
    if bres['missing_count'] > 0:
        print(f"[backfill] 自愈补录 {bres['missing_count']}/{bres['checked']} 条 → {HISTORY_FILE}")

    if log.get('today') != today:
        log = {"today": today, "total_ml": 0, "cup_count": 0,
               "goal_ml": 2000, "cup_ml": 350, "records": []}

    if not is_override_mode and is_duplicate_recent(log, seconds=120):
        print("⚠️ 检测到重复记录(2分钟内相同杯数),已忽略")
        print(format_reply(log))
        sys.exit(0)

    # 预计算累积值（不保存，用于打印）
    projected = dict(log)
    if is_override_mode:
        # 覆盖模式：重置 records 为单条 + 注上「共/补/漏」语义
        now_str = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
        projected['total_ml'] = ml
        projected['cup_count'] = override_cups
        projected['records'] = [{
            "time": now_str,
            "ml": ml,
            "note": f"覆盖补录 {override_cups} 杯（Lee 16:42 拍板 B 脚本改造）"
        }]
    else:
        projected['total_ml'] = log['total_ml'] + ml
        projected['cup_count'] = log['cup_count'] + 1
        projected['records'] = log['records'] + [{
            "time": datetime.now(CST).strftime("%Y-%m-%d %H:%M"),
            "ml": ml,
            "note": f"第{projected['cup_count']}杯"
        }]

    reply_text = format_reply(projected)

    # dry-run：只打印累积预览，不保存、不生成卡片、不推送
    if args.dry_run:
        print(reply_text)
        print(f"[dry-run] 不会保存记录、不生成卡片、不推送飞书")
        sys.exit(0)

    # 旧行为兼容：--stdout-only 时不推送、只输出 __CARD_PATH__ 供调用方发
    if args.stdout_only:
        # stdout-only 模式下要真保存（跟旧版一致）
        log['total_ml'] = projected['total_ml']
        log['cup_count'] = projected['cup_count']
        log['records'] = projected['records']
        save_log(log)
        # 2026-06-14 Lee 拍 A+A：追加历史
        hres = append_history(log, 'override' if is_override_mode else 'append', override_cups if is_override_mode else 0)
        if hres['ok']:
            print(f"[history] appended → {hres['path']}")
        card_path = generate_card()
        print(reply_text)
        print(f"__CARD_PATH__:{card_path}")
        sys.exit(0)

    # 正常路径：保存记录 + 生成卡片 + 异步推送
    save_log(projected)
    # 2026-06-14 Lee 拍 A+A：追加历史
    hres = append_history(projected, 'override' if is_override_mode else 'append', override_cups if is_override_mode else 0)
    if hres['ok']:
        print(f"[history] appended → {hres['path']}")
    else:
        print(f"[history] ⚠️ append failed: {hres.get('error')}")

    # 默认流程：生成卡片 + 推送飞书（文字+图片同发）
    card_path = generate_card()
    print(f"卡片生成:{card_path}")
    print(reply_text)

    if not args.push:
        print("[--no-push] 跳过飞书推送，__CARD_PATH__ 已生成")
        print(f"__CARD_PATH__:{card_path}")
        sys.exit(0)

    # === 实际推送（必走） ===
    print(f"推送中 → 飞书日常安排群 {FEISHU_DAILY_CHAT_ID} ...")
    push_result = push_to_feishu(reply_text, card_path)
    if push_result["ok"]:
        print(f"✅ 推送已加入队列 (异步):log={push_result.get('log_path')}")
        print(f"   payload={push_result.get('payload_file')}")
        print(f"   target_chat={FEISHU_DAILY_CHAT_ID}")
    else:
        print(f"❌ 推送失败:{push_result.get('error')}", file=sys.stderr)
        print(f"   卡片路径保留:{card_path}", file=sys.stderr)
        sys.exit(1)
