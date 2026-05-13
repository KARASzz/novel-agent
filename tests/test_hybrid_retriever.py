import pytest
from unittest.mock import MagicMock
from rag_engine.retriever import HybridRetriever

def test_hybrid_retriever_fallback():
    """验证 HybridRetriever 在远程失效时是否正确回退"""
    local_kb_dir = "." # 仅测试接口
    mock_remote = MagicMock()
    # 模拟远程报错
    mock_remote.search.side_effect = Exception("Network Error")
    
    # 局部 Mock LocalRetriever 以免真的建立索引
    with pytest.MonkeyPatch().context() as m:
        mock_local = MagicMock()
        m.setattr("rag_engine.retriever.LocalRetriever", lambda dir: mock_local)
        
        hybrid = HybridRetriever(local_kb_dir, remote_retriever=mock_remote)
        hybrid.search("test query")
        
        # 验证是否调用了 local.search
        assert mock_local.search.called
        assert str(hybrid.last_fallback_reason).startswith("remote_exception")
        
def test_hybrid_retriever_empty_fallback():
    """验证 HybridRetriever 在远程结果为空时是否回退"""
    local_kb_dir = "."
    mock_remote = MagicMock()
    mock_remote.search.return_value = [] # 结果为空
    
    with pytest.MonkeyPatch().context() as m:
        mock_local = MagicMock()
        m.setattr("rag_engine.retriever.LocalRetriever", lambda dir: mock_local)
        
        hybrid = HybridRetriever(local_kb_dir, remote_retriever=mock_remote)
        hybrid.search("test query")
        
        assert mock_local.search.called
        assert hybrid.last_fallback_reason == "remote_empty_result"
