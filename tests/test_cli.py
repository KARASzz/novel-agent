import scripts.cli as cli
import pytest


def test_cli_package_dispatches_to_packager(monkeypatch):
    calls = {}

    def fake_package(project_name, genre, author_name):
        calls["project_name"] = project_name
        calls["genre"] = genre
        calls["author_name"] = author_name
        return "dummy.zip"

    monkeypatch.setattr(cli, "_package_command", fake_package)

    exit_code = cli.main([
        "package",
        "--name",
        "复仇之夜",
        "--genre",
        "都市逆袭",
        "--author",
        "测试工作室",
    ])

    assert exit_code == 0
    assert calls == {
        "project_name": "复仇之夜",
        "genre": "都市逆袭",
        "author_name": "测试工作室",
    }


def test_cli_clear_cache_with_yes_skips_prompt(monkeypatch, capsys):
    calls = {}

    def fake_clear_cache(filter_keyword):
        calls["filter_keyword"] = filter_keyword
        return 3

    monkeypatch.setattr(cli, "_clear_cache_command", fake_clear_cache)

    exit_code = cli.main([
        "clear-cache",
        "--filter",
        "都市",
        "--yes",
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls == {"filter_keyword": "都市"}
    assert "成功清理 3 条缓存快照" in output


def test_cli_verify_rag_returns_command_exit_code(monkeypatch):
    monkeypatch.setattr(cli, "_verify_rag_command", lambda: 1)

    assert cli.main(["verify-rag"]) == 1


def test_cli_validator_self_test_dispatch(monkeypatch):
    calls = {}

    def fake_self_test(target):
        calls["target"] = target

    monkeypatch.setattr(cli, "_self_test_command", fake_self_test)

    exit_code = cli.main([
        "self-test",
        "validator",
    ])

    assert exit_code == 0
    assert calls == {"target": "validator"}


def test_cli_no_longer_exposes_legacy_run_command():
    with pytest.raises(SystemExit) as exc:
        cli.main(["run"])

    assert exc.value.code == 2


def test_cli_ltm_review_dispatch(monkeypatch):
    calls = {}

    def fake_review(project_id, apply_approved):
        calls["project_id"] = project_id
        calls["apply_approved"] = apply_approved
        return 0

    monkeypatch.setattr(cli, "_ltm_review_command", fake_review)

    exit_code = cli.main(["ltm-review", "--project-id", "p1", "--apply-approved"])

    assert exit_code == 0
    assert calls == {"project_id": "p1", "apply_approved": True}


def test_cli_production_run_dispatches_to_runner(monkeypatch, capsys):
    from types import SimpleNamespace

    calls = {}
    FakeResult = SimpleNamespace(
        ok=True,
        run_id="run_test",
        project_id="sample_zerg_queen",
        dry_run=True,
        chapter_indexes=[1, 2, 3],
        stop_reason="opening_review",
        completed_chapters=[],
        failed_chapter=None,
        error="",
        run_root="/tmp/run_test",
        next_action="dry_run_only",
    )

    class FakeRunner:
        def __init__(self, workspace_root):
            calls["workspace_root"] = workspace_root

        def run(self, **kwargs):
            calls.update(kwargs)
            return FakeResult

    monkeypatch.setattr(cli, "ProductionRunner", FakeRunner, raising=False)

    exit_code = cli.main([
        "production-run",
        "--project",
        "sample_zerg_queen",
        "--chapters",
        "3",
        "--model-slot",
        "model_slot_1",
        "--dry-run",
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls["project_id"] == "sample_zerg_queen"
    assert calls["chapters"] == 3
    assert calls["model_slot"] == "model_slot_1"
    assert calls["dry_run"] is True
    assert "run_test" in output


def test_cli_production_run_returns_failure_exit(monkeypatch):
    from types import SimpleNamespace

    FakeResult = SimpleNamespace(
        ok=False,
        run_id="run_failed",
        project_id="sample_zerg_queen",
        dry_run=False,
        chapter_indexes=[1],
        stop_reason="opening_review",
        completed_chapters=[],
        failed_chapter=1,
        error="missing_env:MINIMAX_API_KEY",
        run_root="/tmp/run_failed",
        next_action="repair_failed_chapter",
    )

    class FakeRunner:
        def __init__(self, workspace_root):
            pass

        def run(self, **kwargs):
            return FakeResult

    monkeypatch.setattr(cli, "ProductionRunner", FakeRunner, raising=False)

    assert cli.main(["production-run", "--project", "sample_zerg_queen"]) == 1
