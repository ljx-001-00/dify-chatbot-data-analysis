# -*- coding: utf-8 -*-
"""
热水器客服 · 聊天数据可视化大屏（PyCharm + Flask + ECharts）

启动：
    python app.py
然后浏览器打开 http://127.0.0.1:5001

数据源：../data_analysis/datacube_export/*.csv
        （由 data_analysis/ 下的分析脚本产出，本程序只读取，不修改）
"""
import csv
import os
import sys
from datetime import datetime

from flask import Flask, jsonify, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data_analysis", "datacube_export")
DATA_DIR = os.path.normpath(DATA_DIR)

app = Flask(__name__)

# ---------------------------------------------------------------- 读取工具

def _read_csv(name):
    """读取 UTF-8-SIG 的 CSV，返回 list[dict]。文件缺失返回空列表。"""
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        sys.stderr.write("[warn] 缺少数据文件: %s\n" % path)
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _f(v, default=0.0):
    """安全转 float。"""
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return default


def _i(v, default=0):
    """安全转 int。"""
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return default


def _month_label(ym):
    """2023-09 -> 09月（大屏上不显示年份，避免 X 轴被当成日期字段）。"""
    s = str(ym).strip()
    if "-" in s:
        parts = s.split("-")
        if len(parts) >= 2:
            return "%02d月" % _i(parts[1], 0)
    return s


# LDA 主题编号 -> 业务主题名（依据 data_analysis/output/LDA主题词表.csv 的高频词人工归类）
TOPIC_NAME = {
    "主题1": "售后与退换",   # 地址/出库/收货/审核/申请/提交/退货
    "主题2": "物流时效",     # 物流/没动静/包裹/订单/同一个
    "主题3": "选购咨询",     # 合适/身高/体重/批发价/鼠标/无线
    "主题4": "配送取件",     # 快递/发货/送到/楼下/取件
    "主题5": "退款与质量",   # 退款/太贵/流程/太差/质量/凑单
}

# ---------------------------------------------------------------- 数据组装

