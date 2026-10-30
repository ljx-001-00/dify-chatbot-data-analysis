"""
本地自测客户端：不经过 Dify，直接连上 mysql_server.py 验证工具是否可用。

用法（先另开一个终端把 mysql_server.py 跑起来）：
    python test_mcp.py                       # 默认 http://127.0.0.1:8095/mcp
    python test_mcp.py http://127.0.0.1:8095/sse
"""

import asyncio
import json
import sys

from fastmcp import Client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8095/mcp"


def show(result) -> None:
    """把 CallToolResult 里的文本抽出来打印。"""
    try:
        for item in result.content:
            text = getattr(item, "text", None)
            if text:
                print(text)
    except Exception:
        print(result)


async def main() -> None:
    print(f"连接 {URL} ...")
    async with Client(URL) as client:
        tools = await client.list_tools()
        print(f"\n发现 {len(tools)} 个工具：")
        for t in tools:
            desc = (t.description or "").split("\n")[0]
            print(f"  - {t.name}: {desc}")

        print("\n[1] 调用 list_tables")
        show(await client.call_tool("list_tables", {}))

        print("\n[2] 调用 execute_sqlstatement（SELECT）")
        show(
            await client.call_tool(
                "execute_sqlstatement",
                {"sql": "SELECT * FROM chathistory ORDER BY create_time DESC", "limit": 3},
            )
        )

        print("\n[3] 调用 execute_sqlstatement（INSERT 测试）")
        show(
            await client.call_tool(
                "execute_sqlstatement",
                {
                    "sql": (
                        "INSERT INTO chathistory (user_input, response) "
                        "VALUES ('mcp 连通性测试', '写入成功')"
                    )
                },
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
