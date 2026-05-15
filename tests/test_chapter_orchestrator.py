from chapter_pipeline.orchestrator import (
    BEAT_GROUPS,
    SIX_B_ITERATION_ROUNDS,
    AgentLevel,
    ChapterOrchestrator,
    ChapterPipelineInput,
    ExecutionMode,
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
