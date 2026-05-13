import copy
import json
import os
from typing import Any, Dict, Optional

_CONFIG_CACHE = None
DEFAULT_MODEL = "qwen3.6-plus"


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
        "pipeline": {
            "max_workers": 3,
            "report_json": True,
            "file_timeout_sec": 300,
            "rate_limit": {
                "requests_per_second": 0,  # 0 means disabled
            },
        },
        "parser": {
            "api_key_env": "DASHSCOPE_API_KEY",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": DEFAULT_MODEL,
            "max_retries": 3,
            "timeout": 300,
            "enable_rag": False,
            "strict_validation": True,
            "tools": {
                "web_search": True,
                "web_extractor": True,
                "code_interpreter": True,
                "file_search": False,
                "enable_thinking": True,
            },
            "retry": {
                "base_delay_sec": 1.0,
                "max_delay_sec": 8.0,
                "jitter_sec": 0.25,
            },
        },
        "validator": {
            "min_duration_sec": 60,
            "max_duration_sec": 150,
            "speech_rate": 4.5,
        },
        "scoring": {
            "duration_short_penalty": 10,
            "duration_long_penalty": 30,
            "no_hook_penalty": 15,
            "paywall_no_hook_penalty": 40,
            "first3_no_hook_penalty": 20,
        },
        "logging": {
            "log_level": "INFO",
        },
        "rag": {
            "backend": "local",
            "workspace_id_env": "WORKSPACE_ID",
            "index_id_env": "BAILIAN_INDEX_ID",
            "default_query": "短剧编剧通用规范、商业钩子设计、付费点卡点技巧",
            "max_candidates": 120,
            "snippet_chars": 500,
            "top_k": 2,
        },
        "cache": {
            "parser_result_ttl_days": 180,
        },
    }
