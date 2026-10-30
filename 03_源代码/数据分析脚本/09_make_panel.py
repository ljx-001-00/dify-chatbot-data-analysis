# -*- coding: utf-8 -*-
"""
生成大屏面板底框：panel.png（500×400，透明底，四角切角科技风）
比课件版增加：四角 L 形亮角、顶部渐变加速条、内侧微光、斜纹角标
输出：assets/parts/panel.png（500×400）+ panel@2x.png（1000×800）
用法： python 09_make_panel.py
"""
import os

import cfg  # noqa: F401

from PIL import Image, ImageDraw, ImageFilter

W, H = 500, 400
S = 2  # 超采样
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "parts")
os.makedirs(OUT, exist_ok=True)

CYAN = (79, 216, 255)
DEEP = (46, 168, 255)


def px(v):
    return int(round(v * S))


def build():
    w, h = W * S, H * S
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    inset = 2
    x0, y0, x1, y1 = px(inset), px(inset), w - px(inset), h - px(inset)

    # —— 1. 内部极淡填充，让面板比背景“更实”一点 ——
    d.rounded_rectangle([x0, y0, x1, y1], radius=px(6), fill=(14, 42, 82, 84))

    # —— 2. 主体描边（1px 青蓝，alpha 偏低，不抢图表）——
    d.rounded_rectangle([x0, y0, x1, y1], radius=px(6), outline=DEEP + (120,), width=max(1, S))

    # —— 3. 四角 L 形亮角 ——
    L = 26
    lw = 2.5
    corners = [
        ((x0, y0 + L * S), (x0, y0), (x0 + L * S, y0)),                      # 左上
        ((x1 - L * S, y0), (x1, y0), (x1, y0 + L * S)),                      # 右上
        ((x0, y1 - L * S), (x0, y1), (x0 + L * S, y1)),                      # 左下
        ((x1 - L * S, y1), (x1, y1), (x1, y1 - L * S)),                      # 右下
    ]
    for p1, p2, p3 in corners:
        d.line([p1, p2, p3], fill=CYAN + (255,), width=px(lw), joint="curve")

    # —— 4. 顶部加速条：从左上角向右渐隐 ——
    bar_y = y0 + px(10)
    bar_len = int(w * 0.38)
    for i in range(bar_len):
        a = int(190 * (1 - i / bar_len) ** 1.6)
        d.line([(x0 + px(10) + i, bar_y), (x0 + px(10) + i, bar_y + px(2.2))],
               fill=CYAN + (a,))
    # 条尾小方点
    d.rectangle([x0 + px(10) + bar_len + px(4), bar_y - px(1),
                 x0 + px(10) + bar_len + px(9), bar_y + px(3.4)], fill=CYAN + (150,))

    # —— 5. 右上角斜纹（缺口装饰） ——
    for i in range(4):
        sx = x1 - px(14) - i * px(7)
        d.line([(sx, y0 + px(8)), (sx + px(9), y0 + px(17))], fill=CYAN + (95,), width=S)

    # —— 6. 底部细光带（很淡，托住面板） ——
    d.line([(x0 + px(30), y1 - px(1)), (x1 - px(30), y1 - px(1))],
           fill=CYAN + (46,), width=S)

    # —— 7. 左侧竖条指示 ——
    d.line([(x0 + px(1), y0 + px(46)), (x0 + px(1), y0 + px(46) + px(54))],
           fill=CYAN + (170,), width=px(2))

    return img


def with_glow(base):
    out = Image.new("RGBA", base.size, (0, 0, 0, 0))
    halo = base.filter(ImageFilter.GaussianBlur(px(7)))
    halo.putalpha(halo.getchannel("A").point(lambda v: int(v * 0.55)))
    out.alpha_composite(halo)
    out.alpha_composite(base)
    return out


def main():
    p2 = with_glow(build())
    out2 = os.path.join(OUT, "panel@2x.png")
    p2.save(out2, optimize=True)
    out1 = os.path.join(OUT, "panel.png")
    p2.resize((W, H), Image.LANCZOS).save(out1, optimize=True)
    print("saved:", out2, os.path.getsize(out2) // 1024, "KB")
    print("saved:", out1, os.path.getsize(out1) // 1024, "KB")


if __name__ == "__main__":
    main()

