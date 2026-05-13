from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core_engine.config_loader import resolve_model_config
from core_engine.llm_client import LLMClient


@patch("core_engine.llm_client.OpenAI")
def test_llm_client_initialization_uses_plain_openai_client(mock_openai):
    LLMClient(api_key="sk-test", base_url="http://test.ai")

    mock_openai.assert_called_once()
    _, kwargs = mock_openai.call_args
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["base_url"] == "http://test.ai"
    assert "default_headers" not in kwargs


@patch("core_engine.llm_client.OpenAI")
def test_llm_client_create_response_uses_chat_completions(mock_openai):
    mock_chat = MagicMock()
    mock_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="hello result"))],
        usage=SimpleNamespace(total_tokens=12),
    )
    mock_chat.completions.create.return_value = mock_response
    mock_openai.return_value.chat = mock_chat

    client = LLMClient(api_key="sk-test", base_url="http://test.ai")
    response = client.create_response(
        model="model-test",
        instructions="do this",
        input_text="hello",
        temperature=0.5,
        enable_thinking=True,
        tools=[{"type": "function", "function": {"name": "noop"}}],
    )

    mock_chat.completions.create.assert_called_once()
    call_kwargs = mock_chat.completions.create.call_args.kwargs

    assert call_kwargs["model"] == "model-test"
    assert call_kwargs["messages"] == [
        {"role": "system", "content": "do this"},
        {"role": "user", "content": "hello"},
    ]
    assert call_kwargs["temperature"] == 0.5
    assert call_kwargs["tools"] == [{"type": "function", "function": {"name": "noop"}}]
    assert "extra_body" not in call_kwargs
    assert response.output_text == "hello result"


@patch("core_engine.llm_client.OpenAI")
def test_llm_client_converts_legacy_text_json_schema(mock_openai):
    mock_chat = MagicMock()
    mock_chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
        usage=None,
    )
    mock_openai.return_value.chat = mock_chat

    client = LLMClient(api_key="sk-test", base_url="http://test.ai")
    client.create_response(
        model="model-test",
        instructions="system",
        input_text="user",
        text={
            "format": {
                "type": "json_schema",
                "name": "episode_schema",
                "strict": True,
                "schema": {"type": "object"},
            }
        },
    )

    call_kwargs = mock_chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "episode_schema",
            "strict": True,
            "schema": {"type": "object"},
        },
    }


def test_resolve_model_config_reads_five_slots():
    config = {
        "models": {
            "default_slot": "model_slot_3",
            "slots": {
                f"model_slot_{idx}": {
                    "display_name": f"模型 {idx}",
                    "base_url": f"https://example-{idx}.test/v1",
                    "api_key_env": f"MODEL_SLOT_{idx}_API_KEY",
                    "model_id": f"model-{idx}",
                    "enabled": idx == 3,
                }
                for idx in range(1, 6)
            },
        },
        "parser": {},
    }

    resolved = resolve_model_config(config)
    assert resolved["slot_name"] == "model_slot_3"
    assert resolved["display_name"] == "模型 3"
    assert resolved["base_url"] == "https://example-3.test/v1"
    assert resolved["api_key_env"] == "MODEL_SLOT_3_API_KEY"
    assert resolved["model_id"] == "model-3"
