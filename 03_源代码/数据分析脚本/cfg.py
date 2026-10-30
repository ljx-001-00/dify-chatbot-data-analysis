# -*- coding: utf-8 -*-
"""公共配置：数据库连接 + 路径 + 停用词"""
import os
import sys

# 让 Windows 上装的 pymysql 能被导入（之前 --target 装在 libs 目录）
_ROOT = os.path.dirname(os.path.abspath(__file__))
for p in [os.path.join(_ROOT, "..", "libs"), os.path.join(_ROOT, "libs")]:
    p = os.path.abspath(p)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

DB = dict(host=os.getenv("MYSQL_HOST", "192.168.1.10"), port=3306, user="root", password=os.getenv("MYSQL_PASSWORD", "<MYSQL_PASSWORD>"),
          charset="utf8mb4", autocommit=True)

DATA_DIR = os.path.join(_ROOT, "data")
OUT_DIR = os.path.join(_ROOT, "output")
for d in (DATA_DIR, OUT_DIR):
    os.makedirs(d, exist_ok=True)

# 中文停用词（电商客服场景，去掉无信息量的高频虚词与口头语）
STOPWORDS = set("""
的 了 是 我 你 他 她 它 们 在 有 和 就 都 也 还 要 会 能 可以 这个 那个
吗 呢 吧 啊 呀 哦 嗯 哈 呵 么 嘛 啦 哇 呗 着 过 地 得 把 被 让 给 对 从 到 与 及 或 而 但 却
请问 请 谢谢 你好 您好 老师 客服 亲 麻烦 一下 一个 什么 怎么 怎样 为什么 哪些 哪个 多少 多久
是不是 有没有 能不能 可不可以 如果 因为 所以 但是 而且 然后 现在 已经 一直 还是 就是 真的
我吗 那我 我这 我要 我想 你们 我们 他们 自己 这里 那里 这样 那样 时候 的话 一个 两个
这边 那边 显示 不能 没有 现在 需要 感觉 看看 查一下 好吗 是否 已经 还有 一点 有点
嗯 那个 这个 东西 情况 问题 麻烦 帮 弄 搞 行 好 对 是 在 有 个 条 次 元 块 天 小时 分钟
啊 呢 嘛 哎 唉 喂
""".split())

# 语料里的模板化套话（前后缀），占每条约 1/8，不剔掉会污染词频与 LDA
TEMPLATES = [
    "不好意思打扰了", "不好意思", "打扰了", "打扰一下",
    "麻烦问一下", "麻烦", "想咨询一下", "咨询一下", "请问",
    "客服你好", "您好", "你好", "在吗", "在不在",
    "谢谢", "多谢", "帮帮忙", "帮忙",
    "在线等", "这单还要吗", "这单还要", "还要吗",
    "请尽快回复", "尽快回复", "尽快", "回复",
    "急",
]

# 自定义词典：商品/业务词，防止被 jieba 切碎
USERDICT = [
    "热水器", "电热水器", "燃气热水器", "储水式", "即热式", "内胆", "加热管", "镁棒",
    "花洒", "混水阀", "进水阀", "安全阀", "温控器", "保温层", "漏电保护",
    "保修", "保价", "退换货", "优惠券", "满减", "会员价", "活动价", "发票",
    "安装", "上门", "售后", "维修", "换新", "以旧换新", "运费", "包邮",
    "功率", "升数", "容量", "能效", "一级能效", "二级能效", "耗电", "度数",
    "漏水", "不加热", "跳闸", "打不着火", "水不热", "出水小", "噪音大",
    "R40-A0", "R50-B2", "R60-A1", "R60-D5", "X50", "R80",
]
