from chapter_pipeline.orchestrator import (
    BEAT_GROUPS,
    SIX_B_ITERATION_ROUNDS,
    AgentLevel,
    ChapterOrchestrator,
    ChapterPipelineInput,
    ExecutionMode,
    TaskStatus,
)
from chapter_pipeline.prompt_registry import ChapterPromptRegistry, PROMPT_BLOCK_TAGS


def test_prompt_registry_uses_builtin_prompt_blocks_without_master_file():
    registry = ChapterPromptRegistry(master_path="/definitely/not-used.md")

    for name in PROMPT_BLOCK_TAGS:
        content = registry.get(name)
        assert content.startswith(f"<{name}")
        assert content.endswith(f"</{name}>")

    assert "继续第1步" in registry.section("stage_commands")
    assert "每章最低放行标准" in registry.section("minimum_acceptance")


def test_chapter_orchestrator_builds_6a_6b_fixed_rounds():
    plan = ChapterOrchestrator().build_plan(
        project_goal="番茄小说章节生产",
        current_chapter="第一章：误入旧站台",
        previous_chapter_script="上一章状态",
    )

    task_ids = [task.task_id for task in plan.tasks]
    assert "ceo_intake" in task_ids
    assert plan.six_b_rounds == list(SIX_B_ITERATION_ROUNDS)

    for left, right in BEAT_GROUPS:
        group_id = f"beats_{left}_{right}"
        draft_task = f"stage_6a_{group_id}"
        assert draft_task in task_ids
        previous_id = draft_task
        for index, round_name in enumerate(SIX_B_ITERATION_ROUNDS, start=1):
            task_id = f"stage_6b_{group_id}_round_{index}"
            task = next(task for task in plan.tasks if task.task_id == task_id)
            assert task.title.endswith(round_name)
            assert task.depends_on == [previous_id]
            assert task.prompt_block == "stage_6b_single_factor_iteration"
            previous_id = task_id

    stage_7 = next(task for task in plan.tasks if task.task_id == "stage_7")
    assert stage_7.depends_on == ["stage_6b_beats_5_6_round_6"]


def test_stage_6_tasks_are_never_parallel():
    plan = ChapterOrchestrator().build_plan(
        project_goal="番茄小说章节生产",
        current_chapter="第一章",
        previous_chapter_script="上一章状态",
    )

    stage_6_tasks = [task for task in plan.tasks if task.task_id.startswith("stage_6")]
    assert len([task for task in stage_6_tasks if task.task_id.startswith("stage_6b")]) == 18
    assert all(task.execution_mode == ExecutionMode.SERIAL for task in stage_6_tasks)
    assert all(task.can_run_parallel is False for task in stage_6_tasks)

    qa_task = next(task for task in plan.tasks if task.task_id == "qa_acceptance_parallel")
    assert qa_task.execution_mode == ExecutionMode.PARALLEL
    assert qa_task.can_run_parallel is True
    assert qa_task.prompt_block == "qa_acceptance_parallel"


def test_plan_validation_rejects_parallel_stage_6():
    plan = ChapterOrchestrator().build_plan(
        project_goal="番茄小说章节生产",
        current_chapter="第一章",
        previous_chapter_script="上一章状态",
    )
    task = next(task for task in plan.tasks if task.task_id == "stage_6b_beats_1_2_round_1")
    task.execution_mode = ExecutionMode.PARALLEL

    import pytest

    with pytest.raises(ValueError, match="Stage 6 must be strictly serial"):
        plan.validate()


def test_chapter_orchestrator_uses_hierarchical_roles_and_ledger():
    plan = ChapterOrchestrator().build_plan(
        project_goal="番茄小说章节生产",
        current_chapter="第一章",
    )

    levels = {task.agent_level for task in plan.tasks}
    assert AgentLevel.CEO in levels
    assert AgentLevel.MANAGER in levels
    assert AgentLevel.WORKER in levels
    assert plan.ledger.current_stage == "ceo_intake"
    assert "不把6B写成一次性综合润色。" in plan.ledger.forbidden
    assert plan.ledger.human_decisions


