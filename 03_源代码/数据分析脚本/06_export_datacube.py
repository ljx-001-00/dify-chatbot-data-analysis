# -*- coding: utf-8 -*-
"""
任务14 数据准备：把 5 张表导出成「数据魔方」可直接上传的格式
------------------------------------------------------------
数据魔方（eduplus datacube）上传数据集的两个坑：
  1. CSV 带 BOM 时，第一列表头会变成 "\\ufeff小时"，字段识别失败 -> 这里写无 BOM 的 UTF-8
  2. 表头不能有空格/括号/特殊符号 -> 统一成中文纯词组
同时导出 .xlsx，平台只吃 Excel 时直接用。

用法： python 06_export_datacube.py
"""
import os

from cfg import OUT_DIR

import pandas as pd

EXPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datacube_export")
os.makedirs(EXPORT, exist_ok=True)

# 文件名 -> (源文件, 需要改名的列)
TABLES = {
    "聊天密度小时分布": ("聊天密度小时分布.csv", None),
    "聊天密度月分布": ("聊天密度月分布.csv", None),
    "月度主题趋势数据": ("月度主题趋势数据.csv", None),
    "情感分布": ("情感分布.csv", None),
    "聊天词语频次数据": ("聊天词语频次数据.csv", None),
}

# 额外给「趋势图」用（课件没列，但大屏上用得上）
EXTRA = {"情感趋势数据": "情感趋势数据.csv"}


def to_long_topic(df: pd.DataFrame) -> pd.DataFrame:
    """宽表转长表：月份/主题/占比，方便平台做多系列堆叠"""
    cols = [c for c in df.columns if c.startswith("主题")]
    return df.melt(id_vars="月份", value_vars=cols,
                   var_name="主题", value_name="占比")


def main():
    print("=" * 62)
    print("任务14  导出数据魔方上传文件")
    print("=" * 62)

    for name, (src, _) in TABLES.items():
        df = pd.read_csv(os.path.join(OUT_DIR, src))
        p_csv = os.path.join(EXPORT, f"{name}.csv")
        df.to_csv(p_csv, index=False, encoding="utf-8")          # 无 BOM
        df.to_excel(os.path.join(EXPORT, f"{name}.xlsx"), index=False)
        print(f"  {name:<16} {len(df):>4} 行 × {len(df.columns)} 列  {list(df.columns)}")

    # 主题趋势：额外一份长表
    t = pd.read_csv(os.path.join(OUT_DIR, "月度主题趋势数据.csv"))
    long = to_long_topic(t)
    long.to_csv(os.path.join(EXPORT, "月度主题趋势数据_长表.csv"), index=False, encoding="utf-8")
    long.to_excel(os.path.join(EXPORT, "月度主题趋势数据_长表.xlsx"), index=False)
    print(f"  {'月度主题趋势(长表)':<16} {len(long):>4} 行 × {len(long.columns)} 列  {list(long.columns)}")

    for name, src in EXTRA.items():
        df = pd.read_csv(os.path.join(OUT_DIR, src))
        df.to_csv(os.path.join(EXPORT, f"{name}.csv"), index=False, encoding="utf-8")
        df.to_excel(os.path.join(EXPORT, f"{name}.xlsx"), index=False)
        print(f"  {name:<16} {len(df):>4} 行 × {len(df.columns)} 列  {list(df.columns)}")

    print(f"\n导出目录: {EXPORT}")


if __name__ == "__main__":
    main()
