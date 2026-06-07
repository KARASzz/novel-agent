import json

from core_engine.production_runner import DEFAULT_PROJECT_ID, ProductionRunner


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


def test_non_ascii_project_ids_get_distinct_deterministic_roots(tmp_path):
    runner = ProductionRunner(workspace_root=tmp_path)

    first_root = runner.project_root("测试项目")
    second_root = runner.project_root("另一个项目")

    assert first_root == runner.project_root("测试项目")
    assert first_root != second_root
    assert first_root.name.startswith(DEFAULT_PROJECT_ID)
    assert second_root.name.startswith(DEFAULT_PROJECT_ID)


def test_completed_book_returns_empty_plan_with_completion_reason(tmp_path):
    runner = ProductionRunner(workspace_root=tmp_path)
    runner.ensure_project("sample_zerg_queen")

    progress = runner.load_progress("sample_zerg_queen")
    progress.last_completed_chapter_index = 400
    progress.next_chapter_index = 401
    runner.save_progress("sample_zerg_queen", progress)

    plan = runner.plan_run(project_id="sample_zerg_queen", dry_run=True)

    assert plan.chapter_indexes == []
    assert plan.chapter_titles == []
    assert plan.stop_reason == "book_completed"


def test_save_progress_syncs_position_fields_from_next_chapter(tmp_path):
    runner = ProductionRunner(workspace_root=tmp_path)
    runner.ensure_project("sample_zerg_queen")

    progress = runner.load_progress("sample_zerg_queen")
    progress.next_chapter_index = 26
    progress.current_volume = 99
    progress.current_arc = 99
    progress.current_unit = 99

    runner.save_progress("sample_zerg_queen", progress)

    reloaded = runner.load_progress("sample_zerg_queen")
    assert reloaded.current_volume == 1
    assert reloaded.current_arc == 2
    assert reloaded.current_unit == 1


def test_dry_run_persists_run_config_and_summary_without_chapters(tmp_path):
    runner = ProductionRunner(workspace_root=tmp_path)

    result = runner.run(project_id="sample_zerg_queen", dry_run=True)

    run_root = (
        tmp_path
        / "novel_outputs"
        / "production_runs"
        / "sample_zerg_queen"
        / "runs"
        / result.run_id
    )
    assert result.ok is True
    assert result.dry_run is True
    assert (run_root / "run_config.json").exists()
    assert (run_root / "run_summary.json").exists()
    assert not (run_root / "chapters").exists()

    summary = json.loads((run_root / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["chapter_indexes"] == [1, 2, 3]
    assert summary["stop_reason"] == "opening_review"
    assert summary["next_action"] == "dry_run_only"


from types import SimpleNamespace


class FakeOrchestrator:
    def __init__(self):
        self.calls = []
        self.llm_client = None

    def run_chapter(self, project_goal, chapter_input, model_id, output_root, write_files=True, verbose=True):
        self.calls.append(
            {
                "project_goal": project_goal,
                "chapter": chapter_input.current_chapter,
                "index": chapter_input.chapter_index,
                "previous": chapter_input.previous_chapter_writeback,
                "model_id": model_id,
                "output_root": str(output_root),
            }
        )
        return SimpleNamespace(
            project_id=chapter_input.project_bundle["project_id"],
            chapter_index=chapter_input.chapter_index,
            chapter_title=chapter_input.current_chapter,
            chapter_text=f"# {chapter_input.current_chapter}\n正文",
            stage_summaries={"stage_9": "已回写"},
            fanqie_quality_report={"is_valid": True, "score": 90},
            next_chapter_writeback={
                "source_chapter_index": chapter_input.chapter_index,
                "writeback_script": f"第{chapter_input.chapter_index}章回写",
            },
            output_files={},
        )


_FAKE_CONFIG = {
    "models": {
        "default_slot": "model_slot_1",
        "slots": {
            "model_slot_1": {
                "display_name": "MiniMax-M3",
                "base_url": "https://api.minimaxi.com/v1",
                "api_key_env": "MINIMAX_API_KEY",
                "model_id": "MiniMax-M3",
                "enabled": True,
            }
        },
    },
    "llm": {},
}


def test_real_run_chains_only_step_9_writeback(monkeypatch, tmp_path):
    fake = FakeOrchestrator()

    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test")
    monkeypatch.setattr("core_engine.production_runner.ChapterOrchestrator", lambda: fake)
    monkeypatch.setattr("core_engine.production_runner.LLMClient", lambda api_key, base_url: object())
    monkeypatch.setattr("core_engine.production_runner.load_config", lambda: _FAKE_CONFIG)

    runner = ProductionRunner(workspace_root=tmp_path)
    result = runner.run(project_id="sample_zerg_queen", chapters=2)

    assert result.ok is True
    assert result.completed_chapters == [1, 2]
    assert fake.calls[0]["previous"] == "新书开局，败局重启，无上一章回写。"
    assert json.loads(fake.calls[1]["previous"]) == {
        "source_chapter_index": 1,
        "writeback_script": "第1章回写",
    }

    progress = runner.load_progress("sample_zerg_queen")
    assert progress.last_completed_chapter_index == 2
    assert progress.next_chapter_index == 3
    assert json.loads(progress.previous_chapter_writeback)["source_chapter_index"] == 2


def test_real_run_stops_on_orchestrator_failure(monkeypatch, tmp_path):
    class FailingOrchestrator(FakeOrchestrator):
        def run_chapter(self, *args, **kwargs):
            if len(self.calls) == 1:
                raise RuntimeError("stage_8_not_approved")
            return super().run_chapter(*args, **kwargs)

    fake = FailingOrchestrator()
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test")
    monkeypatch.setattr("core_engine.production_runner.ChapterOrchestrator", lambda: fake)
    monkeypatch.setattr("core_engine.production_runner.LLMClient", lambda api_key, base_url: object())
    monkeypatch.setattr("core_engine.production_runner.load_config", lambda: _FAKE_CONFIG)

    runner = ProductionRunner(workspace_root=tmp_path)
    result = runner.run(project_id="sample_zerg_queen", chapters=3)

    assert result.ok is False
    assert result.completed_chapters == [1]
    assert result.failed_chapter == 2
    assert "stage_8_not_approved" in result.error
    assert runner.load_progress("sample_zerg_queen").next_chapter_index == 2


def test_review_packet_is_written_after_successful_run(monkeypatch, tmp_path):
    fake = FakeOrchestrator()
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test")
    monkeypatch.setattr("core_engine.production_runner.ChapterOrchestrator", lambda: fake)
    monkeypatch.setattr("core_engine.production_runner.LLMClient", lambda api_key, base_url: object())
    monkeypatch.setattr("core_engine.production_runner.load_config", lambda: _FAKE_CONFIG)

    runner = ProductionRunner(workspace_root=tmp_path)
    result = runner.run(project_id="sample_zerg_queen", chapters=1)

    run_root = (
        tmp_path
        / "novel_outputs"
        / "production_runs"
        / "sample_zerg_queen"
        / "runs"
        / result.run_id
    )
    review = run_root / "review_packet" / "batch_review.md"
    continuity = run_root / "review_packet" / "continuity_report.json"
    assert review.exists()
    assert "第 1 章" in review.read_text(encoding="utf-8")
    assert json.loads(continuity.read_text(encoding="utf-8"))["completed_chapters"] == [1]
