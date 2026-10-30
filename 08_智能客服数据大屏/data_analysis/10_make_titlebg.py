# -*- coding: utf-8 -*-
"""
生成标题背景光带：title-bg.png（1600×200 透明底）
比课件版增加：中心透镜光晕、双层光束、端部斜切括号、细密竖线栅格
输出：assets/parts/title-bg.png + title-bg@2x.png
用法： python 10_make_titlebg.py
"""
import os

import cfg  # noqa: F401

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1600, 200
S = 2
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "parts")
os.makedirs(OUT, exist_ok=True)

CYAN = (79, 216, 255)
PALE = (120, 235, 255)
DEEP = (46, 150, 235)


def px(v):
    return int(round(v * S))


def ribbon():
    """横向透镜状光晕主体"""
    w, h = W * S, H * S
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h / 2.0, w / 2.0

    # 横向衰减：中心最强
    ax = np.exp(-((xx - cx) / (w * 0.40)) ** 2)
    # 纵向衰减：窄，形成光带
    ay = np.exp(-((yy - cy) / (h * 0.26)) ** 2)

    rgba = np.zeros((h, w, 4), dtype=np.float32)
    alpha = 118.0 * ax * ay
    # 中心偏白，向两侧转深蓝
    t = np.clip(ax, 0, 1)[..., None]
    col = np.array(CYAN, np.float32) * t + np.array(DEEP, np.float32) * (1 - t)
    rgba[..., :3] = col
    rgba[..., 3] = alpha

    # 更亮的核心细带
    ay2 = np.exp(-((yy - cy) / (h * 0.045)) ** 2)
    core = 82.0 * (ax ** 1.6) * ay2
    for i in range(3):
        rgba[..., i] = rgba[..., i] * (1 - core / 255.0) + PALE[i] * (core / 255.0)
    rgba[..., 3] = np.clip(rgba[..., 3] + core * 0.85, 0, 255)

    return Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")


def shafts():
    """两道斜向光束"""
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = W * S, H * S
    d.polygon([(w * 0.06, h), (w * 0.30, 0), (w * 0.34, 0), (w * 0.10, h)],
              fill=(70, 190, 255, 16))
    d.polygon([(w * 0.90, h), (w * 0.66, 0), (w * 0.70, 0), (w * 0.94, h)],
              fill=(70, 190, 255, 16))
    return layer.filter(ImageFilter.GaussianBlur(px(9)))


def details():
    """端部括号、竖线栅格、上下细线"""
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = W * S, H * S
    cy = h // 2

    # 端部斜切括号
    arm, drop = 70, 42
    for x_end, sgn in [(px(26), 1), (w - px(26), -1)]:
        d.line([(x_end, cy - px(drop)), (x_end + sgn * px(arm), cy - px(drop))],
               fill=CYAN + (150,), width=px(2))
        d.line([(x_end, cy + px(drop)), (x_end + sgn * px(arm), cy + px(drop))],
               fill=CYAN + (150,), width=px(2))
        d.line([(x_end, cy - px(drop)), (x_end, cy + px(drop))],
               fill=CYAN + (90,), width=px(1.5))

    # 中央竖线栅格（短促的“频谱”感）
    for i in range(-9, 10):
        if i == 0:
            continue
        x = w // 2 + i * px(11)
        hh = px(30) * (1 - abs(i) / 11.0)
        a = int(70 * (1 - abs(i) / 11.0))
        d.line([(x, cy - hh), (x, cy + hh)], fill=CYAN + (a,), width=px(1))

    # 上下极细边线，向两端渐隐
    for dy in (-px(46), px(46)):
        for i in range(int(w * 0.62)):
            k = i / (w * 0.62)
            a = int(60 * (1 - k) ** 2)
            x = int(w * 0.19) + i
            d.point((x, cy + dy), fill=CYAN + (a,))
    return layer


def build():
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    img.alpha_composite(ribbon())
    img.alpha_composite(shafts())
    img.alpha_composite(details())
    # 整体再叠一层大光晕，让边缘柔和
    halo = img.filter(ImageFilter.GaussianBlur(px(14)))
    halo.putalpha(halo.getchannel("A").point(lambda v: int(v * 0.5)))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.alpha_composite(halo)
    out.alpha_composite(img)
    return out


def main():
    big = build()
    p2 = os.path.join(OUT, "title-bg@2x.png")
    big.save(p2, optimize=True)
    p1 = os.path.join(OUT, "title-bg.png")
    big.resize((W, H), Image.LANCZOS).save(p1, optimize=True)
    print("saved:", p2, os.path.getsize(p2) // 1024, "KB")
    print("saved:", p1, os.path.getsize(p1) // 1024, "KB")


if __name__ == "__main__":
    main()

