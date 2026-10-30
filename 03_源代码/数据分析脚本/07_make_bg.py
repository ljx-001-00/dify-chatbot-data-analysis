# -*- coding: utf-8 -*-
"""
生成「科技感深蓝」大屏背景图（引力波式曲线 + 网格 + 星点）
输出：assets/bg06.png（3840×2160）、assets/bg06_1080.png（1920×1080）
用法： python 07_make_bg.py
"""
import os

import cfg  # noqa: F401  把 workspace/libs 加进 sys.path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 3840, 2160
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20261022)


def blank():
    return np.zeros((H, W, 3), dtype=np.float32)


def add_layer(img, layer, blur=0.0):
    if blur:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    a = np.array(layer, dtype=np.float32)
    return img + a[..., :3] * (a[..., 3:4] / 255.0)


def gradient_base():
    stops = [(0.00, (3, 9, 22)), (0.40, (9, 30, 61)),
             (0.72, (6, 20, 44)), (1.00, (2, 6, 16))]
    ys = np.linspace(0, 1, H)
    img = blank()
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        m = (ys >= t0) & (ys <= t1)
        k = ((ys[m] - t0) / (t1 - t0))[:, None, None]
        img[m, :, :] = np.array(c0, np.float32) * (1 - k) + np.array(c1, np.float32) * k
    return img


def radial_glow(img, cx, cy, rx, ry, color, strength):
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    g = np.clip(1 - d, 0, 1) ** 2.2
    for i in range(3):
        img[..., i] += color[i] * g * strength
    return img


def waves():
    """多条大振幅正弦曲线交织，模拟引力波 / 数据流"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    xs = np.arange(0, W + 8, 6, dtype=np.float32)

    for i in range(11):
        cy = H * (0.26 + 0.045 * i)
        A = H * (0.10 + 0.012 * i)
        k = 2 * np.pi / (W * (1.55 - 0.07 * i))
        ph = 0.62 * i
        ys = (cy + A * np.sin(k * xs + ph)
              + A * 0.34 * np.sin(k * 2.7 * xs + ph * 1.8)
              + A * 0.15 * np.sin(k * 5.1 * xs + ph * 2.9))
        pts = list(zip(xs.tolist(), ys.tolist()))
        alpha = int(58 + 30 * np.sin(i * 1.1) ** 2)
        d.line(pts, fill=(72, 172, 238, alpha), width=6)
        d.line([(x, y + 10) for x, y in pts], fill=(120, 205, 245, alpha // 2), width=3)

    # 中心最亮的两条
    for i, (amp, al) in enumerate([(0.16, 130), (0.12, 100)]):
        cy = H * (0.46 + 0.02 * i)
        k = 2 * np.pi / (W * 1.35)
        ys = cy + H * amp * np.sin(k * xs + 1.2 * i)
        d.line(list(zip(xs.tolist(), ys.tolist())), fill=(150, 230, 255, al), width=8)

    core = add_layer(blank(), layer, blur=2.5)
    halo = add_layer(blank(), layer.filter(ImageFilter.GaussianBlur(26)))
    return core + halo


def grid():
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    step = 120
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=(88, 158, 212, 13), width=1)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=(88, 158, 212, 13), width=1)
    a = np.array(layer, dtype=np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    fade = np.exp(-(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.5) / (H * 0.60)) ** 2))
    a[..., 3] *= fade
    return add_layer(blank(), Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA"))


def rings():
    """四角同心圆弧，压边"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    groups = [
        (int(W * 0.01), int(H * 1.02), [620, 900, 1180, 1460], (80, 175, 235)),
        (int(W * 1.01), int(H * -0.02), [520, 780, 1040, 1300], (70, 150, 225)),
    ]
    for cx, cy, radii, col in groups:
        for i, r in enumerate(radii):
            a = max(95 - i * 14, 26)
            d.arc([cx - r, cy - r, cx + r, cy + r], 200, 340, fill=col + (a,),
                  width=3 if i % 2 == 0 else 2)
            d.arc([cx - r, cy - r, cx + r, cy + r], 20, 160, fill=col + (max(a - 40, 16),), width=2)
    return add_layer(blank(), layer, blur=2.0)


def particles():
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(460):
        x = int(rng.integers(0, W))
        y = int(rng.integers(0, H))
        r = float(rng.choice([1.5, 2, 2.5, 3, 4, 5.5, 7]))
        a = int(rng.integers(35, 130))
        col = tuple(int(v) for v in rng.choice([[160, 215, 255], [120, 195, 245], [210, 240, 255]]))
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (a,))
    return add_layer(blank(), layer, blur=0.8)


def vignette(img):
    yy, xx = np.mgrid[0:H, 0:W]
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    v = np.clip(1.12 - 0.46 * np.sqrt(dx ** 2 * 0.8 + dy ** 2), 0.48, 1.04)
    return img * v[..., None]


def main():
    img = gradient_base()
    img = radial_glow(img, W * 0.50, H * 1.06, W * 0.62, H * 0.72, (26, 102, 168), 0.62)
    img = radial_glow(img, W * 0.03, H * 0.98, W * 0.34, H * 0.42, (18, 88, 150), 0.50)
    img = radial_glow(img, W * 0.99, H * 0.02, W * 0.32, H * 0.40, (16, 80, 140), 0.46)
    img += grid()
    img += waves()
    img += rings()
    img += particles()
    img = vignette(img)

    arr = np.clip(img, 0, 255).astype(np.uint8)
    im = Image.fromarray(arr, "RGB")
    big = os.path.join(OUT, "bg06.png")
    im.save(big, optimize=True)
    small = os.path.join(OUT, "bg06_1080.png")
    im.resize((1920, 1080), Image.LANCZOS).save(small, optimize=True)
    print("saved:", big, os.path.getsize(big) // 1024, "KB")
    print("saved:", small, os.path.getsize(small) // 1024, "KB")


if __name__ == "__main__":
    main()

