#!/usr/bin/env python3
"""
🦞 小龙虾每日学习日志生成器 v3
同时更新 index.html 日期导航 + 新日志内容
"""
import os, sys, json, base64, urllib.request, urllib.error, re, html
from datetime import datetime, timedelta
from _timezone import CST
from pathlib import Path

# ── 环境变量 ──────────────────────────────────────
ENV_FILE = Path(os.path.expanduser("~/.openclaw/.env"))
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "leeiceice/OpenClaw-Diary"
WORKSPACE = Path("~/.openclaw/workspace").expanduser()
MEMORY_DIR = WORKSPACE / "memory"
PROACTIVITY_DIR = WORKSPACE / "proactivity"

HEADERS = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}

# ── GitHub API ──────────────────────────────────────
def api(path, method="GET", data=None):
    url = f"https://api.github.com/{path}"
    req = urllib.request.Request(url, headers=HEADERS, method=method)
    if data:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "msg": e.read().decode()}

# ── 读取 index.html 并添加新日期按钮 ───────────────────
def add_date_to_index_html(new_date, current_html):
    """在 index.html 中添加新的日期按钮"""
    # 新的按钮 HTML
    new_button = f'''<button onclick="showDate('{new_date}')">📅 {new_date}</button>'''
    
    # 在 date-tabs 的 </div> 前插入（找到第一个 button 后面）
    if f"showDate('{new_date}')" in current_html:
        return current_html  # 已经存在
    
    # 找到 </div> class="date-tabs" 并插入新按钮
    pattern = r'(<div class="date-tabs">.*?)(</div>)'
    match = re.search(pattern, current_html, re.DOTALL)
    if match:
        # 在第一个 button 后插入新按钮
        insert_point = match.end(1)
        current_html = current_html[:insert_point] + '\n    ' + new_button + current_html[insert_point:]
    
    return current_html

# ── 日志内容生成（调用 MiniMax）───────────────────────────
def call_minimax(prompt, max_tokens=400):
    key = os.environ.get("MINIMAX_API_KEY", "")
    if not key:
        return None, "MINIMAX_API_KEY not found"
    
    try:
        req = urllib.request.Request(
            "https://api.minimaxi.com/anthropic/v1/messages",
            data=json.dumps({
                "model": "MiniMax-M2.7",
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": "你是小龙虾的每日学习日志助手，用简洁自然的中文写作，像手写日记一样，200-400字，不要标题不要列表。"},
                    {"role": "user", "content": prompt}
                ]
            }).encode(),
            headers={"x-api-key": key, "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            if result.get("type") != "message":
                return None, f"Unexpected type: {result.get('type')}"
            for c in result.get("content", []):
                if c.get("type") == "text":
                    return c["text"].strip(), None
            return None, "No text in response"
    except Exception as e:
        return None, str(e)

# ── 数据源读取 ──────────────────────────────────────
def load_today_memory():
    today = datetime.now(CST).strftime("%Y-%m-%d")
    path = MEMORY_DIR / f"{today}.md"
    if not path.exists():
        # 用昨天的
        for i in range(1, 7):
            path = MEMORY_DIR / ((datetime.now(CST) - timedelta(days=i)).strftime("%Y-%m-%d") + ".md")
            if path.exists():
                break
    if path.exists():
        lines = path.read_text(encoding="utf-8").split("\n")
        in_frontmatter = False
        meaningful = []
        for line in lines:
            if line.strip() == "---":
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter:
                continue
            if line.startswith("# ") or line.startswith("<!--") or line.startswith("***"):
                continue
            if line.strip():
                meaningful.append(line.strip())
        return "\n".join(meaningful[:60])
    return ""

def load_proactivity():
    log_path = PROACTIVITY_DIR / "log.md"
    if not log_path.exists():
        return ""
    lines = log_path.read_text(encoding="utf-8").split("\n")
    today = datetime.now(CST).strftime("%Y-%m-%d")
    in_today = False
    entries = []
    for line in lines:
        if line.strip() == f"## {today}":
            in_today = True
            continue
        if in_today and line.startswith("## "):
            break
        if in_today and line.strip():
            entries.append(line.strip())
    return "\n".join(entries[:8])

def get_system_status():
    status = []
    try:
        result = __import__('subprocess').run(
            ["openclaw", "cron", "list"], capture_output=True, text=True, timeout=10
        )
        cron_text = result.stdout
        error_count = cron_text.count('error')
        idle_count = cron_text.count('idle')
        status.append(f"Cron 异常: {error_count+idle_count}" if error_count+idle_count > 0 else "Cron 正常 ✅")
    except:
        status.append("Cron: 查询失败")
    
    water = WORKSPACE / "data" / "water-log.json"
    if water.exists():
        try:
            data = json.loads(water.read_text())
            if data.get("today") == datetime.now(CST).strftime("%Y-%m-%d"):
                status.append(f"喝水: {data.get('cup_count',0)}杯")
        except:
            pass
    
    return " | ".join(status) if status else ""

# ── GitHub Stars ────────────────────────────────────
def get_stars():
    repos = ["openclaw/openclaw", "YAI-Lab/OpenClaw-Diary", "leeiceice/xiaolongxia-openclaw"]
    result = []
    for repo in repos:
        try:
            data = api(f"repos/{repo}")
            if "stargazers_count" in data:
                result.append(f"{repo.split('/')[1]}: ⭐{data['stargazers_count']}")
        except:
            pass
    return " | ".join(result)

# ── 推送 ─────────────────────────────────────────
def push_file(path, content, message):
    try:
        existing = api(f"repos/{REPO}/contents/{path}")
        sha = existing.get("sha")
    except:
        sha = None
    
    data = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode(),
    }
    if sha:
        data["sha"] = sha
    
    result = api(f"repos/{REPO}/contents/{path}", method="PUT", data=data)
    if "error" in result:
        return False, f"{result['error']}: {result.get('msg','')}"
    return True, result.get("content", {}).get("html_url", "")

