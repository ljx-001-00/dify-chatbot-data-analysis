# -*- coding: utf-8 -*-
"""
任务14：数据可视化展示
--------------------------------------------------
读取 output/ 下已生成的 CSV，画 5 张图存到 output/figs/：
  01_小时密度.png  02_月度密度.png  03_词云.png
  04_主题趋势.png  05_情感分布.png

用法： python 05_viz.py
"""
import os

from cfg import OUT_DIR                # 先导入 cfg 以挂载 libs

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import rcParams

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False

FIG = os.path.join(OUT_DIR, "figs")
os.makedirs(FIG, exist_ok=True)

C_MAIN, C_ACC, C_WARN = "#2E86DE", "#10AC84", "#EE5A24"


def p(name):
    return os.path.join(OUT_DIR, name)


def fig_hour():
    df = pd.read_csv(p("聊天密度小时分布.csv"))
    fig, ax = plt.subplots(figsize=(10, 4.6))
    colors = [C_ACC if 9 <= h <= 22 else "#B2BEC3" for h in df["小时"]]
    ax.bar(df["小时"], df["消息数"], color=colors, width=0.72)
    ax.set_xticks(range(0, 24))
    ax.set_xlabel("小时")
    ax.set_ylabel("消息数")
    ax.set_title("客户咨询的 24 小时分布（绿=营业时段）", fontsize=13, pad=12)
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    out = os.path.join(FIG, "01_小时密度.png")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("  ->", out)


def fig_month():
    df = pd.read_csv(p("聊天密度月分布.csv"))
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot(df["月份"], df["消息数"], marker="o", color=C_MAIN, linewidth=2.2)
    ax.fill_between(df["月份"], df["消息数"], min(df["消息数"]) * 0.9, color=C_MAIN, alpha=0.12)
    ax.set_ylabel("消息数")
    ax.set_title("近 12 个月咨询量趋势", fontsize=13, pad=12)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    out = os.path.join(FIG, "02_月度密度.png")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("  ->", out)


def fig_wordcloud():
    from wordcloud import WordCloud
    df = pd.read_csv(p("聊天词语频次数据.csv"))
    freq = dict(zip(df["词语"], df["频次"]))
    wc = WordCloud(font_path=r"C:\Windows\Fonts\msyh.ttc",
                   width=1400, height=800, background_color="white",
                   colormap="viridis", max_words=100).generate_from_frequencies(freq)
    fig, ax = plt.subplots(figsize=(11, 6.3))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("客户咨询高频词云（TOP100）", fontsize=14, pad=10)
    out = os.path.join(FIG, "03_词云.png")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("  ->", out)


def fig_topic():
    df = pd.read_csv(p("月度主题趋势数据.csv"))
    cols = [c for c in df.columns if c.startswith("主题")]
    fig, ax = plt.subplots(figsize=(10.5, 5))
    ax.stackplot(df["月份"], [df[c] for c in cols], labels=cols,
                 colors=plt.cm.Set3.colors[:len(cols)], alpha=0.92)
    ax.set_ylabel("占比 (%)")
    ax.set_ylim(0, 100)
    ax.set_title("各主题在近 12 个月中的占比变化", fontsize=13, pad=12)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=len(cols), frameon=False)
    out = os.path.join(FIG, "04_主题趋势.png")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("  ->", out)


def fig_sentiment():
    df = pd.read_csv(p("情感分布.csv"))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.4),
                                 gridspec_kw={"width_ratios": [1, 1.15]})
    colors = [C_ACC, "#F9CA24", C_WARN]
    a1.pie(df["数量"], labels=df["情感类别"], autopct="%1.1f%%", colors=colors,
           startangle=110, wedgeprops=dict(width=0.42, edgecolor="w"))
    a1.set_title("情感三分类占比", fontsize=12)

    t = pd.read_csv(p("情感趋势数据.csv"))
    for lab, c in zip(["正面", "中性", "负面"], colors):
        if lab in t.columns:
            a2.plot(t["月份"], t[lab], marker="o", markersize=4, label=lab, color=c, linewidth=1.8)
    a2.set_ylabel("占比 (%)")
    a2.set_title("情感倾向的月度变化", fontsize=12)
    plt.setp(a2.get_xticklabels(), rotation=45, ha="right")
    a2.legend(frameon=False)
    a2.grid(axis="y", alpha=0.25, linestyle="--")
    for s in ("top", "right"):
        a2.spines[s].set_visible(False)
    out = os.path.join(FIG, "05_情感分布.png")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("  ->", out)


def main():
    print("=" * 62)
    print("任务14  数据可视化")
    print("=" * 62)
    for fn in (fig_hour, fig_month, fig_wordcloud, fig_topic, fig_sentiment):
        try:
            fn()
        except FileNotFoundError as e:
            print(f"  跳过 {fn.__name__}：缺少输入文件 {e.filename}")
    print(f"\n全部图片 -> {FIG}")


if __name__ == "__main__":
    main()
