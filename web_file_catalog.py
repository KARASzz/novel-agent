from __future__ import annotations

import base64
import html
import json
import mimetypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


DISPLAY_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".log",
    ".html",
}


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
                        "can_preview": ext in DISPLAY_EXTENSIONS,
                        "mime_type": mimetypes.guess_type(path.name)[0] or "text/plain",
                        "open_url": f"/files/open/{file_id}",
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

    def preview_html(self, file_id: str, max_chars: int = 240_000) -> str:
        path = self.resolve(file_id)
        root_label = next(
            root.label for root in self.roots.values() if path.is_relative_to(root.path.resolve())
        )
        ext = path.suffix.lower()
        stat = path.stat()
        title = path.name
        if ext in DISPLAY_EXTENSIONS:
            content = path.read_text(encoding="utf-8", errors="replace")
            truncated = len(content) > max_chars
            if truncated:
                content = content[:max_chars] + "\n\n[内容过长，已在网页预览中截断。]"
            body = f"<pre>{html.escape(content)}</pre>"
        else:
            body = (
                "<div class=\"binary-note\">"
                "该文件不是文本预览类型。网页已打开文件清单页，不触发浏览器下载。"
                "</div>"
            )
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin: 0; background: #f6f4ee; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    header {{ background: #22324a; color: white; padding: 14px 18px; }}
    main {{ padding: 18px; }}
    .meta {{ color: #536271; font-size: 13px; margin-top: 6px; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: white; border: 1px solid #d6dde6; border-radius: 8px; padding: 16px; line-height: 1.6; }}
    .binary-note {{ background: white; border: 1px solid #d6dde6; border-radius: 8px; padding: 16px; }}
  </style>
</head>
<body>
  <header>
    <strong>{html.escape(title)}</strong>
    <div class="meta">{html.escape(root_label)} | {self._format_size(stat.st_size)} | {datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")}</div>
  </header>
  <main>{body}</main>
</body>
</html>"""
