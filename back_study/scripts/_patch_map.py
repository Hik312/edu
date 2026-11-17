import io
p = 'back_study/scripts/draw_arch_map.py'
s = io.open(p, encoding='utf-8').read()

# 1) 行 2 末尾箭头条件写错：`(t != '返回复习队列',)` 是 tuple，恒为 True
old = "    x += w\n    if w != 15.0 and (t != '返回复习队列',):\n        hlink(x + 0.3, y + NH / 2)\n        x += AR"
new = "    x += w\n    if t != '返回复习队列':\n        hlink(x + 0.3, y + NH / 2)\n        x += AR"
assert old in s, 'row2 arrow block not found'
s = s.replace(old, new)

# 2) 收紧留白：层高略增、层间距缩小
s = s.replace('LH, GAP, Y_TOP = 5.2, 3.0, 90.2', 'LH, GAP, Y_TOP = 5.4, 2.6, 90.0')
s = s.replace('NH, AV, TX = 3.8, 2.0, RX + 4.8', 'NH, AV, TX = 3.9, 1.9, RX + 4.8')
s = s.replace('y -= NH + 1.7', 'y -= NH + 1.5')

# 3) 脚注收紧
s = s.replace('FN = LY - 2.2', 'FN = LY - 1.9')
s = s.replace("txt(4, FN - i * 1.5, s, pick_font(s), 7.0, c, ha='left')",
              "txt(4, FN - i * 1.6, s, pick_font(s), 7.1, c, ha='left')")

# 4) 画布按内容高度收窄，去掉底部大片空白
s = s.replace('figsize=(13.0, 17.6)', 'figsize=(13.0, 16.9)')

io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
