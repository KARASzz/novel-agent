# pre_hub/adapters/novel_payload_to_bundle.py
"""
将 NovelPreflightOrchestrator 返回的原始 dict 负载转换为旧版的 ChapterProductionBundle (Pydantic 模型)。
这是为了保证现有流水线（scripts/preflight.py 等）在不修改大量代码的情况下依然可用。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from pre_hub.schemas.pre_hub_models import (
    AuthorMemoryPack,
    BranchScore,
    ChapterProductionBundle,
    ContentLane,
    EmotionCore,
    FormatLane,
    HeatmapItem,
    HookNode,
    MarketContextPack,
    NarrativeSeedPack,
    PreflightPassport,
    ProjectCapsule,
    RewriteDecision,
    RiskItem,
    RiskLevel,
    RiskPack,
    RouteDecisionPack,
    SourceConfidenceItem,
    SourceTier,
    TargetPlatform,
    TrendDirection,
    VisualCore,
    utc_now,
)


def novel_payload_to_bundle(payload: Dict[str, Any]) -> ChapterProductionBundle:
    """转换核心逻辑。"""
    meta = payload.get("_meta", {})
    run_id = meta.get("run_id", uuid.uuid4().hex[:10])
    project_id = f"prj_{run_id}_{int(datetime.now().timestamp())}"

    capsule_data = payload.get("project_capsule", {})
    passport_data = payload.get("preflight_passport", {})
    route_data = payload.get("route_decision_pack", {})
    seed_data = payload.get("narrative_seed_pack", {})
    risk_data = payload.get("risk_pack", {})
    market_data = payload.get("market_context_pack", {})
    memory_data = payload.get("author_memory_pack", {})

    # 1. ProjectCapsule
    emotion_map = {
        "复仇": EmotionCore.REVENGE,
        "代偿": EmotionCore.COMPENSATION,
        "亲情修复": EmotionCore.FAMILY_REPAIR,
        "身份跃迁": EmotionCore.IDENTITY_ASCENT,
        "求真": EmotionCore.TRUTH_SEEKING,
        "成长": EmotionCore.GROWTH,
    }
    emotion = emotion_map.get(capsule_data.get("emotion_core", ""), EmotionCore.COMPENSATION)

    # 从路线推断 VisualCore
    lane_str = route_data.get("content_lane", "")
    if "精品" in lane_str:
        visual = VisualCore.MIXED
    elif "混搭" in lane_str or "创新" in lane_str:
        visual = VisualCore.SPECTACLE_SETTING
    else:
        visual = VisualCore.REAL_RELATION

    capsule = ProjectCapsule(
        project_id=project_id,
        author_id=capsule_data.get("author_id", "default"),
        project_title=capsule_data.get("project_title", "未命名小说"),
        one_line_premise=capsule_data.get("one_line_premise", ""),
        theme_tags=capsule_data.get("theme_tags", []),
        emotion_core=emotion,
        visual_core=visual,
        target_platform=TargetPlatform.FANQIE_NOVEL,
        target_chapter_count=capsule_data.get("target_chapter_count", 120),
        target_chapter_words=capsule_data.get("target_chapter_words", 2200),
        preferred_format=FormatLane.REAL,  # 默认
        hard_constraints=capsule_data.get("hard_constraints", []),
    )

    # 2. MarketContextPack
    lane_heatmap = []
    for item in market_data.get("lane_heatmap", []):
        lane_heatmap.append(
            HeatmapItem(
                label=item.get("label", ""),
                score=item.get("score", 0),
                trend=TrendDirection.UP,
                confidence=market_data.get("platform_state_snapshot", {}).get("confidence", 0.5),
            )
        )

    market = MarketContextPack(
        pack_id=f"mkt_{project_id}",
        project_id=project_id,
        as_of_date=datetime.now().strftime("%Y-%m-%d"),
        platform_state_snapshot=market_data.get("platform_state_snapshot", {}),
        lane_heatmap=lane_heatmap,
        fallback_reasons=meta.get("fallback_reasons", []),
    )

    # 3. AuthorMemoryPack
    author_memory = AuthorMemoryPack(
        pack_id=f"mem_{project_id}",
        author_id=capsule_data.get("author_id", "default"),
        ltm_snapshot_id="llm_driven",
        strongest_lanes=memory_data.get("strongest_lanes", []),
        weakest_lanes=memory_data.get("weakest_lanes", []),
        reusable_pattern_pack=memory_data.get("reusable_pattern_pack", []),
        anti_pattern_blacklist=memory_data.get("anti_pattern_blacklist", []),
        author_bias_report=memory_data.get("author_bias_report", []),
    )

    # 4. RouteDecisionPack
    lane_map = {
        "保底爆款": ContentLane.STABLE_HIT,
        "上升混搭": ContentLane.RISING_MIX,
        "创新精品": ContentLane.INNOVATION_PREMIUM,
    }
    content_lane = lane_map.get(route_data.get("content_lane", ""), ContentLane.RISING_MIX)
    
    route = RouteDecisionPack(
        pack_id=f"route_{project_id}",
        project_id=project_id,
        content_lane=content_lane,
        format_lane=FormatLane.REAL,
        decision_rationale=route_data.get("decision_rationale", ""),
        route_confidence=route_data.get("route_confidence", 0.0),
        forbidden_cliche_list=route_data.get("forbidden_cliche_list", []),
        production_burden_estimate=route_data.get("production_burden_estimate", {"level": "medium"}),
    )

    # 5. NarrativeSeedPack
    arena = payload.get("concept_arena_pack", {})
    winner_data = None
    for branch in arena.get("concept_branches", []):
        if branch.get("branch_id") == arena.get("winner_branch_id"):
            winner_data = branch
            break
    
    winner = None
    if winner_data:
        sc = winner_data.get("scorecard", {})
        winner = BranchScore(
            branch_id=winner_data.get("branch_id", "A"),
            branch_description=f"{winner_data.get('title')}：{winner_data.get('one_line_pitch')}",
            platform_fit=sc.get("platform_fit", 0),
            hook_density=sc.get("hook_density", 0),
            ip_potential=sc.get("novelty", 0),
            producibility=sc.get("serial_sustainability", 0),
            total_score=sc.get("total_score", 0),
            verdict="winner",
        )

    hooks = []
    for h in seed_data.get("chapter_hook_chain", []):
        hooks.append(
            HookNode(
                episode_no=h.get("chapter", 1),
                hook_type=h.get("hook_type", ""),
                hook_text=h.get("hook_text", ""),
                intensity=80,
            )
        )

    narrative = NarrativeSeedPack(
        pack_id=f"seed_{project_id}",
        project_id=project_id,
        winner_branch=winner,
        hook_chain_map=hooks,
        writing_brief_v1=seed_data.get("writing_brief_v1", {}),
    )

    # 6. RiskPack
    decision_str = str(risk_data.get("rewrite_or_kill_decision", "rewrite")).lower()
    decision = (
        RewriteDecision.PASS if "pass" in decision_str
        else RewriteDecision.KILL if "kill" in decision_str
        else RewriteDecision.REWRITE
    )

    risk = RiskPack(
        pack_id=f"risk_{project_id}",
        project_id=project_id,
        adversarial_report=risk_data.get("adversarial_report", {}),
        rewrite_or_kill_decision=decision,
        must_fix_before_prod=risk_data.get("must_fix_before_prod", []),
    )

    # 7. PreflightPassport
    passport = PreflightPassport(
        passport_id=f"pass_{project_id}",
        project_id=project_id,
        **{"pass": bool(passport_data.get("pass", False))},
        total_score=passport_data.get("total_score", 0),
        gate_scores=passport_data.get("gate_scores", {}),
        blocking_issues=passport_data.get("blocking_issues", []),
        required_actions=passport_data.get("required_actions", []),
        fallback_reasons=meta.get("fallback_reasons", []),
        signoff=passport_data.get("signoff", {}),
        expiry_at=utc_now() + timedelta(days=passport_data.get("expiry_days", 14)),
    )

    bundle = ChapterProductionBundle(
        bundle_id=f"bundle_{project_id}",
        project_id=project_id,
        project_capsule=capsule,
        market_context=market,
        author_memory=author_memory,
        route_decision=route,
        narrative_seed=narrative,
        risk_pack=risk,
        preflight_passport=passport,
        token_budget_plan=payload.get("context_bundle_for_parser", {}).get("token_budget_plan", {}),
        fallback_reasons=meta.get("fallback_reasons", []),
    ).seal()

    return bundle
