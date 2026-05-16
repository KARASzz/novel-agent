from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

try:  # pragma: no cover - Windows-only import path
    import winreg  # type: ignore
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None  # type: ignore[assignment]


DEFAULT_RUNTIME_ENV_NAMES = (
    "MINIMAX_API_KEY",
    "DASHSCOPE_API_KEY",
    "TAVILY_API_KEY",
    "BRAVE_SEARCH_API_KEY",
    "BRAVE_API_KEY",
    "MODEL_SLOT_1_API_KEY",
    "MODEL_SLOT_2_API_KEY",
    "MODEL_SLOT_3_API_KEY",
    "MODEL_SLOT_4_API_KEY",
    "MODEL_SLOT_5_API_KEY",
    "ALIBABA_CLOUD_ACCESS_KEY_ID",
    "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    "WORKSPACE_ID",
    "BAILIAN_INDEX_ID",
)

_USER_ENV_KEY = r"Environment"
_MACHINE_ENV_KEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"


def _read_windows_registry_env(name: str) -> Optional[Dict[str, str]]:
    if os.name != "nt" or winreg is None:
        return None

    registry_paths = (
        ("user", winreg.HKEY_CURRENT_USER, _USER_ENV_KEY),
        ("machine", winreg.HKEY_LOCAL_MACHINE, _MACHINE_ENV_KEY),
    )
    for source, hive, subkey in registry_paths:
        try:
            with winreg.OpenKey(hive, subkey) as handle:
                value, _ = winreg.QueryValueEx(handle, name)
        except FileNotFoundError:
            continue
        except OSError:
            continue
        if value is None:
            continue
        return {"name": name, "value": str(value), "source": source}
    return None


def bootstrap_runtime_environment(
    names: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Populate missing runtime env vars from the Windows user registry."""
    target_names = tuple(names or DEFAULT_RUNTIME_ENV_NAMES)
    loaded: List[Dict[str, str]] = []
    missing: List[str] = []

    for name in target_names:
        if os.environ.get(name):
            loaded.append({"name": name, "source": "process"})
            continue

        record = _read_windows_registry_env(name)
        if record and record.get("value"):
            os.environ[name] = record["value"]
            loaded.append({"name": name, "source": record["source"]})
        else:
            missing.append(name)

    return {
        "loaded": loaded,
        "missing": missing,
    }


def describe_runtime_environment(names: Optional[Iterable[str]] = None) -> List[Dict[str, str]]:
    report = bootstrap_runtime_environment(names)
    loaded_map = {item["name"]: item["source"] for item in report["loaded"]}
    status: List[Dict[str, str]] = []
    for name in tuple(names or DEFAULT_RUNTIME_ENV_NAMES):
        if name in loaded_map:
            status.append({"name": name, "status": "present", "source": loaded_map[name]})
        else:
            status.append({"name": name, "status": "missing", "source": ""})
    return status
