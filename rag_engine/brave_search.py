import os
import json
import asyncio
import concurrent.futures
from typing import Any, Callable, Dict, List, Optional
from rag_engine.mcp_client import call_mcp_tool

def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", "ignore").decode("ascii"))


def _call_mcp_tool_sync(**kwargs: Any) -> str:
    """Run the async MCP call from both sync CLI code and async FastAPI handlers."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(call_mcp_tool(**kwargs))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(call_mcp_tool(**kwargs))).result()

class BraveSearcher:
    """Brave Web Search adapter using MCP tools."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("BRAVE_SEARCH_API_KEY") or os.environ.get("BRAVE_API_KEY")
        self.last_status: str = "idle"
        self.last_error: str = ""
        if not self.api_key:
            self.last_status = "disabled"
            _safe_print("[Brave] 未配置 API Key，Brave 搜索功能已禁用。")

    def search_hot_trends(
        self,
        query: str,
        max_results: int = 4,
        tool_runner: Optional[Callable[..., Any]] = None,
        **kwargs,
    ) -> List[Dict]:
        if not self.api_key:
            self.last_status = "disabled"
            return []

        try:
            self.last_status = "running"
            self.last_error = ""
            _safe_print(f"[Brave] 正在通过 MCP LLM Context 检索网文趋势：【{query}】")
            env = os.environ.copy()
            env["BRAVE_API_KEY"] = self.api_key
            
            tool_args = {
                "query": f"番茄小说 网文 爆款 趋势 {query}",
                "count": max(1, min(int(max_results), 20))
            }
            # 合并额外参数
            if kwargs:
                tool_args.update(kwargs)

            if tool_runner is not None:
                raw_res = tool_runner(
                    command="npx",
                    args=["-y", "@brave/brave-search-mcp-server"],
                    env=env,
                    tool_name="brave_llm_context",
                    tool_args=tool_args,
                )
            else:
                raw_res = _call_mcp_tool_sync(
                    command="npx",
                    args=["-y", "@brave/brave-search-mcp-server"],
                    env=env,
                    tool_name="brave_llm_context",
                    tool_args=tool_args,
                )
            
            data = json.loads(raw_res)
            generic_items = data.get("grounding", {}).get("generic", [])
            self.last_status = "ok" if generic_items else "empty"
            
            return [
                {
                    "title": item.get("title", ""),
                    "content": " ".join(item.get("snippets", [])),
                    "url": item.get("url", ""),
                    "source": "brave",
                    "published_at": "",
                    "origin": "brave",
                }
                for item in generic_items[:max_results]
            ]
        except Exception as exc:
            self.last_status = "failed"
            self.last_error = f"{type(exc).__name__}: {exc}"
            _safe_print(f"[Brave] MCP 网络检索异常: {exc}")
            return []
