from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_PROJECT_ID = "sample_zerg_queen"
DEFAULT_MODEL_SLOT = "model_slot_1"
UNIT_PATTERN = (6, 6, 6, 7)


@dataclass
class ProductionProject:
    project_id: str
    title: str
    genre: str
    author_name: str
    core_promise: str
    ip_policy: str
    first_world: str
    total_chapters: int = 400
    target_chars_per_chapter: int = 2500
    default_model_slot: str = DEFAULT_MODEL_SLOT
    chapter_title_seeds: Dict[str, str] = field(default_factory=dict)

    def project_bundle(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_title": self.title,
            "genre": self.genre,
            "core_promise": self.core_promise,
            "ip_policy": self.ip_policy,
            "first_world": self.first_world,
            "total_chapters": self.total_chapters,
            "target_chars_per_chapter": self.target_chars_per_chapter,
        }


@dataclass
class ProductionProgress:
    last_completed_chapter_index: int = 0
    next_chapter_index: int = 1
    current_volume: int = 1
    current_arc: int = 1
    current_unit: int = 1
    previous_chapter_writeback: str = "新书开局，败局重启，无上一章回写。"
    last_run_id: str = ""
    last_review_stop_point: str = ""
    state: str = "ready"


@dataclass
class ProductionPlan:
    project_id: str
    chapter_indexes: List[int]
    chapter_titles: List[str]
    stop_reason: str
    model_slot: str
    output_root: str
    dry_run: bool = True


@dataclass
class ProductionRunResult:
    ok: bool
    run_id: str
    project_id: str
    dry_run: bool
    chapter_indexes: List[int]
    stop_reason: str
    completed_chapters: List[int] = field(default_factory=list)
    failed_chapter: Optional[int] = None
    error: str = ""
    run_root: str = ""
    next_action: str = ""


def _safe_slug(value: str) -> str:
    normalized = value.strip()
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", normalized).strip("_")
    if slug and slug == normalized:
        return slug

    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    prefix = slug or DEFAULT_PROJECT_ID
    return f"{prefix}_{digest}"


def _default_project(project_id: str = DEFAULT_PROJECT_ID) -> ProductionProject:
    return ProductionProject(
        project_id=_safe_slug(project_id),
        title="我，虫族女皇，带领虫族踏遍万界",
        genre="诸天万界流",
        author_name="默认作者",
        core_promise="败局重启的虫族女皇带领虫群进入原创影子世界，把每个世界变成虫族进化资源场。",
        ip_policy="只使用原创影子世界，不直接使用任何真实知名 IP 世界名。",
        first_world="忍术血脉世界",
        chapter_title_seeds={
            "1": "第一章：败局重启，女皇归巢",
            "2": "第二章：第一枚血脉样本",
            "3": "第三章：忍村边境的寄生眼",
            "4": "第四章：查克拉适配虫",
            "5": "第五章：暗部巡逻线",
            "6": "第六章：母巢第一次进化",
        },
    )


