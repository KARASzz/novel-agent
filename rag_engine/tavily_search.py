import os
import json
import asyncio
import concurrent.futures
from typing import List, Dict
from rag_engine.mcp_client import call_mcp_tool

def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", "ignore").decode("ascii"))


def _call_mcp_tool_sync(**kwargs):
    """Run the async MCP call from both CLI and FastAPI request contexts."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(call_mcp_tool(**kwargs))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(call_mcp_tool(**kwargs))).result()

class TavilySearcher:
    """
    网络智能雷达 (Tavily Web Searcher)
    核心职能：接入具有实时获取网络最新数据能力的 Tavily MCP Server，
    专门用于扫描番茄小说与网文市场的最新爆款题材、追读钩子和平台规则。
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        self.last_status: str = "idle"
        self.last_error: str = ""
        if not self.api_key:
            self.last_status = "disabled"
            _safe_print("[Tavily] 未配置 API Key，网络检索功能已禁用。")

    def search_hot_trends(self, query: str, max_results: int = 4, **kwargs) -> List[Dict]:
        """
        全量检索并爬取含有指定"题材关键词"的网页热议点。
        """
        if not self.api_key:
            self.last_status = "disabled"
            return []

        try:
            self.last_status = "running"
            self.last_error = ""
            _safe_print(f"[Tavily] 正在通过 MCP 扫描外网全域关于【{query}】的最新趋势与设定点...")
            
            tool_args = {
                "query": f"番茄小说 网文 爆款 追读 分析 {query}",
                "max_results": max_results,
                "search_depth": "advanced",
            }
            # 合并额外参数
            if kwargs:
                tool_args.update(kwargs)
            # 当前 Tavily MCP schema 不接受 include_answer，默认移除避免验证失败
            tool_args.pop("include_answer", None)

            raw_res = _call_mcp_tool_sync(
                command="npx",
                args=["-y", "mcp-remote", f"https://mcp.tavily.com/mcp/?tavilyApiKey={self.api_key}"],
                env=os.environ.copy(),
                tool_name="tavily_search",
                tool_args=tool_args,
            )
            
            # The tool usually returns a text that is a JSON string
            try:
                data = json.loads(raw_res)
                if isinstance(data, dict):
                    results = data.get("results", [])
                elif isinstance(data, list):
                    results = data
                else:
                    results = []
            except json.JSONDecodeError:
                # If it's not JSON, we wrap it as a single result
                return [{
                    "title": "Tavily Search Summary",
                    "content": raw_res,
                    "url": "https://tavily.com",
                    "source": "tavily",
                    "published_at": "",
                    "origin": "tavily",
                }]

            formatted = []
            for item in results:
                formatted.append({
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "url": item.get("url", ""),
                    "source": "tavily",
                    "published_at": "",
                    "origin": "tavily",
                })
            self.last_status = "ok" if formatted else "empty"
            return formatted
            
        except Exception as e:
            self.last_status = "failed"
            self.last_error = f"{type(e).__name__}: {e}"
            _safe_print(f"[Tavily] MCP 网络连接检索异常: {e}")
            return []

if __name__ == "__main__":
    searcher = TavilySearcher()
    if searcher.api_key:
        print("\n=== Tavily MCP 活体雷达下潜测试 ===")
        results = searcher.search_hot_trends("都市逆袭 马甲掉落")
        for idx, r in enumerate(results):
            print(f"\n[{idx+1}] {r.get('title')}\n> 摘要: {r.get('content')[:120]}...\n> 链接: {r.get('url')}")
    else:
        _safe_print("[未配置 API Key] 请在系统环境中设置 `TAVILY_API_KEY`。")
