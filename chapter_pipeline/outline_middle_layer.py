from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional


SOURCE_UPSTREAM_TEMPLATES = (
    "templates/webnovel_outline_template_v1.md",
    "templates/webnovel_setting_bible_template_v1.md",
)


REQUIRED_MIDDLE_LAYER_TEMPLATES = (
    "templates/webnovel_orchestration_template_v1.md",
    "templates/webnovel_volume_story_list_template_v1.md",
    "templates/webnovel_chapter_construction_card_template_v1.md",
    "templates/webnovel_handoff_gate_template_v1.md",
)


UNIT_CHAPTER_PATTERN = (6, 6, 6, 7)
SIX_CHAPTER_FUNCTION_PATTERN = ("起", "承", "承", "转", "转", "合")
SEVEN_CHAPTER_FUNCTION_PATTERN = ("起", "承", "承", "转", "转", "合", "合")


@dataclass(frozen=True)
class ChapterSlot:
    chapter_index: int
    volume_id: int
    arc_id: int
    unit_id: int
    volume_chapter_index: int
    arc_chapter_index: int
    unit_chapter_index: int
    unit_chapter_count: int
    structural_function: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class VolumeAgentAssignment:
    agent_id: str
    volume_id: int
    chapter_range: str
    allowed_sources: List[str]
    output_contract: str
    forbidden: List[str]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class OutlineMiddleLayer:
    """Deterministic contracts for the outline-to-chapter-card middle layer."""

    def __init__(self, workspace_root: str | Path | None = None):
        self.workspace_root = Path(workspace_root or Path(__file__).resolve().parents[1])

    def template_paths(self) -> Dict[str, Path]:
        return {
            filename: self.workspace_root / filename
            for filename in SOURCE_UPSTREAM_TEMPLATES + REQUIRED_MIDDLE_LAYER_TEMPLATES
        }

    def validate_templates(self) -> None:
        missing = [str(path) for path in self.template_paths().values() if not path.exists()]
        if missing:
            raise FileNotFoundError("Missing webnovel middle-layer templates: " + ", ".join(missing))

    def build_volume_agent_assignments(self) -> List[VolumeAgentAssignment]:
        assignments: List[VolumeAgentAssignment] = []
        for volume_id in range(1, 5):
            start = (volume_id - 1) * 100 + 1
            end = volume_id * 100
            assignments.append(
                VolumeAgentAssignment(
                    agent_id=f"volume_{volume_id}_story_agent",
                    volume_id=volume_id,
                    chapter_range=f"{start}-{end}",
                    allowed_sources=list(SOURCE_UPSTREAM_TEMPLATES),
                    output_contract="VolumeStoryList",
                    forbidden=[
                        "不能改写全书大纲",
                        "不能改写设定集锁定项",
                        "不能生成正文",
                        "不能直接进入九步第2步",
                    ],
                )
            )
        return assignments

    def build_chapter_slots(self, volume_id: Optional[int] = None) -> List[ChapterSlot]:
        if volume_id is not None and volume_id not in {1, 2, 3, 4}:
            raise ValueError("volume_id must be one of 1, 2, 3, 4")

        slots: List[ChapterSlot] = []
        global_chapter_index = 1
        for current_volume in range(1, 5):
            volume_chapter_index = 1
            for arc_id in range(1, 5):
                arc_chapter_index = 1
                for unit_id, unit_chapter_count in enumerate(UNIT_CHAPTER_PATTERN, start=1):
                    pattern = (
                        SIX_CHAPTER_FUNCTION_PATTERN
                        if unit_chapter_count == 6
                        else SEVEN_CHAPTER_FUNCTION_PATTERN
                    )
                    for unit_chapter_index, structural_function in enumerate(pattern, start=1):
                        slot = ChapterSlot(
                            chapter_index=global_chapter_index,
                            volume_id=current_volume,
                            arc_id=arc_id,
                            unit_id=unit_id,
                            volume_chapter_index=volume_chapter_index,
                            arc_chapter_index=arc_chapter_index,
                            unit_chapter_index=unit_chapter_index,
                            unit_chapter_count=unit_chapter_count,
                            structural_function=structural_function,
                        )
                        if volume_id is None or current_volume == volume_id:
                            slots.append(slot)
                        global_chapter_index += 1
                        volume_chapter_index += 1
                        arc_chapter_index += 1
        return slots

    def build_chapter_construction_card_shell(self, slot: ChapterSlot) -> Dict[str, object]:
        return {
            "chapter_index": slot.chapter_index,
            "structural_position": {
                "volume": slot.volume_id,
                "arc": slot.arc_id,
                "unit": slot.unit_id,
                "volume_chapter_index": slot.volume_chapter_index,
                "arc_chapter_index": slot.arc_chapter_index,
                "unit_chapter_index": slot.unit_chapter_index,
                "function": slot.structural_function,
            },
            "two_sentence_summary": [],
            "core_event": "",
            "character_state_change": "",
            "visible_consequence": "",
            "cliffhanger": "",
            "active_rules": [],
            "active_terms": [],
            "active_characters": [],
            "active_location": "",
            "must_not_write": [],
        }
