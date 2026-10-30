# -*- coding: utf-8 -*-
"""
任务11（续）：聊天密度与词频统计
--------------------------------------------------
输入 data/clean.csv，输出三张表：
  output/聊天密度小时分布.csv   24 行（小时, 消息数, 占比）
  output/聊天密度月分布.csv     最近 12 个月（月份, 消息数, 占比）
  output/聊天词语频次数据.csv   TOP 100（词语, 频次）
同时把分词结果缓存到 data/tokens.pkl，供 LDA 复用。

用法： python 02_stats.py
"""
import os
import pickle

from cfg import DATA_DIR, OUT_DIR, STOPWORDS, USERDICT   # 先导入 cfg 以挂载 libs

import jieba
import pandas as pd

CLEAN_CSV = os.path.join(DATA_DIR, "clean.csv")
TOKENS_PKL = os.path.join(DATA_DIR, "tokens.pkl")


def load_tokens():
    if os.path.exists(TOKENS_PKL):
        with open(TOKENS_PKL, "rb") as f:
            return pickle.load(f)

    df = pd.read_csv(CLEAN_CSV)
    for w in USERDICT:
        jieba.add_word(w)

    tokens, docs = [], []
    for t in df.text.astype(str):
        words = []
        for w in jieba.cut(t):
            w = w.strip()
            if len(w) < 2:
                continue
            if w.isdigit():          # 纯数字（"30"、"20"）对主题无意义
                continue
            if w in STOPWORDS:
                continue
            if not w.replace("-", "").isalnum() and not all(
                    "\u4e00" <= ch <= "\u9fa5" for ch in w):
                continue
            words.append(w)
        docs.append(words)
        tokens.extend(words)

    with open(TOKENS_PKL, "wb") as f:
        pickle.dump((tokens, docs), f)
    return tokens, docs


def main():
    print("=" * 62)
    print("任务11  聊天密度与词频")
    print("=" * 62)

    df = pd.read_csv(CLEAN_CSV, parse_dates=["time"])
    print(f"读到清洗后语料 {len(df):,} 条")

    # ---------- 1. 小时分布 ----------
    hour = df.time.dt.hour.value_counts().reindex(range(24), fill_value=0).sort_index()
    hdf = pd.DataFrame({"小时": hour.index, "消息数": hour.values})
    hdf["占比"] = (hdf["消息数"] / hdf["消息数"].sum() * 100).round(2)
    p1 = os.path.join(OUT_DIR, "聊天密度小时分布.csv")
    hdf.to_csv(p1, index=False, encoding="utf-8-sig")
    peak = hdf.loc[hdf["消息数"].idxmax()]
    print(f"[1] 小时分布 -> {p1}")
    print(f"    峰值 {int(peak['小时'])} 点，{int(peak['消息数']):,} 条（{peak['占比']}%）")
    print(f"    夜间 0-6 点合计 {hdf[hdf['小时'] < 6]['占比'].sum():.1f}%")

    # ---------- 2. 月分布（最近 12 个月） ----------
    mp = df.time.dt.to_period("M")
    mdf = mp.value_counts().sort_index().tail(12)
    m = pd.DataFrame({"月份": [str(x) for x in mdf.index], "消息数": mdf.values})
    m["占比"] = (m["消息数"] / m["消息数"].sum() * 100).round(2)
    p2 = os.path.join(OUT_DIR, "聊天密度月分布.csv")
    m.to_csv(p2, index=False, encoding="utf-8-sig")
    print(f"[2] 月分布 -> {p2}（{len(m)} 行，{m['月份'].iloc[0]} ~ {m['月份'].iloc[-1]}）")

    # ---------- 3. 词频 TOP100 ----------
    tokens, _ = load_tokens()
    freq = pd.Series(tokens).value_counts().head(100)
    wdf = pd.DataFrame({"词语": freq.index, "频次": freq.values})
    p3 = os.path.join(OUT_DIR, "聊天词语频次数据.csv")
    wdf.to_csv(p3, index=False, encoding="utf-8-sig")
    print(f"[3] 词频 TOP100 -> {p3}（总词数 {len(tokens):,}）")
    print("    TOP10: " + "、".join(f"{w}({c})" for w, c in freq.head(10).items()))


if __name__ == "__main__":
    main()
