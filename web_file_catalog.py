from __future__ import annotations

import base64
import json
import mimetypes
import os
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class CatalogRoot:
    key: str
    label: str
    path: Path
    description: str


class GeneratedFileCatalog:
    """Manifest service for generated project files shown in the web console."""

    def __init__(self, workspace_root: str | Path):
        self.workspace_root = Path(workspace_root).resolve()
        self.roots: Dict[str, CatalogRoot] = {
            "novel_outputs": CatalogRoot(
                key="novel_outputs",
                label="小说章节产物",
                path=self.workspace_root / "novel_outputs",
                description="九步章节生产线生成的正文、质检报告、回写和执行计划。",
            ),
            "scripts_output": CatalogRoot(
                key="scripts_output",
                label="存稿与打包产物",
                path=self.workspace_root / "scripts_output",
                description="番茄小说存稿包、历史流水线文本产物和导出压缩包。",
            ),
            "reports": CatalogRoot(
                key="reports",
                label="运行报告",
                path=self.workspace_root / "reports",
                description="前置立项、批处理、诊断和审计报告。",
            ),
        }

    @staticmethod
    def _encode_id(root_key: str, rel_path: str) -> str:
        raw = json.dumps({"root": root_key, "path": rel_path}, ensure_ascii=False, separators=(",", ":"))
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_id(file_id: str) -> Dict[str, str]:
        padded = file_id + "=" * (-len(file_id) % 4)
        payload = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        data = json.loads(payload)
        if not isinstance(data, dict) or not isinstance(data.get("root"), str) or not isinstance(data.get("path"), str):
            raise ValueError("Invalid file id")
        return {"root": data["root"], "path": data["path"]}

    @staticmethod
    def _iter_files(root: Path) -> Iterable[Path]:
        if not root.exists() or not root.is_dir():
            return []
        return (
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.name != ".DS_Store"
            and "__pycache__" not in path.parts
        )

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / 1024 / 1024:.1f} MB"

    def list_files(self, max_files_per_root: int = 120) -> Dict[str, object]:
        groups: List[Dict[str, object]] = []
        total = 0
        for root in self.roots.values():
            files = []
            for path in sorted(self._iter_files(root.path), key=lambda p: p.stat().st_mtime, reverse=True)[:max_files_per_root]:
                stat = path.stat()
                rel_path = path.relative_to(root.path).as_posix()
                file_id = self._encode_id(root.key, rel_path)
                ext = path.suffix.lower()
                files.append(
                    {
                        "id": file_id,
                        "name": path.name,
                        "relative_path": rel_path,
                        "root": root.key,
                        "size": stat.st_size,
                        "size_label": self._format_size(stat.st_size),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "extension": ext or "file",
                        "mime_type": mimetypes.guess_type(path.name)[0] or "text/plain",
                        "open_url": f"/api/open-file/{file_id}",
                    }
                )
            total += len(files)
            groups.append(
                {
                    "key": root.key,
                    "label": root.label,
                    "description": root.description,
                    "path": str(root.path),
                    "files": files,
                }
            )
        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": total,
            "groups": groups,
        }

    def resolve(self, file_id: str) -> Path:
        data = self._decode_id(file_id)
        root = self.roots.get(data["root"])
        if root is None:
            raise FileNotFoundError("Unknown file root")
        candidate = (root.path / data["path"]).resolve()
        try:
            candidate.relative_to(root.path.resolve())
        except ValueError as exc:
            raise PermissionError("File is outside allowed generated roots") from exc
        if not candidate.exists() or not candidate.is_file():
            raise FileNotFoundError("Generated file not found")
        return candidate

    def open_with_default_app(self, file_id: str) -> Dict[str, str]:
        path = self.resolve(file_id)
        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(["open", str(path)])
        elif system == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return {"status": "opened", "path": str(path), "name": path.name}
