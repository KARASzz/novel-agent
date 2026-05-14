"""番茄小说前置立项中台 - LLM 驱动评审引擎 (新版：立项中台总线)。

架构：
  1. 委托 NovelPreflightOrchestrator 负责总线流程（收集、拼装、LLM 评审）。
  2. 使用 novel_payload_to_bundle 适配器保证向下兼容。

已弃用：
  - 弃用 _TOPIC_KEYWORDS 关键词工程。
  - 弃用 Python 侧的手工分数修正。
  - 弃用 Python 侧的准入逻辑（全部由 LLM 判断）。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pre_hub.novel_preflight_orchestrator import NovelPreflightOrchestrator
from pre_hub.adapters.novel_payload_to_bundle import novel_payload_to_bundle
from pre_hub.schemas.pre_hub_models import (
    ChapterProductionBundle,
    FormatLane,
)
from pre_hub.ltm import LTMClient, LTMGovernance


class PreHubOrchestrator:
    """番茄小说立项评审中台，LLM 驱动。
    
    这是旧版 PreHubOrchestrator 的外观类，内部已切换为 NovelPreflightOrchestrator 总线。
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        workspace_root: Optional[str] = None,
        ltm_client: Optional[LTMClient] = None,
        ltm_governance: Optional[LTMGovernance] = None,
    ) -> None:
        self.config = config or {}
        self.workspace_root = workspace_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 内部总线
        self.bus = NovelPreflightOrchestrator(
            config=self.config,
            workspace_root=self.workspace_root,
            bundle_adapter=novel_payload_to_bundle
        )

    def run(
        self,
        topic: str,
        format_lane: FormatLane = FormatLane.REAL,
        author_id: str = "default",
        use_rag: bool = True,
        model_slot: Optional[str] = None,
    ) -> ChapterProductionBundle:
        """主入口，保持方法签名一致，返回 ChapterProductionBundle。"""
        
        # 将 format_lane 转换为 novel_form (字符串描述)
        novel_form = format_lane.label if hasattr(format_lane, "label") else str(format_lane)
        
        # 调用新总线
        bundle = self.bus.run(
            topic=topic,
            author_id=author_id,
            model_slot=model_slot,
            use_rag=use_rag,
            novel_form=novel_form,
            target_platform="番茄小说"
        )
        
        return bundle

    # 为了兼容性保留但可能不再需要的私有方法可选择删除或保留为空
    def _collect_sources(self, *args, **kwargs): pass
    def _collect_memory(self, *args, **kwargs): pass
    def _llm_evaluate(self, *args, **kwargs): pass
