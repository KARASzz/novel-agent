from types import SimpleNamespace

import web_ui


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
