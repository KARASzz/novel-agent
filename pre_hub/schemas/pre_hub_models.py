from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        use_enum_values=False,
    )


class VersionedModel(StrictModel):
    schema_version: str = "4.0.0"
    data_version: str = "v1"


class TargetPlatform(str, Enum):
    REDFRUIT = "redfruit"
    FANQIE_NOVEL = "fanqie_novel"


class EmotionCore(str, Enum):
    REVENGE = "复仇"
    COMPENSATION = "代偿"
    FAMILY_REPAIR = "亲情修复"
    IDENTITY_ASCENT = "身份跃迁"
    TRUTH_SEEKING = "求真"
    GROWTH = "成长"


class VisualCore(str, Enum):
    REAL_RELATION = "现实关系"
    SPECTACLE_SETTING = "奇观设定"
    MIXED = "混合"


class FormatLane(str, Enum):
    REAL = "real"
    AI = "ai"
    MIXED = "mixed"

    @property
    def label(self) -> str:
        return {
            FormatLane.REAL: "正文连载型",
            FormatLane.AI: "设定辅助型",
            FormatLane.MIXED: "混合增强型",
        }[self]


class PreferredFormat(str, Enum):
    REAL = "real"
    AI = "ai"
    MIXED = "mixed"
    AUTO = "auto"


class BudgetTier(str, Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    UNKNOWN = "unknown"


class SourceTier(str, Enum):
    OFFICIAL = "official"
    MAINSTREAM = "mainstream"
    THIRD_PARTY = "third_party"
    INDUSTRY = "industry_media"
    SELF_MEDIA = "self_media"
    OTHER = "other"


class TrendDirection(str, Enum):
    UP = "up"
    FLAT = "flat"
    DOWN = "down"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContentLane(str, Enum):
    STABLE_HIT = "保底爆款"
    RISING_MIX = "上升混搭"
    INNOVATION_PREMIUM = "创新精品"


class RewriteDecision(str, Enum):
    PASS = "pass"
    REWRITE = "rewrite"
    KILL = "kill"


class AudienceZone(str, Enum):
    IMMUNE = "免疫区"
    FATIGUED = "疲惫区"
    HIGH_SENSITIVE = "高敏区"
    INTEGRATABLE = "可整合惊讶带"
    OVERLOAD = "过载区"


class ViewingMode(str, Enum):
    REAL_EMOTION = "强情绪快读型"
    REAL_RELATION = "关系拉扯型"
    AI_SPEC = "高概念设定型"
    SERIES_ADDICT = "追更成瘾型"
    SINGLE_BURST = "单章爆点型"


class MemoryType(str, Enum):
    PATTERN_SUCCESS = "pattern_success"
    PATTERN_FAILURE = "pattern_failure"
    STYLE_PREFERENCE = "style_preference"
    RISK_ALERT = "risk_alert"
    MARKET_CALIBRATION = "market_calibration"


class ReviewState(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    SHADOW_ONLY = "shadow_only"
    APPLIED = "applied"


class AuditAction(str, Enum):
    ADD = "add"
    UPDATE = "update"
    REJECT = "reject"
    ARCHIVE = "archive"
    SHADOW = "shadow"


class SourceConfidenceItem(StrictModel):
    source_name: str
    source_tier: SourceTier = SourceTier.OTHER
    source_url: Optional[str] = None
    published_at: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    is_fact: bool = True
    evidence_refs: List[str] = Field(default_factory=list)


class HeatmapItem(StrictModel):
    label: str
    score: int = Field(default=0, ge=0, le=100)
    trend: TrendDirection = TrendDirection.UNKNOWN
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_refs: List[str] = Field(default_factory=list)


class FormatFitItem(StrictModel):
    format_lane: FormatLane
    fit_score: int = Field(default=0, ge=0, le=100)
    reasons: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_refs: List[str] = Field(default_factory=list)


class BayesiaFreeEnergyScore(StrictModel):
    surprise_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confusion_score: float = Field(default=0.0, ge=0.0, le=1.0)
    integration_score: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)


class AudiencePriorMatrix(StrictModel):
    zone_distribution: Dict[str, float] = Field(default_factory=dict)
    viewing_mode_scores: Dict[str, float] = Field(default_factory=dict)
    integration_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class RouteDecision(StrictModel):
    content_lane: ContentLane
    format_lane: FormatLane
    decision_rationale: str
    route_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    forbidden_cliche: List[str] = Field(default_factory=list)
    production_burden: str = "medium"


class BranchScore(StrictModel):
    branch_id: str
    branch_description: str
    platform_fit: int = Field(default=0, ge=0, le=100)
    hook_density: int = Field(default=0, ge=0, le=100)
    ip_potential: int = Field(default=0, ge=0, le=100)
    producibility: int = Field(default=0, ge=0, le=100)
    rights_risk: int = Field(default=0, ge=0, le=100)
    ltm_match: int = Field(default=0, ge=0, le=100)
    total_score: int = Field(default=0, ge=0, le=100)
    verdict: str = "unknown"
    evidence_refs: List[str] = Field(default_factory=list)


class NarrativeGraphNode(StrictModel):
    node_id: str
    node_type: str
    content: str
    episode_range: str = ""
    dependencies: List[str] = Field(default_factory=list)


class HookNode(StrictModel):
    episode_no: int = Field(ge=1)
    hook_type: str
    hook_text: str
    intensity: int = Field(default=0, ge=0, le=100)
    emotional_debt_raised: int = Field(default=0, ge=0, le=100)
    emotional_debt_repaid: int = Field(default=0, ge=0, le=100)


class RiskItem(StrictModel):
    category: str
    level: RiskLevel
    description: str
    mitigation: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)


