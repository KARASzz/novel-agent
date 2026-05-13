from typing import Any, Dict, List, Optional

def get_enabled_tools(tools_cfg: Dict[str, Any], index_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    根据配置统一构造阿里云百炼大模型的可选内置工具列表。
    涵盖：联网搜索、网页重排、代码执行、知识库检索。
    """
    enabled_tools = []
    
    if tools_cfg.get("web_search", True):
        enabled_tools.append({"type": "web_search"})
        
    if tools_cfg.get("web_extractor", True):
        enabled_tools.append({"type": "web_extractor"})
        
    if tools_cfg.get("code_interpreter", True):
        enabled_tools.append({"type": "code_interpreter"})
        
    if tools_cfg.get("file_search", False):
        # 开启内置知识库检索工具
        file_search_tool = {"type": "file_search"}
        if index_id:
            file_search_tool["file_search"] = {"index_id": index_id}
        enabled_tools.append(file_search_tool)
        
    return enabled_tools
