# -*- coding: utf-8 -*-
"""生成 PWA 图标（192 / 512），配色跟随全站唯一主题：暖牛皮纸卷宗。

用法：
    python back_study/scripts/make_icon.py

产物写到 `web/public/icons/`（前端从「单文件 web/index.html」迁到 Vite 工程后，
图标挪进了 public/ —— 构建时 vite 会把它复制到 dist/icons/）。

⚠️ 2026-09-26 修的两个历史问题：
  1. 输出路径原来写的是 `web/icons/`，那是迁移前的旧位置。结果是这个脚本
     一跑就新建一个没人引用的 web/icons/ 目录，**真图标一个都不更新**，
     而且它 print 的 'wrote ...' 看起来还挺正常。路径已改到 public/。
  2. 原配色是旧深色主题（底 #14161a / 卡片 #22262f / 青 #4dd0a7）。
     全站统一成牛皮纸后，图标是唯一还发黑的东西，已整体换掉。

色值来源是 `web/src/styles/tokens.css` 的 :root，**改主题时这里要跟着改**：
    --bg #eee5d3 · --panel #f8f3e6 · --panel2 #e5dbc5 · --line2 #c8b894
    --tx #3a2f21 · --mu #63543c · --dim #8a7859 · --ac #1f4b6b · --red #a8392a
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']

# ---- tokens.css 里的牛皮纸色板 ----
BG = '#eee5d3'      # --bg      桌面：牛皮纸
SHEET = '#f8f3e6'   # --panel   纸面：卡片、面板
SHEET_BACK = '#e5dbc5'  # --panel2  底下那张纸露出的边
EDGE = '#c8b894'    # --line2   加重的折痕 / 描边
EDGE_SOFT = '#ddd1b6'   # --line
INK = '#3a2f21'     # --tx      墨褐正文
MID = '#63543c'     # --mu      次级
FAINT = '#8a7859'   # --dim     三级
INDIGO = '#1f4b6b'  # --ac      靛蓝墨水：档签
SEAL = '#a8392a'    # --red     朱砂：印章

# 画布用 0..100 的抽象坐标，跟像素尺寸解耦；下面每个 size 都按同一套比例渲。
W = 100.0


def make(size, out):
    fig = plt.figure(figsize=(size / 128.0, size / 128.0), dpi=128)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, W)
    ax.axis('off')

    # 桌面底：整块牛皮纸。maskable 图标会被系统裁圆，所以底色必须铺满，
    # 而且主体内容要留在中间 80%（10..90）以内，否则裁完会切到纸边。
    ax.add_patch(Rectangle((0, 0), W, W, color=BG))

    # 后页：往左下错开一点，露出纸边，读起来才像「一叠卷宗」而不是一张图。
    ax.add_patch(FancyBboxPatch(
        (15, 14), 66, 68,
        boxstyle='round,pad=0,rounding_size=8',
        linewidth=1.0, edgecolor=EDGE_SOFT, facecolor=SHEET_BACK))

    # 前页：主卡片。
    ax.add_patch(FancyBboxPatch(
        (22, 20), 62, 66,
        boxstyle='round,pad=0,rounding_size=8',
        linewidth=1.4, edgecolor=EDGE, facecolor=SHEET))

    # 档签：靛蓝的标签条压在纸页上沿。先用圆角矩形，再补一个方角矩形把下沿压平，
    # 免得底边也带圆角、看着像悬浮的胶囊而不是贴在纸上的标签。
    ax.add_patch(FancyBboxPatch(
        (22, 74), 62, 12,
        boxstyle='round,pad=0,rounding_size=6',
        linewidth=0, facecolor=INDIGO))
    ax.add_patch(Rectangle((22, 74), 62, 6, color=INDIGO))

    # 正文线：三级墨色递减，模拟卡片的一行标题 + 两行说明。
    ax.add_patch(Rectangle((33, 62), 38, 3.6, color=INK))
    ax.add_patch(Rectangle((33, 51), 30, 3.2, color=MID))
    ax.add_patch(Rectangle((33, 41), 21, 3.2, color=FAINT))

    # 朱砂印：实心圆 + 中间一个纸色的斜方块，做出「白文印」的缺口感。
    ax.add_patch(Circle((69, 29), 7.2, color=SEAL))
    d = 3.3
    ax.add_patch(Polygon(
        [(69, 29 + d), (69 + d, 29), (69, 29 - d), (69 - d, 29)],
        closed=True, color=SHEET))

    fig.savefig(out, dpi=128, facecolor=BG)
    plt.close(fig)
    print('wrote %s (%dx%d)' % (out, size, size))


here = os.path.dirname(os.path.abspath(__file__))        # back_study/scripts
root = os.path.dirname(os.path.dirname(here))            # study
icons = os.path.join(root, 'web', 'public', 'icons')     # ← 不是 web/icons
os.makedirs(icons, exist_ok=True)

make(192, os.path.join(icons, 'icon-192.png'))
make(512, os.path.join(icons, 'icon-512.png'))
