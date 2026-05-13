from __future__ import annotations

import json
import os
import time
import uuid
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx

from pre_hub.schemas.pre_hub_models import (
    AuditAction,
    LTMWriteAudit,
    MemoryCandidatePack,
    ReviewState,
)


class LTMClient:
    """Alibaba Model Studio long-term memory adapter.

    The API key and optional memory identifiers are read only from environment
    variables. Missing credentials disable cloud calls without blocking local
    Pre-Hub execution.
    """

    BASE_URL = "https://dashscope.aliyuncs.com/api/v2/apps/memory"

    def __init__(
        self,
        api_key_env: str = "DASHSCOPE_API_KEY",
        library_id_env: str = "LTM_MEMORY_LIBRARY_ID",
        profile_schema_env: str = "LTM_PROFILE_SCHEMA_ID",
        timeout: float = 30.0,
    ) -> None:
        self.api_key_env = api_key_env
        self.library_id_env = library_id_env
        self.profile_schema_env = profile_schema_env
        self.api_key = os.getenv(api_key_env)
        self.memory_library_id = os.getenv(library_id_env)
        self.profile_schema_id = os.getenv(profile_schema_env)
        self.timeout = timeout

    @property
    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise RuntimeError(f"Missing environment variable: {self.api_key_env}")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _library_payload(self) -> Dict[str, str]:
        if self.memory_library_id:
            return {"memory_library_id": self.memory_library_id}
        return {}

    def search_memory(
        self,
        author_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if not self.is_enabled:
            return [], {
                "fallback_reason": f"missing_env:{self.api_key_env}",
                "source": "local_shadow",
            }

        payload: Dict[str, Any] = {
            "user_id": author_id,
            "messages": [{"role": "user", "content": query}],
            "top_k": top_k,
            "min_score": min_score,
        }
        payload.update(self._library_payload())
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.BASE_URL}/memory_nodes/search",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            meta = {
                "source": "cloud_ltm",
                "request_id": data.get("request_id"),
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "top_k_raw": top_k,
                "top_k_final": min(top_k, len(data.get("memory_nodes", []))),
                "min_score": min_score,
                "query": query,
            }
            return data.get("memory_nodes", []), meta
        except Exception as exc:
            return [], {
                "fallback_reason": f"ltm_search_failed:{type(exc).__name__}",
                "error": str(exc),
                "source": "local_shadow",
            }

    def add_memory(self, author_id: str, candidate: MemoryCandidatePack) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "user_id": author_id,
            "custom_content": candidate.to_custom_content(),
            "timestamp": int(time.time()),
            "meta_data": {
                "project_id": candidate.project_id,
                "candidate_id": candidate.candidate_id,
                "memory_type": candidate.memory_type.value,
                "confidence": candidate.candidate_confidence,
            },
        }
        payload.update(self._library_payload())
        if self.profile_schema_id:
            payload["profile_schema"] = self.profile_schema_id
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.BASE_URL}/add",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def update_memory(
        self,
        author_id: str,
        memory_node_id: str,
        candidate: MemoryCandidatePack,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "user_id": author_id,
            "custom_content": candidate.to_custom_content(),
            "timestamp": int(time.time()),
            "meta_data": {
                "project_id": candidate.project_id,
                "candidate_id": candidate.candidate_id,
                "memory_type": candidate.memory_type.value,
                "confidence": candidate.candidate_confidence,
            },
        }
        payload.update(self._library_payload())
        with httpx.Client(timeout=self.timeout) as client:
            response = client.patch(
                f"{self.BASE_URL}/memory_nodes/{memory_node_id}",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()


class LTMShadowStore:
    """Append-only local audit mirror for LTM decisions."""

    def __init__(self, workspace_root: str) -> None:
        self.workspace_root = workspace_root
        self.audit_dir = os.path.join(workspace_root, "reports", "ltm_audit")
        self.audit_path = os.path.join(self.audit_dir, "ltm_audit.jsonl")

    def append_audit(self, audit: LTMWriteAudit) -> None:
        os.makedirs(self.audit_dir, exist_ok=True)
        with open(self.audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(audit.model_dump(mode="json"), ensure_ascii=False) + "\n")

    def iter_audits(self) -> Iterable[LTMWriteAudit]:
        if not os.path.exists(self.audit_path):
            return []
        items: List[LTMWriteAudit] = []
        with open(self.audit_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(LTMWriteAudit.model_validate_json(line))
                except Exception:
                    continue
        return items

    def candidates(self, project_id: Optional[str] = None) -> List[MemoryCandidatePack]:
        seen: Dict[str, MemoryCandidatePack] = {}
        for audit in self.iter_audits():
            if project_id and audit.project_id != project_id:
                continue
            if audit.candidate:
                seen[audit.candidate.candidate_id] = audit.candidate
        return list(seen.values())

    def find_same_hash(self, candidate: MemoryCandidatePack) -> Optional[MemoryCandidatePack]:
        candidate.ensure_hash()
        for existing in self.candidates():
            existing.ensure_hash()
            if existing.normalized_hash == candidate.normalized_hash:
                return existing
        return None


def candidate_similarity(left: MemoryCandidatePack, right: MemoryCandidatePack) -> float:
    return SequenceMatcher(None, left.normalized_text(), right.normalized_text()).ratio()


class LTMGovernance:
    def __init__(
        self,
        workspace_root: str,
        client: Optional[LTMClient] = None,
        confidence_threshold: float = 0.80,
        semantic_update_threshold: float = 0.92,
    ) -> None:
        self.shadow = LTMShadowStore(workspace_root)
        self.client = client or LTMClient()
        self.confidence_threshold = confidence_threshold
        self.semantic_update_threshold = semantic_update_threshold

    def audit_candidate(
        self,
        candidate: MemoryCandidatePack,
        action: AuditAction = AuditAction.SHADOW,
        reason: str = "shadow_first",
        target_memory_id: Optional[str] = None,
        similarity_score: Optional[float] = None,
        error: Optional[str] = None,
        cloud_request_id: Optional[str] = None,
    ) -> LTMWriteAudit:
        candidate.ensure_hash()
        audit = LTMWriteAudit(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            candidate_id=candidate.candidate_id,
            action=action,
            author_id=candidate.author_id,
            project_id=candidate.project_id,
            target_memory_id=target_memory_id,
            reason=reason,
            similarity_score=similarity_score,
            candidate=candidate,
            error=error,
            cloud_request_id=cloud_request_id,
        )
        self.shadow.append_audit(audit)
        return audit

    def stage_candidate(self, candidate: MemoryCandidatePack) -> LTMWriteAudit:
        candidate.ensure_hash()
        duplicate = self.shadow.find_same_hash(candidate)
        if duplicate:
            candidate.review_state = ReviewState.REJECTED
            return self.audit_candidate(
                candidate,
                action=AuditAction.REJECT,
                reason=f"duplicate_hash:{duplicate.candidate_id}",
                similarity_score=1.0,
            )
        if candidate.candidate_confidence >= self.confidence_threshold:
            candidate.review_state = ReviewState.APPROVED
            return self.audit_candidate(candidate, reason="auto_approved_shadow_first")
        candidate.review_state = ReviewState.SHADOW_ONLY
        return self.audit_candidate(candidate, reason="below_cloud_threshold_shadow_only")

    def apply_approved(self, project_id: Optional[str] = None) -> List[LTMWriteAudit]:
        applied: List[LTMWriteAudit] = []
        if not self.client.is_enabled:
            for candidate in self.shadow.candidates(project_id=project_id):
                if candidate.review_state == ReviewState.APPROVED:
                    applied.append(
                        self.audit_candidate(
                            candidate,
                            action=AuditAction.REJECT,
                            reason=f"cloud_disabled_missing_env:{self.client.api_key_env}",
                        )
                    )
            return applied

        for candidate in self.shadow.candidates(project_id=project_id):
            if candidate.review_state != ReviewState.APPROVED:
                continue
            query = candidate.to_custom_content()
            nodes, _ = self.client.search_memory(candidate.author_id, query, top_k=5, min_score=0.0)
            best_node: Optional[Dict[str, Any]] = None
            best_score = 0.0
            for node in nodes:
                content = str(node.get("content", ""))
                score = SequenceMatcher(None, query, content).ratio()
                if score > best_score:
                    best_score = score
                    best_node = node
            try:
                if best_node and best_score >= self.semantic_update_threshold:
                    memory_id = best_node.get("memory_node_id")
                    result = self.client.update_memory(candidate.author_id, memory_id, candidate)
                    candidate.review_state = ReviewState.APPLIED
                    applied.append(
                        self.audit_candidate(
                            candidate,
                            action=AuditAction.UPDATE,
                            reason="semantic_duplicate_update",
                            target_memory_id=memory_id,
                            similarity_score=best_score,
                            cloud_request_id=result.get("request_id"),
                        )
                    )
                else:
                    result = self.client.add_memory(candidate.author_id, candidate)
                    nodes_created = result.get("memory_nodes") or []
                    memory_id = nodes_created[0].get("memory_node_id") if nodes_created else None
                    candidate.review_state = ReviewState.APPLIED
                    applied.append(
                        self.audit_candidate(
                            candidate,
                            action=AuditAction.ADD,
                            reason="new_memory",
                            target_memory_id=memory_id,
                            similarity_score=best_score,
                            cloud_request_id=result.get("request_id"),
                        )
                    )
            except Exception as exc:
                applied.append(
                    self.audit_candidate(
                        candidate,
                        action=AuditAction.REJECT,
                        reason="cloud_apply_failed",
                        similarity_score=best_score,
                        error=str(exc),
                    )
                )
        return applied