class ProductionRunner:
    def __init__(self, workspace_root: str | Path):
        self.workspace_root = Path(workspace_root)
        self.production_root = self.workspace_root / "novel_outputs" / "production_runs"

    def project_root(self, project_id: str) -> Path:
        return self.production_root / _safe_slug(project_id)

    def ensure_project(self, project_id: str = DEFAULT_PROJECT_ID) -> ProductionProject:
        root = self.project_root(project_id)
        root.mkdir(parents=True, exist_ok=True)
        project_path = root / "project.json"
        progress_path = root / "progress.json"
        if project_path.exists():
            project = ProductionProject(
                **json.loads(project_path.read_text(encoding="utf-8"))
            )
        else:
            project = _default_project(project_id)
            project_path.write_text(
                json.dumps(asdict(project), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if not progress_path.exists():
            self.save_progress(project.project_id, ProductionProgress())
        return project

    def load_progress(self, project_id: str) -> ProductionProgress:
        path = self.project_root(project_id) / "progress.json"
        if not path.exists():
            self.ensure_project(project_id)
        return ProductionProgress(**json.loads(path.read_text(encoding="utf-8")))

    def save_progress(self, project_id: str, progress: ProductionProgress) -> None:
        root = self.project_root(project_id)
        root.mkdir(parents=True, exist_ok=True)
        position = self.position_for_chapter(progress.next_chapter_index)
        progress.current_volume = position["volume"]
        progress.current_arc = position["arc"]
        progress.current_unit = position["unit"]
        (root / "progress.json").write_text(
            json.dumps(asdict(progress), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def position_for_chapter(chapter_index: int) -> Dict[str, int]:
        zero_based = max(chapter_index - 1, 0)
        volume = zero_based // 100 + 1
        chapter_in_volume = zero_based % 100
        arc = chapter_in_volume // 25 + 1
        chapter_in_arc = chapter_in_volume % 25 + 1

        cumulative = 0
        unit = 1
        for index, length in enumerate(UNIT_PATTERN, start=1):
            cumulative += length
            if chapter_in_arc <= cumulative:
                unit = index
                break
        return {"volume": volume, "arc": arc, "unit": unit}

    @staticmethod
    def _default_count_and_reason(next_chapter_index: int) -> tuple[int, str]:
        if next_chapter_index == 1:
            return 3, "opening_review"
        if next_chapter_index == 4:
            return 3, "first_unit_completion"

        chapter_in_arc = (next_chapter_index - 1) % 25 + 1
        unit_start = 1
        for length in UNIT_PATTERN:
            unit_end = unit_start + length - 1
            if unit_start <= chapter_in_arc <= unit_end:
                return unit_end - chapter_in_arc + 1, f"unit_review_{length}"
            unit_start = unit_end + 1
        return 1, "chapter_review"

    def _chapter_title(self, project: ProductionProject, chapter_index: int) -> str:
        return project.chapter_title_seeds.get(
            str(chapter_index),
            f"第{chapter_index}章：虫群远征记录",
        )

    def plan_run(
        self,
        project_id: str = DEFAULT_PROJECT_ID,
        chapters: Optional[int] = None,
        from_chapter: Optional[int] = None,
        model_slot: Optional[str] = None,
        dry_run: bool = True,
    ) -> ProductionPlan:
        project = self.ensure_project(project_id)
        progress = self.load_progress(project.project_id)
        start = from_chapter if from_chapter is not None else progress.next_chapter_index
        if start > project.total_chapters:
            return ProductionPlan(
                project_id=project.project_id,
                chapter_indexes=[],
                chapter_titles=[],
                stop_reason="book_completed",
                model_slot=model_slot or project.default_model_slot,
                output_root=str(self.project_root(project.project_id)),
                dry_run=dry_run,
            )
        default_count, stop_reason = self._default_count_and_reason(start)
        count = chapters if chapters is not None else default_count
        indexes = list(range(start, min(start + count, project.total_chapters + 1)))
        return ProductionPlan(
            project_id=project.project_id,
            chapter_indexes=indexes,
            chapter_titles=[self._chapter_title(project, index) for index in indexes],
            stop_reason=stop_reason if chapters is None else "manual_chapter_count",
            model_slot=model_slot or project.default_model_slot,
            output_root=str(self.project_root(project.project_id)),
            dry_run=dry_run,
        )

    @staticmethod
    def _new_run_id() -> str:
        return "run_" + datetime.now().strftime("%Y%m%d_%H%M%S")

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def run(
        self,
        project_id: str = DEFAULT_PROJECT_ID,
        chapters: Optional[int] = None,
        from_chapter: Optional[int] = None,
        model_slot: Optional[str] = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> ProductionRunResult:
        plan = self.plan_run(
            project_id=project_id,
            chapters=chapters,
            from_chapter=from_chapter,
            model_slot=model_slot,
            dry_run=dry_run,
        )
        run_id = self._new_run_id()
        run_root = self.project_root(plan.project_id) / "runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)

        run_config = {
            "run_id": run_id,
            "project_id": plan.project_id,
            "chapter_indexes": plan.chapter_indexes,
            "chapter_titles": plan.chapter_titles,
            "stop_reason": plan.stop_reason,
            "model_slot": plan.model_slot,
            "dry_run": dry_run,
            "force": force,
        }
        self._write_json(run_root / "run_config.json", run_config)

        if dry_run:
            result = ProductionRunResult(
                ok=True,
                run_id=run_id,
                project_id=plan.project_id,
                dry_run=True,
                chapter_indexes=plan.chapter_indexes,
                stop_reason=plan.stop_reason,
                run_root=str(run_root),
                next_action="dry_run_only",
            )
            self._write_json(run_root / "run_summary.json", asdict(result))
            return result

        raise RuntimeError("production execution is implemented in the execution task")
