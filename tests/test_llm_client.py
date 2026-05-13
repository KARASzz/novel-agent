import pytest
from unittest.mock import MagicMock, patch
from core_engine.llm_client import LLMClient

@patch('core_engine.llm_client.OpenAI')
def test_llm_client_initialization(mock_openai):
    client = LLMClient(api_key="sk-test", base_url="http://test.ai")
    
    # Check if OpenAI was initialized with session cache header
    mock_openai.assert_called_once()
    args, kwargs = mock_openai.call_args
    assert kwargs['api_key'] == "sk-test"
    assert kwargs['base_url'] == "http://test.ai"
    assert kwargs['default_headers'] == {"x-dashscope-session-cache": "enable"}

@patch('core_engine.llm_client.OpenAI')
def test_llm_client_create_response(mock_openai):
    # Setup mock
    mock_responses = MagicMock()
    mock_openai.return_value.responses = mock_responses
    
    client = LLMClient(api_key="sk-test")
    
    client.create_response(
        model="qwen-test",
        instructions="do this",
        input_text="hello",
        temperature=0.5,
        enable_thinking=True,
        tools=[{"type": "web_search"}]
    )
    
    # Verify create call parameters
    mock_responses.create.assert_called_once()
    call_kwargs = mock_responses.create.call_args.kwargs
    
    assert call_kwargs['model'] == "qwen-test"
    assert call_kwargs['instructions'] == "do this"
    assert call_kwargs['input'] == "hello"
    assert call_kwargs['temperature'] == 0.5
    assert call_kwargs['extra_body'] == {"enable_thinking": True}
    assert call_kwargs['tools'] == [{"type": "web_search"}]

@patch('core_engine.llm_client.OpenAI')
def test_llm_client_extra_kwargs(mock_openai):
    mock_responses = MagicMock()
    mock_openai.return_value.responses = mock_responses
    
    client = LLMClient(api_key="sk-test")
    
    # Test strict mode / json schema passing via extra kwargs
    client.create_response(
        model="qwen-test",
        instructions="system",
        input_text="user",
        text={"format": "json"}
    )
    
    call_kwargs = mock_responses.create.call_args.kwargs
    assert call_kwargs['text'] == {"format": "json"}
