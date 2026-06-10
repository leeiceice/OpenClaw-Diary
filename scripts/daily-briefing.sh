#!/bin/bash
# 每日新闻简报生成脚本 v13（跨天去重版）
# 6大板块：时政 / 金融经济 / 科技 / 国际 / 社会 / 锐推
# 新增：跨3天去重 + 相似度阈值50% + 持久化已推标题

CACHE_DIR="~/.openclaw/workspace/.briefing_cache"
TRACK_FILE="$CACHE_DIR/pushed_titles.jsonl"
TMPDIR=$(mktemp -d /tmp/briefing_XXXXXX)

[ ! -d "$CACHE_DIR" ] && mkdir -p "$CACHE_DIR"
[ ! -f "$TRACK_FILE" ] && echo "" > "$TRACK_FILE"

cleanup() {
    rm -rf "$TMPDIR"
}
trap cleanup EXIT

echo "📰 开始生成每日简报 v13..."

# ============ 1. 获取福州天气 ============
echo "🌤️  获取福州天气..."

WEATHER_INFO=$(curl -s --max-time 8 "wttr.in/Fuzhou?format=j1" 2>/dev/null | python3 -c "
import sys, json

try:
    d = json.load(sys.stdin)
    cc = d['current_condition'][0]
    today = d['weather'][0]
    tomorrow = d['weather'][1] if len(d['weather']) > 1 else today
    
    weather_map = {
        'Sunny': '☀️ 晴天', 'Clear': '☀️ 晴天', 'Partly cloudy': '⛅ 多云', 'Cloudy': '☁️ 阴天',
        'Overcast': '☁️ 阴天', 'Mist': '🌫️ 薄雾', 'Fog': '🌫️ 大雾', 'Light rain': '🌧️ 小雨',
        'Moderate rain': '🌧️ 中雨', 'Heavy rain': '🌧️ 大雨', 'Patchy rain nearby': '🌦️ 局部小雨',
        'Light drizzle': '🌧️ 小雨', 'Thunderstorm': '⛈️ 雷暴', 'Snow': '❄️ 雪', 'Light snow': '🌨️ 小雪',
        'Moderate snow': '🌨️ 中雪', 'Hot': '🔥 炎热', 'Warm': '🌡️ 温暖', 'Cool': '🍃 凉爽', 'Cold': '🥶 寒冷',
        'Breezy': '🌬️ 微风'
    }
    
    def get_cn_weather(desc):
        for k, v in weather_map.items():
            if k.lower() in desc.lower():
                return v
        return desc
    
    cur_w = get_cn_weather(cc['weatherDesc'][0]['value'])
    today_w = get_cn_weather(today['hourly'][4]['weatherDesc'][0]['value'])
    tomorrow_w = get_cn_weather(tomorrow['hourly'][4]['weatherDesc'][0]['value'])
    
    tmp = int(cc['temp_C'])
    emoji = '🌤️'
    if tmp >= 32: emoji = '🔥'
    elif tmp >= 28: emoji = '☀️'
    elif tmp >= 20: emoji = '🌤️'
    elif tmp >= 10: emoji = '🍃'
    else: emoji = '🥶'
    
    print(f\"{emoji} 福州当前：{cc['temp_C']}°C，{cur_w}，体感 {cc['FeelsLikeC']}°C\")
    print(f\"💧 湿度：{cc['humidity']}% | 🌬️ 风速：{cc['windspeedKmph']}km/h\")
    print(f\"📅 今天：{today['maxtempC']}°C / {today['mintempC']}°C，{today_w}\")
    print(f\"📅 明天：{tomorrow['maxtempC']}°C / {tomorrow['mintempC']}°C，{tomorrow_w}\")
except:
    print('⚠️ 天气获取失败')
" 2>/dev/null)
[ -z "$WEATHER_INFO" ] && WEATHER_INFO="⚠️ 天气获取失败"

# ============ 2. 并行获取所有新闻源（6个板块） ============
echo "📡 并行获取新闻（最多8秒超时）..."

curl -s -L --max-time 8 "https://news.sina.com.cn/" -o "$TMPDIR/politics.html" &
curl -s -L --max-time 8 "https://finance.sina.com.cn/" -o "$TMPDIR/finance.html" &
curl -s -L --max-time 8 "https://tech.sina.com.cn/" -o "$TMPDIR/tech.html" &
curl -s -L --max-time 8 "https://news.sina.com.cn/world/" -o "$TMPDIR/world.html" &
curl -s -L --max-time 8 "https://36kr.com/feed" -o "$TMPDIR/36kr_rss.xml" &
curl -s -L --max-time 8 "https://www.tmtpost.com/rss" -o "$TMPDIR/tmtpost_rss.xml" &
curl -s -L --max-time 8 "https://api.zhihu.com/topstory/hot-lists/total?limit=10" -o "$TMPDIR/zhihu_api.json" -A "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)" &
curl -s -L --max-time 8 "https://www.eeo.com.cn/rss.xml" -o "$TMPDIR/eeo_rss.xml" &
wait

# ============ 3. 加载近3天已推标题（跨天去重核心） ============
load_pushed_titles() {
    python3 - "$TRACK_FILE" << 'PYEOF'
import sys, json
from datetime import datetime, timedelta
import sys as _sys
_sys.path.insert(0, "/root/.openclaw/workspace/scripts")
from _timezone import now_cst

track_file = sys.argv[1]
cutoff = (now_cst() - timedelta(days=3)).strftime("%Y-%m-%d")

pushed = []
try:
    with open(track_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                date = obj.get("date", "")
                # 只保留近3天
                if date >= cutoff:
                    pushed.extend(obj.get("titles", []))
            except:
                pass
except:
    pass

# 输出扁平列表
for t in pushed:
    print(t)
PYEOF
}

PUSHED_TITLES=$(load_pushed_titles)
PUSHED_COUNT=$(echo "$PUSHED_TITLES" | grep -c "." 2>/dev/null || echo 0)
echo "📋 近3天已推：${PUSHED_COUNT}条（将用于跨天去重）"

# ============ 4. 通用解析函数 ============
parse_to_file() {
    local file=$1
    local outfile=$2
    local limit=${3:-8}
    
    python3 - "$file" "$outfile" "$limit" "$PUSHED_TITLES" << 'PYEOF'
import sys, re, json

file, outfile, limit = sys.argv[1], sys.argv[2], int(sys.argv[3])
pushed_titles = [t.strip() for t in sys.argv[4].split("\n") if t.strip()]

def chinese_words(text, n=2):
    words = set()
    for i in range(len(text) - n + 1):
        chunk = text[i:i+n]
        if re.search(r'[\u4e00-\u9fff]', chunk):
            words.add(chunk)
    return words

def is_similar_to_pushed(title, threshold=0.5):
    """对比近3天已推标题，相似度>=50%视为重复"""
    tw = chinese_words(title)
    if not tw:
        return False
    for p in pushed_titles:
        pw = chinese_words(p)
        if not pw:
            continue
        # 重叠词 / 最大词数 >= threshold
        overlap = len(tw & pw)
        max_w = max(len(tw), len(pw))
        if max_w > 0 and overlap / max_w >= threshold:
            return True
    return False

def is_within_pushed(title):
    """精确匹配已推标题（去重池外额外保险）"""
    return title in pushed_titles

try:
    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
except:
    json.dump([], open(outfile, 'w'), ensure_ascii=False)
    sys.exit(0)

content = re.sub(r'&[a-z]+;', ' ', content)
content = re.sub(r'&#x[0-9a-f]+;?', ' ', content)

pattern = r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>([^<]{15,80})</a>'
matches = re.findall(pattern, content)
seen = set()
results = []

skip_words = ['专题', '视频', '图集', '直播', '下载', '首页', '导航', '排行榜',
              'Copyright', 'javascript', '返回', '展开', '收起', 'app', '客户端',
              '世界电信', '世界互联网', 'Google开发者']

stale_patterns = ['去年', '前年', '上月', '上周', '昔日', '历年', '往期', '回顾',
                  '2024年', '2023年', '2022年', '2021年', '2020年', '一文读懂',
                  '收藏', '关注', '往期回顾', '历年真题', '2025年春节', '2024年春节']

for url, title in matches:
    title = re.sub(r'<[^>]+>', '', title).strip()
    title = re.sub(r'\s+', ' ', title)
    
    if len(title) < 12 or len(title) > 68:
        continue
    if any(w in title for w in skip_words):
        continue
    if any(p in title for p in stale_patterns):
        continue
    if 'sina.com.cn' not in url:
        continue
    if title in seen:
        continue
    if is_within_pushed(title):
        continue
    if is_similar_to_pushed(title, threshold=0.5):
        continue
    
    seen.add(title)
    results.append(title)
    if len(results) >= limit:
        break

json.dump(results, open(outfile, 'w'), ensure_ascii=False)
PYEOF
}

# ============ 5. 解析各板块 ============
echo "🏛️ 解析时政..."
parse_to_file "$TMPDIR/politics.html" "$TMPDIR/politics.json" 8

echo "💰 解析金融经济..."
parse_to_file "$TMPDIR/finance.html" "$TMPDIR/finance.json" 8

echo "🌍 解析国际..."
parse_to_file "$TMPDIR/world.html" "$TMPDIR/world.json" 8

echo "💻 解析科技..."
parse_to_file "$TMPDIR/tech.html" "$TMPDIR/tech.json" 8

echo "🚀 解析36氪..."
python3 - "$TMPDIR/36kr_rss.xml" "$TMPDIR/36kr.json" "$PUSHED_TITLES" << 'PYEOF'
import sys, re, json

pushed_titles = [t.strip() for t in sys.argv[3].split("\n") if t.strip()]

def chinese_words(text, n=2):
    words = set()
    for i in range(len(text) - n + 1):
        chunk = text[i:i+n]
        if re.search(r'[\u4e00-\u9fff]', chunk):
            words.add(chunk)
    return words

def is_similar_to_pushed(title, threshold=0.5):
    tw = chinese_words(title)
    if not tw:
        return False
    for p in pushed_titles:
        pw = chinese_words(p)
        if not pw:
            continue
        overlap = len(tw & pw)
        max_w = max(len(tw), len(pw))
        if max_w > 0 and overlap / max_w >= threshold:
            return True
    return False

try:
    with open(sys.argv[1], 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
except:
    json.dump([], open(sys.argv[2], 'w'))
    sys.exit(0)

titles = []
items = re.findall(r'<title>(.*?)</title>', content, re.DOTALL)
links = re.findall(r'<link>(.*?)</link>', content, re.DOTALL)

seen = set()
for i, (title, link) in enumerate(zip(items[1:], links[1:])):
    title = title.strip()
    if not title or title in seen:
        continue
    if any(x in title for x in ['去年', '前年', '上月', '上周', '2024', '2023', '2022', '2025春节']):
        continue
    if len(title) < 10 or title in pushed_titles:
        continue
    if is_similar_to_pushed(title, 0.5):
        continue
    seen.add(title)
    titles.append(title)
    if len(titles) >= 6:
        break

json.dump(titles, open(sys.argv[2], 'w'), ensure_ascii=False)
PYEOF

echo "📱 解析钛媒体..."
python3 - "$TMPDIR/tmtpost_rss.xml" "$TMPDIR/tmtpost.json" "$PUSHED_TITLES" << 'PYEOF'
import sys, re, json

pushed_titles = [t.strip() for t in sys.argv[3].split("\n") if t.strip()]

def chinese_words(text, n=2):
    words = set()
    for i in range(len(text) - n + 1):
        chunk = text[i:i+n]
        if re.search(r'[\u4e00-\u9fff]', chunk):
            words.add(chunk)
    return words

def is_similar_to_pushed(title, threshold=0.5):
    tw = chinese_words(title)
    if not tw:
        return False
    for p in pushed_titles:
        pw = chinese_words(p)
        if not pw:
            continue
        overlap = len(tw & pw)
        max_w = max(len(tw), len(pw))
        if max_w > 0 and overlap / max_w >= threshold:
            return True
    return False

try:
    with open(sys.argv[1], 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
except:
    json.dump([], open(sys.argv[2], 'w'))
    sys.exit(0)

titles = []
items = re.findall(r'<title>(.*?)</title>', content, re.DOTALL)
links = re.findall(r'<link>(.*?)</link>', content, re.DOTALL)

seen = set()
for i, (title, link) in enumerate(zip(items[1:], links[1:])):
    title = title.strip()
    if not title or title in seen:
        continue
    if any(x in title for x in ['去年', '前年', '上月', '上周', '2024', '2023', '2022']):
        continue
    if len(title) < 10 or title in pushed_titles:
        continue
    if is_similar_to_pushed(title, 0.5):
        continue
    seen.add(title)
    titles.append(title)
    if len(titles) >= 6:
        break

json.dump(titles, open(sys.argv[2], 'w'), ensure_ascii=False)
PYEOF

echo "📊 解析经济观察报..."
python3 - "$TMPDIR/eeo_rss.xml" "$TMPDIR/eeo.json" "$PUSHED_TITLES" << 'PYEOF'
import sys, re, json

pushed_titles = [t.strip() for t in sys.argv[3].split("\n") if t.strip()]

def chinese_words(text, n=2):
    words = set()
    for i in range(len(text) - n + 1):
        chunk = text[i:i+n]
        if re.search(r'[\u4e00-\u9fff]', chunk):
            words.add(chunk)
    return words

def is_similar_to_pushed(title, threshold=0.5):
    tw = chinese_words(title)
    if not tw:
        return False
    for p in pushed_titles:
        pw = chinese_words(p)
        if not pw:
            continue
        overlap = len(tw & pw)
        max_w = max(len(tw), len(pw))
        if max_w > 0 and overlap / max_w >= threshold:
            return True
    return False

try:
    with open(sys.argv[1], 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
except:
    json.dump([], open(sys.argv[2], 'w'))
    sys.exit(0)

titles = []
items = re.findall(r'<!\[CDATA\[(.*?)\]\]>', content)
seen = set()
for title in items:
    title = title.strip()
    if not title or title in seen:
        continue
    if re.search(r'(http|https|jpg|png|obs\.cn|myhuaweicloud)', title, re.I):
        continue
    if re.search(r'<[^>]+>', title):
        continue
    if re.search(r'^https?://', title):
        continue
    if any(x in title for x in ['去年', '前年', '上月', '上周', '2024', '2023', '2022']):
        continue
    title = re.sub(r'&[a-z]+;', '', title)
    title = re.sub(r'<[^>]+>', '', title).strip()
    if len(title) < 10 or len(title) > 80:
        continue
    if not re.search(r'[\u4e00-\u9fff]', title):
        continue
    if title in pushed_titles or is_similar_to_pushed(title, 0.5):
        continue
    seen.add(title)
    titles.append(title)
    if len(titles) >= 6:
        break

json.dump(titles, open(sys.argv[2], 'w'), ensure_ascii=False)
PYEOF

echo "💬 解析知乎热榜（社会）..."
python3 - "$TMPDIR/zhihu_api.json" "$TMPDIR/zhihu.json" "$PUSHED_TITLES" << 'PYEOF'
import sys, json, re

pushed_titles = [t.strip() for t in sys.argv[3].split("\n") if t.strip()]

def chinese_words(text, n=2):
    words = set()
    for i in range(len(text) - n + 1):
        chunk = text[i:i+n]
        if re.search(r'[\u4e00-\u9fff]', chunk):
            words.add(chunk)
    return words

def is_similar_to_pushed(title, threshold=0.5):
    tw = chinese_words(title)
    if not tw:
        return False
    for p in pushed_titles:
        pw = chinese_words(p)
        if not pw:
            continue
        overlap = len(tw & pw)
        max_w = max(len(tw), len(pw))
        if max_w > 0 and overlap / max_w >= threshold:
            return True
    return False

try:
    with open(sys.argv[1], 'r', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
except:
    json.dump([], open(sys.argv[2], 'w'))
    sys.exit(0)

titles = []
seen = set()
for item in data.get('data', []):
    target = item.get('target', {})
    title = target.get('title', '')
    if not title:
        continue
    title = title.strip()
    if len(title) < 6 or len(title) > 60:
        continue
    title = re.sub(r'\d+[\.\d]*万热度$', '', title)
    title = re.sub(r'#', '', title)
    if title in seen or title in pushed_titles:
        continue
    if is_similar_to_pushed(title, 0.5):
        continue
    seen.add(title)
    titles.append(title)
    if len(titles) >= 8:
        break

json.dump(titles, open(sys.argv[2], 'w'), ensure_ascii=False)
PYEOF

# ============ 6. 跨板块去重 + 合并 ============
POLITICS_JSON=$(cat "$TMPDIR/politics.json")
FINANCE_JSON=$(cat "$TMPDIR/finance.json")
TECH_JSON=$(cat "$TMPDIR/tech.json")
WORLD_JSON=$(cat "$TMPDIR/world.json")
ZHIHU_JSON=$(cat "$TMPDIR/zhihu.json")
EEO_JSON=$(cat "$TMPDIR/eeo.json")
KR36_JSON=$(cat "$TMPDIR/36kr.json")
TMTPOST_JSON=$(cat "$TMPDIR/tmtpost.json")

DEDUP_RESULT=$(python3 - "$POLITICS_JSON" "$FINANCE_JSON" "$TECH_JSON" "$WORLD_JSON" "$ZHIHU_JSON" "$EEO_JSON" "$KR36_JSON" "$TMTPOST_JSON" << 'PYEOF'
import sys, json, re

def chinese_words(text, n=2):
    words = set()
    for i in range(len(text) - n + 1):
        chunk = text[i:i+n]
        if re.search(r'[\u4e00-\u9fff]', chunk):
            words.add(chunk)
    return words

def is_similar(a, b, threshold=0.5):
    w1, w2 = chinese_words(a), chinese_words(b)
    if not w1 or not w2:
        return False
    return len(w1 & w2) / max(len(w1), len(w2)) >= threshold

def dedup_and_limit(arr, pool, limit=8):
    result = []
    for x in arr:
        if not any(is_similar(x, p, 0.5) for p in pool):
            result.append(x)
            pool.append(x)
        if len(result) >= limit:
            break
    return result

try:
    politics = json.loads(sys.argv[1])
    finance = json.loads(sys.argv[2])
    tech = json.loads(sys.argv[3])
    world = json.loads(sys.argv[4])
    zhihu = json.loads(sys.argv[5]) if len(sys.argv) > 5 else []
    eeo = json.loads(sys.argv[6]) if len(sys.argv) > 6 else []
    kr36 = json.loads(sys.argv[7]) if len(sys.argv) > 7 else []
    tmtpost = json.loads(sys.argv[8]) if len(sys.argv) > 8 else []
except:
    print(json.dumps({'politics':[],'finance':[],'tech':[],'world':[],'zhihu':[],'eeo':[],'kr36':[],'tmtpost':[]}))
    sys.exit(0)

pool = []
finance_merged = finance + [x for x in eeo if x not in finance]
politics_d = dedup_and_limit(politics, pool, 8)
finance_d = dedup_and_limit(finance_merged, pool, 8)
tech_d = dedup_and_limit(tech, pool, 8)
world_d = dedup_and_limit(world, pool, 8)
zhihu_d = dedup_and_limit(zhihu, pool, 8)
rutui_pool = []
kr36_d = dedup_and_limit(kr36, rutui_pool, 4)
tmtpost_d = dedup_and_limit(tmtpost, rutui_pool, 4)
rutui_d = kr36_d + tmtpost_d

print(json.dumps({
    'politics': politics_d,
    'finance': finance_d,
    'tech': tech_d,
    'world': world_d,
    'zhihu': zhihu_d,
    'rutui': rutui_d
}, ensure_ascii=False))
PYEOF
)

DEDUP_RESULT_STR="$DEDUP_RESULT"

# ============ 7. 记录本次推送标题（用于明日去重） ============
TODAY=$(date "+%Y-%m-%d")
NEW_TITLES=$(echo "$DEDUP_RESULT_STR" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
all_titles = []
for v in data.values():
    if isinstance(v, list):
        all_titles.extend(v)
print(json.dumps({'date': '$TODAY', 'titles': all_titles}, ensure_ascii=False))
" 2>/dev/null)

echo "$NEW_TITLES" >> "$TRACK_FILE"

# 清理超过7天的旧记录
python3 - "$TRACK_FILE" << 'PYEOF'
import sys, json
from datetime import datetime, timedelta
import sys as _sys
_sys.path.insert(0, "/root/.openclaw/workspace/scripts")
from _timezone import now_cst

track_file = sys.argv[1]
cutoff = (now_cst() - timedelta(days=7)).strftime("%Y-%m-%d")

kept = []
with open(track_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get("date", "") >= cutoff:
                kept.append(line)
        except:
            pass

with open(track_file, "w", encoding="utf-8") as f:
    for line in kept:
        f.write(line + "\n")
PYEOF

# ============ 8. 输出完整简报 ============
DATE_INFO=$(date "+%Y年%m月%d日 %A %H:%M")

render_section() {
    local key=$1
    echo "$DEDUP_RESULT_STR" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
items = data.get('$key', [])
for i, n in enumerate(items, 1):
    print(f'{i}. {n}')
" 2>/dev/null
}

POLITICS_ITEMS=$(render_section "politics")
FINANCE_ITEMS=$(render_section "finance")
TECH_ITEMS=$(render_section "tech")
WORLD_ITEMS=$(render_section "world")
ZHIHU_ITEMS=$(render_section "zhihu")
RUTUI_ITEMS=$(render_section "rutui")

cat << REPORT
🦞 **每日简报** | $DATE_INFO

━━━━━━━━━━━━━━━━━━

🌤️ **福州天气预报**

$WEATHER_INFO

━━━━━━━━━━━━━━━━━━

🏛️ **时政**

${POLITICS_ITEMS:-（暂无更新）}

━━━━━━━━━━━━━━━━━━

💰 **金融经济**

${FINANCE_ITEMS:-（暂无更新）}

━━━━━━━━━━━━━━━━━━

💻 **科技**

${TECH_ITEMS:-（暂无更新）}

━━━━━━━━━━━━━━━━━━

🌍 **国际**

${WORLD_ITEMS:-（暂无更新）}

━━━━━━━━━━━━━━━━━━

💬 **社会**

${ZHIHU_ITEMS:-（暂无更新）}

━━━━━━━━━━━━━━━━━━

🚀 **锐推**

${RUTUI_ITEMS:-（暂无更新）}

━━━━━━━━━━━━━━━━━━

🦞 _由小龙虾自动生成 · 新浪 + 36氪 + 钛媒体 + 知乎 + 经济观察报_
REPORT