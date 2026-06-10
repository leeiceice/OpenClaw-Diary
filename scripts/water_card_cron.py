#!/usr/bin/env python3
"""
喝水追踪每日推送脚本
生成水卡片图片并发送到日常安排群
"""
import sys
sys.path.insert(0, '~/.openclaw/workspace/scripts')

from water_card_generator import load_data, generate_card
from pathlib import Path

OUTPUT_FILE = Path("/tmp/water_card.png")

def main():
    data = load_data()
    generate_card(data, OUTPUT_FILE)
    print("water_card_path:" + str(OUTPUT_FILE))
    return str(OUTPUT_FILE)

if __name__ == '__main__':
    main()
