# -*- coding: utf-8 -*-
"""校验《电热水器商品介绍.md》里的价格表与 MySQL products 表是否一致。"""

import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "libs"))
import pymysql  # noqa: E402

MD = os.path.join(BASE, "知识库文件", "电热水器商品介绍.md")
ROW = re.compile(r"\|\s*\d\s*\|\s*([A-Z0-9\-]+)\s*\|\s*(\S+?)\s*\|\s*(\d+)\s*L\s*\|\s*(\d+)\s*\|")


def main():
    text = open(MD, encoding="utf-8").read()
    doc = {m: int(p) for m, _cat, _cap, p in ROW.findall(text)}
    if not doc:
        print("没有解析到价格表，检查 md 里的「全系价格一览」表格")
        return 1

    conn = pymysql.connect(host=os.getenv("MYSQL_HOST", "192.168.1.10"),
                           port=int(os.getenv("MYSQL_PORT", "3306")),
                           user=os.getenv("MYSQL_USER", "root"),
                           password=os.getenv("MYSQL_PASSWORD", "root"),
                           database=os.getenv("MYSQL_DB", "wechat"), charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT model, price FROM products")
            db = dict(cur.fetchall())
    finally:
        conn.close()

    same_tag, diff_tag = "一致", "不一致"
    ok = len(doc) == len(db)
    for model, price in sorted(doc.items(), key=lambda x: -x[1]):
        hit = db.get(model)
        same = hit == price
        ok = ok and same
        print(f"  {model:14s} 文档 {price:5d}  数据库 {str(hit):>5s}  {same_tag if same else diff_tag}")

    for model in set(db) - set(doc):
        print(f"  {model:14s} 只在数据库里，文档缺这一行")
    for model in set(doc) - set(db):
        print(f"  {model:14s} 只在文档里，数据库缺这一行")

    print("结论：" + ("全部一致" if ok else "存在差异，需修正"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
