import pytest
from core_engine.renderer import FormatRenderer


def test_renderer_basic():
    renderer = FormatRenderer()
    test_data = {
        "episode_number": 1,
        "title": "Test Episode",
        "is_paywall": False,
        "scenes": [
            {
                "scene_id": "1-1",
                "time": "日",
                "location_type": "内",
                "location": "办公室",
                "characters": ["主角"],
                "plots": [
                    {"type": "action", "content": "主角在打字"},
                    {"type": "dialogue", "character": "主角", "content": "你好"},
                ],
            }
        ],
    }
    output = renderer.render_episode(test_data)
    assert "1-1 日 内 办公室" in output
    assert "■主角在打字" in output
    assert "主角：你好" in output
    assert "【单集统计】" in output


def test_renderer_os_dialogue():
    renderer = FormatRenderer()
    test_data = {
        "scenes": [
            {"plots": [{"type": "os", "character": "路人", "content": "内心独白"}]}
        ]
    }
    output = renderer.render_episode(test_data)
    assert "路人OS：内心独白" in output
