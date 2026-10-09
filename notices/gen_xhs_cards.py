# -*- coding: utf-8 -*-
"""生成 P3+P4 完成情况的小红书配图（多张卡片）。"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = r"C:/Users/hd/WorkBuddy/Worktrees/gamesclub/main-cf29d12c/notices/e2e-screenshots"
FONT_YAHEI = r"C:\Windows\Fonts\msyh.ttc"
FONT_YAHEI_B = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_HEI = r"C:\Windows\Fonts\simhei.ttf"

def font(path, size):
    return ImageFont.truetype(path, size)

def rounded(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def text(draw, xy, s, fnt, fill):
    draw.text(xy, s, font=fnt, fill=fill)

def text_center(draw, cx, y, s, fnt, fill):
    bbox = draw.textbbox((0, 0), s, font=fnt)
    w = bbox[2] - bbox[0]
    draw.text((cx - w / 2, y), s, font=fnt, fill=fill)

def save(img, name):
    p = os.path.join(OUT, name)
    img.save(p)
    print("saved", p)

# ---- 配色 ----
PURPLE = (60, 52, 137)
PURPLE_L = (238, 237, 254)
BLUE = (24, 95, 165)
BLUE_L = (230, 241, 251)
TEAL = (15, 110, 86)
TEAL_L = (225, 245, 238)
AMBER = (133, 79, 11)
AMBER_L = (250, 238, 218)
INK = (44, 44, 42)
MUTED = (95, 94, 90)
HINT = (136, 135, 128)
WHITE = (255, 255, 255)
RED = (163, 45, 45)
RED_L = (252, 235, 235)
BG = (247, 247, 250)

# ============ 1. 竖版封面总览卡 1080x1520 (约 3:4) ============
W, H = 1080, 1520
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

f_title = font(FONT_HEI, 72)
f_big = font(FONT_YAHEI_B, 56)
f_body = font(FONT_YAHEI, 40)
f_body_b = font(FONT_YAHEI_B, 40)
f_small = font(FONT_YAHEI, 34)
f_tag = font(FONT_YAHEI, 30)
f_huge = font(FONT_YAHEI_B, 96)

# 顶栏
rounded(d, (60, 60, W-60, 240), 24, fill=PURPLE_L)
text(d, (100, 95), "游戏陪玩俱乐部", f_big, PURPLE)
text(d, (100, 175), "P3 + P4 开发进度记录", f_body, PURPLE)

# 日期徽标
rounded(d, (W-320, 80, W-80, 200), 20, fill=WHITE)
text_center(d, (W-320+W-80)/2, 108, "2026-10-09", f_small, MUTED)

# P3 卡
y0 = 300
rounded(d, (60, y0, W-60, y0+340), 28, fill=WHITE, outline=(230,230,235), width=2)
rounded(d, (84, y0+40, 116, y0+300), 16, fill=BLUE)
text(d, (150, y0+50), "P3 · 真实微信登录", f_body_b, BLUE)
text(d, (150, y0+120), "uni.login → code2session", f_small, INK)
text(d, (150, y0+170), "openid 归并 · 签发 Token", f_small, INK)
text(d, (150, y0+220), "AppSecret 隔离 · 数据脱敏", f_small, MUTED)
rounded(d, (150, y0+270, 420, y0+320), 14, fill=BLUE_L)
text(d, (175, y0+277), "21 项测试通过", f_tag, BLUE)

# P4 卡
y1 = y0 + 380
rounded(d, (60, y1, W-60, y1+420), 28, fill=WHITE, outline=(230,230,235), width=2)
rounded(d, (84, y1+40, 116, y1+380), 16, fill=TEAL)
text(d, (150, y1+50), "P4 · 订单与派单服务", f_body_b, TEAL)
text(d, (150, y1+120), "8 态履约状态机", f_small, INK)
text(d, (150, y1+170), "人工派单 + 时段冲突拦截", f_small, INK)
text(d, (150, y1+220), "陪玩入驻审核 · 档案管理", f_small, INK)
text(d, (150, y1+270), "订单增删改查", f_small, MUTED)
rounded(d, (150, y1+320, 420, y1+370), 14, fill=TEAL_L)
text(d, (175, y1+327), "43 项测试通过", f_tag, TEAL)

# 底部：bug 修复 + 下一步
y2 = y1 + 460
rounded(d, (60, y2, W-60, H-60), 28, fill=AMBER_L)
text(d, (100, y2+35), "本次修复 3 个隐蔽 bug", f_body_b, AMBER)
text(d, (100, y2+100), "· PATCH /me/ 丢陪玩字段", f_small, INK)
text(d, (100, y2+148), "· 接单开关缺事务 500", f_small, INK)
text(d, (100, y2+196), "· 审核接口同类 bug", f_small, INK)
text(d, (100, y2+262), "下一步 P5：售后结算 + 上线部署", f_small, AMBER)

save(img, "xhs-01-cover.png")

# ============ 2. 方图 P3 卡 1080x1080 ============
W, H = 1080, 1080
img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)
rounded(d, (0, 0, W, 200), 0, fill=BLUE_L)
text(d, (80, 60), "P3 · 真实微信登录", f_big, BLUE)
text(d, (80, 130), "账号体系从「演示」到「真机」", f_body, MUTED)

steps = [
    ("01", "uni.login 取 code", "小程序端拉起微信授权"),
    ("02", "code2session 换 openid", "服务端调微信接口"),
    ("03", "openid 归并建号", "同 openid 不重复建号"),
    ("04", "签发自有 Token", "Bearer 鉴权闭环"),
]
y = 260
for num, t1, t2 in steps:
    rounded(d, (80, y, W-80, y+170), 24, fill=BG)
    rounded(d, (100, y+35, 190, y+135), 18, fill=BLUE)
    text_center(d, 145, y+52, num, font(FONT_YAHEI_B, 40), WHITE)
    text(d, (230, y+42), t1, f_body_b, INK)
    text(d, (230, y+100), t2, f_small, MUTED)
    y += 200

save(img, "xhs-02-p3-wechat.png")

# ============ 3. 方图 P4 卡（状态机）1080x1080 ============
W, H = 1080, 1080
img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)
rounded(d, (0, 0, W, 200), 0, fill=TEAL_L)
text(d, (80, 60), "P4 · 订单与派单服务", f_big, TEAL)
text(d, (80, 130), "8 态履约状态机，全链路闭环", f_body, MUTED)

states = [
    "待付款", "待派单", "待陪玩确认", "已接单",
    "服务中", "待验收", "已完成", "已取消",
]
# 两列状态流
col_x = [80, W//2 + 40]
y = 260
for i, s in enumerate(states):
    col = i // 4
    row = i % 4
    x = col_x[col]
    yy = y + row * 180
    rounded(d, (x, yy, x+420, yy+140), 22, fill=BG)
    # 序号圆
    rounded(d, (x+20, yy+45, x+95, yy+120), 16, fill=TEAL)
    text_center(d, x+57, yy+58, str(i+1), font(FONT_YAHEI_B, 34), WHITE)
    text(d, (x+120, yy+55), s, f_body_b, INK)

# 底部特性
rounded(d, (80, 980, W-80, 1060), 0, fill=AMBER_L)
text_center(d, W//2, 1000, "人工派单 · 时段冲突拦截 · 陪玩入驻审核", f_small, AMBER)

save(img, "xhs-03-p4-order.png")

# ============ 4. 方图 Bug 修复卡 1080x1080 ============
W, H = 1080, 1080
img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)
rounded(d, (0, 0, W, 200), 0, fill=RED_L)
text(d, (80, 60), "修 bug 的日常", f_big, RED)
text(d, (80, 130), "SQLite 跑得通 ≠ PostgreSQL 跑得通", f_body, MUTED)

bugs = [
    ("接单开关 500", "select_for_update 缺事务", "加 @transaction.atomic"),
    ("工作台入口消失", "PATCH /me/ 漏返 is_partner", "GET/PATCH 统一返回"),
    ("审核接口 500", "同类行锁事务 bug", "一并修复"),
]
y = 260
for t1, t2, t3 in bugs:
    rounded(d, (80, y, W-80, y+200), 24, fill=BG)
    text(d, (110, y+35), t1, f_body_b, INK)
    text(d, (110, y+95), "根因：" + t2, f_small, MUTED)
    text(d, (110, y+145), "修复：" + t3, f_small, TEAL)
    y += 230

# 金句
rounded(d, (80, y+10, W-80, y+150), 24, fill=AMBER_L)
text_center(d, W//2, y+45, "并发/锁相关代码，务必在真实数据库验证", f_small, AMBER)

save(img, "xhs-04-bugs.png")

# ============ 5. 横图技术栈卡 1080x720 ============
W, H = 1080, 720
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
text_center(d, W//2, 60, "技术栈速览", f_big, INK)

f_stack1 = font(FONT_YAHEI_B, 36)
f_stack2 = font(FONT_YAHEI, 30)
f_stack3 = font(FONT_YAHEI, 26)
stack = [
    ("后端", "Django 5 + DRF", "PostgreSQL", "乐观锁 · 幂等", PURPLE, PURPLE_L),
    ("小程序", "uni-app", "Vue3 + TS", "跨端 H5+小程序", BLUE, BLUE_L),
    ("管理端", "Vue3", "Element Plus", "CSRF 鉴权", TEAL, TEAL_L),
]
x0 = 60
card_w = 300
gap = 30
for i, (t1, t2, t3, key, c1, c2) in enumerate(stack):
    x = x0 + i * (card_w + gap)
    rounded(d, (x, 180, x+card_w, 620), 28, fill=WHITE, outline=(230,230,235), width=2)
    rounded(d, (x+40, 220, x+card_w-40, 300), 20, fill=c2)
    text_center(d, x+card_w//2, 240, t1, f_stack1, c1)
    text_center(d, x+card_w//2, 350, t2, f_stack2, INK)
    text_center(d, x+card_w//2, 410, t3, f_stack2, MUTED)
    rounded(d, (x+40, 500, x+card_w-40, 570), 16, fill=c2)
    text_center(d, x+card_w//2, 520, key, f_stack3, c1)

save(img, "xhs-05-stack.png")

# ============ 6. 方图 管理端功能卡 1080x1080 ============
W, H = 1080, 1080
img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)
rounded(d, (0, 0, W, 200), 0, fill=PURPLE_L)
text(d, (80, 60), "管理端 · 运营后台", f_big, PURPLE)
text(d, (80, 130), "一个人也要有专业的运营工具", f_body, MUTED)

feats = [
    ("订单管理", "增删改查 · 状态筛选 · 派单"),
    ("陪玩审核", "入驻申请 通过/驳回"),
    ("陪玩档案", "编辑 · 删除保护 · 接单开关"),
    ("商品/首页", "分区 · 类型 · 轮播配置"),
    ("操作日志", "全程留痕可追溯"),
]
y = 250
for t1, t2 in feats:
    rounded(d, (80, y, W-80, y+130), 22, fill=BG)
    rounded(d, (104, y+45, 116, y+85), 6, fill=PURPLE)
    text(d, (150, y+30), t1, f_body_b, INK)
    text(d, (150, y+80), t2, f_small, MUTED)
    y += 155

save(img, "xhs-06-admin.png")

# ============ 7. 方图 阶段路线图卡 1080x1080 ============
W, H = 1080, 1080
img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)
rounded(d, (0, 0, W, 200), 0, fill=AMBER_L)
text(d, (80, 60), "开发路线图", f_big, AMBER)
text(d, (80, 130), "五个阶段，一步步走", f_body, MUTED)

milestones = [
    ("P1", "基础框架", "Django + uni-app 脚手架", True),
    ("P2", "双端跑通", "管理端 CRUD + 小程序首页", True),
    ("P3", "真实微信登录", "openid 归并 + 数据安全", True),
    ("P4", "订单与派单", "8 态状态机 + 派单闭环", True),
    ("P5", "售后与上线", "结算 · HTTPS · 部署", False),
]
y = 250
for pid, t1, t2, done in milestones:
    color = TEAL if done else HINT
    bgc = TEAL_L if done else (240, 240, 240)
    rounded(d, (80, y, W-80, y+130), 22, fill=bgc)
    # 阶段徽标
    rounded(d, (104, y+30, 220, y+100), 16, fill=color)
    text_center(d, 162, y+45, pid, font(FONT_YAHEI_B, 36), WHITE)
    text(d, (250, y+28), t1, f_body_b, INK if done else MUTED)
    text(d, (250, y+78), t2, f_small, MUTED)
    # 完成标记
    if done:
        text(d, (W-190, y+40), "已完成", f_body_b, TEAL)
    else:
        text(d, (W-190, y+40), "规划中", f_body_b, HINT)
    y += 155

save(img, "xhs-07-roadmap.png")

print("ALL DONE")
