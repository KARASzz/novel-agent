import os
from typing import Any, Dict, List, Optional, Tuple

from core_engine.logger import get_logger

logger = get_logger(__name__)


class SearchAggregator:
    """Aggregate Brave, Tavily, and local knowledge results with fallback notes."""

    def __init__(
        self,
        local_kb_dir: Optional[str] = None,
        enable_brave: bool = True,
        enable_tavily: bool = True,
        enable_local: bool = True,
    ) -> None:
        self.local_kb_dir = local_kb_dir
        self.enable_brave = enable_brave
        self.enable_tavily = enable_tavily
        self.enable_local = enable_local
        self.fallback_reasons: List[str] = []

    @staticmethod
    def _dedupe_key(item: Dict[str, Any]) -> Tuple[str, str]:
        url = str(item.get("url", "")).strip().lower()
        if url:
            return (url, "")
        return ("", str(item.get("title", "")).strip().lower()[:120])

    def _add_results(
        self,
        merged: List[Dict[str, Any]],
        seen: set[Tuple[str, str]],
        items: List[Dict[str, Any]],
        origin: str,
    ) -> None:
        if not items:
            self.fallback_reasons.append(f"{origin}_empty_result")
            return
        for item in items:
            title = str(item.get("title", "")).strip()
            content = str(item.get("content", "")).strip()
            if not title and not content:
                continue
            enriched = dict(item)
            enriched.setdefault("origin", origin)
            enriched.setdefault("source", origin)
            key = self._dedupe_key(enriched)
            if key in seen:
                continue
            seen.add(key)
            merged.append(enriched)

    def _search_brave(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        if not self.enable_brave:
            self.fallback_reasons.append("brave_disabled")
            return []
        if not os.getenv("BRAVE_SEARCH_API_KEY"):
            self.fallback_reasons.append("missing_env:BRAVE_SEARCH_API_KEY")
            return []
        try:
            from rag_engine.brave_search import BraveSearcher

            return BraveSearcher().search_hot_trends(query, max_results=max_results)
        except Exception as exc:
            self.fallback_reasons.append(f"brave_failed:{type(exc).__name__}")
            logger.warning("Brave search failed: %s", exc)
            return []

    def _search_tavily(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        if not self.enable_tavily:
            self.fallback_reasons.append("tavily_disabled")
            return []
        if not os.getenv("TAVILY_API_KEY"):
            self.fallback_reasons.append("missing_env:TAVILY_API_KEY")
            return []
        try:
            from rag_engine.tavily_search import TavilySearcher

            return TavilySearcher().search_hot_trends(query, max_results=max_results)
        except Exception as exc:
            self.fallback_reasons.append(f"tavily_failed:{type(exc).__name__}")
            logger.warning("Tavily search failed: %s", exc)
            return []

    def _search_local(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        if not self.enable_local:
            self.fallback_reasons.append("local_kb_disabled")
            return []
        if not self.local_kb_dir or not os.path.isdir(self.local_kb_dir):
            self.fallback_reasons.append("local_kb_missing")
            return []
        try:
            from rag_engine.retriever import LocalRetriever

            retriever = LocalRetriever(self.local_kb_dir)
            retriever.build_index()
            results = retriever.search(query, top_k=max_results)
            return [
                {
                    "title": title,
                    "content": snippet,
                    "url": f"local://{category}/{title}",
                    "source": "local_knowledge_base",
                    "origin": "local",
                    "score": score,
                }
                for score, title, category, snippet in results
            ]
        except Exception as exc:
            self.fallback_reasons.append(f"local_kb_failed:{type(exc).__name__}")
            logger.warning("Local knowledge search failed: %s", exc)
            return []

    def search(self, query: str, max_results_per_source: int = 4) -> Dict[str, Any]:
        self.fallback_reasons = []
        merged: List[Dict[str, Any]] = []
        seen: set[Tuple[str, str]] = set()

        self._add_results(
            merged,
            seen,
            self._search_brave(query, max_results_per_source),
            origin="brave",
        )
        self._add_results(
            merged,
            seen,
            self._search_tavily(query, max_results_per_source),
            origin="tavily",
        )
        self._add_results(
            merged,
            seen,
            self._search_local(query, max_results_per_source),
            origin="local",
        )

        return {
            "query": query,
            "results": merged,
            "fallback_reasons": sorted(set(self.fallback_reasons)),
        }
