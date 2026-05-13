# 3-Pydantic 数据模型草案（可直接转代码）

收到，直接上可用草案（**Pydantic v2**，Python 3.11+）。

```python
# schemas/pre_hub_models.py
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


# =========
# 基础配置
# =========

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )


class VersionedModel(StrictModel):
    schema_version: str = Field(default="1.0.0")
    data_version: str = Field(default="v1")


# =========
# 枚举定义
# =========

class TargetPlatform(str, Enum):
    REDFRUIT = "redfruit"


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
    MAINSTREAM_MEDIA = "mainstream_media"
    THIRD_PARTY_DATA = "third_party_data"
    INDUSTRY_MEDIA = "industry_media"
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


class FormatLane(str, Enum):
    REAL = "real"
    AI = "ai"
    MIXED = "mixed"


class RewriteDecision(str, Enum):
    PASS = "pass"
    REWRITE = "rewrite"
    KILL = "kill"


class OriginalityType(str, Enum):
    ORIGINAL = "original"
    ADAPTED = "adapted"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class RightsStatus(str, Enum):
    CLEAN = "clean"
    PENDING = "pending"
    RISKY = "risky"
    UNKNOWN = "unknown"


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


class AuditAction(str, Enum):
    ADD = "add"
    UPDATE = "update"
    REJECT = "reject"
    ARCHIVE = "archive"


# =========
# 通用子模型
# =========

class SourceConfidenceItem(StrictModel):
    source_name: str
    source_tier: SourceTier
    source_url: HttpUrl | None = None
    published_at: datetime | None = None
    confidence: float = Field(..., ge=0, le=1)
    evidence_refs: list[str] = Field(default_factory=list)


class MetricRule(StrictModel):
    metric_name: str
    raw_definition: str
    normalized_rule: str
    caution: str | None = None


class MetricNormalizationNote(StrictModel):
    rules: list[MetricRule] = Field(default_factory=list)
    notes: str | None = None


class HeatmapItem(StrictModel):
    label: str
    score: int = Field(..., ge=0, le=100)
    trend: TrendDirection = TrendDirection.UNKNOWN
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence_refs: list[str] = Field(default_factory=list)


class FormatFitItem(StrictModel):
    format_lane: FormatLane
    fit_score: int = Field(..., ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence_refs: list[str] = Field(default_factory=list)


class InnovationOpportunityItem(StrictModel):
    title: str
    lane_hint: ContentLane | None = None
    format_hint: FormatLane | None = None
    opportunity_score: int = Field(..., ge=0, le=100)
    window_days: int | None = Field(default=None, ge=1, le=365)
    notes: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class RiskHeatItem(StrictModel):
    category: str
    level: RiskLevel
    score: int = Field(..., ge=0, le=100)
    mitigation_hint: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class PlatformStateSnapshot(StrictModel):
    as_of_date: date
    dau: int | None = Field(default=None, ge=0)
    mau: int | None = Field(default=None, ge=0)
    watch_volume_100m: float | None = Field(default=None, ge=0, description="单位：亿")
    payout_100m_cny: float | None = Field(default=None, ge=0, description="单位：亿元")
    strategic_signals: list[str] = Field(default_factory=list)
    notes: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class RetrievalMeta(StrictModel):
    top_k_raw: int = Field(default=8, ge=1, le=50)
    top_k_final: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.0, ge=0, le=1)
    latency_ms: int | None = Field(default=None, ge=0)
    query: str | None = None
    source_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_k(self) -> "RetrievalMeta":
        if self.top_k_final > self.top_k_raw:
            raise ValueError("top_k_final 不能大于 top_k_raw")
        return self


class PatternItem(StrictModel):
    pattern_id: str | None = None
    title: str
    condition: str
    action: str
    result: str
    scope: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(..., ge=0, le=1)
    evidence_refs: list[str] = Field(default_factory=list)


class AntiPatternItem(PatternItem):
    risk_level: RiskLevel = RiskLevel.MEDIUM


class BiasReportItem(StrictModel):
    bias_name: str
    description: str
    impact_level: RiskLevel = RiskLevel.MEDIUM
    mitigation: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class LTMConflictNotice(StrictModel):
    topic: str
    conflict_summary: str
    memory_ids: list[str] = Field(default_factory=list)
    resolution_hint: str | None = None


class ProductionBurdenEstimate(StrictModel):
    script_complexity: int = Field(..., ge=0, le=100)
    production_complexity: int = Field(..., ge=0, le=100)
    budget_pressure: int = Field(..., ge=0, le=100)
    schedule_pressure: int = Field(..., ge=0, le=100)
    notes: str | None = None


class RouteMatrixScoreItem(StrictModel):
    route_id: str
    content_lane: ContentLane
    format_lane: FormatLane
    market_fit_score: int = Field(..., ge=0, le=100)
    audience_fit_score: int = Field(..., ge=0, le=100)
    novelty_score: int = Field(..., ge=0, le=100)
    producibility_score: int = Field(..., ge=0, le=100)
    compliance_score: int = Field(..., ge=0, le=100)
    ltm_match_score: int = Field(..., ge=0, le=100)
    total_score: int = Field(..., ge=0, le=100)
    notes: str | None = None


class BranchSummary(StrictModel):
    branch_id: str
    title: str
    one_line_pitch: str
    key_conflict: str
    novelty_score: int = Field(..., ge=0, le=100)
    clarity_score: int = Field(..., ge=0, le=100)
    hook_density_score: int = Field(..., ge=0, le=100)
    format_fit_score: int = Field(..., ge=0, le=100)
    risk_score: int = Field(..., ge=0, le=100)
    notes: str | None = None


class KnowledgeStateItem(StrictModel):
    episode_no: int = Field(..., ge=1)
    actor: str
    knows: list[str] = Field(default_factory=list)
    misbeliefs: list[str] = Field(default_factory=list)
    audience_knows_more: bool | None = None


class EmotionalDebtItem(StrictModel):
    episode_no: int = Field(..., ge=1)
    debt_open: int = Field(..., ge=0, le=100)
    debt_close: int = Field(..., ge=0, le=100)
    repay_ratio: float = Field(..., ge=0, le=100)
    new_debt_seeded: bool = False
    notes: str | None = None


class HookNode(StrictModel):
    episode_no: int = Field(..., ge=1)
    hook_type: str
    hook_text: str
    prediction_break_target: str
    intensity: int = Field(..., ge=0, le=100)


class FormatConstraintSheet(StrictModel):
    format_lane: FormatLane
    must_have: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    production_limits: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class RightsComplianceStub(StrictModel):
    originality_type: OriginalityType = OriginalityType.UNKNOWN
    rights_status: RightsStatus = RightsStatus.UNKNOWN
    required_licenses: list[str] = Field(default_factory=list)
    sensitive_flags: list[str] = Field(default_factory=list)
    notes: str | None = None


class RightsRiskItem(StrictModel):
    risk_id: str
    category: str
    level: RiskLevel
    description: str
    mitigation: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class FatalFlawItem(StrictModel):
    flaw_id: str
    category: str
    severity: RiskLevel
    description: str
    fix_hint: str | None = None


class AdversarialReport(StrictModel):
    summary: str
    checks: dict[str, int] = Field(default_factory=dict, description="每项0-100")
    route_mismatch_flag: bool = False
    key_risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @field_validator("checks")
    @classmethod
    def validate_checks(cls, v: dict[str, int]) -> dict[str, int]:
        for k, score in v.items():
            if not 0 <= score <= 100:
                raise ValueError(f"checks[{k}] 必须在 0~100")
        return v


class SignoffInfo(StrictModel):
    auto_gate_version: str
    reviewer: str | None = None
    reviewer_comment: str | None = None
    reviewed_at: datetime | None = None


class PromptInjectionPayload(StrictModel):
    system_rules: list[str] = Field(default_factory=list)
    writing_constraints: list[str] = Field(default_factory=list)
    forbidden_list: list[str] = Field(default_factory=list)
    required_outputs: list[str] = Field(default_factory=list)


class TokenBudgetPlan(StrictModel):
    max_total_tokens: int = Field(..., ge=1)
    per_stage_budget: dict[str, int] = Field(default_factory=dict)
    reserve_ratio: float = Field(default=0.1, ge=0, le=0.5)

    @field_validator("per_stage_budget")
    @classmethod
    def validate_budget(cls, v: dict[str, int]) -> dict[str, int]:
        for k, n in v.items():
            if n < 0:
                raise ValueError(f"per_stage_budget[{k}] 不能为负数")
        return v


class MemoryScope(StrictModel):
    content_lanes: list[ContentLane] = Field(default_factory=list)
    format_lanes: list[FormatLane] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    audience_segments: list[str] = Field(default_factory=list)
    ttl_days: int | None = Field(default=None, ge=1, le=720)


# =========
# 核心包模型（7包+2治理包）
# =========

class ProjectCapsule(VersionedModel):
    project_id: str = Field(..., description="建议前缀 prj_")
    author_id: str
    project_title: str
    one_line_premise: str
    theme_tags: list[str] = Field(..., min_length=1, max_length=8)
    emotion_core: EmotionCore
    visual_core: VisualCore
    target_platform: TargetPlatform = TargetPlatform.REDFRUIT
    target_episode_count: int = Field(..., ge=20, le=120)
    target_duration_sec: int = Field(..., ge=60, le=180)
    preferred_format: PreferredFormat = PreferredFormat.AUTO
    budget_tier: BudgetTier = BudgetTier.UNKNOWN
    hard_constraints: list[str] = Field(default_factory=list)
    soft_goals: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class MarketContextPack(VersionedModel):
    pack_id: str = Field(..., description="建议前缀 pkg_")
    project_id: str
    as_of_date: date
    market_window_days: int = Field(default=90, ge=1, le=365)
    platform_state_snapshot: PlatformStateSnapshot
    lane_heatmap: list[HeatmapItem] = Field(default_factory=list)
    format_fit_map: list[FormatFitItem] = Field(default_factory=list)
    innovation_opportunity_map: list[InnovationOpportunityItem] = Field(default_factory=list)
    risk_heatmap: list[RiskHeatItem] = Field(default_factory=list)
    source_confidence_map: list[SourceConfidenceItem] = Field(default_factory=list)
    metric_normalization_note: MetricNormalizationNote
    generated_at: datetime = Field(default_factory=utc_now)


class AuthorMemoryPack(VersionedModel):
    pack_id: str
    author_id: str
    ltm_snapshot_id: str
    profile_version: str
    strongest_lanes: list[str] = Field(default_factory=list)
    weakest_lanes: list[str] = Field(default_factory=list)
    reusable_pattern_pack: list[PatternItem] = Field(default_factory=list)
    anti_pattern_blacklist: list[AntiPatternItem] = Field(default_factory=list)
    author_bias_report: list[BiasReportItem] = Field(default_factory=list)
    ltm_conflict_notice: list[LTMConflictNotice] = Field(default_factory=list)
    retrieval_meta: RetrievalMeta


class RouteDecisionPack(VersionedModel):
    pack_id: str
    project_id: str
    content_lane: ContentLane
    format_lane: FormatLane
    route_matrix_scorecard: list[RouteMatrixScoreItem] = Field(default_factory=list)
    decision_rationale: str
    route_confidence: float = Field(..., ge=0, le=1)
    forbidden_cliche_list: list[str] = Field(default_factory=list)
    production_burden_estimate: ProductionBurdenEstimate
    platform_fit_reason: str
    created_at: datetime = Field(default_factory=utc_now)


class NarrativeSeedPack(VersionedModel):
    pack_id: str
    project_id: str
    winner_branch: BranchSummary
    runner_up_branch: BranchSummary | None = None
    narrative_graph_v1: dict[str, Any] = Field(default_factory=dict)
    knowledge_state_map: list[KnowledgeStateItem] = Field(default_factory=list)
    emotional_debt_ledger: list[EmotionalDebtItem] = Field(default_factory=list)
    hook_chain_map: list[HookNode] = Field(default_factory=list)
    format_constraint_sheet: FormatConstraintSheet
    rights_compliance_stub: RightsComplianceStub
    writing_brief_v1: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class RiskPack(VersionedModel):
    pack_id: str
    project_id: str
    rights_risk_pack: list[RightsRiskItem] = Field(default_factory=list)
    compliance_flags: list[str] = Field(default_factory=list)
    route_mismatch_flag: bool = False
    fatal_flaw_list: list[FatalFlawItem] = Field(default_factory=list)
    adversarial_report: AdversarialReport
    rewrite_or_kill_decision: RewriteDecision
    must_fix_before_prod: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class PreflightPassport(VersionedModel):
    passport_id: str
    project_id: str
    is_pass: bool = Field(..., alias="pass")
    total_score: int = Field(..., ge=0, le=100)
    gate_scores: dict[str, int] = Field(default_factory=dict, description="每个门 0~100")
    blocking_issues: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    expiry_at: datetime
    issued_at: datetime = Field(default_factory=utc_now)
    signoff: SignoffInfo

    @field_validator("gate_scores")
    @classmethod
    def validate_gate_scores(cls, v: dict[str, int]) -> dict[str, int]:
        for k, score in v.items():
            if not 0 <= score <= 100:
                raise ValueError(f"gate_scores[{k}] 必须在 0~100")
        return v

    @model_validator(mode="after")
    def validate_expiry(self) -> "PreflightPassport":
        if self.expiry_at <= self.issued_at:
            raise ValueError("expiry_at 必须晚于 issued_at")
        return self


class ContextBundleForParser(VersionedModel):
    bundle_id: str
    project_id: str
    project_capsule_ref: str
    market_context_ref: str
    author_memory_ref: str
    route_decision_ref: str
    narrative_seed_ref: str
    risk_pack_ref: str
    passport_ref: str
    prompt_injection_payload: PromptInjectionPayload
    token_budget_plan: TokenBudgetPlan
    integrity_hash: str = Field(..., pattern=r"^[a-fA-F0-9]{64}$")
    created_at: datetime = Field(default_factory=utc_now)


# =========
# LTM 治理包
# =========

class MemoryCandidatePack(VersionedModel):
    candidate_id: str
    author_id: str
    project_id: str
    memory_type: MemoryType
    condition: str
    action: str
    result: str
    scope: MemoryScope
    evidence_refs: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] | None = None
    candidate_confidence: float = Field(..., ge=0, le=1)
    review_state: ReviewState = ReviewState.DRAFT
    created_at: datetime = Field(default_factory=utc_now)


class LTMWriteAudit(VersionedModel):
    event_id: str
    candidate_id: str
    action: AuditAction
    target_memory_id: str | None = None
    reason: str
    similarity_score: float | None = Field(default=None, ge=0, le=1)
    operator: str
    event_time: datetime = Field(default_factory=utc_now)
    before_snapshot_ref: str | None = None
    after_snapshot_ref: str | None = None


# =========
# 可选：总线对象（一次性打包）
# =========

class PreHubArtifacts(VersionedModel):
    project_capsule: ProjectCapsule
    market_context_pack: MarketContextPack
    author_memory_pack: AuthorMemoryPack
    route_decision_pack: RouteDecisionPack
    narrative_seed_pack: NarrativeSeedPack
    risk_pack: RiskPack
    preflight_passport: PreflightPassport
    context_bundle_for_parser: ContextBundleForParser
```

---

如果你要，我下一步直接给你补两件实用的：

1. ​**​`json schema`​**​ **导出脚本**（一键生成给前后端对齐）
2. ​**​`sample payload`​**​ **（每个包一份最小可通过样例）**   
   这样你能马上接 `run_preflight.py`​ 和 `parser.py`。
