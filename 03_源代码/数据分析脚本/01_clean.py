# -*- coding: utf-8 -*-
"""
任务11：基于大模型的数据清洗和探索
--------------------------------------------------
从 MySQL 拉取原始聊天记录（chat.records 8.4 万条 + wechat.chathistory 真实对话），
做去空、去重、去噪声、长度过滤、文本规整，输出 clean.csv 并打印清洗前后对照。

用法： python 01_clean.py
"""
import os
import re

from cfg import DB, DATA_DIR, TEMPLATES          # 先导入 cfg：它会把 libs 加进 sys.path

import pandas as pd
import pymysql

OUT_CSV = os.path.join(DATA_DIR, "clean.csv")
RAW_CSV = os.path.join(DATA_DIR, "raw.csv")

# ---------- 噪声模式 ----------
RE_URL = re.compile(r"https?://\S+|www\.\S+")
RE_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E0-\U0001F1FF"
    "\u2190-\u21FF\u2B00-\u2BFF\uFE0F\u200d]+")
RE_QQNUM = re.compile(r"\b\d{5,}\b")          # 长串数字（QQ号/订单号）
RE_REPEAT = re.compile(r"(.)\1{3,}")            # 连续重复4次以上
RE_SPACE = re.compile(r"\s+")
RE_PUNCT_ONLY = re.compile(r"^[\W_]+$", re.UNICODE)


def normalize(s: str) -> str:
    """文本规整：去 URL / 表情 / 长数字 / 重复字符，统一空白与标点"""
    s = str(s)
    s = s.replace("\u3000", " ")
    s = RE_URL.sub(" ", s)
    s = RE_EMOJI.sub(" ", s)
    s = RE_QQNUM.sub(" ", s)
    s = RE_REPEAT.sub(r"\1", s)
    s = re.sub(r"[，,]{2,}", "，", s)
    s = re.sub(r"[!！?？。.]{2,}", "。", s)
    s = RE_SPACE.sub(" ", s)
    # 去掉模板套话（"不好意思打扰了…这单还要吗 在线等 啊" 这类）
    for ph in TEMPLATES:
        s = s.replace(ph, " ")
    s = RE_SPACE.sub(" ", s)
    return s.strip(" ，。,.;；")


def has_meaning(s: str, min_cn: int = 2) -> bool:
    """至少含 min_cn 个连续中文，才算有语义的客户咨询"""
    if not s:
        return False
    if RE_PUNCT_ONLY.match(s):
        return False
    cn = re.findall(r"[\u4e00-\u9fa5]", s)
    return len(cn) >= min_cn


def load_raw() -> pd.DataFrame:
    conn = pymysql.connect(**DB)
    try:
        df1 = pd.read_sql(
            "SELECT time, records AS text, 'chat.records' AS src FROM chat.records", conn)
        df2 = pd.read_sql(
            "SELECT create_time AS time, user_input AS text, 'wechat.chathistory' AS src "
            "FROM wechat.chathistory", conn)
    finally:
        conn.close()
    df = pd.concat([df1, df2], ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])
    return df

def main():
    print("=" * 62)
    print("任务11  数据清洗与探索")
    print("=" * 62)

    df = load_raw()
    n0 = len(df)
    # 实训期间（2026-10）产生的真实对话与预置语料时间轴不连续，
    # 若一起做月度趋势会出现大段空月，因此单独计数、不参与时序统计
    tail_cut = pd.Timestamp("2024-09-01")
    n_wechat = int((df.time >= tail_cut).sum())
    df = df[df.time < tail_cut]
    print(f"[1] 原始记录              : {n0:,} 条"
          f"（其中实训期真实对话 {n_wechat} 条，另计）")
    print(f"    参与分析              : {len(df):,} 条")
    print(f"    时间范围              : {df.time.min()} ~ {df.time.max()}")

    # --- 逐步清洗，每步记录剩余量，方便写报告 ---
    steps = []

    df["text"] = df["text"].astype(str).map(normalize)
    df = df[df.text != ""]
    steps.append(("去空与规整（URL/表情/长数字）", len(df)))

    df = df[df.text.map(has_meaning)]
    steps.append(("去纯符号 / 无中文语义", len(df)))

    df = df.drop_duplicates(subset=["text", "time"])
    steps.append(("按 (时间,文本) 去重", len(df)))

    df = df.drop_duplicates(subset=["text"])
    steps.append(("按文本内容去重", len(df)))

    L = df.text.str.len()
    df = df[(L >= 4) & (L <= 60)]
    steps.append(("长度过滤 4~60 字", len(df)))

    # 商业噪声：纯问候、纯"客服"、测试数据
    noise = r"^(你好|您好|在吗|在不在|客服|测试|test|hello|hi|哈喽|1+)$"
    df = df[~df.text.str.lower().str.match(noise)]
    steps.append(("去纯问候 / 测试数据", len(df)))

    df = df.sort_values("time").reset_index(drop=True)
    df["text_len"] = df.text.str.len()

    print(f"[2] 清洗步骤：")
    prev = n0
    for name, left in steps:
        print(f"     {name:<28} {left:>7,}  (剔除 {prev - left:>6,})")
        prev = left
    print(f"[3] 清洗后有效语料          : {len(df):,} 条  ({len(df)/n0*100:.1f}%)")

    # --- 探索性统计 ---
    print(f"[4] 探索：")
    print(f"     平均长度              : {df.text_len.mean():.1f} 字")
    print(f"     长度中位数            : {df.text_len.median():.0f} 字")
    print(f"     覆盖月份              : {df.time.dt.to_period('M').nunique()} 个")
    print(f"     高峰小时（消息最多）  : {df.time.dt.hour.value_counts().idxmax()} 点")
    top = df.text.value_counts().head(5)
    print(f"     最高频的 5 句话：")
    for t, c in top.items():
        print(f"        {c:>4}× {t[:40]}")

    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n[5] 已保存 -> {OUT_CSV}")


if __name__ == "__main__":
    main()
