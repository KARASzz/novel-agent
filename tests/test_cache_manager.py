import json

from core_engine.cache_manager import CacheManager


def test_cache_manager_ttl_expire(tmp_path, monkeypatch):
    manager = CacheManager(str(tmp_path))
    content = "demo"
    data = {"title": "ttl-case", "chapter_index": 1}

    current = 1000.0

    def fake_time():
        return current

    monkeypatch.setattr("core_engine.cache_manager.time.time", fake_time)
    manager.set_cache(content, data, salt="s1", ttl_seconds=10)

    # 未过期可读取
    assert manager.get_cache(content, salt="s1") == data

    # 过期后返回空并自动清理
    current = 1011.0
    assert manager.get_cache(content, salt="s1") is None


def test_cache_manager_backward_compatible_payload(tmp_path):
    manager = CacheManager(str(tmp_path))
    content = "legacy"
    salt = "legacy-salt"
    cache_id = manager._get_hash(content, salt)
    cache_file = tmp_path / f"{cache_id}.json"

    legacy_payload = {"title": "old-format", "chapter_index": 2}
    cache_file.write_text(json.dumps(legacy_payload, ensure_ascii=False), encoding="utf-8")

    assert manager.get_cache(content, salt=salt) == legacy_payload


def test_cache_manager_persist_new_payload_format(tmp_path):
    manager = CacheManager(str(tmp_path))
    content = "persist"
    salt = "persist-salt"
    data = {"title": "new-format", "chapter_index": 3}

    manager.set_cache(content, data, salt=salt, ttl_seconds=3600)

    cache_id = manager._get_hash(content, salt)
    cache_file = tmp_path / f"{cache_id}.json"
    payload = json.loads(cache_file.read_text(encoding="utf-8"))

    assert "meta" in payload
    assert "data" in payload
    assert payload["data"] == data
