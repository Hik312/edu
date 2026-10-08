# -*- coding: utf-8 -*-
"""生成小程序 tabBar 的 PNG 图标（离线、可复现，不依赖设计稿）。

为什么要有这个：`miniapp/app.json` 的 tabBar 之前把 emoji 塞进 `text`
当图标用（`"text": "🏠 首页"`），而**原生 tabBar 根本不渲染 emoji** ——
安卓和开发者工具上都只剩「首页」两个字，底部导航看起来像没做完。
原生 tabBar 的图标只能是 PNG 文件（`iconPath` / `selectedIconPath`），
不能用字体图标、也不能用 CSS，所以这里用 PIL 画一套。

用法：
    python back_study/scripts/gen_miniapp_icons.py

产物（4 组 × 2 态，写进 miniapp/images/tab/）：
    home.png  / home-on.png    首页（房子）
    learn.png / learn-on.png   学习（翻开的书）
    cards.png / cards-on.png   卡包（叠卡）
    mine.png  / mine-on.png    我的（人像）

配色跟全局主题走：未选中 = 牛皮纸棕 `#63543c`，选中 = 靛蓝 `#1f4b6b`
（对应 app.wxss 的 `--dim` / `--accent`，别在这儿另立颜色）。
"""

import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    print('需要 Pillow：pip install pillow')
    sys.exit(1)

_HERE = os.path.dirname(os.path.abspath(__file__))      # .../back_study/scripts
_BACK = os.path.dirname(_HERE)                          # .../back_study
_ROOT = os.path.dirname(_BACK)                          # .../study
OUT_DIR = os.path.join(_ROOT, 'miniapp', 'images', 'tab')

#: 微信用 81×81 的 tabBar 图标（官方推荐尺寸），别改。
SIZE = 81
#: 超采样倍数：先在 SIZE*SS 的画布上画，再缩回去 —— PIL 没有抗锯齿，
#: 只能靠这招把边缘磨平。6 倍在 81px 上足够干净。
SS = 6
#: 线宽（以 81 坐标系计），4~6 之间看着最舒服。
LW = 5.6

DIM = (99, 84, 60, 255)      # #63543c 未选中（--dim）
ON = (31, 75, 107, 255)      # #1f4b6b 选中（--accent）


def _S(v):
    """坐标换算到超采样画布（取整，PIL 的 C 层只吃 int）。"""
    return int(round(v * SS))


def _poly(d, pts, w, color):
    """折线 + 圆头圆角。

    PIL 的 `line(joint='curve')` 只圆折点、不圆端点，所以每个顶点再补一个
    实心小圆当「笔帽」—— 这才是描边图标该有的样子。
    坐标和线宽都取整：PIL 的 C 层不接受 float。
    """
    p = [(int(round(_S(x))), int(round(_S(y)))) for x, y in pts]
    d.line(p, fill=color, width=int(w), joint='curve')
    r = w / 2.0
    for (x, y) in p:
        d.ellipse([x - r, y - r, x + r, y + r], fill=color)


# ---------- 四个图标（都在 81×81 坐标系里画） ----------
def _home(d, w, c):
    _poly(d, [(10, 40), (40.5, 15), (71, 40)], w, c)              # 屋顶
    _poly(d, [(18, 36), (18, 68), (63, 68), (63, 36)], w, c)      # 两墙 + 地
    _poly(d, [(33, 68), (33, 53), (48, 53), (48, 68)], w, c)      # 门


def _learn(d, w, c):
    # 翻开的书：左右两页在中间书脊处交汇
    _poly(d, [(40, 25), (14, 30), (14, 61), (40, 57), (40, 25)], w, c)
    _poly(d, [(41, 25), (67, 30), (67, 61), (41, 57), (41, 25)], w, c)


def _cards(d, w, c):
    # 叠卡：后面一张露一角，前面一张带个卡芯点
    d.rounded_rectangle([_S(17), _S(17), _S(57), _S(51)],
                        radius=_S(8), outline=c, width=w)
    d.rounded_rectangle([_S(25), _S(27), _S(65), _S(65)],
                        radius=_S(8), outline=c, width=w)
    cx, cy, r = _S(51), _S(54), _S(3.4)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)


def _mine(d, w, c):
    d.ellipse([_S(29), _S(14), _S(52), _S(37)], outline=c, width=w)   # 头
    # 肩膀：大椭圆的上半弧（PIL 角度顺时针，180°→360° 正好是上半圈）
    d.arc([_S(17), _S(45), _S(64), _S(95)],
          start=180, end=360, fill=c, width=w)


ICONS = {
    'home': _home,
    'learn': _learn,
    'cards': _cards,
    'mine': _mine,
}


def render(fn, color):
    img = Image.new('RGBA', (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
    fn(ImageDraw.Draw(img), int(round(LW * SS)), color)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def main():
    mini = os.path.join(_ROOT, 'miniapp')
    if not os.path.isdir(mini):
        print('找不到 miniapp 目录：%s' % mini)
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, fn in ICONS.items():
        render(fn, DIM).save(os.path.join(OUT_DIR, name + '.png'))
        render(fn, ON).save(os.path.join(OUT_DIR, name + '-on.png'))
        print('  %-10s %-10s -> %s' % (name + '.png', name + '-on.png', OUT_DIR))
    print('共生成 %d 个图标（%d×%d）' % (len(ICONS) * 2, SIZE, SIZE))
    return 0


if __name__ == '__main__':
    sys.exit(main())
