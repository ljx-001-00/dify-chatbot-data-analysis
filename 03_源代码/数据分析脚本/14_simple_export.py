# -*- coding: utf-8 -*-
"""
简化版数据集：不带序号/排名列，最多 3 列，用来排查平台预览空白的问题。
输出：C:\\数据大屏素材\\简化版\\*.xlsx / *.csv
用法： python 14_simple_export.py
"""
import os

import cfg  # noqa: F401

import pandas as pd

SRC = r"C:\数据大屏素材"
OUT = os.path.join(SRC, "简化版")
os.makedirs(OUT, exist_ok=True)

TOPIC_MAP = {"主题1": "售后与退换", "主题2": "物流时效", "主题3": "选购咨询",
             "主题4": "配送取件", "主题5": "退款与质量"}


def save(df, name):
    df.to_excel(os.path.join(OUT, name + ".xlsx"), index=False)
    df.to_csv(os.path.join(OUT, name + ".csv"), index=False, encoding="utf-8-sig")
    print(f"[ok] {name}: {df.shape[0]}x{df.shape[1]} -> {list(df.columns)}")


def main():
    m = pd.read_excel(os.path.join(SRC, "聊天密度月分布.xlsx")).copy()
    m["月份"] = m["月份"].map(lambda s: "%d月" % int(str(s).split("-")[1]))
    save(m[["月份", "消息数", "占比"]], "月分布")

    h = pd.read_excel(os.path.join(SRC, "聊天密度小时分布.xlsx")).copy()
    h["小时"] = h["小时"].map(lambda x: "%d时" % int(x))
    save(h[["小时", "消息数", "占比"]], "小时分布")

    w = pd.read_excel(os.path.join(SRC, "聊天词语频次数据.xlsx")).copy()
    w["词语"] = w["词语"].map(lambda x: {"价给": "报价", "没收": "没收到"}.get(str(x).strip(), str(x).strip()))
    w = w.groupby("词语", as_index=False)["频次"].sum().sort_values("频次", ascending=False).head(100)
    save(w[["词语", "频次"]], "词频")

    s = pd.read_excel(os.path.join(SRC, "情感分布.xlsx")).copy()
    s = s[["情感类别", "数量", "占比"]]
    save(s, "情感分布")

    share = pd.read_excel(os.path.join(SRC, "月度主题趋势数据_长表.xlsx")).copy()
    mm = pd.read_excel(os.path.join(SRC, "聊天密度月分布.xlsx"))
    tot = dict(zip(mm["月份"], mm["消息数"]))
    share["消息数"] = (share["月份"].map(tot) * share["占比"] / 100).round(0).astype(int)
    share["主题"] = share["主题"].map(lambda x: TOPIC_MAP.get(x, x))
    share["月份"] = share["月份"].map(lambda s: "%d月" % int(str(s).split("-")[1]))
    save(share[["月份", "主题", "消息数"]], "主题趋势")

    print("\n月分布预览：")
    print(m[["月份", "消息数", "占比"]].to_string(index=False))
    print("\n目录：", OUT)


if __name__ == "__main__":
    main()