# ── 主流程 ─────────────────────────────────────────
def main():
    today = datetime.now(CST).strftime("%Y-%m-%d")
    date_cn = datetime.now(CST).strftime("%Y年%m月%d日")
    weekday_cn = ["周一","周二","周三","周四","周五","周六","周日"][datetime.now(CST).weekday()]

    # 构建 prompt
    memory = load_today_memory()
    proactivity = load_proactivity()
    system = get_system_status()
    stars = get_stars()

    prompt = f"""日期：{date_cn} {weekday_cn}（{today}）

今日小龙虾的主要事件和记录：
{memory}

今日主动行为日志：
{proactivity}

系统状态：{system}

相关 Stars：{stars}

请用简洁自然的中文写一段200-300字的学习日记，像手写一样，包含：
1) 今天主要做了什么
2) 学到了什么
3) 明天想做的一件具体小事
不要标题，不要列表，自然段落。"""

    content_text, err = call_deepseek_pro(prompt)
    if err:
        print(f"❌ 生成失败: {err}")
        sys.exit(1)
    
    if not content_text:
        print("⚠️ 生成内容为空，跳过")
        sys.exit(0)

    # HTML 转义防止特殊字符（: 等）破坏结构
    content_escaped = html.escape(content_text)

    # 组装日志条目（HTML 格式）
    entry_html = f'''    <div class="screen" id="screen-{today}">
        <div class="entry">
            <div class="entry-bar">
                <span class="entry-filename">~/openclaw-diary/entries/{today}.md</span>
            </div>
            <div class="entry-body">
                <div class="quote-box">
                    <div class="quote-title">📅 {date_cn} {weekday_cn}</div>
                    <p>{content_escaped}</p>
                </div>
            </div>
        </div>
    </div>'''

    # 推送日志条目
    entry_ok, entry_url = push_file(
        f"openclaw-diary/entries/{today}.md",
        f"# 🦞 小龙虾学习日记 — {date_cn} {weekday_cn}\n\n{content_text}\n\n---\n_由 OpenClaw 自动生成 | {today}_",
        f"📝 每日学习日志 {today}"
    )
    print(f"{'✅' if entry_ok else '❌'} 日志: {entry_url}" if entry_ok else f"❌ 日志: {entry_url}")

    # 更新 index.html
    index_ok, index_url = update_index_add_date(today)
    print(f"{'✅' if index_ok else '❌'} 导航: {index_url}" if index_ok else f"❌ 导航: {index_url}")

    if not entry_ok and not index_ok:
        sys.exit(1)

def update_index_add_date(today):
    """更新 index.html 添加新日期"""
    # 读取 index.html
    index_data = api(f"repos/{REPO}/contents/index.html")
    if "error" in index_data:
        return False, f"读取 index.html 失败: {index_data['error']}"
    
    html_content = base64.b64decode(index_data["content"]).decode("utf-8")
    sha = index_data["sha"]

    # 检查是否已有此日期
    if f"showDate('{today}')" in html_content:
        return True, "日期已存在，跳过更新"

    # 添加日期按钮（在 date-tabs 最后插入）
    new_button = f'\n        <button onclick="showDate(\'{today}\')">📅 {today}</button>'
    
    # 找到 </div> class="date-tabs" 的位置，在最后一个 button 后插入
    # 方法：在 </div> 前最近的一个 </button> 后插入
    pattern = r'(</button>\s*)(</div>\s*<!-- Date Navigation -->)'
    replacement = rf'\1{new_button}\2'
    new_html = re.sub(pattern, replacement, html_content)
    
    # 同时在 body 末尾添加 entry
    new_entry = f'\n\n<!-- Entry {today} -->\n    <div class="screen" id="screen-{today}">\n        <div class="entry">\n            <div class="entry-bar">\n                <span class="entry-filename">~/openclaw-diary/entries/{today}.md</span>\n            </div>\n            <div class="entry-body">\n                <div class="quote-box">\n                    <div class="quote-title">📅 {today}</div>\n                    <p>（查看完整日志）</p>\n                </div>\n            </div>\n        </div>\n    </div>'
    
    # 在 </body> 前插入
    new_html = new_html.replace('</body>', new_entry + '\n</body>')

    data = {
        "message": f"chore: 添加 {today} 日期导航",
        "content": base64.b64encode(new_html.encode("utf-8")).decode(),
        "sha": sha
    }
    result = api(f"repos/{REPO}/contents/index.html", method="PUT", data=data)
    if "error" in result:
        return False, f"更新 index.html 失败: {result['error']}"
    return True, result.get("content", {}).get("html_url", "")



def call_deepseek_pro(prompt, max_tokens=500):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return None, "DEEPSEEK_API_KEY not found"
    try:
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=json.dumps({
                "model": "deepseek-v4-pro",
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": "你是小龙虾的每日学习日志助手，用简洁自然的中文写作，像手写日记一样，200-400字，不要标题不要列表。"},
                    {"role": "user", "content": prompt}
                ]
            }).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    main()