# -*- coding: utf-8 -*-
"""
统一口径：把大屏所有图表都限定在「2023-09 ~ 2024-08」这 12 个月（17,191 条）。
重新导出小时分布 / 情感分布 / 词频，使 5 张图的数据可以互相对得上。
输出：C:\\数据大屏素材\\简化版\\*.xlsx / *.csv（覆盖同名文件）
用法： python 15_unify_window.py
"""
import os

import cfg  # noqa: F401

import pandas as pd

SRC = r"C:\数据大屏素材"
OUT = os.path.join(SRC, "简化版")
os.makedirs(OUT, exist_ok=True)

WINDOW = ["2023-09", "2023-10", "2023-11", "2023-12",
          "2024-01", "2024-02", "2024-03", "2024-04",
          "2024-05", "2024-06", "2024-07", "2024-08"]

STOP = set("价给 没收".split())


def save(df, name):
    df.to_excel(os.path.join(OUT, name + ".xlsx"), index=False)
    df.to_csv(os.path.join(OUT, name + ".csv"), index=False, encoding="utf-8-sig")
    print(f"[ok] {name}: {df.shape[0]} 行 -> {list(df.columns)}")


def main():
    d = pd.read_csv(os.path.join("data", "clean_with_sentiment.csv"))
    d["月份"] = d["月份"].astype(str)
    sub = d[d["月份"].isin(WINDOW)].copy()
    print("窗口内条数：", len(sub), " / 全量：", len(d))

    # 小时分布
    sub["小时"] = pd.to_datetime(sub["time"]).dt.hour
    h = (sub.groupby("小时").size().rename("消息数").reset_index()
         .sort_values("小时").reset_index(drop=True))
    h["占比"] = (h["消息数"] / h["消息数"].sum() * 100).round(2)
    h["小时"] = h["小时"].map(lambda x: "%d时" % int(x))
    save(h[["小时", "消息数", "占比"]], "小时分布")

    # 情感分布
    s = (sub.groupby("情感").size().rename("数量").reset_index()
         .rename(columns={"情感": "情感类别"}))
    order = {"正面": 1, "中性": 2, "负面": 3}
    s["_o"] = s["情感类别"].map(order)
    s = s.sort_values("_o").drop(columns="_o").reset_index(drop=True)
    s["占比"] = (s["数量"] / s["数量"].sum() * 100).round(2)
    save(s[["情感类别", "数量", "占比"]], "情感分布")

    print("\n小时合计：", int(h["消息数"].sum()))
    print("情感合计：", int(s["数量"].sum()))
    print(s.to_string(index=False))


if __name__ == "__main__":
    main()
