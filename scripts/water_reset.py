#!/usr/bin/env python3
"""喝水记录每日重置脚本"""
import json
from datetime import date

import os

LOG = os.path.expanduser('~/.openclaw/workspace/data/water-log.json')

with open(LOG) as f:
    d = json.load(f)

# 重置只清汇总字段，保留 records 历史数据
d['today'] = str(date.today())
d['total_ml'] = 0
d['cup_count'] = 0
# 注意：不再清空 records，所有历史永久保留

with open(LOG, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print(f"✅ 喝水记录已重置: {d['today']}, total_ml=0, records 保留历史")
