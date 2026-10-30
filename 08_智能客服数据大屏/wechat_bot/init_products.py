# -*- coding: utf-8 -*-
"""初始化商品价格表 / 用 CSV 覆盖真实价目。

用法：
    python init_products.py                  # 建表 + 灌入 products.sql 里的示例数据
    python init_products.py 价目表.csv        # 建表 + 用 CSV 覆盖

CSV 表头（UTF-8，逗号分隔，中文表头也行）：
    model,category,capacity_l,price,energy,warranty,stock,features
    型号,类型,容量,价格,能效,保修,库存,卖点

价格必须是整数（元），不要带「￥」「元」。
"""

import csv
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs"))
import pymysql  # noqa: E402

CONF = dict(
    host=os.getenv("MYSQL_HOST", "192.168.1.10"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", "root"),
    charset="utf8mb4",
)

BASE = os.path.dirname(os.path.abspath(__file__))
SQL_FILE = os.path.join(BASE, "products.sql")

HEADER_MAP = {
    "型号": "model", "model": "model",
    "类型": "category", "category": "category", "类别": "category",
    "容量": "capacity_l", "capacity_l": "capacity_l", "容量升": "capacity_l",
    "价格": "price", "售价": "price", "price": "price",
    "能效": "energy", "能效等级": "energy", "energy": "energy",
    "保修": "warranty", "保修政策": "warranty", "warranty": "warranty",
    "库存": "stock", "stock": "stock",
    "卖点": "features", "特点": "features", "features": "features",
}


def create_table(conn):
    with open(SQL_FILE, encoding="utf-8") as f:
        raw = f.read()
    raw = re.sub(r"--[^\n]*", "", raw)                 # 去掉行注释
    stmts = [s.strip() for s in raw.split(";") if s.strip()]
    with conn.cursor() as cur:
        for s in stmts:
            cur.execute(s)
    conn.commit()
    print(f"建表完成，执行 {len(stmts)} 条语句")


def load_csv(conn, path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("CSV 是空的")
        return

    def pick(row, key):
        for k, v in row.items():
            if HEADER_MAP.get((k or "").strip().lower()) == key or HEADER_MAP.get((k or "").strip()) == key:
                return (v or "").strip()
        return ""

    sql = ("INSERT INTO products (model,category,capacity_l,price,energy,warranty,stock,features) "
           "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE "
           "category=VALUES(category), capacity_l=VALUES(capacity_l), price=VALUES(price), "
           "energy=VALUES(energy), warranty=VALUES(warranty), stock=VALUES(stock), "
           "features=VALUES(features)")
    data = []
    for r in rows:
        model = pick(r, "model").upper()
        if not model:
            continue
        try:
            price = int(re.sub(r"[^\d]", "", pick(r, "price") or "0"))
            cap = int(re.sub(r"[^\d]", "", pick(r, "capacity_l") or "0"))
            stock = int(re.sub(r"[^\d]", "", pick(r, "stock") or "0"))
        except ValueError:
            print(f"跳过（数字有问题）: {model}")
            continue
        data.append((model, pick(r, "category") or "", cap, price,
                     pick(r, "energy"), pick(r, "warranty"), stock, pick(r, "features")))
    with conn.cursor() as cur:
        cur.executemany(sql, data)
    conn.commit()
    print(f"导入 {len(data)} 行")


def main():
    conn = pymysql.connect(**CONF)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE IF NOT EXISTS wechat DEFAULT CHARSET utf8mb4")
        conn.select_db("wechat")
        create_table(conn)
        if len(sys.argv) > 1:
            load_csv(conn, sys.argv[1])
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), MIN(price), MAX(price) FROM products")
            n, lo, hi = cur.fetchone()
            print(f"products 表：{n} 条，价格 {lo} ~ {hi} 元")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
