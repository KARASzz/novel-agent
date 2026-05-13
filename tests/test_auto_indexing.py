import pytest
from unittest.mock import MagicMock
from rag_engine.content_cleaner import ContentCleaner

def test_auto_indexing_on_tavily_ingest():
    """Verify that index rebuild is triggered after Tavily ingestion"""
    mock_retriever = MagicMock()
    cleaner = ContentCleaner(knowledge_base_dir=".", retriever=mock_retriever)
    
    # Mocking results to trigger ingestion
    mock_results = [{"title": "Test Doc", "url": "http://test.com", "content": "This is a long enough content for testing."}]
    
    # Mocking filesystem calls to avoid actual writes
    with pytest.MonkeyPatch().context() as m:
        m.setattr("os.makedirs", MagicMock())
        m.setattr("builtins.open", MagicMock())
        
        cleaner.ingest_tavily_results(mock_results)
        
        # Verify build_index was called
        assert mock_retriever.build_index.called

def test_auto_indexing_on_manual_ingest():
    """Verify that index rebuild is triggered after manual ingestion"""
    mock_retriever = MagicMock()
    cleaner = ContentCleaner(knowledge_base_dir=".", retriever=mock_retriever)
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr("os.makedirs", MagicMock())
        m.setattr("builtins.open", MagicMock())
        
        cleaner.ingest_manual_text("Title", "Content")
        
        assert mock_retriever.build_index.called
