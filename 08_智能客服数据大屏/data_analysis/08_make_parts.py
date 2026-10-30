# -*- coding: utf-8 -*-
"""
生成大屏头部装饰组件：header-left.png / header-right.png（透明底 PNG）
风格：电路走线 + 折角 + 刻度组 + 光晕，比课件版更亮更精细
输出：assets/parts/*.png
用法： python 08_make_parts.py
"""
import os

import cfg  # noqa: F401

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 900, 150
S = 4  # 超采样倍数
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "parts")
os.makedirs(OUT, exist_ok=True)

CYAN = (79, 216, 255)
BLUE = (46, 168, 255)


def canvas():
    return Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))


def p(v):
    return int(round(v * S))


def draw_left():
    layer = canvas()
    d = ImageDraw.Draw(layer)
    base = H * 0.60
    lw = 3

    # —— 主走线：从左端淡入，带两处 45° 折角，右端收成箭头 ——
    y1 = base
    trace = [
        (0, y1), (W * 0.18, y1),
        (W * 0.24, y1 - 22), (W * 0.50, y1 - 22),
        (W * 0.56, y1), (W * 0.78, y1),
        (W * 0.83, y1 - 16), (W * 0.92, y1 - 16),
    ]
    d.line([(p(x), p(y)) for x, y in trace], fill=BLUE + (215,), width=lw * S, joint="curve")

    # —— 副走线：下方平行一条，更细更淡 ——
    y2 = base + 34
    trace2 = [(0, y2), (W * 0.30, y2), (W * 0.35, y2 - 14), (W * 0.62, y2 - 14)]
    d.line([(p(x), p(y)) for x, y in trace2], fill=CYAN + (120,), width=2 * S, joint="curve")

    # —— 右端箭头（指向标题） ——
    ax, ay = W * 0.92, y1 - 16
    d.polygon([(p(ax), p(ay - 13)), (p(ax + 26), p(ay)), (p(ax), p(ay + 13))],
              outline=CYAN + (235,), width=2 * S)

    # —— 刻度组：两组短竖线，像电路接口 ——
    for gx, n, gap, hgt in [(W * 0.07, 6, 9, 26), (W * 0.64, 8, 8, 20)]:
        for i in range(n):
            x = gx + i * gap
            d.line([(p(x), p(y1 - hgt)), (p(x), p(y1 - 4))], fill=CYAN + (150,), width=2 * S)

    # —— 节点：三处焊点 ——
    for nx, ny, r in [(W * 0.18, y1, 5), (W * 0.50, y1 - 22, 5), (W * 0.78, y1, 5)]:
        d.ellipse([p(nx - r), p(ny - r), p(nx + r), p(ny + r)], fill=CYAN + (245,))
        d.ellipse([p(nx - r - 6), p(ny - r - 6), p(nx + r + 6), p(ny + r + 6)],
                  outline=CYAN + (90,), width=1 * S)

    # —— 斜纹装饰（左下角） ——
    for i in range(5):
        x0 = W * 0.005 + i * 9
        d.line([(p(x0), p(y1 + 40)), (p(x0 + 16), p(y1 + 12))], fill=CYAN + (110,), width=2 * S)

    # 左侧渐隐蒙版（避免左边出现硬边）
    mask = Image.new("L", (W * S, H * S), 255)
    md = ImageDraw.Draw(mask)
    fade = int(W * 0.10) * S
    for i in range(fade):
        md.line([(i, 0), (i, H * S)], fill=int(255 * i / fade))
    layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", layer.size, 0), mask))
    return layer


def glow(layer, radius=6, strength=0.85):
    g = layer.filter(ImageFilter.GaussianBlur(radius * S))
    a = g.getchannel("A").point(lambda v: int(v * strength))
    g.putalpha(a)
    return g


def compose(base):
    """原图 + 两层光晕，超采样降回实际尺寸"""
    out = Image.new("RGBA", base.size, (0, 0, 0, 0))
    out.alpha_composite(glow(base, 10, 0.55))
    out.alpha_composite(glow(base, 3.5, 0.75))
    out.alpha_composite(base)
    return out.resize((W, H), Image.LANCZOS)


def main():
    left = compose(draw_left())
    right = left.transpose(Image.FLIP_LEFT_RIGHT)

    pl = os.path.join(OUT, "header-left.png")
    pr = os.path.join(OUT, "header-right.png")
    left.save(pl, optimize=True)
    right.save(pr, optimize=True)
    print("saved:", pl, os.path.getsize(pl) // 1024, "KB")
    print("saved:", pr, os.path.getsize(pr) // 1024, "KB")


if __name__ == "__main__":
    main()
