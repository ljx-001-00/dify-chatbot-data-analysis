"""
MySQL 数据库访问服务（MCP Server）
任务2：在 Windows 服务器上用 PyCharm 编写，把 MySQL 包装成 MCP 工具，
       供 openEuler 上的 Dify 通过 MCP 协议调用。

依赖安装：
    pip install fastmcp pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple

运行：
    python mysql_server.py                  # 默认 streamable-http，监听 0.0.0.0:8095
    python mysql_server.py --transport sse  # 如果 Dify 那边选的是 SSE
    python mysql_server.py --check          # 只做一次数据库连通性自检，不开服务

数据库连接参数优先读环境变量，其次用下面的默认值：
    MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB
"""

import argparse
import json
import os
import sys
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

try:
    from fastmcp import FastMCP
except ImportError:  # 让 --check 在没有 fastmcp 时也能跑
    FastMCP = None


# ----------------------------------------------------------------------------
# 数据库配置
# ----------------------------------------------------------------------------
DB_CONFIG: dict[str, Any] = {
    "host": os.getenv("MYSQL_HOST", "192.168.1.10"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "root"),
    "database": os.getenv("MYSQL_DB", "chat"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
    "connect_timeout": 10,
    "autocommit": True,
}

# 只允许这些语句，防止 LLM 拼错把库删了
ALLOWED_PREFIXES = ("select", "insert", "show", "desc", "describe", "explain")
FORBIDDEN_KEYWORDS = (
    "drop ", "truncate ", "alter ", "grant ", "revoke ",
    "create user", "into outfile", "load_file", "shutdown",
)


def _connect() -> pymysql.connections.Connection:
    return pymysql.connect(**DB_CONFIG)


def _guard(sql: str) -> str:
    """校验 SQL，返回规范化后的语句；不合法则抛 ValueError。"""
    s = (sql or "").strip().rstrip(";").strip()
    if not s:
        raise ValueError("SQL 不能为空")
    low = s.lower()
    for kw in FORBIDDEN_KEYWORDS:
        if kw in low:
            raise ValueError(f"检测到危险语句关键字 `{kw.strip()}`，已拒绝执行")
    if not low.startswith(ALLOWED_PREFIXES):
        raise ValueError(
            "只允许 SELECT / INSERT / SHOW / DESC / EXPLAIN 语句，收到：" + s[:60]
        )
    return s


def _rows_to_json(rows: Any) -> str:
    """把查询结果序列化成 JSON 字符串（中文不转义，便于直接看）。"""
    if isinstance(rows, list):
        # datetime / Decimal 等类型统一转成字符串
        cleaned = [{k: _val(v) for k, v in r.items()} for r in rows]
        return json.dumps(cleaned, ensure_ascii=False, default=str)
    return json.dumps(rows, ensure_ascii=False, default=str)


def _val(v: Any) -> Any:
    if v is None or isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


# ----------------------------------------------------------------------------
# MCP 工具定义
# ----------------------------------------------------------------------------
if FastMCP is not None:
    mcp = FastMCP("mysql-db-service")

    @mcp.tool()
    def execute_sqlstatement(sql: str, limit: int = 200) -> str:
        """执行一条 SQL 并返回结果（JSON 字符串）。

        支持 SELECT / INSERT / SHOW / DESC / EXPLAIN。
        SELECT 类语句自动追加 LIMIT（默认 200 行）。

        Args:
            sql: 要执行的 SQL 语句，例如
                 "SELECT user_input, response FROM chathistory ORDER BY create_time DESC"
            limit: SELECT 返回的最大行数，默认 200

        Returns:
            JSON 字符串：查询返回行数组；INSERT 返回 {"affected_rows": n, "last_id": id}
        """
        try:
            statement = _guard(sql)
        except ValueError as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

        is_select = statement.lower().startswith(("select", "show", "desc", "describe", "explain"))
        if is_select and " limit " not in statement.lower():
            statement = f"{statement} LIMIT {max(1, min(int(limit), 1000))}"

        try:
            conn = _connect()
        except Exception as e:
            return json.dumps(
                {"ok": False, "error": f"数据库连接失败：{e}"}, ensure_ascii=False
            )

        try:
            with conn.cursor() as cur:
                cur.execute(statement)
                if is_select:
                    data = cur.fetchall()
                    return json.dumps(
                        {"ok": True, "count": len(data), "rows": json.loads(_rows_to_json(data))},
                        ensure_ascii=False,
                        default=str,
                    )
                return json.dumps(
                    {"ok": True, "affected_rows": cur.rowcount, "last_id": cur.lastrowid},
                    ensure_ascii=False,
                )
        except Exception as e:
            return json.dumps({"ok": False, "error": f"SQL 执行失败：{e}"}, ensure_ascii=False)
        finally:
            conn.close()

    @mcp.tool()
    def list_tables() -> str:
        """列出当前数据库中的所有表名及行数，用于探查数据结构。"""
        try:
            conn = _connect()
        except Exception as e:
            return json.dumps({"ok": False, "error": f"数据库连接失败：{e}"}, ensure_ascii=False)
        try:
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES")
                tables = [list(r.values())[0] for r in cur.fetchall()]
                info = []
                for t in tables:
                    try:
                        cur.execute(f"SELECT COUNT(*) AS c FROM `{t}`")
                        info.append({"table": t, "rows": cur.fetchone()["c"]})
                    except Exception:
                        info.append({"table": t, "rows": None})
            return json.dumps({"ok": True, "tables": info}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
        finally:
            conn.close()


# ----------------------------------------------------------------------------
# 自检 & 启动
# ----------------------------------------------------------------------------
def self_check() -> int:
    print("=" * 56)
    print(f"目标数据库: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    try:
        conn = _connect()
    except Exception as e:
        print(f"[FAIL] 连接失败: {e}")
        print("\n排查顺序：")
        print("  1. node2 上 MySQL 是否在跑： ss -lntp | grep 3306")
        print("  2. 是否允许远程登录：SELECT user, host FROM mysql.user;")
        print("     需要存在 root@'%' 或你专用的 mcp 用户")
        print("  3. bind-address 是否 0.0.0.0（/etc/my.cnf）")
        print("  4. Windows 能否 ping 通 node2： ping 192.168.1.10")
        return 1
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION() AS v")
            print(f"[ OK ] MySQL 版本: {cur.fetchone()['v']}")
            cur.execute("SHOW TABLES")
            tables = [list(r.values())[0] for r in cur.fetchall()]
            print(f"[ OK ] 库 `{DB_CONFIG['database']}` 共 {len(tables)} 张表: {', '.join(tables) or '(空)'}")
    finally:
        conn.close()
    print("=" * 56)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="MySQL MCP 服务")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8095)
    parser.add_argument("--transport", default="http", choices=["http", "sse", "stdio"])
    parser.add_argument("--check", action="store_true", help="只测数据库连通性")
    args = parser.parse_args()

    if args.check:
        sys.exit(self_check())

    if FastMCP is None:
        print("[FAIL] 没有安装 fastmcp，请先执行： pip install fastmcp pymysql")
        sys.exit(1)

    print(f"启动 MCP 服务：transport={args.transport} 监听 {args.host}:{args.port}")
    if args.transport == "http":
        print(f"  Dify 里填： http://<本机IP>:{args.port}/mcp")
    elif args.transport == "sse":
        print(f"  Dify 里填： http://<本机IP>:{args.port}/sse")

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
