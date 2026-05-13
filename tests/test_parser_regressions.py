import json
from unittest.mock import MagicMock

from core_engine.llm_client import LLMClient
from core_engine.parser import DraftParser


VALID_EPISODE_JSON = json.dumps(
    {
        "episode_number": 1,
        "title": "测试集",
        "is_paywall": False,
        "scenes": [
            {
                "scene_id": "1",
                "time": "日",
                "location_type": "内",
                "location": "客厅",
                "characters": ["甲"],
                "plots": [{"type": "dialogue", "content": "开始", "is_cliffhanger": False}],
            }
        ],
    },
    ensure_ascii=False,
)


def test_repair_json_trailing_comma_control_char_regression():
    repaired = DraftParser._repair_json_string('```json\n{"a": 1,}\n```')

    assert "\x01" not in repaired
    assert json.loads(repaired) == {"a": 1}


def test_no_cache_constructor_disables_cache_lookup(monkeypatch):
    parser = DraftParser(config={"parser": {"model": "qwen-test", "enable_rag": False}}, no_cache=True)
    parser._client = MagicMock(spec=LLMClient)
    parser._client.create_response.return_value = MagicMock(output_text=VALID_EPISODE_JSON)
    parser.cache_manager.get_cache = MagicMock(side_effect=AssertionError("cache must not be read"))
    parser.cache_manager.set_cache = MagicMock(side_effect=AssertionError("cache must not be written"))

    result = parser.parse_draft("第1集 客厅 甲：开始")

    assert result.is_success is True
    parser.cache_manager.get_cache.assert_not_called()
    parser.cache_manager.set_cache.assert_not_called()


def test_context_bundle_changes_cache_salt():
    parser = DraftParser(config={"parser": {"model": "qwen-test", "enable_rag": False}})

    salt_a = parser._build_cache_salt(context_bundle={"project_id": "p1", "integrity_hash": "hash-a"})
    salt_b = parser._build_cache_salt(context_bundle={"project_id": "p1", "integrity_hash": "hash-b"})

    assert salt_a != salt_b
