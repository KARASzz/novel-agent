from pathlib import Path

from chapter_pipeline import ChapterOrchestrator, ChapterPipelineInput, OutlineMiddleLayer
from chapter_pipeline.outline_middle_layer import (
    REQUIRED_MIDDLE_LAYER_TEMPLATES,
    SOURCE_UPSTREAM_TEMPLATES,
)


def test_outline_middle_layer_templates_exist_and_reference_sources():
    root = Path(__file__).resolve().parents[1]

    for filename in SOURCE_UPSTREAM_TEMPLATES + REQUIRED_MIDDLE_LAYER_TEMPLATES:
        assert (root / filename).exists(), filename

    orchestration = (root / "templates/webnovel_orchestration_template_v1.md").read_text(encoding="utf-8")
    assert "templates/webnovel_outline_template_v1.md" in orchestration
    assert "templates/webnovel_setting_bible_template_v1.md" in orchestration
    assert "4个卷Agent" in orchestration


def test_outline_middle_layer_builds_400_chapter_structure():
    layer = OutlineMiddleLayer()

    slots = layer.build_chapter_slots()

    assert len(slots) == 400
    assert [slot.chapter_index for slot in slots[:3]] == [1, 2, 3]
    assert slots[-1].chapter_index == 400
    assert {slot.volume_id for slot in slots} == {1, 2, 3, 4}

    for volume_id in range(1, 5):
        volume_slots = [slot for slot in slots if slot.volume_id == volume_id]
        assert len(volume_slots) == 100
        assert {slot.arc_id for slot in volume_slots} == {1, 2, 3, 4}

        for arc_id in range(1, 5):
            arc_slots = [slot for slot in volume_slots if slot.arc_id == arc_id]
            assert len(arc_slots) == 25
            unit_counts = [
                len([slot for slot in arc_slots if slot.unit_id == unit_id])
                for unit_id in range(1, 5)
            ]
            assert unit_counts == [6, 6, 6, 7]


def test_outline_middle_layer_assigns_four_volume_agents_only_to_their_volume():
    layer = OutlineMiddleLayer()

    assignments = layer.build_volume_agent_assignments()

    assert [item.agent_id for item in assignments] == [
        "volume_1_story_agent",
        "volume_2_story_agent",
        "volume_3_story_agent",
        "volume_4_story_agent",
    ]
    assert [item.chapter_range for item in assignments] == ["1-100", "101-200", "201-300", "301-400"]
    assert all(item.output_contract == "VolumeStoryList" for item in assignments)
    assert all("不能改写全书大纲" in item.forbidden for item in assignments)


def test_chapter_construction_card_is_handed_to_stage_1_without_changing_later_flow():
    construction_card = {
        "chapter_index": 37,
        "current_chapter": "第三十七章：黄星回执",
        "structural_position": {
            "volume": 1,
            "arc": 2,
            "unit": 2,
            "function": "承",
        },
        "two_sentence_summary": [
            "金哲洙在旧终端里逼出第一份黄星回执。",
            "回执没有给他权限，只把他的失误变成全楼可见的流程卡点。",
        ],
        "core_event": "黄星回执第一次成为可见制度后果。",
        "visible_consequence": "流程被退回，旁人开始误判金哲洙掌握了隐藏权限。",
        "cliffhanger": "下一章必须处理旁人误判造成的新压力。",
        "must_not_write": ["不得让主角获得授权权", "不得扩写后续卷大纲"],
    }
    setting_payload = {
        "active_rules": ["黄星只卡新增最高战略命令闭合"],
        "active_terms": ["黄星回执"],
        "active_characters": ["金哲洙", "K09"],
        "active_location": "旧终端室",
    }

    plan = ChapterOrchestrator().build_plan(
        project_goal="番茄小说章节生产",
        current_chapter="第三十七章：黄星回执",
        previous_chapter_script="上一章第9步回写",
        chapter_index=37,
        chapter_construction_card=construction_card,
        chapter_setting_payload=setting_payload,
    )

    stage_1 = next(task for task in plan.tasks if task.task_id == "stage_1_2")
    assert stage_1.input_payload["chapter_construction_card"] == construction_card
    assert stage_1.input_payload["chapter_setting_payload"] == setting_payload

    stage_7 = next(task for task in plan.tasks if task.task_id == "stage_7")
    assert stage_7.depends_on == ["stage_6b_beats_5_6_round_6"]
    assert plan.six_b_rounds == [
        "事件推进",
        "身体感受",
        "环境变化",
        "旁人反应",
        "流程卡点",
        "去AI腔与句子口感",
    ]
