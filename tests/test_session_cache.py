import pytest
from unittest.mock import MagicMock
from core_engine.parser import DraftParser
from core_engine.llm_client import LLMClient


def test_parser_session_cache_stability():
    # 验证在解析不同剧本时，系统指令 (instructions) 保持一致
    parser = DraftParser(config={"parser": {"model": "qwen-max"}})
    parser._client = MagicMock(spec=LLMClient)

    draft1 = "Scene 1: Home. John says hello."
    draft2 = "Episode 2: Park. Mary is crying."

    # 第一次解析
    parser.parse_draft(draft1, use_cache=False)
    args1, kwargs1 = parser._client.create_response.call_args
    instr1 = kwargs1.get("instructions")

    # 第二次解析
    parser.parse_draft(draft2, use_cache=False)
    args2, kwargs2 = parser._client.create_response.call_args
    instr2 = kwargs2.get("instructions")

    # 验证两次指令完全一致，没有混入剧本内容
    assert instr1 == instr2
    assert draft1 not in instr1
    assert draft2 not in instr2
