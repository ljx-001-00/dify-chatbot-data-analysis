# -*- coding: utf-8 -*-
"""
把 Flask 大屏导出为纯静态站点（GitHub Pages 用）

用法：
    python export_static.py

做法：
    1. 复用 app.build_payload() 的数据组装逻辑，导出 data.json
    2. 复制 static/ 资源
    3. 把 index.html 里的 url_for 换成相对路径
    4. 把 screen.js 的 /api/dashboard 换成相对 data.json 路径

产物写到仓库根的 docs/ ，GitHub Pages 选 main 分支 /docs 目录即可。
"""
import json
import os
import re
import shutil
import sys
import types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(BASE_DIR)                 # 08_智能客服数据大屏
REPO_ROOT = os.path.dirname(PKG_DIR)                # 仓库根
DOCS_DIR = os.path.join(REPO_ROOT, "docs")

# ---- 用假 flask 模块骗过 app.py 的模块级 app = Flask(__name__) ----
fake = types.ModuleType("flask")


class _FakeFlask(object):
    def __init__(self, *a, **k):
        pass

    def route(self, *a, **k):
        def deco(fn):
            return fn
        return deco

    def run(self, *a, **k):
        pass


fake.Flask = _FakeFlask
fake.jsonify = lambda x: x
fake.render_template = lambda *a, **k: ""
sys.modules["flask"] = fake

sys.path.insert(0, BASE_DIR)
import app  # noqa: E402


def build_payload():
    payload = app.build_payload()
    # 不把本机绝对路径写进公开 JSON
    payload.pop("data_dir", None)
    payload["source"] = "MySQL chat.records → data_analysis/datacube_export"
    return payload


def main():
    if os.path.isdir(DOCS_DIR):
        shutil.rmtree(DOCS_DIR)
    os.makedirs(DOCS_DIR)

    # 1) data.json
    payload = build_payload()
    out_json = os.path.join(DOCS_DIR, "data.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print("[1] data.json  %.1f KB" % (os.path.getsize(out_json) / 1024))
    kpi = payload["kpi"]
    print("    消息 %s / 月份 %s / 负面 %s%% / 关键词 %s"
          % (kpi["total"], kpi["months"], kpi["neg_pct"], kpi["keyword_count"]))

    # 2) static 资源
    shutil.copytree(os.path.join(BASE_DIR, "static"), os.path.join(DOCS_DIR, "static"))
    print("[2] static/ 已复制")

    # 3) index.html：url_for -> 相对路径
    html = open(os.path.join(BASE_DIR, "templates", "index.html"), encoding="utf-8").read()
    html = re.sub(
        r"\{\{\s*url_for\(\s*'static'\s*,\s*filename\s*=\s*'([^']+)'\s*\)\s*\}\}",
        r"static/\1", html)
    html = html.replace(
        '<link rel="stylesheet"',
        '<!-- GitHub Pages 静态版：由 export_static.py 生成 -->\n<link rel="stylesheet"', 1)
    open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8").write(html)
    print("[3] index.html 已生成")

    # 4) screen.js：API 地址 -> 相对 JSON
    js_path = os.path.join(DOCS_DIR, "static", "js", "screen.js")
    js = open(js_path, encoding="utf-8").read()
    before = js.count('"/api/dashboard"')
    js = js.replace('fetch("/api/dashboard"', 'fetch("../../data.json"')
    open(js_path, "w", encoding="utf-8", newline="").write(js)
    print("[4] screen.js  fetch 替换 %d 处" % before)

    # 5) 自检
    assert '"/api/dashboard"' not in open(js_path, encoding="utf-8").read(), "仍有 /api/dashboard 残留"
    assert "url_for" not in open(os.path.join(DOCS_DIR, "index.html"), encoding="utf-8").read(), "仍有 url_for 残留"
    print("[5] 自检通过：无 url_for / api 残留")

    total = 0
    for dp, dn, fn in os.walk(DOCS_DIR):
        for f in fn:
            total += os.path.getsize(os.path.join(dp, f))
    print("\n完成 → %s" % DOCS_DIR)
    print("     共 %.1f MB，可直接作为 GitHub Pages 源" % (total / 1024 / 1024))


if __name__ == "__main__":
    main()
