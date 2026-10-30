# -*- coding: utf-8 -*-
"""
任务13：基于 AI 的文本情感分析
--------------------------------------------------
用 snownlp 对每条客户提问打情感分（0~1，越大越正面），三分类后输出：
  output/情感分布.csv        情感类别 / 数量 / 占比
  output/情感趋势数据.csv    月份 × 正面/中性/负面 占比
  data/clean_with_sentiment.csv

用法： python 04_sentiment.py
"""
import os

from cfg import DATA_DIR, OUT_DIR      # 先导入 cfg 以挂载 libs

import pandas as pd
from snownlp import SnowNLP

CLEAN_CSV = os.path.join(DATA_DIR, "clean.csv")
POS, NEG = 0.65, 0.35          # 情感阈值

LABELS = ["正面", "中性", "负面"]


def score(text: str) -> float:
    try:
        return SnowNLP(str(text)).sentiments
    except Exception:
        return 0.5


def classify(s: float) -> str:
    if s >= POS:
        return "正面"
    if s <= NEG:
        return "负面"
    return "中性"


def main():
    print("=" * 62)
    print("任务13  文本情感分析（snownlp）")
    print("=" * 62)

    df = pd.read_csv(CLEAN_CSV, parse_dates=["time"])
    print(f"待分析语料: {len(df):,} 条（snownlp 逐条打分，约需 1~3 分钟）")

    df["情感分"] = [score(t) for t in df.text]
    df["情感"] = df["情感分"].map(classify)

    # ---------- 分布 ----------
    vc = df["情感"].value_counts().reindex(LABELS, fill_value=0)
    dist = pd.DataFrame({
        "情感类别": LABELS,
        "数量": vc.values,
        "占比": (vc.values / len(df) * 100).round(2),
    })
    p1 = os.path.join(OUT_DIR, "情感分布.csv")
    dist.to_csv(p1, index=False, encoding="utf-8-sig")
    print(f"\n[1] 情感分布 -> {p1}")
    print(dist.to_string(index=False))
    print(f"    平均情感分: {df['情感分'].mean():.3f}")

    # 各类别代表句
    print("\n[2] 典型样本:")
    for lab in LABELS:
        s = df[df["情感"] == lab]
        if len(s):
            print(f"    {lab}(n={len(s)}): {s.iloc[0].text[:36]}")

    # ---------- 月度趋势 ----------
    df["月份"] = df.time.dt.to_period("M").astype(str)
    months = sorted(df["月份"].unique())[-12:]
    sub = df[df["月份"].isin(months)]
    piv = sub.groupby(["月份", "情感"]).size().unstack(fill_value=0).reindex(columns=LABELS, fill_value=0)
    pct = piv.div(piv.sum(axis=1), axis=0).mul(100).round(2).reset_index()
    p2 = os.path.join(OUT_DIR, "情感趋势数据.csv")
    pct.to_csv(p2, index=False, encoding="utf-8-sig")
    print(f"\n[3] 情感月度趋势 -> {p2}")
    print(pct.to_string(index=False))

    p3 = os.path.join(DATA_DIR, "clean_with_sentiment.csv")
    df.to_csv(p3, index=False, encoding="utf-8-sig")
    print(f"\n[4] 带情感标签的明细 -> {p3}")


if __name__ == "__main__":
    main()
