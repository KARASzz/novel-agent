import os
from typing import Dict, List, Optional

import requests


def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", "ignore").decode("ascii"))


class BraveSearcher:
    """Brave Web Search adapter for market and reference discovery."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("BRAVE_SEARCH_API_KEY")
        if not self.api_key:
            _safe_print("[Brave] 未配置 API Key，Brave 搜索功能已禁用。")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    def search_hot_trends(self, query: str, max_results: int = 4) -> List[Dict]:
        if not self.api_key:
            return []

        params = {
            "q": f"番茄小说 网文 爆款 趋势 {query}",
            "count": max(1, min(int(max_results), 20)),
            "text_decorations": "false",
            "search_lang": "zh-hans",
        }
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }

        try:
            _safe_print(f"[Brave] 正在检索番茄小说/网文趋势：【{query}】")
            response = requests.get(self.base_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            results = data.get("web", {}).get("results", [])
            return [
                {
                    "title": item.get("title", ""),
                    "content": item.get("description") or item.get("snippet") or "",
                    "url": item.get("url", ""),
                    "source": "brave",
                    "published_at": item.get("age") or "",
                    "origin": "brave",
                }
                for item in results[:max_results]
            ]
        except requests.exceptions.HTTPError as exc:
            _safe_print(f"[Brave] 认证或配额失败: {exc}")
            return []
        except Exception as exc:
            _safe_print(f"[Brave] 网络检索异常: {exc}")
            return []
