import pytest

from pre_hub.adapters.novel_payload_to_bundle import _normalize_token_budget_plan
from pre_hub.ltm import LTMClient, LTMGovernance, LTMShadowStore
from pre_hub.pre_hub import PreHubOrchestrator
from pre_hub.schemas.pre_hub_models import FormatLane, MemoryCandidatePack, MemoryType, ReviewState


def test_prehub_requires_model_slot_or_env_var(tmp_path):
    """测试缺少 model_slot 且没有环境变量时抛出明确错误"""
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir()
    
    with pytest.raises(RuntimeError, match="model_slot 必须指定"):
        PreHubOrchestrator(workspace_root=str(tmp_path)).run(
            "测试题材",
            format_lane=FormatLane.REAL,
            author_id="test_author",
            use_rag=False,
            # 故意不传 model_slot
        )


def test_ltm_client_search_memory_http(monkeypatch):
    """测试 LTM 客户端 HTTP 调用"""
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
    """测试 LTM 治理重复候选拒绝"""
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
    """测试影子存储读取候选"""
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


def test_token_budget_plan_sanitizer_drops_note_and_keeps_numbers():
    plan = _normalize_token_budget_plan(
        {
            "prehub_injection_chars": "5000",
            "rag_context_chars": 3000,
            "draft_chars": "12000",
            "note": "本轮token消耗为无穷大时需重新计算",
        }
    )

    assert plan == {
        "prehub_injection_chars": 5000,
        "rag_context_chars": 3000,
        "draft_chars": 12000,
    }
