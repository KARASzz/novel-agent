from chapter_pipeline.orchestrator import (
    BEAT_GROUPS,
    SIX_B_ITERATION_ROUNDS,
    AgentLevel,
    ChapterOrchestrator,
)
from chapter_pipeline.prompt_registry import ChapterPromptRegistry, PROMPT_BLOCK_TAGS


def test_prompt_registry_extracts_master_prompt_blocks():
    registry = ChapterPromptRegistry()

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
