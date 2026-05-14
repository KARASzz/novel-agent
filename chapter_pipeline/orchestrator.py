from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from chapter_pipeline.prompt_registry import ChapterPromptRegistry


class AgentLevel(str, Enum):
    CEO = "CEO Agent"
    MANAGER = "Manager Agent"
    WORKER = "Worker Agent"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionMode(str, Enum):
    SERIAL = "serial"
    PARALLEL = "parallel"


SIX_B_ITERATION_ROUNDS = (
    "事件推进",
    "身体感受",
    "环境变化",
    "旁人反应",
    "流程卡点",
    "去AI腔与句子口感",
)


BEAT_GROUPS = ((1, 2), (3, 4), (5, 6))


@dataclass
class OrchestratorLedger:
    project_goal: str
    current_stage: str = "not_started"
    completed: List[str] = field(default_factory=list)
    pending: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    human_decisions: List[str] = field(default_factory=list)
    forbidden: List[str] = field(default_factory=list)
    next_step: str = "start"

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class ChapterPipelineInput:
    project_bundle: Dict[str, Any] = field(default_factory=dict)
    current_chapter: str = ""
    previous_chapter_writeback: str = ""
    local_kb_reference: str = ""
    search_summary: str = ""
    chapter_index: int = 1
    model_slot: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class AgentTask:
    task_id: str
    title: str
    agent_level: AgentLevel
    manager: str
    worker: Optional[str]
    prompt_block: Optional[str]
    depends_on: List[str] = field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.SERIAL
    can_run_parallel: bool = False
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    failure_reason: Optional[str] = None
    input_payload: Dict[str, object] = field(default_factory=dict)
    output_payload: Dict[str, object] = field(default_factory=dict)
    final_decision: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["agent_level"] = self.agent_level.value
        payload["execution_mode"] = self.execution_mode.value
        payload["status"] = self.status.value
        return payload


@dataclass
class ChapterExecutionPlan:
    ledger: OrchestratorLedger
    chapter_input: ChapterPipelineInput
    tasks: List[AgentTask]
    prompt_blocks: List[str]
    six_b_rounds: List[str]

    def task_map(self) -> Dict[str, AgentTask]:
        return {task.task_id: task for task in self.tasks}

    def validate(self) -> None:
        tasks = self.task_map()

        stage_6_tasks = [task for task in self.tasks if task.task_id.startswith("stage_6")]
        for task in stage_6_tasks:
            if task.can_run_parallel or task.execution_mode != ExecutionMode.SERIAL:
                raise ValueError(f"Stage 6 must be strictly serial: {task.task_id}")

        previous_task = "stage_5"
        for left, right in BEAT_GROUPS:
            group_id = f"beats_{left}_{right}"
            draft_task_id = f"stage_6a_{group_id}"
            draft_task = tasks[draft_task_id]
            if draft_task.depends_on != [previous_task]:
                raise ValueError(f"Invalid 6A dependency: {draft_task_id}")

            previous_round_id = draft_task_id
            for round_index in range(1, len(SIX_B_ITERATION_ROUNDS) + 1):
                round_task_id = f"stage_6b_{group_id}_round_{round_index}"
                round_task = tasks[round_task_id]
                if round_task.depends_on != [previous_round_id]:
                    raise ValueError(f"Invalid 6B dependency: {round_task_id}")
                previous_round_id = round_task_id
            previous_task = previous_round_id

        stage_7 = tasks["stage_7"]
        if stage_7.depends_on != ["stage_6b_beats_5_6_round_6"]:
            raise ValueError("Stage 7 must wait for the final 6B round.")

    def to_dict(self) -> Dict[str, object]:
        return {
            "ledger": self.ledger.to_dict(),
            "chapter_input": self.chapter_input.to_dict(),
            "tasks": [task.to_dict() for task in self.tasks],
            "prompt_blocks": self.prompt_blocks,
            "six_b_rounds": self.six_b_rounds,
        }


