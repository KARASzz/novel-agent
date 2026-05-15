from pathlib import Path
from unittest.mock import patch, AsyncMock

from rag_engine.search_aggregator import SearchAggregator


def test_brave_searcher_maps_results(monkeypatch):
    """测试 BraveSearcher 结果映射（mock MCP 调用）"""
    # 清空所有 Brave API key 环境变量
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    
    # 设置测试用的 API key
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-key")
    
    # Mock MCP 调用返回的数据
    fake_mcp_response = '''{"grounding": {"generic": [{"title": "番茄爆款", "snippets": ["追读钩子和爽点节奏"], "url": "https://example.test/a"}]}}'''

    with patch("rag_engine.brave_search.asyncio.run") as mock_run:
        mock_run.return_value = fake_mcp_response
        
        from rag_engine.brave_search import BraveSearcher
        results = BraveSearcher(api_key="brave-key").search_hot_trends("都市异能", max_results=3)

    assert len(results) == 1
    assert results[0]["title"] == "番茄爆款"
    assert results[0]["content"] == "追读钩子和爽点节奏"
    assert results[0]["url"] == "https://example.test/a"
    assert results[0]["source"] == "brave"


def test_search_aggregator_falls_back_to_local(monkeypatch, tmp_path):
    """测试搜索聚合器在 API key 缺失时回退到本地知识库"""
    # 必须清空所有 API key 环境变量，防止意外覆盖
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_SEARCH_API_KEY", raising=False)
    
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir()
    Path(kb_dir / "method.md").write_text(
        "# 番茄开篇\n都市异能 番茄小说 追读钩子 爽点外化",
        encoding="utf-8",
    )

    payload = SearchAggregator(local_kb_dir=str(kb_dir)).search("都市异能")

    # 验证 fallback_reasons 正确记录了缺失的 API key
    assert "missing_env:BRAVE_SEARCH_API_KEY" in payload["fallback_reasons"]
    assert "missing_env:TAVILY_API_KEY" in payload["fallback_reasons"]
    # 验证本地搜索有结果
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


def test_search_aggregator_all_disabled():
    """测试所有搜索源都被禁用时的情况"""
    payload = SearchAggregator(
        enable_brave=False, 
        enable_tavily=False, 
        enable_local=False
    ).search("测试查询")

    assert "brave_disabled" in payload["fallback_reasons"]
    assert "tavily_disabled" in payload["fallback_reasons"]
    assert "local_kb_disabled" in payload["fallback_reasons"]
    assert len(payload["results"]) == 0


def test_search_aggregator_handles_partial_results(monkeypatch, tmp_path):
    """测试部分搜索源有结果时的情况"""
    # 清空所有 API key
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir()
    Path(kb_dir / "test.md").write_text(
        "# 测试内容\n测试查询 相关信息",
        encoding="utf-8",
    )

    payload = SearchAggregator(local_kb_dir=str(kb_dir)).search("测试查询")

    # Brave 和 Tavily 缺失，本地应有结果
    assert "missing_env:BRAVE_SEARCH_API_KEY" in payload["fallback_reasons"]
    assert "missing_env:TAVILY_API_KEY" in payload["fallback_reasons"]
    assert payload["results"]
    assert any(r["origin"] == "local" for r in payload["results"])