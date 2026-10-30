# -*- coding: utf-8 -*-
"""价格 / 型号 / 排名类问题的结构化查询路由。

设计目标：把「最贵、最便宜、多少钱、有哪些型号」这类**全局或精确**问题
从 RAG 检索中拿出来，直接查 MySQL 得出唯一确定的答案。

- 命中价格意图：返回话术（毫秒级，结果确定，不经过 LLM）
- 未命中：返回 None，调用方回退到 Dify 工作流

这样模型不再有机会"从 4 段文字里挑一个价格"，价格永远不会漂移。
"""

import logging
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs"))

try:
    import pymysql
except ImportError:                      # 没装就整体降级为"不接管"
    pymysql = None

log = logging.getLogger("bot")

MYSQL_CONF = dict(
    host=os.getenv("MYSQL_HOST", "192.168.1.10"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", "root"),
    database=os.getenv("MYSQL_DB", "wechat"),
    charset="utf8mb4",
    connect_timeout=2,
    read_timeout=3,
)

# 型号：JSQ30-16HM8 / R40-A0 / X50-B2（要求 ≥2 位数字，避免误伤 16L 这类）
_MODEL_RE = re.compile(r"[A-Z]{1,4}\d{2,4}(?:-[A-Z0-9]{2,6})?", re.I)
_MAX_RE = re.compile(r"最贵|最高价|价格最高|最豪华|顶配")
_MIN_RE = re.compile(r"最便宜|最低价|价格最低|最实惠")
_PRICE_RE = re.compile(r"多少钱|价格|售价|报价|什么价|几块钱|怎么卖")
_LIST_RE = re.compile(r"有哪些型号|都有什么型号|全部型号|型号列表|都有哪些|推荐几款|有什么型号")
_COMPARE_RE = re.compile(r"对比|区别|差别|哪个好|选哪个")
_CAP_RE = re.compile(r"(\d{2,3})\s*(?:L|升|l)")

_LIMIT_LIST = 8


def _conn():
    if pymysql is None:
        return None
    try:
        return pymysql.connect(**MYSQL_CONF)
    except Exception as e:                # noqa: BLE001
        log.warning("价格路由连不上 MySQL，降级走工作流: %s", e)
        return None


def _query(sql, args=()):
    conn = _conn()
    if conn is None:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    except Exception as e:                # noqa: BLE001
        log.warning("价格查询失败: %s | %s", e, sql)
        return None
    finally:
        conn.close()


def _fmt(row):
    """把一行商品格式化成客服口吻。"""
    model, cat, cap, price, energy, warranty = row[:6]
    tail = []
    if energy:
        tail.append(f"{energy}能效")
    if warranty:
        tail.append(warranty)
    extra = "，".join(tail)
    return f"{model}（{cat} {cap}L）售价 {price} 元" + (f"，{extra}" if extra else "")


def _find_models(text):
    """从问句里抽出所有像型号的词，并回库校验是否真实存在。"""
    cands = {m.group(0).upper() for m in _MODEL_RE.finditer(text)}
    if not cands:
        return []
    marks = ",".join(["%s"] * len(cands))
    rows = _query(f"SELECT model FROM products WHERE UPPER(model) IN ({marks})",
                  tuple(cands))
    if rows is None:
        return []
    return [r[0] for r in rows]


def answer_price_question(text):
    """命中价格类意图就返回确定话术，否则返回 None。"""
    if pymysql is None or not text:
        return None

    q = text.strip()

    # 型号比较：A 和 B 对比
    models = _find_models(q)
    if len(models) >= 2 and _COMPARE_RE.search(q):
        marks = ",".join(["%s"] * len(models))
        rows = _query(
            f"SELECT model,category,capacity_l,price,energy,warranty FROM products "
            f"WHERE model IN ({marks}) ORDER BY price DESC", tuple(models))
        if rows:
            head = "这两款的差别：\n"
            body = "\n".join("· " + _fmt(r) for r in rows)
            cheap = rows[-1]
            return head + body + f"\n差价 {rows[0][3] - cheap[3]} 元，预算够就上贵的，追求性价比选 {cheap[0]}。"

    # 单型号问价
    if models and _PRICE_RE.search(q):
        rows = _query(
            "SELECT model,category,capacity_l,price,energy,warranty,stock,features "
            "FROM products WHERE model=%s", (models[0],))
        if rows:
            r = rows[0]
            stock = "有现货" if (r[6] or 0) > 0 else "暂时缺货，需要预订"
            return (f"{_fmt(r)}。{r[7] or ''}\n{stock}，需要我帮您预约安装吗？")

    # 最贵 / 最便宜
    if _MAX_RE.search(q) or _MIN_RE.search(q):
        order = "DESC" if _MAX_RE.search(q) else "ASC"
        word = "最贵" if order == "DESC" else "最便宜"
        rows = _query(
            f"SELECT model,category,capacity_l,price,energy,warranty FROM products "
            f"ORDER BY price {order} LIMIT 2")
        if rows:
            top = rows[0]
            msg = f"目前{word}的是 {_fmt(top)}。"
            if len(rows) > 1:
                msg += f"\n第二{'贵' if order == 'DESC' else '便宜'}的是 {rows[1][0]}（{rows[1][3]} 元）。"
            msg += "\n需要我帮您看看这款的安装或优惠吗？"
            log.info("价格路由命中: %s -> %s %s 元", q[:20], top[0], top[3])
            return msg

    # 按容量问价：「40 升的多少钱」
    cap_hit = _CAP_RE.search(q)
    if _PRICE_RE.search(q) and cap_hit and not models:
        cap = int(cap_hit.group(1))
        rows = _query(
            "SELECT model,category,capacity_l,price,energy,warranty FROM products "
            "WHERE capacity_l=%s ORDER BY price ASC", (cap,))
        if rows:
            body = "\n".join(f"· {_fmt(r)}" for r in rows)
            return f"{cap} 升的有 {len(rows)} 款：\n{body}\n您看哪款合适？"

    # 全部型号 / 推荐
    if _LIST_RE.search(q):
        rows = _query(
            f"SELECT model,category,capacity_l,price,energy,warranty FROM products "
            f"ORDER BY price ASC LIMIT {_LIMIT_LIST}")
        if rows:
            body = "\n".join(f"· {_fmt(r)}" for r in rows)
            return f"目前在售 {len(rows)} 款（按价格从低到高）：\n{body}\n您家里几口人用？我帮您挑一款。"

    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for t in ["最贵的是哪款", "最便宜的呢", "JSQ30-16HM8多少钱",
              "R40-A0 和 R60-A1 有什么区别", "你们有哪些型号", "漏水怎么办"]:
        print(f"Q: {t}\nA: {answer_price_question(t)}\n" + "-" * 50)
