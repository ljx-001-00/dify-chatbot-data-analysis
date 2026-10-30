# -*- coding: utf-8 -*-
"""
任务12：基于 AI 的 LDA 主题分析
--------------------------------------------------
用 gensim 对清洗后的语料做 LDA 主题建模，输出：
  output/LDA主题词表.csv       每个主题的 TOP10 词及权重
  output/月度主题趋势数据.csv  月份 × 各主题占比（近12个月）

用法： python 03_lda.py [主题数，默认 5]
"""
import os
import pickle
import sys

from cfg import DATA_DIR, OUT_DIR      # 先导入 cfg 以挂载 libs

import pandas as pd
from gensim import corpora, models

CLEAN_CSV = os.path.join(DATA_DIR, "clean.csv")
TOKENS_PKL = os.path.join(DATA_DIR, "tokens.pkl")
K = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def main():
    print("=" * 62)
    print(f"任务12  LDA 主题分析（k={K}）")
    print("=" * 62)

    df = pd.read_csv(CLEAN_CSV, parse_dates=["time"])
    with open(TOKENS_PKL, "rb") as f:
        _, docs = pickle.load(f)
    assert len(docs) == len(df), "分词结果与语料行数不一致，请重跑 02_stats.py"

    # 过滤空文档
    keep = [i for i, d in enumerate(docs) if len(d) >= 2]
    df = df.iloc[keep].reset_index(drop=True)
    docs = [docs[i] for i in keep]
    print(f"参与建模的有效文档: {len(docs):,}")

    # ---------- 词典与向量 ----------
    dic = corpora.Dictionary(docs)
    dic.filter_extremes(no_below=5, no_above=0.5, keep_n=8000)
    corpus = [dic.doc2bow(d) for d in docs]
    print(f"词典规模: {len(dic):,} 词")

    # ---------- 训练 ----------
    lda = models.LdaModel(
        corpus=corpus, id2word=dic, num_topics=K,
        passes=8, iterations=80, random_state=42, alpha="auto", eta="auto")

    # ---------- 主题词表 ----------
    rows = []
    for tid in range(K):
        for word, w in lda.show_topic(tid, topn=10):
            rows.append({"主题编号": f"主题{tid+1}", "词语": word, "权重": round(float(w), 5)})
    tw = pd.DataFrame(rows)
    p1 = os.path.join(OUT_DIR, "LDA主题词表.csv")
    tw.to_csv(p1, index=False, encoding="utf-8-sig")
    print(f"[1] 主题词表 -> {p1}")
    for tid in range(K):
        words = "、".join(w for w, _ in lda.show_topic(tid, topn=8))
        print(f"    主题{tid+1}: {words}")

    # ---------- 每条文档的主主题 ----------
    def dominant(bow):
        dist = lda.get_document_topics(bow, minimum_probability=0)
        return max(dist, key=lambda x: x[1])[0]

    df["主题"] = [dominant(b) + 1 for b in corpus]

    # ---------- 月度主题趋势（近12个月） ----------
    df["月份"] = df.time.dt.to_period("M").astype(str)
    months = sorted(df["月份"].unique())[-12:]
    sub = df[df["月份"].isin(months)]
    piv = (sub.groupby(["月份", "主题"]).size()
              .unstack(fill_value=0))
    piv = piv.reindex(columns=range(1, K + 1), fill_value=0)
    pct = piv.div(piv.sum(axis=1), axis=0).mul(100).round(2)
    pct.columns = [f"主题{c}" for c in pct.columns]
    out = pct.reset_index()
    p2 = os.path.join(OUT_DIR, "月度主题趋势数据.csv")
    out.to_csv(p2, index=False, encoding="utf-8-sig")
    print(f"[2] 月度主题趋势 -> {p2}（{len(out)} 行 × {K} 主题）")
    print(out.to_string(index=False))

    # ---------- 全局主题占比 ----------
    share = (df["主题"].value_counts(normalize=True).sort_index() * 100).round(1)
    print("\n[3] 全局主题占比:")
    for t, v in share.items():
        print(f"    主题{t}: {v}%")


if __name__ == "__main__":
    main()
