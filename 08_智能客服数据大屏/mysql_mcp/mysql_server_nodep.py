"""
零依赖版 MySQL MCP 服务（只用 Python 标准库 + pymysql）

为什么有这个版本：
    你这台机器到 PyPI 的速度只有 ~146 KB/s，而 fastmcp 2.x 的依赖树有上百 MB
    （authlib、cyclonedx-python-lib、openapi-pydantic、rich、typer…），
    装不动。这个版本只需要 pymysql（约 50 KB），十秒钟装完。

协议：
    实现 MCP Streamable HTTP 的最小可用子集 —— initialize / tools/list / tools/call，
    JSON-RPC 2.0 over POST /mcp，响应为 application/json（MCP 允许这种形式）。
    Dify 1.8 的 MCP 插件走的就是这套，可以直接连。

安装：
    pip install pymysql -i https://mirrors.aliyun.com/pypi/simple/

运行：
    python mysql_server_nodep.py                 # 监听 0.0.0.0:8095
    python mysql_server_nodep.py --check         # 只测数据库连通性
    python mysql_server_nodep.py --port 8096

环境变量：
    MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB
"""

import argparse
import json
import os
import queue
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pymysql
from pymysql.cursors import DictCursor

SERVER_NAME = "mysql-db-service"
SERVER_VERSION = "1.0.0"
SESSION_ID = uuid.uuid4().hex

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "192.168.1.10"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "root"),
    "database": os.getenv("MYSQL_DB", "wechat"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
    "connect_timeout": 10,
    "autocommit": True,
}

ALLOWED_PREFIXES = ("select", "insert", "show", "desc", "describe", "explain")
FORBIDDEN_KEYWORDS = (
    "drop ", "truncate ", "alter ", "grant ", "revoke ",
    "create user", "into outfile", "load_file", "shutdown",
)


# ---------------------------------------------------------------- 数据库部分
def connect():
    return pymysql.connect(**DB_CONFIG)


# 连接池：避免每次请求都重新做 TCP 握手（偶发 4 秒长尾的主要嫌疑）
_POOL: "queue.Queue" = queue.Queue(maxsize=4)


def get_conn():
    """取一条已建好的连接，没有就新建。"""
    try:
        conn = _POOL.get_nowait()
    except queue.Empty:
        return connect()
    try:
        conn.ping(reconnect=True)
        return conn
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return connect()


def release(conn):
    """归还连接；池满就关掉。"""
    if conn is None:
        return
    try:
        _POOL.put_nowait(conn)
    except queue.Full:
        try:
            conn.close()
        except Exception:
            pass


def guard_sql(sql: str) -> str:
    s = (sql or "").strip().rstrip(";").strip()
    if not s:
        raise ValueError("SQL 不能为空")
    low = s.lower()
    for kw in FORBIDDEN_KEYWORDS:
        if kw in low:
            raise ValueError(f"检测到危险关键字 `{kw.strip()}`，已拒绝执行")
    if not low.startswith(ALLOWED_PREFIXES):
        raise ValueError(f"只允许 SELECT/INSERT/SHOW/DESC/EXPLAIN，收到: {s[:60]}")
    return s


def execute_sql(sql: str, limit: int = 200) -> str:
    t0 = time.time()
    statement = guard_sql(sql)
    is_query = statement.lower().startswith(
        ("select", "show", "desc", "describe", "explain")
    )
    if is_query and " limit " not in statement.lower():
        statement = f"{statement} LIMIT {max(1, min(int(limit), 1000))}"

    t1 = time.time()
    conn = get_conn()
    t2 = time.time()
    try:
        with conn.cursor() as cur:
            cur.execute(statement)
            t3 = time.time()
            if is_query:
                rows = cur.fetchall()
                result = json.dumps(
                    {"ok": True, "count": len(rows), "rows": rows},
                    ensure_ascii=False,
                    default=str,
                )
            else:
                result = json.dumps(
                    {"ok": True, "affected_rows": cur.rowcount, "last_id": cur.lastrowid},
                    ensure_ascii=False,
                )
            t4 = time.time()
    finally:
        release(conn)

    total = t4 - t0
    if total > 0.5:  # 只打印慢请求，方便定位偶发长尾
        print(f"[SLOW {total:.2f}s] guard={t1-t0:.3f}s connect={t2-t1:.3f}s "
              f"execute={t3-t2:.3f}s fetch={t4-t3:.3f}s | {statement[:60]}", flush=True)
    return result