class ProjectCapsule(VersionedModel):
    project_id: str
    author_id: str = "default"
    project_title: str
    one_line_premise: str
    theme_tags: List[str] = Field(default_factory=list)
    emotion_core: EmotionCore = EmotionCore.COMPENSATION
    visual_core: VisualCore = VisualCore.REAL_RELATION
    target_platform: TargetPlatform = TargetPlatform.FANQIE_NOVEL
    target_episode_count: int = Field(default=60, ge=20, le=120)
    target_duration_sec: int = Field(default=90, ge=60, le=180)
    target_chapter_count: int = Field(default=120, ge=20, le=3000)
    target_chapter_words: int = Field(default=2200, ge=800, le=6000)
    preferred_format: FormatLane = FormatLane.REAL
    budget_tier: BudgetTier = BudgetTier.UNKNOWN
    hard_constraints: List[str] = Field(default_factory=list)
    soft_goals: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class MarketContextPack(VersionedModel):
    pack_id: str
    project_id: str
    as_of_date: str
    market_window_days: int = Field(default=90, ge=1, le=365)
    platform_state_snapshot: Dict[str, Any] = Field(default_factory=dict)
    lane_heatmap: List[HeatmapItem] = Field(default_factory=list)
    format_fit_map: List[FormatFitItem] = Field(default_factory=list)
    innovation_opportunity_map: List[HeatmapItem] = Field(default_factory=list)
    risk_heatmap: List[HeatmapItem] = Field(default_factory=list)
    source_confidence_map: List[SourceConfidenceItem] = Field(default_factory=list)
    metric_normalization_note: Dict[str, str] = Field(default_factory=dict)
    fallback_reasons: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class AuthorMemoryPack(VersionedModel):
    pack_id: str
    author_id: str
    ltm_snapshot_id: str
    profile_version: str = "unknown"
    strongest_lanes: List[str] = Field(default_factory=list)
    weakest_lanes: List[str] = Field(default_factory=list)
    reusable_pattern_pack: List[Dict[str, Any]] = Field(default_factory=list)
    anti_pattern_blacklist: List[Dict[str, Any]] = Field(default_factory=list)
    author_bias_report: List[Dict[str, Any]] = Field(default_factory=list)
    ltm_conflict_notice: List[Dict[str, Any]] = Field(default_factory=list)
    retrieval_meta: Dict[str, Any] = Field(default_factory=dict)
    fallback_reasons: List[str] = Field(default_factory=list)


class RouteDecisionPack(VersionedModel):
    pack_id: str
    project_id: str
    content_lane: ContentLane
    format_lane: FormatLane
    route_matrix_scorecard: List[Dict[str, Any]] = Field(default_factory=list)
    decision_rationale: str
    route_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    forbidden_cliche_list: List[str] = Field(default_factory=list)
    production_burden_estimate: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class NarrativeSeedPack(VersionedModel):
    pack_id: str
    project_id: str
    winner_branch: Optional[BranchScore] = None
    runner_up_branch: Optional[BranchScore] = None
    narrative_graph_v1: List[NarrativeGraphNode] = Field(default_factory=list)
    knowledge_state_map: List[Dict[str, Any]] = Field(default_factory=list)
    emotional_debt_ledger: List[Dict[str, Any]] = Field(default_factory=list)
    hook_chain_map: List[HookNode] = Field(default_factory=list)
    format_constraint_sheet: Dict[str, Any] = Field(default_factory=dict)
    rights_compliance_stub: Dict[str, Any] = Field(default_factory=dict)
    writing_brief_v1: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class RiskPack(VersionedModel):
    pack_id: str
    project_id: str
    rights_risk_pack: List[RiskItem] = Field(default_factory=list)
    compliance_flags: List[str] = Field(default_factory=list)
    route_mismatch_flag: bool = False
    fatal_flaw_list: List[RiskItem] = Field(default_factory=list)
    adversarial_report: Dict[str, Any] = Field(default_factory=dict)
    rewrite_or_kill_decision: RewriteDecision = RewriteDecision.PASS
    must_fix_before_prod: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class PreflightPassport(VersionedModel):
    passport_id: str
    project_id: str
    is_pass: bool = Field(default=False, alias="pass")
    total_score: int = Field(default=0, ge=0, le=100)
    gate_scores: Dict[str, int] = Field(default_factory=dict)
    blocking_issues: List[str] = Field(default_factory=list)
    required_actions: List[str] = Field(default_factory=list)
    fallback_reasons: List[str] = Field(default_factory=list)
    signoff: Dict[str, Any] = Field(default_factory=dict)
    issued_at: datetime = Field(default_factory=utc_now)
    expiry_at: datetime