def build_payload():
    sentiment = []           # [{name, value, pct}]
    sentiment_trend = {}     # {months:[], 正面:[], 中性:[], 负面:[]}
    topic_trend = {}         # {months:[], series:[{name, data}]}
    topic_dist = []          # [{name, value}]
    month_msg = {}           # {months:[], counts:[], pct:[]}
    hour_msg = {}            # {hours:[], counts:[], pct:[]}
    keywords = []            # [{name, value}]

    # ---- 1. 情感分布
    for row in _read_csv("情感分布.csv"):
        name = (row.get("情感类别") or "").strip()
        if not name:
            continue
        sentiment.append({
            "name": name,
            "value": _i(row.get("数量")),
            "pct": _f(row.get("占比")),
        })

    # ---- 2. 情感趋势（12 个月，百分比）
    rows = _read_csv("情感趋势数据.csv")
    if rows:
        sentiment_trend = {
            "months": [_month_label(r.get("月份")) for r in rows],
            "正面": [_f(r.get("正面")) for r in rows],
            "中性": [_f(r.get("中性")) for r in rows],
            "负面": [_f(r.get("负面")) for r in rows],
        }

    # ---- 3. 月度主题趋势（宽表 -> 多系列）
    rows = _read_csv("月度主题趋势数据.csv")
    if rows:
        topic_trend["months"] = [_month_label(r.get("月份")) for r in rows]
        topic_trend["series"] = []
        for key in ("主题1", "主题2", "主题3", "主题4", "主题5"):
            topic_trend["series"].append({
                "name": TOPIC_NAME.get(key, key),
                "data": [_f(r.get(key)) for r in rows],
            })

    # ---- 4. 主题总量分布（长表里是"每月各主题占比%"，按月取均值才是全期占比）
    acc = {}
    cnt = {}
    for row in _read_csv("月度主题趋势数据_长表.csv"):
        t = (row.get("主题") or "").strip()
        if not t:
            continue
        acc[t] = acc.get(t, 0.0) + _f(row.get("占比"))
        cnt[t] = cnt.get(t, 0) + 1
    for key in ("主题1", "主题2", "主题3", "主题4", "主题5"):
        if key in acc and cnt[key]:
            topic_dist.append({
                "name": TOPIC_NAME.get(key, key),
                "value": round(acc[key] / cnt[key], 1),
            })

    # ---- 5. 月度消息量
    rows = _read_csv("聊天密度月分布.csv")
    if rows:
        month_msg = {
            "months": [_month_label(r.get("月份")) for r in rows],
            "counts": [_i(r.get("消息数")) for r in rows],
            "pct": [_f(r.get("占比")) for r in rows],
        }

    # ---- 6. 24 小时聊天密度
    rows = _read_csv("聊天密度小时分布.csv")
    if rows:
        hour_msg = {
            "hours": ["%02d:00" % _i(r.get("小时")) for r in rows],
            "counts": [_i(r.get("消息数")) for r in rows],
            "pct": [_f(r.get("占比")) for r in rows],
        }

    # ---- 7. 高频关键词（取前 24）
    for row in _read_csv("聊天词语频次数据.csv"):
        w = (row.get("词语") or "").strip()
        if not w:
            continue
        keywords.append({"name": w, "value": _i(row.get("频次"))})
    keywords.sort(key=lambda x: -x["value"])
    keywords = keywords[:60]

    # ---------------------------------------------------------- KPI 推导
    total = sum(hour_msg.get("counts", []) or []) or sum(hour_msg.get("counts", []) or [])
    if not total:
        total = sum(x["value"] for x in sentiment)

    hours = hour_msg.get("hours") or []
    hcounts = hour_msg.get("counts") or []
    peak_hour, peak_n = "--", 0
    if hcounts:
        idx = hcounts.index(max(hcounts))
        peak_hour, peak_n = hours[idx], hcounts[idx]

    low_hour, low_n = "--", 0
    if hcounts:
        idx = hcounts.index(min(hcounts))
        low_hour, low_n = hours[idx], hcounts[idx]

    mon_counts = month_msg.get("counts") or []
    mon_months = month_msg.get("months") or []
    mon_top = {"month": "--", "n": 0}
    mon_low = {"month": "--", "n": 0}
    if mon_counts:
        i = mon_counts.index(max(mon_counts))
        mon_top = {"month": mon_months[i], "n": mon_counts[i]}
        j = mon_counts.index(min(mon_counts))
        mon_low = {"month": mon_months[j], "n": mon_counts[j]}

    neg = next((x for x in sentiment if x["name"] == "负面"), {"pct": 0.0, "value": 0})
    pos = next((x for x in sentiment if x["name"] == "正面"), {"pct": 0.0, "value": 0})

    kpi = {
        "total": total,
        "months": len(mon_counts),
        "peak_hour": peak_hour,
        "peak_n": peak_n,
        "low_hour": low_hour,
        "low_n": low_n,
        "month_top": mon_top,
        "month_low": mon_low,
        "neg_pct": neg["pct"],
        "neg_n": neg["value"],
        "pos_pct": pos["pct"],
        "pos_n": pos["value"],
        "topic_count": len(topic_dist),
        "keyword_count": len(keywords),
        "window_total": sum(mon_counts),
    }

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_dir": DATA_DIR,
        "kpi": kpi,
        "sentiment": sentiment,
        "sentiment_trend": sentiment_trend,
        "topic_trend": topic_trend,
        "topic_dist": topic_dist,
        "month_msg": month_msg,
        "hour_msg": hour_msg,
        "keywords": keywords,
    }


# ---------------------------------------------------------------- 路由

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(build_payload())


@app.route("/health")
def health():
    return jsonify({"ok": True, "data_dir": DATA_DIR, "exists": os.path.isdir(DATA_DIR)})


if __name__ == "__main__":
    if not os.path.isdir(DATA_DIR):
        print("[ERROR] 找不到数据目录: %s" % DATA_DIR)
        print("        请确认 dashboard/ 与 data_analysis/ 在同一级目录下。")
        sys.exit(1)

    port = int(os.environ.get("PORT", "5001"))
    print("=" * 62)
    print(" 热水器客服 · 聊天数据可视化大屏")
    print(" 数据目录 : %s" % DATA_DIR)
    print(" 访问地址 : http://127.0.0.1:%d" % port)
    print("=" * 62)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)