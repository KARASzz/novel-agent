import asyncio
import json
import re
import tempfile
from typing import Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _redact_mcp_log(text: str) -> str:
    """Remove API keys and bearer tokens from mcp-remote stderr output."""
    text = re.sub(r"(tavilyApiKey=)[^&\s]+", r"\1<redacted>", text)
    text = re.sub(r'(Authorization["\']?\s*:\s*"?Bearer\s+)([^"\s}]+)', r"\1<redacted>", text)
    text = re.sub(r"(Bearer\s+)([A-Za-z0-9._\-]+)", r"\1<redacted>", text)
    return text

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

    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as errlog:
        try:
            async with stdio_client(server_params, errlog=errlog) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, tool_args)
                    return result.content[0].text if result.content else ""
        except Exception as exc:
            try:
                errlog.flush()
                errlog.seek(0)
                stderr_text = errlog.read().strip()
            except Exception:
                stderr_text = ""
            if stderr_text:
                raise RuntimeError(f"{exc}\n[mcp stderr]\n{_redact_mcp_log(stderr_text)}") from exc
            raise
