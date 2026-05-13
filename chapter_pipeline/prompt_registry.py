from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional


PROMPT_BLOCK_TAGS = (
    "redstar_nine_step_chapter_pipeline_v2_2",
    "stage_1_chapter_variable_extraction",
    "stage_2_input_card",
    "stage_3_ontology_tree_and_tot",
    "stage_4_xy_pruning",
    "stage_5_six_beat_construction_table",
    "stage_6a_draft_two_beats",
    "stage_6b_single_factor_iteration",
    "stage_7_reader_review_and_commercial_revision",
    "stage_8_evidence_exit_gate",
    "stage_9_chapter_navigation_script",
)


SECTION_HEADINGS = {
    "stage_commands": "# 2. 九步生产线阶段口令合集",
    "global_red_lines": "# 3. 全局压测红线",
    "minimum_acceptance": "# 4. 每章最低放行标准",
    "version_notes": "# 5. 版本维护说明",
}


@dataclass(frozen=True)
class PromptBlock:
    name: str
    content: str


class ChapterPromptRegistry:
    """Loads the nine-step chapter pipeline prompts from the master markdown.

    The root markdown remains the source of truth. This registry extracts the
    exact XML prompt blocks by tag so implementation code can use the original
    prompts without hand-maintaining duplicated copies.
    """

    def __init__(self, master_path: Optional[str | Path] = None):
        if master_path is None:
            root = Path(__file__).resolve().parents[1]
            master_path = root / "《红星锚定》九步章节生产线完整母版 v2.2.md"
        self.master_path = Path(master_path)
        self._source: Optional[str] = None
        self._blocks: Optional[Dict[str, PromptBlock]] = None

    @property
    def source(self) -> str:
        if self._source is None:
            self._source = self.master_path.read_text(encoding="utf-8")
        return self._source

    @staticmethod
    def _extract_tag(source: str, tag: str) -> str:
        pattern = rf"<{re.escape(tag)}\b[^>]*>.*?</{re.escape(tag)}>"
        match = re.search(pattern, source, flags=re.DOTALL)
        if not match:
            raise KeyError(f"Prompt block not found: {tag}")
        return match.group(0).strip()

    def blocks(self) -> Dict[str, PromptBlock]:
        if self._blocks is None:
            self._blocks = {
                tag: PromptBlock(tag, self._extract_tag(self.source, tag))
                for tag in PROMPT_BLOCK_TAGS
            }
        return self._blocks

    def get(self, name: str) -> str:
        return self.blocks()[name].content

    def names(self) -> Iterable[str]:
        return self.blocks().keys()

    def section(self, name: str) -> str:
        heading = SECTION_HEADINGS[name]
        source = self.source
        start = source.find(heading)
        if start < 0:
            raise KeyError(f"Section not found: {name}")

        next_heading = re.search(r"\n# \d+\. ", source[start + len(heading) :])
        if next_heading:
            end = start + len(heading) + next_heading.start()
            return source[start:end].strip()
        return source[start:].strip()

    def validate_required_blocks(self) -> None:
        missing = [tag for tag in PROMPT_BLOCK_TAGS if tag not in self.blocks()]
        if missing:
            raise KeyError(f"Missing prompt blocks: {', '.join(missing)}")
        for section_name in SECTION_HEADINGS:
            self.section(section_name)
