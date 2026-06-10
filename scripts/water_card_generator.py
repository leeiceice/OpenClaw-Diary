#!/usr/bin/env python3
"""
喝水追踪可视化卡片 - Pillow 渲染版 v2
生成图片推送至日常安排群
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json
from datetime import date, datetime
from _timezone import CST

LOG_FILE = Path("~/.openclaw/workspace/data/water-log.json").expanduser()
OUTPUT_FILE = Path("/tmp/water_card.png")

# ── 颜色主题（水的蓝色系） ──
C_BG       = (240, 248, 255)   # 浅蓝白背景
C_CARD     = (255, 255, 255)   # 卡片白
C_WATER    = (30, 120, 220)     # 主蓝色
C_WATER2   = (80, 170, 255)    # 浅蓝色
C_TEXT     = (25, 55, 95)      # 深蓝文字
C_TEXT2    = (120, 160, 195)   # 浅蓝次要文字
C_EMPTY    = (220, 235, 250)   # 空杯背景
C_GOAL_OK  = (50, 195, 130)    # 绿色（达成时）

def load_data():
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return {"today": str(date.today()), "total_ml": 0, "cup_count": 0, "goal_ml": 2000, "cup_ml": 350, "records": []}

def draw_water_drop(draw, cx, cy, size, fill_color):
    """画一个水滴形状"""
    w = int(size * 0.8)
    h = int(size * 1.2)
    # 水滴：上尖下圆
    top_x, top_y = cx, cy - h // 2
    bottom_y = cy + h // 2
    
    # 画水滴路径 - 用多个点围成水滴形状
    points = []
    # 左边弧线
    for t in range(0, 91, 5):
        import math
        rx = w / 2 * math.sin(math.radians(t))
        ry = h / 2 * (1 - math.cos(math.radians(t))) / 2  # 椭圆上部压缩
        points.append((cx - rx, cy - h/2 + h/2 + ry if t <= 90 else bottom_y))
    
    # 简化为一个圆润的水滴：用贝塞尔近似
    # 顶部尖点
    top = (cx, cy - h // 2 + 2)
    # 底部圆心
    bottom = (cx, cy + h // 2 - 2)
    # 宽度控制点
    half_w = w // 2
    
    # 画简化水滴：用一个椭圆底部 + 三角形顶部
    # 底部椭圆
    draw.ellipse([cx - half_w, cy, cx + half_w, cy + h // 2 + 2], fill=fill_color)
    # 顶部三角形（用多边形）
    tri_points = [(cx - half_w, cy + 4), (cx + half_w, cy + 4), (cx, top[1])]
    draw.polygon(tri_points, fill=fill_color)

def draw_glass(draw, x, y, w, h, filled, empty_color):
    """画一个玻璃杯形状"""
    r = 8 * 2  # 圆角
    
    if filled:
        # 满杯：蓝色液体
        # 杯身（倒梯形，顶部稍宽）
        pad = 3 * 2
        draw.rounded_rectangle([x + pad, y + pad, x + w - pad, y + h - pad], 
                                radius=r - 2, fill=C_WATER)
        # 高光条纹
        hl_x = x + w // 4
        hl_w = 4 * 2
        draw.rounded_rectangle([hl_x, y + pad + 4*2, hl_x + hl_w, y + h - pad - 4*2],
                                radius=2*2, fill=(80, 160, 255, 128))
    else:
        # 空杯：浅灰边框
        draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=empty_color)
        # 内部更淡
        inner_pad = 4 * 2
        draw.rounded_rectangle([x + inner_pad, y + inner_pad, 
                                 x + w - inner_pad, y + h - inner_pad], 
                                radius=r - 2, fill=(245, 250, 255))

def generate_card(data, output_path):
    scale = 2
    W = 620 * scale
    total_h = 400 * scale

    canvas = Image.new('RGBA', (W, total_h), C_BG)
    draw = ImageDraw.Draw(canvas)

    # ── 字体 ──
    font_title  = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 30 * scale)
    font_big    = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 72 * scale)
    font_unit   = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 28 * scale)
    font_mid    = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 22 * scale)
    font_small  = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 18 * scale)
    font_tiny   = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 15 * scale)

    # ── 数据 ──
    total_ml = data.get('total_ml', 0)
    goal_ml = data.get('goal_ml', 2000)
    cup_count = data.get('cup_count', 0)
    goal_cups = 6

    pct = min(100, int(total_ml / goal_ml * 100))
    is_goal = total_ml >= goal_ml

    # ── 主卡片背景 ──
    card_pad = 20 * scale
    card_x, card_y = card_pad, card_pad
    card_w, card_h = W - card_pad * 2, total_h - card_pad * 2
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], 
                            radius=20 * scale, fill=C_CARD)

    # 顶部装饰条
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + 6 * scale], 
                            radius=3 * scale, fill=C_WATER)

    MARGIN = 36 * scale
    content_w = card_w - MARGIN * 2

    # ── 标题行 ──
    title_y = card_y + 24 * scale
    # 标题（无emoji，纯文字）
    draw.text((card_x + MARGIN, title_y), "Water Tracking", font=font_title, fill=C_TEXT)
    
    # 日期
    date_str = datetime.now(CST).strftime("%m/%d")
    date_bb = draw.textbbox((0, 0), date_str, font=font_small)
    draw.text((card_x + card_w - MARGIN - (date_bb[2] - date_bb[0]), title_y + 4*scale), 
              date_str, font=font_small, fill=C_TEXT2)

    # ── ml 大数字 ──
    data_y = title_y + 48 * scale
    ml_color = C_GOAL_OK if is_goal else C_WATER
    draw.text((card_x + MARGIN, data_y), f"{total_ml}", font=font_big, fill=ml_color)

    # "ml" 单位 + / 目标
    draw.text((card_x + MARGIN + 185 * scale, data_y + 22*scale), 
              f"ml  /  {goal_ml} ml", font=font_unit, fill=C_TEXT2)

    # 达成标签
    if is_goal:
        ok_text = "GOAL!"
        ok_bb = draw.textbbox((0, 0), ok_text, font=font_mid)
        ok_w = ok_bb[2] - ok_bb[0]
        ok_x = card_x + MARGIN + content_w - ok_w
        draw.text((ok_x, data_y + 8*scale), ok_text, font=font_mid, fill=C_GOAL_OK)

    # ── 进度条 ──
    bar_y = data_y + 88 * scale
    bar_h = 14 * scale
    bar_x = card_x + MARGIN
    bar_w = content_w

    # 背景槽
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], 
                            radius=bar_h // 2, fill=(225, 238, 252))

    # 填充
    fill_w = int(bar_w * pct / 100)
    if fill_w > bar_h // 2:
        fill_color = C_GOAL_OK if is_goal else C_WATER
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], 
                                radius=bar_h // 2, fill=fill_color)

    # ── 水杯区 ──
    cups_y = bar_y + 40 * scale
    cups_x = card_x + MARGIN
    cup_w = 52 * scale
    cup_h = 68 * scale
    cup_spacing = cup_w + 16 * scale

    for i in range(goal_cups):
        cx = cups_x + i * cup_spacing
        filled = i < cup_count
        draw_glass(draw, cx, cups_y, cup_w, cup_h, filled, C_EMPTY)

    # ── 底部状态行 ──
    status_y = cups_y + cup_h + 14 * scale
    
    cup_text = f"Cups  {cup_count}  /  {goal_cups}"
    draw.text((card_x + MARGIN, status_y), cup_text, font=font_small, fill=C_TEXT2)

    # 时间
    records = data.get('records', [])
    if records:
        last_time = records[-1].get('time', '')
        if last_time:
            time_str = f"Last  {last_time[-5:]}"  # HH:MM
            time_bb = draw.textbbox((0, 0), time_str, font=font_tiny)
            draw.text((card_x + card_w - MARGIN - (time_bb[2] - time_bb[0]), status_y + 2*scale), 
                      time_str, font=font_tiny, fill=C_TEXT2)

    # ── 保存 ──
    canvas.save(output_path, 'PNG')
    return output_path

if __name__ == '__main__':
    data = load_data()
    output = generate_card(data, OUTPUT_FILE)
    print(f"喝水卡片已生成: {output}")
