import copy
import json
import os
from typing import Any, Dict, Optional

_CONFIG_CACHE = None
DEFAULT_MODEL_SLOT = "model_slot_1"


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def reset_config_cache() -> None:
    global _CONFIG_CACHE
    _CONFIG_CACHE = None


def get_model_registry(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return the configured OpenAI Chat Completions model registry."""
    cfg = config or load_config()
    registry = cfg.get("models", {})
    if not isinstance(registry, dict):
        return {}
    return registry


def resolve_model_config(
    config: Optional[Dict[str, Any]] = None,
    slot_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve a model slot into the values needed by LLMClient.

    The project now treats model choices as runtime slots so the web console can
    switch providers without changing pipeline code.
    """
    cfg = config or load_config()
    llm_cfg = cfg.get("llm", {})
    registry = get_model_registry(cfg)
    slots = registry.get("slots", {}) if isinstance(registry.get("slots", {}), dict) else {}
    selected = (
        slot_name
        or llm_cfg.get("model_slot")
        or registry.get("default_slot")
        or DEFAULT_MODEL_SLOT
    )
    slot = slots.get(selected)

    if isinstance(slot, dict):
        return {
            "slot_name": selected,
            "display_name": slot.get("display_name", selected),
            "base_url": slot.get("base_url") or llm_cfg.get("base_url", ""),
            "api_key_env": slot.get("api_key_env") or llm_cfg.get("api_key_env", ""),
            "model_id": slot.get("model_id") or llm_cfg.get("model", ""),
            "enabled": bool(slot.get("enabled", True)),
            "note": slot.get("note", ""),
        }

    return {
        "slot_name": selected,
        "display_name": selected,
        "base_url": llm_cfg.get("base_url", ""),
        "api_key_env": llm_cfg.get("api_key_env", ""),
        "model_id": llm_cfg.get("model", ""),
        "enabled": True,
        "note": "llm_config",
    }


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load config file and deep-merge with defaults."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    defaults = _defaults()
    if config_path is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(root, "config.yaml")

    if not os.path.exists(config_path):
        _CONFIG_CACHE = defaults
        return _CONFIG_CACHE

    user_cfg: Dict[str, Any] = {}
    try:
        import yaml

        with open(config_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                user_cfg = loaded
    except ImportError:
        json_path = config_path.replace(".yaml", ".json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    user_cfg = loaded
    except Exception:
        user_cfg = {}

    _CONFIG_CACHE = _deep_merge(defaults, user_cfg)
    return _CONFIG_CACHE


def _defaults() -> Dict[str, Any]:
    return {
        "project": {
            "platform": "fanqie_novel",
            "product_name": "番茄小说一键制造机",
        },
        "models": {
            "default_slot": DEFAULT_MODEL_SLOT,
            "slots": {
                "model_slot_1": {
                    "display_name": "模型占位 1",
                    "base_url": "",
                    "api_key_env": "MINIMAX_API_KEY",
                    "model_id": "MiniMax-M2.7",
                    "enabled": True,
                    "note": "预留 OpenAI Chat Completions 模型接口，后续接入真实模型。",
                },
                "model_slot_2": {
                    "display_name": "模型占位 2",
                    "base_url": "",
                    "api_key_env": "DASHSCOPE_API_KEY",
                    "model_id": "kimi-k2.6",
                    "enabled": False,
                    "note": "预留 OpenAI Chat Completions 模型接口，后续接入真实模型。",
                },
                "model_slot_3": {
                    "display_name": "模型占位 3",
                    "base_url": "",
                    "api_key_env": "MODEL_SLOT_3_API_KEY",
                    "model_id": "model-slot-3",
                    "enabled": False,
                    "note": "预留 OpenAI Chat Completions 模型接口，后续接入真实模型。",
                },
                "model_slot_4": {
                    "display_name": "模型占位 4",
                    "base_url": "",
                    "api_key_env": "MODEL_SLOT_4_API_KEY",
                    "model_id": "model-slot-4",
                    "enabled": False,
                    "note": "预留 OpenAI Chat Completions 模型接口，后续接入真实模型。",
                },
                "model_slot_5": {
                    "display_name": "模型占位 5",
                    "base_url": "",
                    "api_key_env": "MODEL_SLOT_5_API_KEY",
                    "model_id": "model-slot-5",
                    "enabled": False,
                    "note": "预留 OpenAI Chat Completions 模型接口，后续接入真实模型。",
                },
            },
        },
        "llm": {
            "model_slot": DEFAULT_MODEL_SLOT,
            "api_key_env": "MINIMAX_API_KEY",
            "base_url": "https://api.minimaxi.com/v1",
            "model": "MiniMax-M2.7",
            "max_retries": 3,
            "timeout": 300,
            "enable_rag": False,
            "strict_validation": True,
            "tools": {
                "web_search": False,
                "web_extractor": False,
                "code_interpreter": False,
                "file_search": False,
                "enable_thinking": False,
            },
            "retry": {
                "base_delay_sec": 1.0,
                "max_delay_sec": 8.0,
                "jitter_sec": 0.25,
            },
        },
        "logging": {
            "log_level": "INFO",
        },
        "rag": {
            "backend": "local",
            "workspace_id_env": "WORKSPACE_ID",
            "index_id_env": "BAILIAN_INDEX_ID",
            "default_query": "番茄小说开篇节奏、追读钩子、爽点外化、章节推进、读者留存",
            "max_candidates": 120,
            "snippet_chars": 500,
            "top_k": 2,
        },
        "cache": {
            "chapter_snapshot_ttl_days": 180,
        },
    }
