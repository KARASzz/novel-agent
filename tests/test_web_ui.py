import web_ui
from web_file_catalog import GeneratedFileCatalog


def test_model_options_exposes_slots(monkeypatch):
    monkeypatch.setattr(
        web_ui,
        "load_config",
        lambda: {
            "models": {
                "default_slot": "model_slot_2",
                "slots": {
                    "model_slot_1": {
                        "display_name": "占位1",
                        "model_id": "m1",
                        "base_url": "https://m1.test/v1",
                        "api_key_env": "M1_KEY",
                        "enabled": True,
                    },
                    "model_slot_2": {
                        "display_name": "占位2",
                        "model_id": "m2",
                        "base_url": "",
                        "api_key_env": "M2_KEY",
                        "enabled": False,
                    },
                },
            }
        },
    )

    payload = web_ui._model_options()

    assert payload["default_slot"] == "model_slot_2"
    assert payload["models"][0]["slot"] == "model_slot_1"
    assert payload["models"][0]["api_key_env"] == "M1_KEY"
    assert payload["models"][1]["enabled"] is False


def test_web_ui_no_longer_exposes_legacy_pipeline_command(monkeypatch):
    class FakeRequest:
        async def json(self):
            return {"model_slot": "model_slot_4"}

    def fake_run(cmd, capture_output, text, cwd, encoding, errors):
        raise AssertionError("legacy pipeline command must not run")

    monkeypatch.setattr(web_ui.subprocess, "run", fake_run)
    response = web_ui.run_command

    import asyncio

    payload = asyncio.run(response("pipeline", FakeRequest()))

    assert payload["output"] == "未知命令"
    assert "pipeline" not in {
        command["id"]
        for section in web_ui.DASHBOARD_SECTIONS
        for command in section["commands"]
    }


def test_dashboard_exposes_initialization_self_check_button():
    command_ids = {
        command["id"]
        for section in web_ui.DASHBOARD_SECTIONS
        for command in section["commands"]
    }

    assert "init_self_check" in command_ids


def test_initialization_self_check_payload_passes_core_checks(monkeypatch, tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    for name in web_ui.REQUIRED_WEBNOVEL_TEMPLATES:
        (templates / name).write_text("# template", encoding="utf-8")

    monkeypatch.setattr(web_ui, "BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MODEL_SLOT_1_API_KEY", "sk-test")
    monkeypatch.setattr(
        web_ui,
        "load_config",
        lambda: {
            "models": {
                "default_slot": "model_slot_1",
                "slots": {
                    "model_slot_1": {
                        "display_name": "测试模型",
                        "base_url": "https://example.test/v1",
                        "api_key_env": "MODEL_SLOT_1_API_KEY",
                        "model_id": "model-test",
                        "enabled": True,
                    }
                },
            }
        },
    )
    monkeypatch.setattr(
        web_ui,
        "_load_or_build_plan_snapshot",
        lambda: {
            "source_label": "测试计划",
            "plan": {
                "tasks": [{"task_id": "ceo_intake", "status": "pending"}],
                "ledger": {},
            },
        },
    )

    payload = web_ui._initialization_self_check_payload()

    assert payload["status"] == "pass"
    assert any(item["name"] == "大纲中台模板" and item["status"] == "pass" for item in payload["checks"])
    assert any(item["name"] == "旧草稿清洗链路" and item["status"] == "pass" for item in payload["checks"])


def test_generated_file_catalog_lists_default_app_open_url(tmp_path):
    chapter_dir = tmp_path / "novel_outputs" / "p1" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    target = chapter_dir / "chapter.md"
    target.write_text("# 第一章\n正文", encoding="utf-8")

    catalog = GeneratedFileCatalog(tmp_path)
    payload = catalog.list_files()
    group = next(item for item in payload["groups"] if item["key"] == "novel_outputs")
    file_item = group["files"][0]

    assert file_item["name"] == "chapter.md"
    assert file_item["open_url"].startswith("/api/open-file/")


def test_generated_file_catalog_opens_with_macos_default_app(monkeypatch, tmp_path):
    chapter_dir = tmp_path / "novel_outputs" / "p1" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    target = chapter_dir / "chapter.md"
    target.write_text("# 第一章\n正文", encoding="utf-8")

    catalog = GeneratedFileCatalog(tmp_path)
    file_item = next(
        group["files"][0]
        for group in catalog.list_files()["groups"]
        if group["key"] == "novel_outputs"
    )
    calls = []
    monkeypatch.setattr("web_file_catalog.platform.system", lambda: "Darwin")
    monkeypatch.setattr("web_file_catalog.subprocess.Popen", lambda cmd: calls.append(cmd))

    result = catalog.open_with_default_app(file_item["id"])

    assert result["status"] == "opened"
    assert result["path"] == str(target.resolve())
    assert calls == [["open", str(target.resolve())]]


def test_open_generated_file_response_uses_default_app(monkeypatch, tmp_path):
    chapter_dir = tmp_path / "novel_outputs" / "p1" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "chapter.md").write_text("正文", encoding="utf-8")
    catalog = GeneratedFileCatalog(tmp_path)
    file_id = next(
        group["files"][0]["id"]
        for group in catalog.list_files()["groups"]
        if group["key"] == "novel_outputs"
    )
    monkeypatch.setattr(web_ui, "file_catalog", catalog)
    monkeypatch.setattr(
        catalog,
        "open_with_default_app",
        lambda received_id: {
            "status": "opened",
            "path": str(chapter_dir / "chapter.md"),
            "name": "chapter.md",
            "received_id": received_id,
        },
    )

    import asyncio

    response = asyncio.run(web_ui.open_generated_file(file_id))

    assert response["status"] == "opened"
    assert response["name"] == "chapter.md"
    assert response["received_id"] == file_id


def test_browser_preview_route_is_not_registered():
    assert "/files/open/{file_id}" not in {route.path for route in web_ui.app.routes}


def test_jinja_templates_are_auto_reload_enabled():
    assert getattr(web_ui.templates.env, "auto_reload", False) is True
