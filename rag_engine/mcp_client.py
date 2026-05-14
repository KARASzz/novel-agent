import asyncio
import json
from typing import Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def call_mcp_tool(
    command: str,
    args: list[str],
    env: dict[str, str],
    tool_name: str,
    tool_args: dict[str, Any]
) -> str:
    """Run an MCP server via stdio and call a specific tool."""
    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=env
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            return result.content[0].text if result.content else ""
