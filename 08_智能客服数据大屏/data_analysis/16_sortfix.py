# -*- coding: utf-8 -*-
"""
排序修复版：让平台的「字符串升序」也能排对
- 月份：'9月' -> '09月'（零填充，字典序 = 数值序）
- 小时：'0时' -> 0（纯数字，按数值排序）
输出：C:\\数据大屏素材\\简化版\\ 覆盖 月分布 / 小时分布 / 主题趋势
用法： python 16_sortfix.py
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

TOPIC_MAP = {"主题1": "售后与退换", "主题2": "物流时效", "主题3": "选购咨询",
             "主题4": "配送取件", "主题5": "退款与质量"}


def label(ym):
    return "%02d月" % int(str(ym).split("-")[1])


def save(df, name):
    df.to_excel(os.path.join(OUT, name + ".xlsx"), index=False)
    df.to_csv(os.path.join(OUT, name + ".csv"), index=False, encoding="utf-8-sig")
    print(f"[ok] {name}: {df.shape[0]} 行 -> {list(df.columns)}")


def main():
    d = pd.read_csv(os.path.join("data", "clean_with_sentiment.csv"))
    d["月份"] = d["月份"].astype(str)
    sub = d[d["月份"].isin(WINDOW)].copy()
    print("窗口内条数：", len(sub))

    # 1. 月分布（零填充标签，按月份数值排序）
    sub["月号"] = pd.to_datetime(sub["time"]).dt.month
    m = sub.groupby("月号").size().rename("消息数").reset_index().sort_values("月号")
    m["月份"] = m["月号"].map(lambda x: "%02d月" % int(x))
    m["占比"] = (m["消息数"] / m["消息数"].sum() * 100).round(2)
    save(m[["月份", "消息数", "占比"]], "月分布")

    # 2. 小时分布（纯数字小时）
    sub["小时"] = pd.to_datetime(sub["time"]).dt.hour
    h = sub.groupby("小时").size().rename("消息数").reset_index().sort_values("小时")
    h["占比"] = (h["消息数"] / h["消息数"].sum() * 100).round(2)
    save(h[["小时", "消息数", "占比"]], "小时分布")

    # 3. 主题趋势（条数版，月份同样零填充）
    share = pd.read_excel(os.path.join(SRC, "月度主题趋势数据_长表.xlsx")).copy()
    cnt = dict(zip(m["月号"], m["消息数"]))
    share["月号"] = share["月份"].map(lambda s: int(str(s).split("-")[1]))
    share["消息数"] = (share["月号"].map(cnt) * share["占比"] / 100).round(0).astype(int)
    share["月份"] = share["月号"].map(lambda x: "%02d月" % int(x))
    share["主题"] = share["主题"].map(lambda x: TOPIC_MAP.get(x, x))
    t = share.sort_values(["月号", "主题"])[["月份", "主题", "消息数"]].reset_index(drop=True)
    save(t, "主题趋势")

    print("\n月分布：")
    print(m[["月份", "消息数", "占比"]].to_string(index=False))
    print("\n小时前 6 行：")
    print(h[["小时", "消息数", "占比"]].head(6).to_string(index=False))
    print("\n主题前 6 行：")
    print(t.head(6).to_string(index=False))


if __name__ == "__main__":
    main()
