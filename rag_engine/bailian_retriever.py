import os
import json
from typing import List, Tuple, Optional
from alibabacloud_bailian20231229.client import Client as bailian20231229Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_bailian20231229 import models as bailian_20231229_models

from core_engine.config_loader import load_config
from core_engine.logger import get_logger

logger = get_logger(__name__)

class BailianRetriever:
    """
    阿里云百炼检索器 (Bailian Retriever)
    职责：对接阿里云百炼 Retrieve API，实现云端知识库的向量检索。
    """

    def __init__(self):
        cfg = load_config()
        rag_cfg = cfg.get("rag", {})
        
        # 加载凭证
        self.access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
        self.access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        
        workspace_id_env = rag_cfg.get("workspace_id_env", "WORKSPACE_ID")
        self.workspace_id = os.environ.get(workspace_id_env)
        
        index_id_env = rag_cfg.get("index_id_env", "BAILIAN_INDEX_ID")
        self.index_id = os.environ.get(index_id_env)
        
        if not all([self.access_key_id, self.access_key_secret, self.workspace_id, self.index_id]):
            logger.warning(
                "百炼配置不完整。请检查环境变量：ALIBABA_CLOUD_ACCESS_KEY_ID, "
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET, %s, 和 %s。", 
                workspace_id_env, index_id_env
            )
            self._client = None
            return

        api_config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret
        )
        api_config.endpoint = 'bailian.cn-beijing.aliyuncs.com'
        self._client = bailian20231229Client(api_config)

    def search(self, query: str, top_k: int = 3) -> List[Tuple[float, str, str, str]]:
        if not self._client:
            logger.warning("百炼客户端未初始化。无法进行云端检索。")
            return []

        request = bailian_20231229_models.RetrieveRequest(
            index_id=self.index_id,
            query=query
        )

        try:
            response = self._client.retrieve(self.workspace_id, request)
            if not response.body.success:
                logger.error("百炼检索接口返回失败: %s", response.body.message)
                return []
            
            nodes = response.body.data.nodes
            results = []
            for node in nodes:
                score = getattr(node, "score", 0.0)
                text = getattr(node, "text", "")
                metadata = getattr(node, "metadata", {})
                
                # 处理元数据
                if isinstance(metadata, dict):
                    title = metadata.get("title", "百炼文档")
                else:
                    title = getattr(metadata, "title", "百炼文档")
                    
                category = "Bailian"
                
                # 简单清洗并截断
                snippet = text.replace("\n", " ").strip()
                results.append((round(score, 3), title, category, snippet))
                
            return results[:top_k]
        except Exception as e:
            logger.error("百炼检索异常: %s", str(e))
            return []

    def get_rag_context(self, query: str, top_k: int = 3) -> str:
        results = self.search(query, top_k=top_k)
        if not results:
            return "[RAG 知识库未检索到相关参考资料]"

        lines = ["以下是从 [阿里云百炼远程知识库] 检索到的业务约束与爆款参考：\n"]
        for idx, (score, title, category, snippet) in enumerate(results, start=1):
            lines.append(f"---\n### 远程参考资料 [{idx}] (相关度: {score})")
            lines.append(f"**标题**: {title}")
            lines.append(f"**分类**: {category}")
            lines.append(f"**摘要**: {snippet}\n")
        return "\n".join(lines)