def list_tables() -> str:
    conn = connect()
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
    finally:
        conn.close()


# ---------------------------------------------------------------- MCP 工具表
TOOL_SPECS = [
    {
        "name": "execute_sqlstatement",
        "description": (
            "执行一条 SQL 并返回 JSON 结果。支持 SELECT/INSERT/SHOW/DESC/EXPLAIN。"
            "SELECT 自动追加 LIMIT（默认 200 行）。"
            "例：SELECT user_input, response FROM chathistory ORDER BY create_time DESC"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "要执行的 SQL 语句"},
                "limit": {
                    "type": "integer",
                    "description": "SELECT 返回的最大行数，默认 200",
                    "default": 200,
                },
            },
            "required": ["sql"],
        },
    },
    {
        "name": "list_tables",
        "description": "列出当前数据库的所有表名及行数，用于探查数据结构。",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def call_tool(name: str, args: dict) -> str:
    if name == "execute_sqlstatement":
        return execute_sql(args.get("sql", ""), int(args.get("limit", 200)))
    if name == "list_tables":
        return list_tables()
    raise ValueError(f"未知工具: {name}")


# ---------------------------------------------------------------- JSON-RPC 层
def rpc_ok(mid, result):
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def rpc_err(mid, code, message):
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def handle_rpc(req: dict):
    """处理单条 JSON-RPC 请求；通知（无 id）返回 None。"""
    mid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    if mid is None:  # notification，例如 notifications/initialized
        return None

    if method == "initialize":
        return rpc_ok(
            mid,
            {
                "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    if method == "ping":
        return rpc_ok(mid, {})

    if method == "tools/list":
        return rpc_ok(mid, {"tools": TOOL_SPECS})

    if method == "tools/call":
        tool = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            text = call_tool(tool, arguments)
            return rpc_ok(
                mid, {"content": [{"type": "text", "text": text}], "isError": False}
            )
        except Exception as e:
            return rpc_ok(
                mid,
                {"content": [{"type": "text", "text": f"执行失败: {e}"}], "isError": True},
            )

    return rpc_err(mid, -32601, f"Method not found: {method}")


# ---------------------------------------------------------------- HTTP 层
class MCPHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = f"{SERVER_NAME}/{SERVER_VERSION}"

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.address_string(), fmt % args))

    def _respond(self, code, payload=None, extra_headers=None):
        body = b"" if payload is None else json.dumps(
            payload, ensure_ascii=False, default=str
        ).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Expose-Headers", "Mcp-Session-Id")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._respond(204)

    def do_GET(self):
        if self.path.rstrip("/") in ("/health", ""):
            self._respond(200, {"ok": True, "server": SERVER_NAME, "tools": [
                t["name"] for t in TOOL_SPECS
            ]})
            return
        if self.path.rstrip("/").endswith("/mcp"):
            # MCP Streamable HTTP 规范：GET /mcp 用于建立 SSE 通道。
            # 关键：这条流必须一直挂着并定期发心跳，不能发完就 close。
            # 一旦服务端主动关流，官方客户端会认为会话失效，退避后重建会话
            # （实测造成 4.5 秒的固定尖峰），期间 tools/call 就只能干等。
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.close_connection = True
            try:
                self.wfile.write(b": mcp stream ready\n\n")
                self.wfile.flush()
                deadline = time.time() + 600          # 最多挂 10 分钟
                while time.time() < deadline:
                    time.sleep(15)
                    self.wfile.write(b": ping\n\n")   # 心跳，防止中间设备断链
                    self.wfile.flush()
            except Exception:
                pass                                  # 客户端断开，正常退出
            return
        self._respond(405, {"ok": False, "error": "请用 POST /mcp"})

    def do_DELETE(self):
        # 会话结束通知：返回 204，避免客户端把 501 当异常并重试
        self._respond(204)

    def do_POST(self):
        t_start = time.time()
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw or b"{}")
        except Exception:
            self._respond(400, rpc_err(None, -32700, "JSON 解析失败"))
            return

        if isinstance(data, list):  # 批量请求
            replies = [r for r in (handle_rpc(item) for item in data) if r is not None]
            if not replies:
                # 通知：MCP Streamable HTTP 规范要求 202 Accepted（空体）。
                # 若返回 204，官方 mcp 客户端会把空 body 当 JSON 解析，报
                # "Invalid JSON: EOF while parsing a value at line 1 column 0"
                self._respond(202)
            else:
                self._respond(200, replies)
            return

        reply = handle_rpc(data)
        if reply is None:
            self._respond(202)
            return

        extra = None
        if data.get("method") == "initialize":
            extra = {"Mcp-Session-Id": SESSION_ID}
        self._respond(200, reply, extra)
        total = time.time() - t_start
        if total > 0.5:
            print(f"[SLOW REQ {total:.2f}s] method={data.get('method')} "
                  f"body={len(raw)}B", flush=True)


