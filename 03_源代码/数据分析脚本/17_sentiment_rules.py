# -*- coding: utf-8 -*-
"""
情感重判（规则优先 + SnowNLP 兜底）
思路：
  1) 强负面评价词 → 负面
  2) 强正面表达   → 正面
  3) 疑问句/事务询问（无评价词） → 中性
  4) 其余交给 SnowNLP，但把阈值收紧到 0.75 / 0.15
输出：
  data/clean_with_sentiment_rule.csv   带新标签的全量结果（可追溯）
  C:\\数据大屏素材\\简化版\\情感分布.xlsx / .csv
用法： python 17_sentiment_rules.py
"""
import os
import re

import cfg  # noqa: F401

import pandas as pd

SRC = r"C:\数据大屏素材"
OUT = os.path.join(SRC, "简化版")

WINDOW = ["2023-09", "2023-10", "2023-11", "2023-12",
          "2024-01", "2024-02", "2024-03", "2024-04",
          "2024-05", "2024-06", "2024-07", "2024-08"]

NEG = ["太差", "很差", "差评", "垃圾", "骗", "坑人", "敷衍", "不理", "没人管", "气人", "生气",
       "失望", "恶心", "破损", "划痕", "坏了", "坏掉", "发霉", "异味", "漏发", "错发", "少发",
       "丢件", "投诉", "虚假", "质量问题", "不接受", "不给退", "推脱", "拖延", "太慢", "慢死",
       "催", "态度差", "不理人", "忽悠", "欺骗", "劣质", "次品", "退货都", "差劲", "服了",
       "过分", "离谱", "无语", "闹心", "糟心", "什么破", "再三", "第.次出问题"]

POS = ["谢谢", "感谢", "满意", "不错", "喜欢", "好评", "很棒", "棒", "及时", "赞", "贴心",
       "辛苦了", "太好了", "可以了", "收到货", "服务好", "态度好", "给力", "优秀", "完美"]

Q = ["吗", "呢", "怎么", "多少", "多久", "哪里", "哪个", "几种", "是否", "能不能",
     "有没有", "可不可以", "能否", "请问", "？", "?"]


def has(text, words):
    return any((re.search(w, text) if "." in w else (w in text)) for w in words)


def judge(text, score):
    t = str(text)
    neg, pos = has(t, NEG), has(t, POS)
    if neg and not pos:
        return "负面"
    if pos and not neg:
        return "正面"
    if has(t, Q):
        return "中性"
    if score >= 0.75:
        return "正面"
    if score <= 0.15:
        return "负面"
    return "中性"


def main():
    d = pd.read_csv(os.path.join("data", "clean_with_sentiment.csv"))
    d["月份"] = d["月份"].astype(str)
    d["情感_规则"] = [judge(t, s) for t, s in zip(d["text"], d["情感分"])]
    d.to_csv(os.path.join("data", "clean_with_sentiment_rule.csv"),
             index=False, encoding="utf-8-sig")

    sub = d[d["月份"].isin(WINDOW)]
    print("全量分布（规则版）：")
    print(d["情感_规则"].value_counts().to_string())
    print("\n12 个月窗口内：", len(sub))
    print(sub["情感_规则"].value_counts().to_string())

    s = (sub.groupby("情感_规则").size().rename("数量").reset_index()
         .rename(columns={"情感_规则": "情感类别"}))
    s["_o"] = s["情感类别"].map({"正面": 1, "中性": 2, "负面": 3})
    s = s.sort_values("_o").drop(columns="_o").reset_index(drop=True)
    s["占比"] = (s["数量"] / s["数量"].sum() * 100).round(2)

    s.to_excel(os.path.join(OUT, "情感分布.xlsx"), index=False)
    s.to_csv(os.path.join(OUT, "情感分布.csv"), index=False, encoding="utf-8-sig")
    print("\n导出：")
    print(s.to_string(index=False))

    print("\n判为负面的样例：")
    for t in d[d["情感_规则"] == "负面"]["text"].head(5):
        print("  -", str(t)[:40])
    print("\n判为中性的样例：")
    for t in d[d["情感_规则"] == "中性"]["text"].head(5):
        print("  -", str(t)[:40])


if __name__ == "__main__":
    main()

