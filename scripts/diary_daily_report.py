#!/usr/bin/env python3
"""
每日日记生成 — 微信渠道版
22:30 cron 运行:
1. 读取日记/raw/微信-YYYY-MM-DD.md（微信归档消息）
2. 生成结构化日记
3. 保存 Obsidian + Git push
4. 飞书摘要推送
"""

import os, sys, json, subprocess, fcntl, re, hashlib
import urllib.request, urllib.error
from datetime import datetime
from _timezone import CST
from pathlib import Path

# 加载 .env 环境变量
ENV_FILE = Path(os.path.expanduser("~/.openclaw/.env"))
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

# ============================================================
# 配置
# ============================================================
WORKSPACE = Path("~/.openclaw/workspace").expanduser()
OBSIDIAN_DIARY = Path(os.path.expanduser("~/Obsidian/日记"))
LOCAL_RAW = Path(os.path.expanduser("~/Obsidian/日记/raw"))  # 2026-05-25: 优先读 Obsidian raw（唯一真相源）
OBSIDIAN_RAW = Path(os.path.expanduser("~/Obsidian/日记/raw"))
FEISHU_GROUP_ID = "oc_ad39a8e943103c2164f1d0d9de503da5"
LOG_FILE = "/tmp/diary_daily.log"
LOCK_FILE = "/tmp/diary_daily.lock"
FLAG_DIR = WORKSPACE / "diary" / "flags"