@dataclass
class ChapterPipelineOutput:
    project_id: str
    chapter_index: int
    chapter_title: str
    chapter_text: str
    stage_summaries: Dict[str, str]
    fanqie_quality_report: Dict[str, object]
    next_chapter_writeback: Dict[str, object]
    output_files: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class ChapterOrchestrator:
    """Hierarchical chapter orchestration skeleton.

    This class does not call production models yet. It defines the execution
    ledger, task graph, deterministic mock runner, and output contract that
    the FastAPI console and future model runner will use.
    """

    def __init__(self, prompt_registry: Optional[ChapterPromptRegistry] = None):
        self.prompt_registry = prompt_registry or ChapterPromptRegistry()

    @staticmethod
    def _stage_task(
        task_id: str,
        title: str,
        prompt_block: str,
        depends_on: Optional[List[str]] = None,
    ) -> AgentTask:
        return AgentTask(
            task_id=task_id,
            title=title,
            agent_level=AgentLevel.MANAGER,
            manager="Prompt Manager Agent",
            worker="Stage Worker Agent",
            prompt_block=prompt_block,
            depends_on=depends_on or [],
        )

    @staticmethod
    def _validate_single_chapter_scope(current_chapter: str) -> None:
        if not current_chapter.strip():
            raise ValueError("current_chapter is required")
        range_pattern = r"第\s*[\d一二三四五六七八九十百千万]+\s*[-~至到]\s*[\d一二三四五六七八九十百千万]+\s*章"
        if re.search(range_pattern, current_chapter):
            raise ValueError("Current chapter scope must contain exactly one chapter.")
        chapter_mentions = re.findall(r"第\s*[\d一二三四五六七八九十百千万]+\s*章", current_chapter)
        if len(set(chapter_mentions)) > 1:
            raise ValueError("Current chapter scope must contain exactly one chapter.")

    @staticmethod
    def _project_id(project_bundle: Dict[str, Any]) -> str:
        for key in ("project_id", "id", "bundle_id"):
            value = project_bundle.get(key)
            if value:
                return str(value)
        capsule = project_bundle.get("project_capsule")
        if isinstance(capsule, dict):
            value = capsule.get("project_id") or capsule.get("project_title")
            if value:
                return str(value)
        return "novel_project"

    @staticmethod
    def _safe_slug(value: str, fallback: str) -> str:
        ascii_slug = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
        return ascii_slug[:48] or fallback

    @staticmethod
    def _task_input(task: AgentTask, chapter_input: ChapterPipelineInput) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "current_chapter": chapter_input.current_chapter,
            "chapter_index": chapter_input.chapter_index,
            "project_bundle": chapter_input.project_bundle,
            "previous_chapter_writeback": chapter_input.previous_chapter_writeback,
        }
        if task.task_id == "ceo_intake":
            payload.update(
                {
                    "local_kb_reference": chapter_input.local_kb_reference,
                    "search_summary": chapter_input.search_summary,
                    "model_slot": chapter_input.model_slot,
                }
            )
        if task.task_id.startswith("stage_6a_beats_"):
            payload["beat_group"] = task.task_id.removeprefix("stage_6a_beats_").replace("_", "/")
        if task.task_id.startswith("stage_6b_beats_"):
            payload["iteration_round"] = task.title.split("：", 1)[-1]
            payload["single_factor_only"] = True
        return payload

    def _attach_task_inputs(self, tasks: List[AgentTask], chapter_input: ChapterPipelineInput) -> None:
        for task in tasks:
            task.input_payload = self._task_input(task, chapter_input)

    def build_plan(
        self,
        project_goal: str,
        current_chapter: str,
        previous_chapter_script: str = "",
        project_bundle: Optional[Dict[str, Any]] = None,
        local_kb_reference: str = "",
        search_summary: str = "",
        chapter_index: int = 1,
        model_slot: str = "",
    ) -> ChapterExecutionPlan:
        self.prompt_registry.validate_required_blocks()
        self._validate_single_chapter_scope(current_chapter)

        chapter_input = ChapterPipelineInput(
            project_bundle=project_bundle or {},
            current_chapter=current_chapter,
            previous_chapter_writeback=previous_chapter_script,
            local_kb_reference=local_kb_reference,
            search_summary=search_summary,
            chapter_index=chapter_index,
            model_slot=model_slot,
        )

        tasks: List[AgentTask] = [
            AgentTask(
                task_id="ceo_intake",
                title=f"总调度接收章节任务：{current_chapter}",
                agent_level=AgentLevel.CEO,
                manager="CEO Agent",
                worker=None,
                prompt_block="redstar_nine_step_chapter_pipeline_v2_2",
            ),
            self._stage_task(
                "stage_1_2",
                "第1步章节变量自动抽取，并生成第2步输入卡",
                "stage_1_chapter_variable_extraction",
                depends_on=["ceo_intake"],
            ),
            self._stage_task(
                "stage_3",
                "第3步本体论文字树形图 + ToT多路径发散",
                "stage_3_ontology_tree_and_tot",
                depends_on=["stage_1_2"],
            ),
            self._stage_task(
                "stage_4",
                "第4步X/Y双线剪枝",
                "stage_4_xy_pruning",
                depends_on=["stage_3"],
            ),
            self._stage_task(
                "stage_5",
                "第5步六节拍施工表",
                "stage_5_six_beat_construction_table",
                depends_on=["stage_4"],
            ),
        ]

        previous_task = "stage_5"
        for left, right in BEAT_GROUPS:
            group_id = f"beats_{left}_{right}"
            draft_task_id = f"stage_6a_{group_id}"
            tasks.append(
                AgentTask(
                    task_id=draft_task_id,
                    title=f"第6A步生成第{left}/{right}节拍正文",
                    agent_level=AgentLevel.WORKER,
                    manager="Writing Manager Agent",
                    worker="Two-Beat Draft Worker Agent",
                    prompt_block="stage_6a_draft_two_beats",
                    depends_on=[previous_task],
                )
            )

            previous_round_id = draft_task_id
            for round_index, round_name in enumerate(SIX_B_ITERATION_ROUNDS, start=1):
                round_task_id = f"stage_6b_{group_id}_round_{round_index}"
                tasks.append(
                    AgentTask(
                        task_id=round_task_id,
                        title=f"第6B步第{round_index}轮单要素迭代：{round_name}",
                        agent_level=AgentLevel.WORKER,
                        manager="Revision Manager Agent",
                        worker=f"{round_name} Worker Agent",
                        prompt_block="stage_6b_single_factor_iteration",
                        depends_on=[previous_round_id],
                    )
                )
                previous_round_id = round_task_id
            previous_task = previous_round_id

        tasks.extend(
            [
                self._stage_task(
                    "stage_7",
                    "第7步读者侧人工审阅与商业化润色",
                    "stage_7_reader_review_and_commercial_revision",
                    depends_on=[previous_task],
                ),
                self._stage_task(
                    "stage_8",
                    "第8步证据化出口闸门",
                    "stage_8_evidence_exit_gate",
                    depends_on=["stage_7"],
                ),
                self._stage_task(
                    "stage_9",
                    "第9步章节走向极简脚本回写",
                    "stage_9_chapter_navigation_script",
                    depends_on=["stage_8"],
                ),
            ]
        )

        # Independent acceptance checks can run in parallel after the exit gate.
        tasks.append(
            AgentTask(
                task_id="qa_acceptance_parallel",
                title="并行验收：压测红线、最低放行标准、版本规则",
                agent_level=AgentLevel.MANAGER,
                manager="QA Manager Agent",
                worker="Acceptance Worker Agent",
                prompt_block=None,
                depends_on=["stage_8"],
                can_run_parallel=True,
                execution_mode=ExecutionMode.PARALLEL,
            )
        )

        ledger = OrchestratorLedger(
            project_goal=project_goal,
            current_stage="ceo_intake",
            pending=[task.task_id for task in tasks],
            risks=[
                "第6B必须按六轮单要素顺序迭代，禁止一次混合改六要素。",
                "当前章不得跨章抢跑，只能使用上一章第9步回写作为章间衔接。",
            ],
            forbidden=[
                "不重新设计九步提示词。",
                "不简化母版阶段边界。",
                "不把6B写成一次性综合润色。",
            ],
            next_step="execute ceo_intake",
        )
        if not previous_chapter_script:
            ledger.human_decisions.append("缺少上一章第9步回写时，只允许使用最小临时假设。")

        self._attach_task_inputs(tasks, chapter_input)
        plan = ChapterExecutionPlan(
            ledger=ledger,
            chapter_input=chapter_input,
            tasks=tasks,
            prompt_blocks=list(self.prompt_registry.names()),
            six_b_rounds=list(SIX_B_ITERATION_ROUNDS),
        )
        plan.validate()
        return plan

    def build_plan_from_input(self, project_goal: str, chapter_input: ChapterPipelineInput) -> ChapterExecutionPlan:
        return self.build_plan(
            project_goal=project_goal,
            current_chapter=chapter_input.current_chapter,
            previous_chapter_script=chapter_input.previous_chapter_writeback,
            project_bundle=chapter_input.project_bundle,
            local_kb_reference=chapter_input.local_kb_reference,
            search_summary=chapter_input.search_summary,
            chapter_index=chapter_input.chapter_index,
            model_slot=chapter_input.model_slot,
        )

    def _mock_task_output(self, task: AgentTask) -> Dict[str, object]:
        if task.task_id.startswith("stage_6a_beats_"):
            beat_group = str(task.input_payload.get("beat_group", ""))
            return {
                "summary": f"已生成第{beat_group}节拍正文草稿。",
                "content": f"【第{beat_group}节拍正文草稿】围绕当前章目标推进冲突，保留章尾追读空间。",
            }
        if task.task_id.startswith("stage_6b_beats_"):
            round_name = str(task.input_payload.get("iteration_round", ""))
            return {
                "summary": f"已完成单要素迭代：{round_name}。",
                "content": f"【{round_name}迭代记录】只调整本轮要素，保留前序已定内容。",
            }
        return {
            "summary": f"{task.title} 已按母版提示词完成 mock 产物。",
            "content": f"【{task.task_id}】{task.title}",
        }

    @staticmethod
    def _build_chapter_text(plan: ChapterExecutionPlan) -> str:
        sections = [
            f"# {plan.chapter_input.current_chapter}",
            "",
            "> mock 章节正文：真实模型接入后由第6A/6B产物替换。",
            "",
        ]
        for left, right in BEAT_GROUPS:
            final_task_id = f"stage_6b_beats_{left}_{right}_round_6"
            task = plan.task_map()[final_task_id]
            sections.extend(
                [
                    f"## 节拍 {left}-{right}",
                    str(task.output_payload.get("content", "")),
                    "",
                ]
            )
        sections.append("章尾钩子：更大的代价已经逼近，下一章必须立刻兑现或升级。")
        return "\n".join(sections).strip() + "\n"

    @staticmethod
    def _quality_report(plan: ChapterExecutionPlan, chapter_text: str) -> Dict[str, object]:
        from core_engine.validator import FanqieChapterValidator

        stage_6b_tasks = [task for task in plan.tasks if task.task_id.startswith("stage_6b")]
        failed_stage_6_serial = [
            task.task_id
            for task in stage_6b_tasks
            if task.execution_mode != ExecutionMode.SERIAL or task.can_run_parallel
        ]
        issues = []
        if failed_stage_6_serial:
            issues.append("第6B存在非串行任务。")
        if "下一章" in plan.chapter_input.current_chapter:
            issues.append("当前章标题疑似跨章。")
        fanqie_report = FanqieChapterValidator(min_words=80).validate(
            chapter_text,
            chapter_index=plan.chapter_input.chapter_index,
            chapter_title=plan.chapter_input.current_chapter,
            previous_writeback=plan.chapter_input.previous_chapter_writeback,
        )
        return {
            "chapter_scope_ok": not issues,
            "six_b_serial_ok": not failed_stage_6_serial and len(stage_6b_tasks) == 18,
            "beat_groups": [f"{left}-{right}" for left, right in BEAT_GROUPS],
            "word_count_estimate": len(chapter_text),
            "checks": {
                "current_chapter_only": True,
                "hook_chain_present": "章尾钩子" in chapter_text,
                "stage_7_completed": plan.task_map()["stage_7"].status == TaskStatus.COMPLETED,
                "stage_8_completed": plan.task_map()["stage_8"].status == TaskStatus.COMPLETED,
                "stage_9_completed": plan.task_map()["stage_9"].status == TaskStatus.COMPLETED,
            },
            "issues": issues,
            "fanqie_validator": fanqie_report.__dict__,
        }

    @staticmethod
    def _next_writeback(plan: ChapterExecutionPlan) -> Dict[str, object]:
        return {
            "source_chapter_index": plan.chapter_input.chapter_index,
            "source_chapter": plan.chapter_input.current_chapter,
            "carry_over": [
                "保留主角当前情绪债。",
                "下一章先承接章尾代价，再推进新冲突。",
            ],
            "unresolved_hooks": ["章尾出现的新代价需要在下一章开头回应。"],
            "forbidden": ["不得跳过当前章后果直接进入远期大纲。"],
        }

    def _write_output_files(
        self,
        plan: ChapterExecutionPlan,
        output: ChapterPipelineOutput,
        output_root: str | Path,
    ) -> Dict[str, str]:
        root = Path(output_root)
        project_slug = self._safe_slug(output.project_id, "novel_project")
        chapter_slug = f"chapter_{output.chapter_index:03d}"
        chapter_dir = root / project_slug / chapter_slug
        chapter_dir.mkdir(parents=True, exist_ok=True)

        files = {
            "chapter_text": chapter_dir / "chapter.md",
            "stage_summaries": chapter_dir / "stage_summaries.json",
            "fanqie_quality_report": chapter_dir / "fanqie_quality_report.json",
            "next_chapter_writeback": chapter_dir / "next_chapter_writeback.json",
            "execution_plan": chapter_dir / "execution_plan.json",
        }
        files["chapter_text"].write_text(output.chapter_text, encoding="utf-8")
        files["stage_summaries"].write_text(
            json.dumps(output.stage_summaries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        files["fanqie_quality_report"].write_text(
            json.dumps(output.fanqie_quality_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        files["next_chapter_writeback"].write_text(
            json.dumps(output.next_chapter_writeback, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        files["execution_plan"].write_text(
            json.dumps(plan.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {name: str(path) for name, path in files.items()}

    def run_mock_chapter(
        self,
        project_goal: str,
        chapter_input: ChapterPipelineInput,
        output_root: str | Path = "novel_outputs",
        write_files: bool = True,
    ) -> ChapterPipelineOutput:
        plan = self.build_plan_from_input(project_goal, chapter_input)
        completed: List[str] = []

        for task in plan.tasks:
            missing = [dep for dep in task.depends_on if dep not in completed]
            if missing:
                task.status = TaskStatus.FAILED
                task.failure_reason = f"missing_dependencies:{','.join(missing)}"
                raise RuntimeError(task.failure_reason)
            task.status = TaskStatus.RUNNING
            task.output_payload = self._mock_task_output(task)
            task.status = TaskStatus.COMPLETED
            task.final_decision = "mock_completed"
            completed.append(task.task_id)
            plan.ledger.completed.append(task.task_id)
            if task.task_id in plan.ledger.pending:
                plan.ledger.pending.remove(task.task_id)

        plan.ledger.current_stage = "completed"
        plan.ledger.next_step = "write next chapter from stage_9 writeback"

        chapter_text = self._build_chapter_text(plan)
        stage_summaries = {
            task.task_id: str(task.output_payload.get("summary", ""))
            for task in plan.tasks
        }
        quality_report = self._quality_report(plan, chapter_text)
        next_writeback = self._next_writeback(plan)
        output = ChapterPipelineOutput(
            project_id=self._project_id(chapter_input.project_bundle),
            chapter_index=chapter_input.chapter_index,
            chapter_title=chapter_input.current_chapter,
            chapter_text=chapter_text,
            stage_summaries=stage_summaries,
            fanqie_quality_report=quality_report,
            next_chapter_writeback=next_writeback,
        )
        if write_files:
            output.output_files = self._write_output_files(plan, output, output_root)
        return output

    def run_mock_batch(
        self,
        project_goal: str,
        chapter_titles: Sequence[str],
        project_bundle: Optional[Dict[str, Any]] = None,
        initial_previous_writeback: str = "",
        local_kb_reference: str = "",
        search_summary: str = "",
        output_root: str | Path = "novel_outputs",
        model_slot: str = "",
        start_index: int = 1,
        write_files: bool = True,
    ) -> List[ChapterPipelineOutput]:
        outputs: List[ChapterPipelineOutput] = []
        previous_writeback = initial_previous_writeback
        for offset, chapter_title in enumerate(chapter_titles):
            chapter_input = ChapterPipelineInput(
                project_bundle=project_bundle or {},
                current_chapter=chapter_title,
                previous_chapter_writeback=previous_writeback,
                local_kb_reference=local_kb_reference,
                search_summary=search_summary,
                chapter_index=start_index + offset,
                model_slot=model_slot,
            )
            output = self.run_mock_chapter(
                project_goal=project_goal,
                chapter_input=chapter_input,
                output_root=output_root,
                write_files=write_files,
            )
            outputs.append(output)
            previous_writeback = json.dumps(output.next_chapter_writeback, ensure_ascii=False)
        return outputs
