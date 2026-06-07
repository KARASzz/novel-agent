import json

from core_engine.production_runner import ProductionRunner


def test_default_project_plan_starts_with_chapters_1_to_3(tmp_path):
    runner = ProductionRunner(workspace_root=tmp_path)

    plan = runner.plan_run(project_id="sample_zerg_queen", dry_run=True)

    assert plan.project_id == "sample_zerg_queen"
    assert plan.chapter_indexes == [1, 2, 3]
    assert plan.chapter_titles == [
        "第一章：败局重启，女皇归巢",
        "第二章：第一枚血脉样本",
        "第三章：忍村边境的寄生眼",
    ]
    assert plan.stop_reason == "opening_review"
    assert plan.model_slot == "model_slot_1"

    project_path = (
        tmp_path
        / "novel_outputs"
        / "production_runs"
        / "sample_zerg_queen"
        / "project.json"
    )
    progress_path = (
        tmp_path
        / "novel_outputs"
        / "production_runs"
        / "sample_zerg_queen"
        / "progress.json"
    )
    assert project_path.exists()
    assert progress_path.exists()
    assert json.loads(progress_path.read_text(encoding="utf-8"))["next_chapter_index"] == 1


def test_stop_points_follow_opening_then_structural_units(tmp_path):
    runner = ProductionRunner(workspace_root=tmp_path)
    runner.ensure_project("sample_zerg_queen")

    progress = runner.load_progress("sample_zerg_queen")
    progress.last_completed_chapter_index = 3
    progress.next_chapter_index = 4
    runner.save_progress("sample_zerg_queen", progress)
    plan = runner.plan_run(project_id="sample_zerg_queen", dry_run=True)
    assert plan.chapter_indexes == [4, 5, 6]
    assert plan.stop_reason == "first_unit_completion"

    progress.last_completed_chapter_index = 6
    progress.next_chapter_index = 7
    runner.save_progress("sample_zerg_queen", progress)
    plan = runner.plan_run(project_id="sample_zerg_queen", dry_run=True)
    assert plan.chapter_indexes == [7, 8, 9, 10, 11, 12]
    assert plan.stop_reason == "unit_review_6"

    progress.last_completed_chapter_index = 18
    progress.next_chapter_index = 19
    runner.save_progress("sample_zerg_queen", progress)
    plan = runner.plan_run(project_id="sample_zerg_queen", dry_run=True)
    assert plan.chapter_indexes == [19, 20, 21, 22, 23, 24, 25]
    assert plan.stop_reason == "unit_review_7"