def test_chapter_plan_carries_required_inputs():
    plan = ChapterOrchestrator().build_plan(
        project_goal="番茄小说章节生产",
        current_chapter="第一章：误入旧站台",
        previous_chapter_script="上一章第9步回写",
        project_bundle={"project_id": "p1", "title": "红星锚定"},
        local_kb_reference="本地知识库：番茄追读钩子",
        search_summary="联网摘要：同类题材近期趋势",
        chapter_index=1,
        model_slot="model_slot_2",
    )

    assert plan.chapter_input.project_bundle["project_id"] == "p1"
    ceo_task = next(task for task in plan.tasks if task.task_id == "ceo_intake")
    assert ceo_task.input_payload["previous_chapter_writeback"] == "上一章第9步回写"
    assert ceo_task.input_payload["local_kb_reference"] == "本地知识库：番茄追读钩子"
    assert ceo_task.input_payload["search_summary"] == "联网摘要：同类题材近期趋势"
    assert ceo_task.input_payload["model_slot"] == "model_slot_2"


def test_plan_rejects_cross_chapter_scope():
    import pytest

    with pytest.raises(ValueError, match="exactly one chapter"):
        ChapterOrchestrator().build_plan(
            project_goal="番茄小说章节生产",
            current_chapter="第一章至第三章：连续生成",
        )


def test_propagate_current_text_pulls_content_from_predecessor():
    """stage_6b_* 必须把前序任务的 output_payload.content 串接到 current_text。"""
    orchestrator = ChapterOrchestrator()
    plan = orchestrator.build_plan(
        project_goal="番茄小说章节生产",
        current_chapter="第一章：误入旧站台",
        previous_chapter_script="上一章状态",
    )

    predecessor = next(t for t in plan.tasks if t.task_id == "stage_6a_beats_1_2")
    predecessor.status = TaskStatus.COMPLETED
    predecessor.output_payload = {
        "content": "上一轮真实正文：雨打在站台上，铁皮顶棚发出脆响。",
        "summary": "初稿",
    }

    target = next(t for t in plan.tasks if t.task_id == "stage_6b_beats_1_2_round_1")
    assert "current_text" not in target.input_payload  # 起点干净

    ChapterOrchestrator._propagate_current_text(target, plan)

    assert target.input_payload["current_text"] == "上一轮真实正文：雨打在站台上，铁皮顶棚发出脆响。"
    # 其它字段不能被覆盖丢失
    assert target.input_payload["iteration_round"] == target.title.split("：", 1)[-1]
    assert target.input_payload["single_factor_only"] is True


def test_propagate_current_text_falls_back_to_full_payload_when_content_missing():
    """前置 output_payload 没有 content 键时，回退到整段 JSON 字符串。"""
    plan = ChapterOrchestrator().build_plan(
        project_goal="番茄",
        current_chapter="第一章",
        previous_chapter_script="",
    )

    # stage_6b_round_2 实际依赖 stage_6b_round_1（链式串行），不是 stage_6a
    predecessor = next(t for t in plan.tasks if t.task_id == "stage_6b_beats_3_4_round_1")
    predecessor.status = TaskStatus.COMPLETED
    predecessor.output_payload = {"summary": "只有摘要", "metadata": {"round": 1}}

    target = next(t for t in plan.tasks if t.task_id == "stage_6b_beats_3_4_round_2")

    ChapterOrchestrator._propagate_current_text(target, plan)

    # 兜底：把整段 payload 序列化进 current_text，保证 LLM 至少有结构化上下文
    assert "summary" in target.input_payload["current_text"]
    assert "metadata" in target.input_payload["current_text"]


def test_propagate_current_text_skips_non_stage_6b_tasks():
    """非 stage_6b 任务必须保持原 input_payload 不变。"""
    plan = ChapterOrchestrator().build_plan(
        project_goal="番茄",
        current_chapter="第一章",
        previous_chapter_script="",
    )

    # stage_5 不是 6B，必须不被注入 current_text
    stage_5 = next(t for t in plan.tasks if t.task_id == "stage_5")
    before = dict(stage_5.input_payload)

    ChapterOrchestrator._propagate_current_text(stage_5, plan)

    assert stage_5.input_payload == before
    assert "current_text" not in stage_5.input_payload
