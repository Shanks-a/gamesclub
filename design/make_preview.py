# -*- coding: utf-8 -*-
"""用真实 H5 截图生成 README 用 8 页移动端总览图（替换旧设计稿 preview.png）。"""
from PIL import Image, ImageDraw, ImageFont
import os

SHOTS = 'D:/zth/gamesclub/design/shots'
OUT = 'D:/zth/gamesclub/design/preview.png'

pages = [
    ('01-home.png', '01-首页'),
    ('02-channel.png', '02-频道'),
    ('03-messages.png', '03-消息'),
    ('04-profile.png', '04-我的'),
    ('05-specials.png', '05-特价'),
    ('06-orders.png', '06-订单'),
    ('07-services.png', '07-服务'),
    ('08-login.png', '08-登录'),
]

INK = (48, 51, 69)
MUTED = (117, 103, 132)
ACCENT = (136, 117, 170)
BG = (246, 245, 242)
CARD = (255, 255, 255)

# 布局参数
COLS, ROWS = 4, 2
SHOT_W, SHOT_H = 390, 844
SCALE = 0.82
W_PH, H_PH = int(SHOT_W * SCALE), int(SHOT_H * SCALE)   # 319 x 692
GAP_X, GAP_Y = 36, 56
MARGIN = 56
HEADER = 130
FOOTER = 60

W = MARGIN * 2 + COLS * W_PH + (COLS - 1) * GAP_X
H = HEADER + ROWS * H_PH + (ROWS - 1) * GAP_Y + FOOTER

canvas = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(canvas)

def font(name, size):
    return ImageFont.truetype(os.path.join(r'C:\Windows\Fonts', name), size)

f_title = font('msyh.ttc', 40)
f_sub = font('msyh.ttc', 20)
f_label = font('msyh.ttc', 22)

# 标题区
d.text((MARGIN, 40), '游伴 CLUB · 移动端实际界面', font=f_title, fill=INK)
d.text((MARGIN, 96), 'uni-app + Vue3 · H5 / 微信小程序 · 全幅插画 Banner · 以下为真实运行截图', font=f_sub, fill=MUTED)
d.line([(MARGIN, HEADER - 18), (W - MARGIN, HEADER - 18)], fill=(225, 222, 230), width=2)

# 网格
for i, (file, label) in enumerate(pages):
    r, c = divmod(i, COLS)
    x = MARGIN + c * (W_PH + GAP_X)
    y = HEADER + r * (H_PH + GAP_Y)
    im = Image.open(os.path.join(SHOTS, file)).convert('RGB').resize((W_PH, H_PH), Image.LANCZOS)
    # 手机边框（圆角描边）
    d.rounded_rectangle([x - 3, y - 3, x + W_PH + 3, y + H_PH + 3], radius=22, outline=(210, 205, 220), width=2)
    canvas.paste(im, (x, y))
    # 标签
    d.text((x + W_PH // 2 - len(label) * 6, y + H_PH + 16), label, font=f_label, fill=ACCENT if i == 0 else MUTED)

canvas.save(OUT, quality=92)
print('saved', OUT, canvas.size)