class MemoryCandidatePack(VersionedModel):
    candidate_id: str
    author_id: str
    project_id: str
    memory_type: MemoryType
    condition: str
    action: str
    result: str
    scope: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    candidate_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    review_state: ReviewState = ReviewState.SHADOW_ONLY
    normalized_hash: str = ""
    created_at: datetime = Field(default_factory=utc_now)

    def normalized_text(self) -> str:
        payload = {
            "memory_type": self.memory_type.value,
            "condition": self.condition.strip().lower(),
            "action": self.action.strip().lower(),
            "result": self.result.strip().lower(),
            "scope": self.scope,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def ensure_hash(self) -> "MemoryCandidatePack":
        if not self.normalized_hash:
            self.normalized_hash = hashlib.sha256(self.normalized_text().encode("utf-8")).hexdigest()
        return self

    def to_custom_content(self) -> str:
        return (
            f"[{self.memory_type.value}] Condition: {self.condition}\n"
            f"Action: {self.action}\n"
            f"Result: {self.result}\n"
            f"Scope: {json.dumps(self.scope, ensure_ascii=False, sort_keys=True)}\n"
            f"Confidence: {self.candidate_confidence:.2f}"
        )


class LTMWriteAudit(VersionedModel):
    event_id: str
    candidate_id: str
    action: AuditAction
    author_id: str
    project_id: str
    target_memory_id: Optional[str] = None
    reason: str
    similarity_score: Optional[float] = None
    operator: str = "pre_hub"
    event_time: datetime = Field(default_factory=utc_now)
    before_snapshot_ref: Optional[str] = None
    after_snapshot_ref: Optional[str] = None
    candidate: Optional[MemoryCandidatePack] = None
    cloud_request_id: Optional[str] = None
    error: Optional[str] = None


class ContextBundleForParser(VersionedModel):
    bundle_id: str
    project_id: str
    project_capsule: ProjectCapsule
    market_context: MarketContextPack
    author_memory: AuthorMemoryPack
    route_decision: RouteDecisionPack
    narrative_seed: NarrativeSeedPack
    risk_pack: RiskPack
    preflight_passport: PreflightPassport
    prompt_injection_payload: Dict[str, str] = Field(default_factory=dict)
    token_budget_plan: Dict[str, int] = Field(default_factory=dict)
    integrity_hash: str = ""
    fallback_reasons: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @property
    def market_context_ref(self) -> str:
        return self.market_context.pack_id

    @property
    def author_memory_ref(self) -> str:
        return self.author_memory.pack_id

    @property
    def narrative_seed_ref(self) -> str:
        return self.narrative_seed.pack_id

    @property
    def passport_ref(self) -> str:
        return self.preflight_passport.passport_id

    def compute_integrity_hash(self) -> str:
        payload = self.model_dump(mode="json", exclude={"integrity_hash"})
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def seal(self) -> "ContextBundleForParser":
        self.integrity_hash = self.compute_integrity_hash()
        self.prompt_injection_payload = {"system_addition": self.to_injection_prompt()}
        return self

    def to_injection_prompt(self) -> str:
        capsule = self.project_capsule
        route = self.route_decision
        narrative = self.narrative_seed
        risk = self.risk_pack
        memory = self.author_memory
        market = self.market_context

        lines = [
            "[Novel Preflight ContextBundle]",
            f"ProjectID: {capsule.project_id}",
            f"Title: {capsule.project_title}",
            f"Premise: {capsule.one_line_premise}",
            f"EmotionCore: {capsule.emotion_core.value}",
            f"VisualCore: {capsule.visual_core.value}",
            f"TargetPlatform: {capsule.target_platform.value}",
            f"TargetChapters: {capsule.target_chapter_count}",
            f"TargetChapterWords: {capsule.target_chapter_words}",
            f"ChapterForm: {route.format_lane.label}",
            f"ContentLane: {route.content_lane.value}",
            f"RouteConfidence: {route.route_confidence:.2f}",
            f"MarketAsOf: {market.as_of_date}",
        ]
        if market.lane_heatmap:
            top_lanes = ", ".join(f"{item.label}:{item.score}" for item in market.lane_heatmap[:5])
            lines.append(f"LaneHeatmap: {top_lanes}")
        if narrative.winner_branch:
            lines.append(f"WinnerBranch: {narrative.winner_branch.branch_description}")
        if narrative.hook_chain_map:
            hooks = "; ".join(
                f"CH{node.episode_no} {node.hook_type} {node.hook_text}"
                for node in narrative.hook_chain_map[:6]
            )
            lines.append(f"HookChain: {hooks}")
        if route.forbidden_cliche_list:
            lines.append(f"ForbiddenCliches: {', '.join(route.forbidden_cliche_list)}")
        if memory.reusable_pattern_pack:
            patterns = "; ".join(str(item.get("content") or item.get("title") or item)[:120] for item in memory.reusable_pattern_pack[:3])
            lines.append(f"ProjectKnowledgePatterns: {patterns}")
        if memory.anti_pattern_blacklist:
            anti = "; ".join(str(item.get("content") or item.get("title") or item)[:120] for item in memory.anti_pattern_blacklist[:3])
            lines.append(f"ProjectKnowledgeAntiPatterns: {anti}")
        if risk.must_fix_before_prod:
            lines.append(f"MustFixBeforeProduction: {', '.join(risk.must_fix_before_prod)}")
        if risk.compliance_flags:
            lines.append(f"ComplianceFlags: {', '.join(risk.compliance_flags)}")
        if self.fallback_reasons:
            lines.append(f"FallbackReasons: {', '.join(self.fallback_reasons)}")
        lines.append("[End Novel Preflight ContextBundle]")
        return "\n".join(lines)


NovelProjectBundle = ContextBundleForParser
ChapterProductionBundle = ContextBundleForParser


# Backward-compatible layer shells used by existing helper modules.
class Layer0Output(StrictModel):
    cleaned_sources: List[Dict[str, Any]] = Field(default_factory=list)
    source_confidence_map: List[SourceConfidenceItem] = Field(default_factory=list)
    metric_normalization_note: Dict[str, str] = Field(default_factory=dict)
    content_form_tags: List[str] = Field(default_factory=list)
    rights_risk_signals: List[str] = Field(default_factory=list)


class Layer1Output(StrictModel):
    platform_state_snapshot: Dict[str, Any] = Field(default_factory=dict)
    lane_heatmap: List[HeatmapItem] = Field(default_factory=list)
    format_fit_map: List[FormatFitItem] = Field(default_factory=list)
    innovation_opportunity_map: List[HeatmapItem] = Field(default_factory=list)
    risk_heatmap: List[HeatmapItem] = Field(default_factory=list)
    bayesian_scores: Optional[BayesiaFreeEnergyScore] = None


class Layer2Output(StrictModel):
    audience_prior_matrix: AudiencePriorMatrix
    prediction_error_band: Dict[str, Any] = Field(default_factory=dict)
    viewing_mode_scores: Dict[str, float] = Field(default_factory=dict)
    audience_segment_fit: Dict[str, float] = Field(default_factory=dict)
    fanqie_fit_hypothesis: str = ""


class Layer3Output(StrictModel):
    route_decision: RouteDecision
    route_matrix_scorecard: List[BranchScore] = Field(default_factory=list)


class Layer4Output(StrictModel):
    concept_branches: List[Dict[str, Any]] = Field(default_factory=list)
    branch_scorecard: List[BranchScore] = Field(default_factory=list)
    winner_branch: Optional[BranchScore] = None
    runner_up_branch: Optional[BranchScore] = None
    kill_list: List[Dict[str, str]] = Field(default_factory=list)


class Layer5Output(StrictModel):
    narrative_graph: List[NarrativeGraphNode] = Field(default_factory=list)
    knowledge_state_map: List[Dict[str, Any]] = Field(default_factory=list)
    emotional_debt_ledger: List[Dict[str, Any]] = Field(default_factory=list)
    hook_chain_map: List[HookNode] = Field(default_factory=list)
    format_constraint_sheet: Dict[str, Any] = Field(default_factory=dict)
    rights_compliance_stub: Dict[str, Any] = Field(default_factory=dict)


class Layer6Output(StrictModel):
    adversarial_report: Dict[str, Any] = Field(default_factory=dict)
    fatal_flaw_list: List[RiskItem] = Field(default_factory=list)
    route_mismatch_flag: bool = False
    rights_risk_pack: List[RiskItem] = Field(default_factory=list)
    rewrite_or_kill: RewriteDecision = RewriteDecision.PASS
    must_fix_before_prod: List[str] = Field(default_factory=list)


class Layer7Output(StrictModel):
    preflight_passport: PreflightPassport
    context_bundle: ContextBundleForParser
