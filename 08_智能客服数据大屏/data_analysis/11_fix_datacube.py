# -*- coding: utf-8 -*-
"""
把大屏用的数据集改成「无年份」的中文标签版：
- 聊天密度月分布：月份 2023-09 → 9月，并补「序号」列（1-12，用于排序）
- 聊天密度小时分布：小时 → 0时…23时（同时保留「小时序号」）
- 月度主题趋势数据_长表：月份同上，主题1-5 → 业务化名称
- 情感分布 / 聊天词语频次数据：不动，仅复制
输出：C:\\数据大屏素材\\*_中文.xlsx 与同名 .csv
用法： python 11_fix_datacube.py
"""
import os

import cfg  # noqa: F401

import pandas as pd

SRC = r"C:\数据大屏素材"
OUT = r"C:\数据大屏素材"

TOPIC_MAP = {
    "主题1": "售后与退换",
    "主题2": "物流时效",
    "主题3": "选购咨询",
    "主题4": "配送取件",
    "主题5": "退款与质量",
}


def month_label(s: str) -> str:
    return f"{int(str(s).split('-')[1])}月"


def fix_month(df: pd.DataFrame, col: str = "月份") -> pd.DataFrame:
    df = df.copy()
    df["序号"] = range(1, len(df) + 1)
    df[col] = df[col].map(month_label)
    return df[["序号", col] + [c for c in df.columns if c not in ("序号", col)]]


def main():
    # 1. 月度密度
    d = pd.read_excel(os.path.join(SRC, "聊天密度月分布.xlsx"))
    d = fix_month(d)
    d.to_excel(os.path.join(OUT, "聊天密度月分布_中文.xlsx"), index=False)
    d.to_csv(os.path.join(OUT, "聊天密度月分布_中文.csv"), index=False, encoding="utf-8-sig")
    print("月分布：")
    print(d.head(12).to_string(index=False))

    # 2. 小时密度
    h = pd.read_excel(os.path.join(SRC, "聊天密度小时分布.xlsx"))
    h = h.copy()
    h["小时序号"] = h["小时"]
    h["小时"] = h["小时"].map(lambda x: f"{int(x)}时")
    h = h[["小时序号", "小时", "消息数", "占比"]]
    h.to_excel(os.path.join(OUT, "聊天密度小时分布_中文.xlsx"), index=False)
    h.to_csv(os.path.join(OUT, "聊天密度小时分布_中文.csv"), index=False, encoding="utf-8-sig")
    print("\n小时分布（前6行）：")
    print(h.head(6).to_string(index=False))

    # 3. 主题趋势（长表）
    t = pd.read_excel(os.path.join(SRC, "月度主题趋势数据_长表.xlsx"))
    t = t.copy()
    months = list(dict.fromkeys(t["月份"].tolist()))
    order = {m: i + 1 for i, m in enumerate(months)}
    t["序号"] = t["月份"].map(order)
    t["月份"] = t["月份"].map(month_label)
    t["主题"] = t["主题"].map(lambda x: TOPIC_MAP.get(x, x))
    t = t[["序号", "月份", "主题", "占比"]].sort_values(["序号", "主题"]).reset_index(drop=True)
    t.to_excel(os.path.join(OUT, "月度主题趋势数据_中文.xlsx"), index=False)
    t.to_csv(os.path.join(OUT, "月度主题趋势数据_中文.csv"), index=False, encoding="utf-8-sig")
    print("\n主题趋势（前5行）：")
    print(t.head(5).to_string(index=False))
    print("主题：", sorted(t["主题"].unique()))

    # 4. 原样复制另外两个
    for f in ("情感分布", "聊天词语频次数据"):
        src = os.path.join(SRC, f + ".xlsx")
        if os.path.exists(src):
            pd.read_excel(src).to_excel(os.path.join(OUT, f + "_中文.xlsx"), index=False)
            print("copied:", f)


if __name__ == "__main__":
    main()
