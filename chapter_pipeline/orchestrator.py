from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List, Optional

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
class AgentTask:
    task_id: str
    title: str
    agent_level: AgentLevel
    manager: str
    worker: Optional[str]
    prompt_block: Optional[str]
    depends_on: List[str] = field(default_factory=list)
    can_run_parallel: bool = False
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["agent_level"] = self.agent_level.value
        payload["status"] = self.status.value
        return payload


@dataclass
class ChapterExecutionPlan:
    ledger: OrchestratorLedger
    tasks: List[AgentTask]
    prompt_blocks: List[str]
    six_b_rounds: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "ledger": self.ledger.to_dict(),
            "tasks": [task.to_dict() for task in self.tasks],
            "prompt_blocks": self.prompt_blocks,
            "six_b_rounds": self.six_b_rounds,
        }


class ChapterOrchestrator:
    """Hierarchical chapter orchestration skeleton.

    This class does not call models yet. It defines the execution ledger and
    task graph that the FastAPI console and future model runner will use.
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

    def build_plan(
        self,
        project_goal: str,
        current_chapter: str,
        previous_chapter_script: str = "",
    ) -> ChapterExecutionPlan:
        self.prompt_registry.validate_required_blocks()

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

        return ChapterExecutionPlan(
            ledger=ledger,
            tasks=tasks,
            prompt_blocks=list(self.prompt_registry.names()),
            six_b_rounds=list(SIX_B_ITERATION_ROUNDS),
        )
