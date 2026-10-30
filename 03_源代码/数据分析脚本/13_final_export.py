# -*- coding: utf-8 -*-
"""
最终版数据集统一导出（大屏用）
输出目录：C:\\数据大屏素材\\最终版\\
  01_聊天密度小时分布.xlsx   小时序号 小时 消息数 占比
  02_聊天密度月分布.xlsx     序号 月份 消息数 占比
  03_聊天词语频次.xlsx       排名 词语 频次      （已清洗少量切词碎片）
  04_月度主题趋势.xlsx       序号 月份 主题 消息数   （条数版，可堆叠）
  05_情感分布.xlsx           排序 情感类别 数量 占比
用法： python 13_final_export.py
"""
import os

import cfg  # noqa: F401

import pandas as pd

SRC = r"C:\数据大屏素材"
OUT = os.path.join(SRC, "最终版")
os.makedirs(OUT, exist_ok=True)

TOPIC_MAP = {
    "主题1": "售后与退换",
    "主题2": "物流时效",
    "主题3": "选购咨询",
    "主题4": "配送取件",
    "主题5": "退款与质量",
}

# 切词碎片纠正
WORD_FIX = {"价给": "报价", "没收": "没收到"}


def save(df, name):
    p = os.path.join(OUT, name + ".xlsx")
    df.to_excel(p, index=False)
    df.to_csv(os.path.join(OUT, name + ".csv"), index=False, encoding="utf-8-sig")
    print(f"[ok] {name:<20} {df.shape[0]} 行 × {df.shape[1]} 列  -> {p}")


def main():
    # 1. 小时分布
    h = pd.read_excel(os.path.join(SRC, "聊天密度小时分布.xlsx"))
    h = h.copy()
    h["小时序号"] = h["小时"].astype(int)
    h["小时"] = h["小时"].map(lambda x: f"{int(x)}时")
    save(h[["小时序号", "小时", "消息数", "占比"]], "01_聊天密度小时分布")

    # 2. 月分布
    m = pd.read_excel(os.path.join(SRC, "聊天密度月分布.xlsx")).copy()
    m["序号"] = range(1, len(m) + 1)
    m["月份"] = m["月份"].map(lambda s: f"{int(str(s).split('-')[1])}月")
    save(m[["序号", "月份", "消息数", "占比"]], "02_聊天密度月分布")

    # 3. 词频（清洗碎片 + 加排名）
    w = pd.read_excel(os.path.join(SRC, "聊天词语频次数据.xlsx")).copy()
    w["词语"] = w["词语"].map(lambda x: WORD_FIX.get(str(x).strip(), str(x).strip()))
    w = (w.groupby("词语", as_index=False)["频次"].sum()
          .sort_values("频次", ascending=False).head(100).reset_index(drop=True))
    w["排名"] = w.index + 1
    save(w[["排名", "词语", "频次"]], "03_聊天词语频次")

    # 4. 主题趋势（条数版）
    share = pd.read_excel(os.path.join(SRC, "月度主题趋势数据_长表.xlsx"))
    tot = dict(zip(pd.read_excel(os.path.join(SRC, "聊天密度月分布.xlsx"))["月份"],
                   pd.read_excel(os.path.join(SRC, "聊天密度月分布.xlsx"))["消息数"]))
    order = {k: i + 1 for i, k in enumerate(tot.keys())}
    t = share.copy()
    t["序号"] = t["月份"].map(order)
    t["消息数"] = (t["月份"].map(tot) * t["占比"] / 100).round(0).astype(int)
    t["主题"] = t["主题"].map(lambda x: TOPIC_MAP.get(x, x))
    t["月份"] = t["月份"].map(lambda s: f"{int(str(s).split('-')[1])}月")
    t = t[["序号", "月份", "主题", "消息数"]].sort_values(["序号", "主题"]).reset_index(drop=True)
    save(t, "04_月度主题趋势")

    # 5. 情感分布（加排序 + 占比文本，便于标签显示）
    s = pd.read_excel(os.path.join(SRC, "情感分布.xlsx")).copy()
    rank = {"正面": 1, "中性": 2, "负面": 3}
    s["排序"] = s["情感类别"].map(rank).fillna(9).astype(int)
    s = s.sort_values("排序").reset_index(drop=True)
    s["占比"] = s["占比"].round(2)
    save(s[["排序", "情感类别", "数量", "占比"]], "05_情感分布")

    print("\n情感分布：")
    print(s[["情感类别", "数量", "占比"]].to_string(index=False))
    print("\n目录：", OUT)


if __name__ == "__main__":
    main()
