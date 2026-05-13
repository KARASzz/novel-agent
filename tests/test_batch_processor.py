from core_engine.batch_processor import BatchProcessor, ERROR_SYSTEM, FileProcessResult
from core_engine.parser import ParseResult


def test_batch_processor_injects_shared_rate_limiter(tmp_path):
    processor = BatchProcessor(
        drafts_dir=str(tmp_path / "drafts"),
        output_dir=str(tmp_path / "out"),
        reports_dir=str(tmp_path / "reports"),
        config={
            "pipeline": {
                "rate_limit": {"requests_per_second": 1},
                "file_timeout_sec": 300,
            },
            "parser": {"enable_rag": False},
        },
    )

    assert processor.rate_limiter is not None
    assert processor.parser.rate_limiter is processor.rate_limiter


def test_batch_processor_retries_system_failure_once(tmp_path, monkeypatch):
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir()
    draft_file = drafts_dir / "a.txt"
    draft_file.write_text("demo", encoding="utf-8")

    processor = BatchProcessor(
        drafts_dir=str(drafts_dir),
        output_dir=str(tmp_path / "out"),
        reports_dir=str(tmp_path / "reports"),
        config={"pipeline": {"file_timeout_sec": 300}, "parser": {"enable_rag": False}},
    )

    calls = {"count": 0}

    def fake_process(file_path: str) -> FileProcessResult:
        calls["count"] += 1
        if calls["count"] == 1:
            return FileProcessResult(
                filename="a.txt",
                input_path=file_path,
                output_path=None,
                processed_success=False,
                validation_status="not_run",
                quality_passed=False,
                stage_status={
                    "read": "success",
                    "parse": "failed",
                    "validate": "skipped",
                    "render": "skipped",
                    "write": "skipped",
                },
                error_type=ERROR_SYSTEM,
                error_message="boom",
            )

        return FileProcessResult(
            filename="a.txt",
            input_path=file_path,
            output_path=str(tmp_path / "out" / "a_成品剧本.txt"),
            processed_success=True,
            validation_status="passed",
            quality_passed=True,
            stage_status={
                "read": "success",
                "parse": "success",
                "validate": "success",
                "render": "success",
                "write": "success",
            },
            error_type=None,
            error_message=None,
        )

    monkeypatch.setattr(processor, "_process_single_file", fake_process)
    results = processor.run_batch(max_workers=1)

    assert calls["count"] == 2
    assert len(results) == 1
    assert results[0].processed_success is True


def test_batch_processor_passes_timeout_budget_to_parser(tmp_path, monkeypatch):
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir()
    draft_file = drafts_dir / "a.txt"
    draft_file.write_text("demo", encoding="utf-8")

    processor = BatchProcessor(
        drafts_dir=str(drafts_dir),
        output_dir=str(tmp_path / "out"),
        reports_dir=str(tmp_path / "reports"),
        config={"pipeline": {"file_timeout_sec": 1}, "parser": {"enable_rag": False}},
    )

    def fake_parse(*args, **kwargs):
        assert kwargs.get("total_timeout_sec") == 1
        return ParseResult(
            episode=None,
            is_success=False,
            error_type="timeout",
            error_message="parser_total_timeout",
            attempts=1,
            retries=0,
            request_count=1,
            duration_sec=1.0,
        )

    monkeypatch.setattr(processor.parser, "parse_draft", fake_parse)
    result = processor._process_single_file(str(draft_file))

    assert result.processed_success is False
    assert result.error_type == "timeout"
    assert result.error_message == "parser_total_timeout"