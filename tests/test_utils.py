import pytest
from core_engine.utils import get_enabled_tools

def test_get_enabled_tools_all_on():
    tools_cfg = {
        "web_search": True,
        "web_extractor": True,
        "code_interpreter": True,
        "file_search": True
    }
    index_id = "test-index-123"
    tools = get_enabled_tools(tools_cfg, index_id)
    
    assert len(tools) == 4
    assert {"type": "web_search"} in tools
    assert {"type": "web_extractor"} in tools
    assert {"type": "code_interpreter"} in tools
    
    file_search_tool = next(t for t in tools if t["type"] == "file_search")
    assert file_search_tool["file_search"]["index_id"] == "test-index-123"

def test_get_enabled_tools_partial():
    tools_cfg = {
        "web_search": True,
        "web_extractor": False,
        "code_interpreter": True,
        "file_search": False
    }
    tools = get_enabled_tools(tools_cfg)
    
    assert len(tools) == 2
    assert {"type": "web_search"} in tools
    assert {"type": "code_interpreter"} in tools
    assert not any(t["type"] == "web_extractor" for t in tools)
    assert not any(t["type"] == "file_search" for t in tools)

def test_get_enabled_tools_file_search_no_index():
    tools_cfg = {
        "web_search": False,
        "web_extractor": False,
        "code_interpreter": False,
        "file_search": True
    }
    tools = get_enabled_tools(tools_cfg)
    
    assert len(tools) == 1
    assert tools[0]["type"] == "file_search"
    assert "file_search" not in tools[0] # Should not have the index_id dict if index_id is None
