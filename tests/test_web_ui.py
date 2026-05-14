from types import SimpleNamespace

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


def test_run_command_passes_model_slot_to_pipeline(monkeypatch):
    captured = {}

    class FakeRequest:
        async def json(self):
            return {"model_slot": "model_slot_4"}

    def fake_run(cmd, capture_output, text, cwd, encoding, errors):
        captured["cmd"] = cmd
        return SimpleNamespace(stdout="ok", stderr="", returncode=0)

    monkeypatch.setattr(web_ui.subprocess, "run", fake_run)
    response = web_ui.run_command

    import asyncio

    payload = asyncio.run(response("pipeline", FakeRequest()))

    assert payload["output"] == "ok"
    assert captured["cmd"][-2:] == ["--model-slot", "model_slot_4"]


def test_generated_file_catalog_lists_and_opens_inline(tmp_path):
    chapter_dir = tmp_path / "novel_outputs" / "p1" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    target = chapter_dir / "chapter.md"
    target.write_text("# 第一章\n正文", encoding="utf-8")

    catalog = GeneratedFileCatalog(tmp_path)
    payload = catalog.list_files()
    group = next(item for item in payload["groups"] if item["key"] == "novel_outputs")
    file_item = group["files"][0]

    assert file_item["name"] == "chapter.md"
    assert file_item["open_url"].startswith("/files/open/")
    html = catalog.preview_html(file_item["id"])
    assert "# 第一章" in html
    assert "触发浏览器下载" not in html


def test_open_generated_file_response_is_inline(monkeypatch, tmp_path):
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

    import asyncio

    response = asyncio.run(web_ui.open_generated_file(file_id))

    assert response.status_code == 200
    assert "content-disposition" not in response.headers
    assert "正文".encode("utf-8") in response.body


def test_jinja_templates_are_auto_reload_enabled():
    assert getattr(web_ui.templates.env, "auto_reload", False) is True
