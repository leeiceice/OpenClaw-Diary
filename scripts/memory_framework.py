#!/usr/bin/env python3
"""生成小龙虾记忆逻辑框架图"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'SimHei', 'Noto Sans CJK SC']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(1, 1, figsize=(16, 12))
ax.set_xlim(0, 16)
ax.set_ylim(0, 12)
ax.axis('off')
ax.set_facecolor('#1a1a2e')
fig.patch.set_facecolor('#1a1a2e')

# 颜色定义
colors = {
    'short': '#e94560',      # 短期-红
    'mid': '#0f3460',        # 中期-深蓝
    'long': '#16213e',       # 长期-藏青
    'memos': '#533483',      # MemOS-紫
    'self': '#e94560',       # 自我进化-红
    'pro': '#f39c12',        # 主动性-橙
    'arrow': '#ffffff',
    'text': '#ffffff',
    'subtext': '#a0a0a0',
}

def draw_box(ax, x, y, w, h, color, title, subtitle, title_size=11):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                          facecolor=color, edgecolor='white', linewidth=2, alpha=0.9)
    ax.add_patch(box)
    ax.text(x + w/2, y + h*0.65, title, ha='center', va='center',
            fontsize=title_size, fontweight='bold', color='white', wrap=True)
    if subtitle:
        ax.text(x + w/2, y + h*0.3, subtitle, ha='center', va='center',
                fontsize=8, color='#cccccc', style='italic')

def draw_arrow(ax, x1, y1, x2, y2, label=''):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='#888888', lw=1.5))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx+0.2, my, label, fontsize=7, color='#888888', ha='left', va='center')

# ========== 标题 ==========
ax.text(8, 11.5, '🦞 小龙虾记忆逻辑框架', fontsize=20, fontweight='bold',
        ha='center', va='center', color='white')
ax.text(8, 11.0, 'Memory Logic Framework', fontsize=12,
        ha='center', va='center', color='#888888')

# ========== 三层记忆主体 ==========

# 短期记忆（左上）
draw_box(ax, 0.5, 7.5, 4.5, 2.5, colors['short'],
         '🕐 短期记忆\nSESSION-STATE.md', '当前会话·WAL协议')

# 中期记忆（中上）
draw_box(ax, 5.75, 7.5, 4.5, 2.5, colors['mid'],
         '🕐 中期记忆\nmemory/YYYY-MM-DD.md', '每日复盘·事件记录')

# 长期记忆（右上）
draw_box(ax, 11, 7.5, 4.5, 2.5, colors['long'],
         '🕐 长期记忆\nMEMORY.md', '核心知识·用户偏好')

# 记忆流向箭头（横向）
draw_arrow(ax, 5.0, 8.75, 5.75, 8.75, '提炼合并')
draw_arrow(ax, 10.25, 8.75, 11.0, 8.75, '提炼合并')

# ========== 辅助系统 ==========

# MemOS Local（左下）
draw_box(ax, 0.5, 4.0, 4.5, 2.5, colors['memos'],
         '🧠 MemOS 向量搜索\nhttp://150.158.39.225', '每日02:30增量同步\n3529 chunks / 869 embeddings')

# 自我进化（中下）
draw_box(ax, 5.75, 4.0, 4.5, 2.5, colors['self'],
         '📈 自我进化\n~/self-improving/', 'corrections · domains · projects\n记忆优化·执行改进')

# 主动性系统（右下）
draw_box(ax, 11, 4.0, 4.5, 2.5, colors['pro'],
         '🎯 主动性系统\n~/proactivity/', 'memory · session-state\npatterns · heartbeat')

# 辅助系统与三层记忆的连接
for x_left in [2.75, 8.0, 13.25]:
    draw_arrow(ax, x_left, 7.5, x_left, 6.5, '')

# ========== 数据来源（底部）==========
draw_box(ax, 0.5, 1.0, 15, 2.0, '#2d2d44',
         '📥 数据来源 → 处理 → 存储', '用户交互 · 任务执行 · Cron调度 · 主动检查')

# 来源连接箭头
for x_src in [2.5, 5.5, 8.5, 11.5, 14.5]:
    draw_arrow(ax, x_src, 4.0, x_src, 3.0, '')

# ========== 记忆优先级标注 ==========
priority_text = '记忆优先级: 长期 > 中期 > 当前会话 > 联网搜索'
ax.text(8, 0.3, priority_text, fontsize=9, ha='center', va='center',
        color='#888888', style='italic')

# ========== 图例 ==========
legend_items = [
    mpatches.Patch(color=colors['short'], label='短期记忆 (Session)'),
    mpatches.Patch(color=colors['mid'], label='中期记忆 (Daily)'),
    mpatches.Patch(color=colors['long'], label='长期记忆 (Long-term)'),
    mpatches.Patch(color=colors['memos'], label='MemOS 向量搜索'),
    mpatches.Patch(color=colors['self'], label='Self-Improving'),
    mpatches.Patch(color=colors['pro'], label='Proactivity'),
]
ax.legend(handles=legend_items, loc='lower left', fontsize=8,
          framealpha=0.3, facecolor='#2d2d44', edgecolor='white',
          labelcolor='white')

plt.tight_layout()
plt.savefig('~/.openclaw/workspace/memory_framework.png', dpi=150,
            facecolor='#1a1a2e', edgecolor='none', bbox_inches='tight')
print("Diagram saved to ~/.openclaw/workspace/memory_framework.png")
plt.close()
