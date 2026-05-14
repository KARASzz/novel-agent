import json

from pre_hub.ltm import LTMClient, LTMGovernance, LTMShadowStore
from pre_hub.pre_hub import PreHubOrchestrator
from pre_hub.schemas.pre_hub_models import FormatLane, MemoryCandidatePack, MemoryType, ReviewState, TargetPlatform


def test_prehub_no_rag_does_not_call_tavily(monkeypatch, tmp_path):
    def fail_import(name, *args, **kwargs):
        if name == "rag_engine.tavily_search":
            raise AssertionError("Tavily must not be imported when --no-rag is used")
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr("builtins.__import__", fail_import)

    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir()
    (kb_dir / "local.md").write_text("都市复仇 逆袭 打脸 前三章钩子 章尾追读", encoding="utf-8")

    bundle = PreHubOrchestrator(workspace_root=str(tmp_path)).run(
        "都市复仇",
        format_lane=FormatLane.REAL,
        author_id="author_test",
        use_rag=False,
    )

    assert "rag_disabled_by_cli" in bundle.fallback_reasons
    assert bundle.project_capsule.target_platform == TargetPlatform.FANQIE_NOVEL
    assert bundle.market_context.source_confidence_map
    assert bundle.preflight_passport.total_score > 0


def test_prehub_missing_tavily_env_has_explicit_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir()
    (kb_dir / "method.md").write_text("番茄小说 逆袭 情绪债 反转 追读钩子", encoding="utf-8")

    bundle = PreHubOrchestrator(workspace_root=str(tmp_path)).run(
        "逆袭",
        format_lane=FormatLane.REAL,
        author_id="author_test",
        use_rag=True,
    )

    assert "missing_env:TAVILY_API_KEY" in bundle.fallback_reasons
    assert "missing_env:TAVILY_API_KEY" in bundle.preflight_passport.fallback_reasons
    assert "missing_env:BRAVE_SEARCH_API_KEY" in bundle.fallback_reasons


def test_prehub_default_freezes_cloud_ltm(monkeypatch, tmp_path):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    monkeypatch.setenv("LTM_MEMORY_LIBRARY_ID", "mem-lib")
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir()
    (kb_dir / "method.md").write_text("番茄小说 复仇 追读钩子 爽点密度 本地知识", encoding="utf-8")

    class ExplodingLTM:
        def search_memory(self, *args, **kwargs):
            raise AssertionError("cloud LTM must stay frozen in default preflight")

    bundle = PreHubOrchestrator(workspace_root=str(tmp_path), ltm_client=ExplodingLTM()).run(
        "都市复仇",
        format_lane=FormatLane.REAL,
        author_id="author_test",
        use_rag=False,
    )

    assert bundle.author_memory.ltm_snapshot_id == "cloud_ltm_frozen"
    assert bundle.author_memory.retrieval_meta["source"] == "local_project_knowledge"
    assert "cloud_ltm_frozen" in bundle.author_memory.fallback_reasons


def test_ltm_client_search_memory_http(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    monkeypatch.setenv("LTM_MEMORY_LIBRARY_ID", "mem-lib")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "request_id": "req1",
                "memory_nodes": [{"memory_node_id": "m1", "content": "成功钩子经验"}],
            }

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("pre_hub.ltm.httpx.Client", FakeClient)

    nodes, meta = LTMClient().search_memory("author_1", "都市复仇", top_k=3)

    assert nodes[0]["memory_node_id"] == "m1"
    assert captured["url"].endswith("/memory_nodes/search")
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["json"]["memory_library_id"] == "mem-lib"
    assert meta["request_id"] == "req1"


def test_ltm_governance_duplicate_shadow_rejects(tmp_path):
    governance = LTMGovernance(str(tmp_path), client=LTMClient())
    first = MemoryCandidatePack(
        candidate_id="c1",
        author_id="a1",
        project_id="p1",
        memory_type=MemoryType.PATTERN_SUCCESS,
        condition="都市复仇",
        action="前三章强钩子",
        result="通过",
        candidate_confidence=0.85,
    )
    duplicate = first.model_copy(update={"candidate_id": "c2"})

    audit1 = governance.stage_candidate(first)
    audit2 = governance.stage_candidate(duplicate)

    assert audit1.candidate.review_state == ReviewState.APPROVED
    assert audit2.candidate.review_state == ReviewState.REJECTED
    assert audit2.reason.startswith("duplicate_hash")


def test_shadow_store_reads_candidates(tmp_path):
    governance = LTMGovernance(str(tmp_path), client=LTMClient())
    candidate = MemoryCandidatePack(
        candidate_id="c1",
        author_id="a1",
        project_id="p1",
        memory_type=MemoryType.MARKET_CALIBRATION,
        condition="缺外部源",
        action="本地降级",
        result="可运行",
        candidate_confidence=0.65,
    )
    governance.stage_candidate(candidate)

    loaded = LTMShadowStore(str(tmp_path)).candidates(project_id="p1")

    assert len(loaded) == 1
    assert loaded[0].candidate_id == "c1"


def test_context_bundle_serializes_for_parser(tmp_path):
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir()
    (kb_dir / "method.md").write_text("番茄小说 逆袭 情绪债 反转 追读钩子", encoding="utf-8")
    bundle = PreHubOrchestrator(workspace_root=str(tmp_path)).run(
        "逆袭",
        format_lane=FormatLane.REAL,
        author_id="author_test",
        use_rag=False,
    )

    payload = json.loads(bundle.model_dump_json())

    assert payload["integrity_hash"]
    system_addition = payload["prompt_injection_payload"]["system_addition"]
    assert system_addition.startswith("[Novel Preflight ContextBundle]")
    assert "TargetPlatform: fanqie_novel" in system_addition
    assert "TargetChapters:" in system_addition
    assert "CH1" in system_addition
    assert "TargetEpisodes" not in system_addition