# ============================================================
# 工具函数
# ============================================================
def log(msg):
    print(msg, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(f"{datetime.now(CST).strftime('%H:%M:%S ')}{msg}\n")

def ensure_dirs():
    for d in [LOCAL_RAW, OBSIDIAN_RAW, OBSIDIAN_DIARY, FLAG_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def strip_marker(text, marker="~"):
    return text.strip(marker).strip()

def msg_hash(msg):
    return hashlib.sha256(msg.encode('utf-8')).hexdigest()[:16]

# ============================================================
# 稳定性：每日只运行一次 + 并发锁
# ============================================================
def check_already_run_today(target_date=None):
    # 2026-06-04: 改用参数传入日期（兼容 DIARY_DATE 补跑）
    check_date = target_date or datetime.now(CST).strftime("%Y-%m-%d")
    flag_file = FLAG_DIR / f"ran_{check_date}.flag"
    if flag_file.exists():
        log(f"⏭️ 今日({check_date})已运行过，跳过")
        return True
    return False

def mark_run_today(target_date=None):
    # 2026-06-04: 改用参数传入日期
    mark_date = target_date or datetime.now(CST).strftime("%Y-%m-%d")
    flag_file = FLAG_DIR / f"ran_{mark_date}.flag"
    flag_file.write_text(datetime.now(CST).isoformat())
    log(f"✅ 标记今日已运行: {flag_file}")

def acquire_lock():
    lock_fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        log(f"⏭️ 另一进程正在执行，跳过")
        sys.exit(0)

# ============================================================
# 微信消息读取（从归档 raw 文件）
# ============================================================
def load_weixin_messages(date_str):
    """从日记/raw/微信-YYYY-MM-DD.md 读取消息列表"""
    local_file = LOCAL_RAW / f"微信-{date_str}.md"
    
    if not local_file.exists():
        log(f"⏭️ 微信归档文件不存在: {local_file}")
        return []
    
    content = local_file.read_text(encoding='utf-8')
    
    # 解析所有条目：## HH:MM [sender]\ncontent
    entries = re.split(r'\n(?=## \d{2}:\d{2} \[)', content)
    
    messages = []
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        
        entry = strip_marker(entry, "~")
        
        time_match = re.match(r'## (\d{2}:\d{2}) \[([^\]]+)\]', entry)
        if not time_match:
            continue
        
        time_str = time_match.group(1)
        sender = time_match.group(2)
        
        body_start = entry.find(']\n') + 2
        body = entry[body_start:].strip()
        
        if not body or len(body) < 3:
            continue
        
        if body.startswith('{') and ('"template"' in body or '"title"' in body):
            continue
        
        full_entry = f"## {time_str} [{sender}]\n{body}"
        messages.append(full_entry)
    
    log(f"📥 从微信归档读到 {len(messages)} 条消息")
    return messages

# ============================================================
# 内容保护
# ============================================================
PLACEHOLDER_PATTERNS = [
    "记录今日情绪状态（高/中/低）及触发事件",
    "从今天的经历中提取的认知、教训或方法论",
    "对今天影响最大的 1-3 件事",
    "明天最想要完成的一件具体小事",
    "当天学习/认知/方法的新认知",
    "当天可以做得更好的地方",
    "具体可落地的下一步动作",
    "（无记录）", "无记录",
]

def is_valid_message(body):
    if not body or len(body.strip()) < 3:
        return False
    if body.startswith('{') and ('"template"' in body or '"title"' in body or '"content"' in body or '"divider_text"' in body):
        return False
    if body.startswith('["'):
        return False
    if body.startswith('> '):
        return False
    return True

def is_meaningful_content(content):
    if not content:
        return False
    meaningful_lines = []
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith(('#', '---', '_', '>')):
            continue
        if any(p in line for p in PLACEHOLDER_PATTERNS):
            continue
        stripped = line.lstrip('-•*').strip()
        if len(stripped) > 3:
            meaningful_lines.append(line)
    return len(meaningful_lines) >= 2

# ============================================================
# 日记生成
# ============================================================
EVENT_KEYWORDS = [
    '完成', '做了', '搞定', '成功', '通过', '提交', '交付',
    '上线', '发布', '谈成', '签', '收到', '买到', '解决',
    '开会', '汇报', '演示', '安装', '调试', '测试', '跑通',
    '写完', '学完', '看完', '吃', '喝', '去', '回', '买',
]
THOUGHT_KEYWORDS = [
    '觉得', '在想', '思考', '感觉', '应该', '可能', '也许',
    '为什么', '怎么', '要不要', '是不是', '有点', '似乎',
    '好奇', '担心', '希望', '想要', '后悔', '纠结',
]

def classify_message(msg):
    event_score = sum(1 for kw in EVENT_KEYWORDS if kw in msg)
    thought_score = sum(1 for kw in THOUGHT_KEYWORDS if kw in msg)
    return "thought" if thought_score > event_score else "event"

# ============================================================
# DeepSeek API 调用
# ============================================================
def call_deepseek_raw(prompt: str, system: str = "") -> str:
    """调用 DeepSeek Flash 填充日记内容（不走 OpenClaw）"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        log("⚠️ DEEPSEEK_API_KEY 未配置，跳过 DeepSeek 填充")
        return ""
    
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": "deepseek-v4-pro",
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.3
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), 
                                     headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        log(f"⚠️ DeepSeek API HTTP 错误: {e.code} {e.reason}")
        return ""
    except Exception as e:
        log(f"⚠️ DeepSeek API 调用异常: {e}")
        return ""

def build_diary_prompt(date_str: str, raw_content: str) -> tuple:
    """构建发给 DeepSeek 的 system prompt 和 user prompt，返回 (system, user)"""
    date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y年%m月%d日")
    
    system_prompt = f"""你是一个日记整理助手，帮用户把零散的日记碎片整理成结构化日记。

# 重要原则
1. 语言要简洁、自然，像人写日记，不堆砌
2. 不要用机器语言，要用手写日记的自然风格
3. 不要重复标题，不要写空话套话

# 输出要求：
1. 按模板格式输出，从「## 情绪曲线」开始写，直接写内容，不要写「日记模板」标题
2. 每个栏目都要填写实在内容
3. 生成内容必须基于原始记录，不要自行发挥或补充未记录的信息
4. 如某栏目确实无内容可写，写「（当日未记录）」而非自行编造
5. 生成完成后，在「今日我的一句话」之后，增加「─── 原始记录 ───」区块，原文引用当日 raw 文件全部内容，不删改，不润色，只照抄"""

    user_prompt = f"""原始日记记录：
{raw_content}

---
按以下模板从「## 今天发生了什么」开始写日记：

## 今天发生了什么
（当日概要，bullet list，1-3条，说清楚即可）

## 我在想什么
（情绪背后的念头、内心对话，一句话也行）

## 情绪曲线
今日情绪：**中**
（从早到晚捕捉情绪波动，描述关键转折点，不打分）

## 值得沉淀的洞察
（你从中学到的一个规律/模式/真理，用自己的话写）

## 关键事件
1. （今天真正触动你的1-3件事，不记流水账）

## 明天一件小事
> （结合洞察，定一个具体动作，小到不可能失败）

---

## 每日复盘

### 今日收获
- （从今天学到的一件事）

### 待改进
- （一个温柔的改进点，不自责）

### 明日行动
- （具体可执行的下一步）

---

今日我的一句话：
─── 原始记录 ───
（原文引用当日微信日记 raw 文件全部内容，不删改，不润色，只照抄）"""

    return system_prompt, user_prompt

def generate_structured_diary(date_str, messages, raw_content=""):
    """先用 DeepSeek 填充，失败则 fallback 到本地简单分类"""
    date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y年%m月%d日")

    # 清理 raw_content 里的 ~ 标记
    raw_clean = raw_content.strip().strip('~').strip()
    
    # 用 DeepSeek 填充
    if raw_clean:
        system_prompt, user_prompt = build_diary_prompt(date_str, raw_clean)
        log(f"🤖 调用 DeepSeek 填充日记...")
        ds_result = call_deepseek_raw(user_prompt, system_prompt)
        if ds_result:
            log(f"✅ DeepSeek 填充成功 ({len(ds_result)} 字符)")
            # 追加 header 和 footer
            return f"# 📔 {date_display} 日记\n\n{ds_result}\n\n_由 OpenClaw + DeepSeek 自动生成 | {date_str}_"
        else:
            log(f"⚠️ DeepSeek 填充失败，fallback 到本地分类")
    
    # Fallback：本地简单分类（原有逻辑）
    events, thoughts = [], []
    for msg in messages:
        msg_clean = strip_marker(msg, "~").strip()
        day_num = date_str.split('-')[2]
        msg_clean = msg_clean.replace(f"## {day_num}:", "").strip()
        if not msg_clean:
            continue
        if '\n' in msg_clean:
            body = msg_clean.split('\n', 1)[1]
        else:
            body = msg_clean
        body = strip_marker(body, "~").strip()
        if not is_valid_message(body):
            continue
        if not body:
            continue
        cls = classify_message(body)
        if cls == "event":
            events.append(body)
        else:
            thoughts.append(body)

    events = list(dict.fromkeys(events))[:10]
    thoughts = list(dict.fromkeys(thoughts))[:5]

    events_text = chr(10).join(f"1. {m}" for m in events) if events else "1. （当日未记录）"
    thoughts_text = chr(10).join(f"- {m}" for m in thoughts) if thoughts else "- （当日未记录）"

    raw_block = f"─── 原始记录 ───\n{raw_clean}" if raw_clean else ""

    return f"""# 📔 {date_display} 日记

## 今天发生了什么
{events_text}

## 我在想什么
（情绪背后的念头、内心对话，一句话也行）
{thoughts_text}

## 情绪曲线
今日情绪：**中**
（从早到晚捕捉情绪波动，描述关键转折点，不打分）

## 值得沉淀的洞察
（你从中学到的一个规律/模式/真理，用自己的话写）
- （当日未记录）

## 关键事件
{events_text}

## 明天一件小事
> （结合洞察，定一个具体动作，小到不可能失败）

---

## 每日复盘

### 今日收获
- （从今天学到的一件事）

### 待改进
- （一个温柔的改进点，不自责）

### 明日行动
- （具体可执行的下一步）

---

今日我的一句话：
{raw_block}

_由 OpenClaw 自动生成（本地分类）| {date_str}_
"""

# ============================================================
# Obsidian 操作
# ============================================================
def get_diary_save_path(date_str):
    year, month = date_str.split('-')[0], date_str.split('-')[1]
    dir_path = OBSIDIAN_DIARY / year / month
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path / f"{date_str}.md"

def save_diary_to_obsidian(diary_content, date_str):
    path = get_diary_save_path(date_str)
    path.write_text(diary_content, encoding='utf-8')
    log(f"✅ 日记已写入 Obsidian（强制覆盖）: {path}")
    return path

def push_obsidian_git(date_str):
    diary_path = get_diary_save_path(date_str)
    if not diary_path.exists():
        return
    try:
        subprocess.run(["git", "-C", str(OBSIDIAN_DIARY), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(OBSIDIAN_DIARY), "commit", "-m", f"日记自动同步 {date_str}"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(OBSIDIAN_DIARY), "push", "--force"], check=True, capture_output=True)
        log(f"✅ Obsidian 已 Git push")
    except subprocess.CalledProcessError as e:
        log(f"⚠️ Git push 失败: {e}")

# ============================================================
# 飞书推送
# ============================================================
def push_to_feishu(date_str):
    # 2026-06-04: 补跑历史日期时支持静默（不推飞书）
    if os.environ.get("DIARY_SKIP_FEISHU") == "1":
        log(f"⏭️ DIARY_SKIP_FEISHU=1 跳过飞书推送")
        return
    msg = f"📔 {date_str} 今日日记\n────────────────────\n完整日记已同步到 Obsidian 📓"
    try:
        result = subprocess.run(
            ["openclaw", "message", "send",
             "--channel", "feishu",
             "--target", FEISHU_GROUP_ID,
             "--message", msg],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            log(f"✅ 飞书推送成功")
        else:
            log(f"⚠️ 飞书推送失败: {result.stderr}")
    except Exception as e:
        log(f"⚠️ 飞书推送异常: {e}")

# ============================================================
# 主流程
# ============================================================
def main():
    # 2026-06-04: 支持 DIARY_DATE 环境变量用于补跑历史日期（默认今天）
    today = os.environ.get("DIARY_DATE") or datetime.now(CST).strftime("%Y-%m-%d")
    log(f"=== 日记生成开始 {today} ===")

    ensure_dirs()
    acquire_lock()

    if check_already_run_today(today):
        log(f"=== 日记生成跳过（今日已运行）===")
        return

    messages = load_weixin_messages(today)
    raw_content = ""
    local_file = LOCAL_RAW / f"微信-{today}.md"
    if local_file.exists():
        raw_content = local_file.read_text(encoding='utf-8')

    diary = generate_structured_diary(today, messages, raw_content)

    save_diary_to_obsidian(diary, today)

    push_obsidian_git(today)

    push_to_feishu(today)

    mark_run_today(today)
    log(f"=== 日记生成完成 ===")

if __name__ == "__main__":
    main()
