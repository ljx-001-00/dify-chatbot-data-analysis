"""
零依赖自测：用标准库 urllib 走一遍 MCP 握手 + 工具调用。
不需要 fastmcp，和 mysql_server_nodep.py 配套。

用法（先把服务跑起来）：
    python test_mcp_nodep.py
    python test_mcp_nodep.py http://127.0.0.1:8095/mcp
"""

import json
import sys
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8095/mcp"
SESSION = {"id": None}
_req_id = [0]


def rpc(method, params=None, notify=False):
    _req_id[0] += 1
    payload = {"jsonrpc": "2.0", "method": method}
    if not notify:
        payload["id"] = _req_id[0]
    if params is not None:
        payload["params"] = params

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if SESSION["id"]:
        headers["Mcp-Session-Id"] = SESSION["id"]

    req = urllib.request.Request(URL, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            SESSION["id"] = sid
        body = resp.read().decode("utf-8")
        return json.loads(body) if body.strip() else None


def brief(obj, n=400):
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    print(text if len(text) <= n else text[:n] + " ...(截断)")


def main():
    print(f"目标: {URL}\n")

    print("[1] initialize")
    init = rpc("initialize", {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0"},
    })
    brief(init)
    print(f"    会话 ID: {SESSION['id']}\n")

    print("[2] notifications/initialized")
    rpc("notifications/initialized", notify=True)
    print("    OK（通知无返回是正常的）\n")

    print("[3] tools/list")
    tools = rpc("tools/list", {})
    brief(tools)
    print()

    print("[4] tools/call -> list_tables")
    brief(rpc("tools/call", {"name": "list_tables", "arguments": {}}))
    print()

    print("[5] tools/call -> execute_sqlstatement (SELECT)")
    brief(rpc("tools/call", {
        "name": "execute_sqlstatement",
        "arguments": {
            "sql": "SELECT * FROM records LIMIT 3",
            "limit": 3,
        },
    }))
    print("\n全部通过：MCP 服务可用，可以去 Dify 里配了。")


if __name__ == "__main__":
    main()
