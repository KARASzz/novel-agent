from pathlib import Path

from rag_engine.brave_search import BraveSearcher
from rag_engine.search_aggregator import SearchAggregator


def test_brave_searcher_maps_results(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-key")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "web": {
                    "results": [
                        {
                            "title": "番茄爆款",
                            "description": "追读钩子和爽点节奏",
                            "url": "https://example.test/a",
                        }
                    ]
                }
            }

    def fake_get(url, params, headers, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("rag_engine.brave_search.requests.get", fake_get)

    results = BraveSearcher().search_hot_trends("都市异能", max_results=3)

    assert captured["url"] == "https://api.search.brave.com/res/v1/web/search"
    assert captured["headers"]["X-Subscription-Token"] == "brave-key"
    assert "都市异能" in captured["params"]["q"]
    assert results == [
        {
            "title": "番茄爆款",
            "content": "追读钩子和爽点节奏",
            "url": "https://example.test/a",
            "source": "brave",
            "published_at": "",
            "origin": "brave",
        }
    ]


def test_search_aggregator_falls_back_to_local(monkeypatch, tmp_path):
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir()
    Path(kb_dir / "method.md").write_text(
        "# 番茄开篇\n都市异能 番茄小说 追读钩子 爽点外化",
        encoding="utf-8",
    )

    payload = SearchAggregator(local_kb_dir=str(kb_dir)).search("都市异能")

    assert "missing_env:BRAVE_SEARCH_API_KEY" in payload["fallback_reasons"]
    assert "missing_env:TAVILY_API_KEY" in payload["fallback_reasons"]
    assert payload["results"]
    assert payload["results"][0]["origin"] == "local"


def test_search_aggregator_deduplicates_by_url():
    aggregator = SearchAggregator(enable_brave=False, enable_tavily=False, enable_local=False)
    merged = []
    seen = set()

    aggregator._add_results(
        merged,
        seen,
        [
            {"title": "A", "content": "one", "url": "https://example.test/a"},
            {"title": "A copy", "content": "two", "url": "https://example.test/a"},
        ],
        origin="test",
    )

    assert len(merged) == 1
