from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - exercised when dependency is absent
    class OpenAI:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError("Missing dependency: install `openai` to call model APIs.")


@dataclass
class LLMResponse:
    """Small compatibility wrapper around a Chat Completions response."""

    raw: Any
    output_text: str
    usage: Any = None


class LLMClient:
    """
    OpenAI Chat Completions compatible client.

    The rest of the project can keep calling `create_response(...)` with
    `instructions + input_text`, while this class maps that shape onto the
    provider-neutral `chat.completions.create` API used by MiniMax and other
    OpenAI-compatible domestic endpoints.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float = 300.0,
    ):
        if not base_url:
            raise ValueError("OpenAI Chat Completions base_url is required.")

        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    @staticmethod
    def _normalize_output_text(text: Any) -> str:
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)

        # Remove internal reasoning blocks before persisting model output.
        text = re.sub(r"<think\b[^>]*>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

        # If the whole response is wrapped in a single fence, unwrap it.
        fenced = re.fullmatch(r"```(?:[a-zA-Z0-9_-]+)?\s*([\s\S]*?)\s*```", text)
        if fenced:
            text = fenced.group(1).strip()

        return text.strip()

    @staticmethod
    def _extract_output_text(response: Any) -> str:
        choices = getattr(response, "choices", None)
        if choices is None and isinstance(response, dict):
            choices = response.get("choices")
        if not choices:
            return ""

        first = choices[0]
        message = getattr(first, "message", None)
        if message is None and isinstance(first, dict):
            message = first.get("message")

        if isinstance(message, dict):
            content = message.get("content", "")
        else:
            content = getattr(message, "content", "")

        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or ""))
                else:
                    parts.append(str(item))
            return LLMClient._normalize_output_text("".join(parts))
        return LLMClient._normalize_output_text(content or "")

    @staticmethod
    def _convert_text_format(text: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(text, dict):
            return None
        fmt = text.get("format")
        if fmt == "json":
            return {"type": "json_object"}
        if not isinstance(fmt, dict):
            return None

        fmt_type = fmt.get("type")
        if fmt_type == "json_schema":
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": fmt.get("name", "response_schema"),
                    "strict": bool(fmt.get("strict", True)),
                    "schema": fmt.get("schema", {}),
                },
            }
        if fmt_type == "json_object":
            return {"type": "json_object"}
        return None

    def create_response(
        self,
        model: str,
        instructions: str,
        input_text: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.1,
        top_p: float = 0.7,
        enable_thinking: bool = False,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Create a model response through Chat Completions."""
        body: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": input_text},
            ],
            "temperature": temperature,
            "top_p": top_p,
        }

        if tools:
            body["tools"] = tools

        text_format = kwargs.pop("text", None)
        response_format = kwargs.pop("response_format", None)
        if response_format:
            body["response_format"] = response_format
        else:
            converted_format = self._convert_text_format(text_format)
            if converted_format:
                body["response_format"] = converted_format

        # Generic OpenAI-compatible providers should not receive provider-specific
        # flags by default. Keep a deliberate escape hatch for endpoints that need it.
        extra_body = kwargs.pop("extra_body", None)
        if extra_body:
            body["extra_body"] = extra_body
        elif enable_thinking:
            provider_options = kwargs.pop("provider_options", None)
            if provider_options:
                body["extra_body"] = provider_options

        body.update(kwargs)

        if timeout is not None and hasattr(self.client, "with_options"):
            raw = self.client.with_options(timeout=timeout).chat.completions.create(**body)
        else:
            raw = self.client.chat.completions.create(**body)

        return LLMResponse(
            raw=raw,
            output_text=self._extract_output_text(raw),
            usage=getattr(raw, "usage", None),
        )
