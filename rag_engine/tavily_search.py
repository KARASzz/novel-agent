import os
import requests
from typing import List, Dict


def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", "ignore").decode("ascii"))

class TavilySearcher:
    """
    网络智能雷达 (Tavily Web Searcher)
    核心职能：接入具有实时获取网络最新数据能力的 Tavily Search API，
    专门用于扫描番茄小说与网文市场的最新爆款题材、追读钩子和平台规则。
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not self.api_key:
            _safe_print("[Tavily] 未配置 API Key，网络检索功能已禁用。")
        self.base_url = "https://api.tavily.com/search"

    def search_hot_trends(self, query: str, max_results: int = 4) -> List[Dict]:
        """
        全量检索并爬取含有指定"题材关键词"的网页热议点。
        这些信息将用于 RAG 生成创意时的"时效性增强锚点"。
        """
        if not self.api_key:
            return []

        payload = {
            "api_key": self.api_key,
            "query": f"番茄小说 网文 爆款 追读 分析 {query}",
            "search_depth": "advanced", # 深度挖掘
            "include_answer": True,
            "max_results": max_results
        }
        
        try:
            _safe_print(f"[Tavily] 正在扫描外网全域关于【{query}】的最新趋势与设定点...")
            response = requests.post(self.base_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
            
        except requests.exceptions.HTTPError as e:
            _safe_print(f"[Tavily] 认证或配额失败 (常见于 Key 错误): {e}")
            return []
        except Exception as e:
            _safe_print(f"[Tavily] 网络连接检索异常: {e}")
            return []

if __name__ == "__main__":
    searcher = TavilySearcher()
    if searcher.api_key:
        print("\n=== Tavily 活体雷达下潜测试 ===")
        results = searcher.search_hot_trends("都市逆袭 马甲掉落")
        for idx, r in enumerate(results):
            print(f"\n[{idx+1}] {r.get('title')}\n> 摘要: {r.get('content')[:120]}...\n> 链接: {r.get('url')}")
    else:
        _safe_print("[未配置 API Key] 请在系统环境中设置 `TAVILY_API_KEY` 来解锁实时的外网爆款挖掘能力。")
