# -*- coding: utf-8 -*-
"""
把主题趋势从「占比(%)」改成「消息数(条)」，这样堆叠面积图才有高低起伏，
Y 轴量级也和「各月聊天趋势」对得上（各主题之和 = 当月总消息数）。
输出：C:\\数据大屏素材\\月度主题趋势数据_数量版.xlsx / .csv
用法： python 12_topic_counts.py
"""
import os

import cfg  # noqa: F401

import pandas as pd

SRC = r"C:\数据大屏素材"

TOPIC_MAP = {
    "主题1": "售后与退换",
    "主题2": "物流时效",
    "主题3": "选购咨询",
    "主题4": "配送取件",
    "主题5": "退款与质量",
}


def main():
    share = pd.read_excel(os.path.join(SRC, "月度主题趋势数据_长表.xlsx"))  # 月份 主题 占比
    month = pd.read_excel(os.path.join(SRC, "聊天密度月分布.xlsx"))          # 月份 消息数 占比

    total = dict(zip(month["月份"], month["消息数"]))
    order = {m: i + 1 for i, m in enumerate(month["月份"].tolist())}

    d = share.copy()
    d["序号"] = d["月份"].map(order)
    d["月总量"] = d["月份"].map(total)
    d["消息数"] = (d["月总量"] * d["占比"] / 100.0).round(0).astype(int)
    d["主题"] = d["主题"].map(lambda x: TOPIC_MAP.get(x, x))
    d["月份"] = d["月份"].map(lambda s: f"{int(str(s).split('-')[1])}月")

    out = d[["序号", "月份", "主题", "消息数"]].sort_values(["序号", "主题"]).reset_index(drop=True)

    p_x = os.path.join(SRC, "月度主题趋势数据_数量版.xlsx")
    out.to_excel(p_x, index=False)
    out.to_csv(os.path.join(SRC, "月度主题趋势数据_数量版.csv"), index=False, encoding="utf-8-sig")

    print(out.head(10).to_string(index=False))
    chk = out.groupby("月份", sort=False)["消息数"].sum()
    print("\n每月各主题之和：")
    print(chk.to_string())
    print("\n总量校验：", int(out["消息数"].sum()), "vs", int(month["消息数"].sum()))
    print("saved:", p_x)


if __name__ == "__main__":
    main()
