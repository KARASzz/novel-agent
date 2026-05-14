import os
import json
import asyncio
from typing import Dict, List, Optional
from rag_engine.mcp_client import call_mcp_tool

def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", "ignore").decode("ascii"))

class BraveSearcher:
    """Brave Web Search adapter using MCP tools."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("BRAVE_SEARCH_API_KEY") or os.environ.get("BRAVE_API_KEY")
        if not self.api_key:
            _safe_print("[Brave] 未配置 API Key，Brave 搜索功能已禁用。")

    def search_hot_trends(self, query: str, max_results: int = 4, **kwargs) -> List[Dict]:
        if not self.api_key:
            return []

        try:
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

            raw_res = asyncio.run(
                call_mcp_tool(
                    command="npx",
                    args=["-y", "@brave/brave-search-mcp-server"],
                    env=env,
                    tool_name="brave_llm_context",
                    tool_args=tool_args
                )
            )
            
            data = json.loads(raw_res)
            generic_items = data.get("grounding", {}).get("generic", [])
            
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
            _safe_print(f"[Brave] MCP 网络检索异常: {exc}")
            return []
