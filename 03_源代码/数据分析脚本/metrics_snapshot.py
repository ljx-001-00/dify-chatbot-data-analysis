# -*- coding: utf-8 -*-
"""汇总报告用实测数据，输出 JSON。"""
import json
import os
import sys

import cfg  # noqa: F401
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs"))

M = {}

# ---------- 数据库 ----------
import pymysql

conn = pymysql.connect(host=os.getenv("MYSQL_HOST", "192.168.1.10"), port=3306, user="root",
                       password=os.getenv("MYSQL_PASSWORD", "<MYSQL_PASSWORD>"), database="chat", charset="utf8mb4",
                       connect_timeout=5)
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM records")
    M["records_rows"] = cur.fetchone()[0]
    cur.execute("SELECT MIN(time), MAX(time) FROM records")
    M["records_span"] = [str(x) for x in cur.fetchone()]
    cur.execute("SELECT COUNT(DISTINCT records) FROM records")
    M["records_distinct"] = cur.fetchone()[0]
conn.close()

conn = pymysql.connect(host=os.getenv("MYSQL_HOST", "192.168.1.10"), port=3306, user="root",
                       password=os.getenv("MYSQL_PASSWORD", "<MYSQL_PASSWORD>"), database="wechat", charset="utf8mb4",
                       connect_timeout=5)
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM chathistory")
    M["wechat_rows"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM chathistory WHERE response LIKE '%投诉、曝光%' "
                "OR response LIKE '%请注意措辞%' OR response LIKE '%记录在案%'")
    M["wechat_blocked"] = cur.fetchone()[0]
conn.close()

# ---------- 清洗结果 ----------
d = pd.read_csv(os.path.join("data", "clean_with_sentiment_rule.csv"))
M["clean_rows"] = int(len(d))
M["clean_months"] = int(d["月份"].nunique())
M["clean_month_min"] = str(d["月份"].min())
M["clean_month_max"] = str(d["月份"].max())
M["avg_len"] = round(float(d["text"].astype(str).str.len().mean()), 1)
d["小时"] = pd.to_datetime(d["time"]).dt.hour

win = ["2023-09", "2023-10", "2023-11", "2023-12", "2024-01", "2024-02",
       "2024-03", "2024-04", "2024-05", "2024-06", "2024-07", "2024-08"]
sub = d[d["月份"].isin(win)]
M["window_rows"] = int(len(sub))

# 小时分布
hour = sub["小时"].value_counts().sort_index()
M["hour_peak"] = int(hour.idxmax())
M["hour_peak_n"] = int(hour.max())
M["hour_low"] = int(hour.idxmin())
M["hour_low_n"] = int(hour.min())
M["busy_ratio"] = round(float(hour.loc[8:21].sum() / hour.sum() * 100), 2)

# 月分布
mon = sub["月份"].value_counts().sort_index()
M["month_top"] = [str(mon.idxmax()), int(mon.max())]
M["month_low"] = [str(mon.idxmin()), int(mon.min())]

# 情感
s = sub["情感_规则"].value_counts()
M["sentiment"] = {k: [int(v), round(v / len(sub) * 100, 2)] for k, v in s.items()}

# 主题分布（来自大屏数据集）
tp = pd.read_excel(r"C:\数据大屏素材\简化版\主题趋势.xlsx")
M["topic_counts"] = {str(k): int(v) for k, v in tp.groupby("主题")["消息数"].sum().items()}

print(json.dumps(M, ensure_ascii=False, indent=2))
with open(os.path.join("data", "report_metrics.json"), "w",
          encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=2)