# ---------------------------------------------------------------- 自检 & 入口
def self_check() -> int:
    print("=" * 58)
    print(f"目标库: {DB_CONFIG['user']}@{DB_CONFIG['host']}:"
          f"{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    try:
        conn = connect()
    except Exception as e:
        print(f"[FAIL] 连接失败: {e}")
        print("\n排查顺序：")
        print("  1. node2 上 MySQL 是否在跑： ss -lntp | grep 3306")
        print("  2. 是否允许远程登录： SELECT user, host FROM mysql.user;")
        print("     需要 root@'%' 或专用 mcp 用户")
        print("  3. bind-address 是否 0.0.0.0（/etc/my.cnf）")
        print("  4. Windows 能不能 ping 通 node2")
        return 1
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION() AS v")
            print(f"[ OK ] MySQL 版本: {cur.fetchone()['v']}")
            cur.execute("SHOW TABLES")
            tables = [list(r.values())[0] for r in cur.fetchall()]
            print(f"[ OK ] 库 `{DB_CONFIG['database']}` 共 {len(tables)} 张表: "
                  f"{', '.join(tables) or '(空)'}")
    finally:
        conn.close()
    print("=" * 58)
    return 0


def main():
    parser = argparse.ArgumentParser(description="零依赖 MySQL MCP 服务")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8095)
    parser.add_argument("--check", action="store_true", help="只测数据库连通性")
    args = parser.parse_args()

    if args.check:
        sys.exit(self_check())

    server = ThreadingHTTPServer((args.host, args.port), MCPHandler)
    server.daemon_threads = True
    print(f"MCP 服务已启动: http://{args.host}:{args.port}/mcp")
    print(f"健康检查:      http://127.0.0.1:{args.port}/health")
    print(f"工具:          {', '.join(t['name'] for t in TOOL_SPECS)}")
    print("Dify 里填写:   http://<本机IP>:%d/mcp" % args.port)
    print("按 Ctrl+C 停止")

    # 预热：先把数据库连接建好放进池里，避免第一次请求承担 4 秒握手
    try:
        t0 = time.time()
        release(connect())
        print(f"数据库预热完成 ({time.time() - t0:.2f}s)")
    except Exception as e:
        print(f"[WARN] 数据库预热失败: {e}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
