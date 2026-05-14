from __future__ import annotations

import os
import re
import uuid
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pre_hub.ltm import LTMClient, LTMGovernance
from pre_hub.schemas.pre_hub_models import (
    AudiencePriorMatrix,
    AuthorMemoryPack,
    BranchScore,
    ChapterProductionBundle,
    ContentLane,
    EmotionCore,
    FormatFitItem,
    FormatLane,
    HeatmapItem,
    HookNode,
    MarketContextPack,
    MemoryCandidatePack,
    MemoryType,
    NarrativeGraphNode,
    NarrativeSeedPack,
    PreflightPassport,
    ProjectCapsule,
    RiskItem,
    RiskLevel,
    RiskPack,
    RewriteDecision,
    RouteDecisionPack,
    SourceConfidenceItem,
    SourceTier,
    TargetPlatform,
    TrendDirection,
    ViewingMode,
    VisualCore,
    utc_now,
)


LANE_KEYWORDS = {
    ContentLane.STABLE_HIT: ["逆袭", "复仇", "打脸", "升级", "爽文", "女强", "权谋", "都市"],
    ContentLane.RISING_MIX: ["穿越", "重生", "系统", "玄幻", "奇幻", "异能", "修仙", "末世"],
    ContentLane.INNOVATION_PREMIUM: ["悬疑", "现实", "民国", "职场", "家庭", "求真", "群像", "精品"],
}

RISK_KEYWORDS = {
    "rights": ["侵权", "抄袭", "盗版", "改编权", "IP", "肖像权", "声音授权"],
    "compliance": ["违规", "封禁", "下架", "处罚", "敏感题材", "擦边"],
    "market": ["同质化", "疲劳", "内卷", "伪创新"],
}


class PreHubOrchestrator:
    """Novel Preflight decision orchestrator.

    The workflow keeps the old M00-M09 shape, but the scoring surface is now
    for Fanqie-style serialized novels: reader promise, chapter hooks, setting
    sustainability, continuity, and compliance. Cloud LTM is frozen by default.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        workspace_root: Optional[str] = None,
        ltm_client: Optional[LTMClient] = None,
        ltm_governance: Optional[LTMGovernance] = None,
    ) -> None:
        self.config = config or {}
        self.workspace_root = workspace_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.run_id = uuid.uuid4().hex[:10]
        self.fallback_reasons: List[str] = []
        ltm_cfg = self.config.get("pre_hub", {}).get("ltm", {})
        self.enable_ltm_shadow_write = bool(ltm_cfg.get("enable_shadow_write", False))
        self.ltm_client = ltm_client
        if ltm_governance is not None:
            self.ltm_governance = ltm_governance
        elif self.enable_ltm_shadow_write:
            self.ltm_governance = LTMGovernance(self.workspace_root, client=ltm_client or LTMClient())
        else:
            self.ltm_governance = None

    def run(
        self,
        topic: str,
        format_lane: FormatLane = FormatLane.REAL,
        author_id: str = "default",
        use_rag: bool = True,
    ) -> ChapterProductionBundle:
        print(f"[Novel Preflight] M00 start: topic={topic}, chapter_form={format_lane.label}")
        capsule = self._m00_intake(topic, format_lane, author_id)

        raw_sources = self._collect_sources(topic, use_rag=use_rag)
        cleaned_sources, source_map, risk_signals = self._m01_source_guard(raw_sources)
        print(f"[Novel Preflight] M01 sources: raw={len(raw_sources)} clean={len(cleaned_sources)}")

        market = self._m02_market_radar(capsule, cleaned_sources, source_map, risk_signals)
        print(f"[Novel Preflight] M02 market fallback={len(market.fallback_reasons)}")

        author_memory = self._m03_author_memory(capsule, topic, use_rag=use_rag)
        print(f"[Novel Preflight] M03 local memory items={len(author_memory.reusable_pattern_pack)}")

        audience = self._m04_audience_model(capsule, market, author_memory)
        route = self._m05_route(capsule, market, author_memory, audience)
        print(f"[Novel Preflight] M05 route: {route.content_lane.value}/{route.format_lane.label}")

        print(f"[Novel Preflight] M06 starting concept arena...")
        branches = self._m06_concept_arena(capsule, market, author_memory, route)
        print(f"[Novel Preflight] M07 starting narrative seed...")
        narrative = self._m07_narrative_seed(capsule, route, branches)
        print(f"[Novel Preflight] M08 starting adversarial gate...")
        risk = self._m08_adversarial_gate(capsule, market, route, narrative, risk_signals)
        print(f"[Novel Preflight] M09 starting admission...")
        passport = self._m09_admission(capsule, market, author_memory, route, narrative, risk)

        bundle = ChapterProductionBundle(
            bundle_id=f"bundle_{capsule.project_id}",
            project_id=capsule.project_id,
            project_capsule=capsule,
            market_context=market,
            author_memory=author_memory,
            route_decision=route,
            narrative_seed=narrative,
            risk_pack=risk,
            preflight_passport=passport,
            token_budget_plan={
                "prehub_injection_chars": 2400,
                "rag_context_chars": 1600,
                "draft_chars": 12000,
            },
            fallback_reasons=sorted(set(self.fallback_reasons)),
        ).seal()

        if self.enable_ltm_shadow_write:
            self._mx1_stage_memory_candidate(bundle)
        print(f"[Novel Preflight] M09 passport: pass={passport.is_pass} score={passport.total_score}")
        return bundle

    def _m00_intake(self, topic: str, format_lane: FormatLane, author_id: str) -> ProjectCapsule:
        project_id = f"prj_{self.run_id}_{int(datetime.now().timestamp())}"
        tags = self._extract_tags(topic)
        emotion = EmotionCore.REVENGE if any(k in topic for k in ["复仇", "打脸", "逆袭"]) else EmotionCore.COMPENSATION
        if any(k in topic for k in ["亲情", "家庭", "母女", "父子"]):
            emotion = EmotionCore.FAMILY_REPAIR
        if any(k in topic for k in ["悬疑", "真相", "破案"]):
            emotion = EmotionCore.TRUTH_SEEKING

        if format_lane == FormatLane.AI:
            visual = VisualCore.SPECTACLE_SETTING
        elif format_lane == FormatLane.MIXED:
            visual = VisualCore.MIXED
        else:
            visual = VisualCore.REAL_RELATION

        return ProjectCapsule(
            project_id=project_id,
            author_id=author_id,
            project_title=topic.strip(),
            one_line_premise=f"{topic.strip()}项目，以{emotion.value}为情绪核心，面向番茄小说连载立项评审。",
            theme_tags=tags,
            emotion_core=emotion,
            visual_core=visual,
            target_platform=TargetPlatform.FANQIE_NOVEL,
            preferred_format=format_lane,
            hard_constraints=["不得抄袭或套用未授权 IP", "前三章必须建立读者承诺与追读钩子"],
            soft_goals=["降低同质化风险", "保证设定可持续连载", "保留章节回写空间"],
        )

    def _collect_sources(self, topic: str, use_rag: bool) -> List[Dict[str, Any]]:
        if not use_rag:
            self.fallback_reasons.append("rag_disabled_by_cli")
            return self._local_knowledge_sources(topic, reason="rag_disabled_by_cli")

        try:
            from rag_engine.search_aggregator import SearchAggregator

            kb_dir = os.path.join(self.workspace_root, "knowledge_base")
            aggregated = SearchAggregator(local_kb_dir=kb_dir).search(topic, max_results_per_source=6)
            self.fallback_reasons.extend(aggregated.get("fallback_reasons", []))
            results = aggregated.get("results", [])
            if results:
                return [
                    {
                        "title": item.get("title", ""),
                        "content": item.get("content", ""),
                        "url": item.get("url", ""),
                        "source": item.get("source") or item.get("origin") or "search_aggregator",
                        "published_at": item.get("published_at") or item.get("date") or datetime.now().strftime("%Y-%m-%d"),
                        "origin": item.get("origin", "search_aggregator"),
                    }
                    for item in results
                ]
            self.fallback_reasons.append("search_aggregator_empty_result")
        except Exception as exc:
            self.fallback_reasons.append(f"search_aggregator_failed:{type(exc).__name__}")
        return self._local_knowledge_sources(topic, reason="search_fallback")

    def _local_knowledge_sources(self, topic: str, reason: str) -> List[Dict[str, Any]]:
        kb_dir = os.path.join(self.workspace_root, "knowledge_base")
        if not os.path.isdir(kb_dir):
            return [
                {
                    "title": f"{topic} 本地规则兜底",
                    "content": f"{topic} 缺少外部数据，按番茄小说基础规则评审：前三章读者承诺、追读钩子、爽点外化、设定可持续性、合规风险。",
                    "url": "local://fallback",
                    "source": "local_rules",
                    "published_at": datetime.now().strftime("%Y-%m-%d"),
                    "origin": reason,
                }
            ]

        topic_terms = set(self._extract_tags(topic))
        scored: List[Tuple[int, str, str]] = []
        for root, _, files in os.walk(kb_dir):
            for filename in files:
                if not filename.endswith(".md") or filename == "关于知识库填充.md":
                    continue
                path = os.path.join(root, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    continue
                score = sum(text.count(term) for term in topic_terms)
                score += sum(text.count(term) for terms in LANE_KEYWORDS.values() for term in terms)
                scored.append((score, path, text[:2400]))

        scored.sort(key=lambda item: item[0], reverse=True)
        picked = [item for item in scored if item[0] > 0][:8] or scored[:5]
        sources = []
        for _, path, text in picked:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
            except OSError:
                mtime = datetime.now().strftime("%Y-%m-%d")
            sources.append(
                {
                    "title": os.path.basename(path),
                    "content": text,
                    "url": f"local://{os.path.relpath(path, self.workspace_root).replace(os.sep, '/')}",
                    "source": "local_knowledge_base",
                    "published_at": mtime,
                    "origin": reason,
                }
            )
        if not sources:
            sources.append(
                {
                    "title": f"{topic} 番茄小说本地兜底",
                    "content": f"{topic} 按番茄小说基础规则评审：题材承诺、主角驱动力、前三章追读、章尾钩子、长线设定可持续性。",
                    "url": "local://fallback",
                    "source": "local_knowledge_base",
                    "published_at": datetime.now().strftime("%Y-%m-%d"),
                    "origin": reason,
                }
            )
        return sources

    def _m01_source_guard(
        self, raw_sources: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[SourceConfidenceItem], List[RiskItem]]:
        window_days = int(self.config.get("pre_hub", {}).get("source_guard", {}).get("min_published_days", 90))
        cutoff = datetime.now() - timedelta(days=window_days)
        cleaned: List[Dict[str, Any]] = []
        source_map: List[SourceConfidenceItem] = []
        risks: List[RiskItem] = []
        seen = set()

        for item in raw_sources:
            title = str(item.get("title", "")).strip()
            content = str(item.get("content", "")).strip()
            url = str(item.get("url", "")).strip()
            source = str(item.get("source", "unknown")).strip() or "unknown"
            published_at = str(item.get("published_at", "")).strip()
            dedupe_key = (title[:80], url or content[:120])
            if dedupe_key in seen or not content:
                continue
            seen.add(dedupe_key)

            dt = self._parse_date(published_at)
            stale = bool(dt and dt < cutoff)
            future = bool(dt and dt > datetime.now() + timedelta(days=1))
            if stale or future:
                self.fallback_reasons.append(f"source_rejected:{'stale' if stale else 'future'}:{title[:30]}")
                continue

            tier = self._classify_source(source, url)
            confidence = self._source_confidence(tier, item.get("origin"))
            is_fact = not any(marker in content for marker in ["我觉得", "可能", "大概", "网传", "据说"])
            if not is_fact:
                confidence = max(0.2, confidence - 0.2)

            evidence = [url or title]
            cleaned_item = {
                "title": title,
                "content": content,
                "url": url,
                "source": source,
                "tier": tier.value,
                "confidence": confidence,
                "published_at": published_at,
                "is_fact": is_fact,
                "evidence_refs": evidence,
            }
            cleaned.append(cleaned_item)
            source_map.append(
                SourceConfidenceItem(
                    source_name=source,
                    source_tier=tier,
                    source_url=url or None,
                    published_at=published_at or None,
                    confidence=confidence,
                    is_fact=is_fact,
                    evidence_refs=evidence,
                )
            )

            for category, keywords in RISK_KEYWORDS.items():
                for keyword in keywords:
                    if keyword.lower() in content.lower():
                        risks.append(
                            RiskItem(
                                category=category,
                                level=RiskLevel.HIGH if category == "rights" else RiskLevel.MEDIUM,
                                description=f"信源提到风险关键词：{keyword}",
                                mitigation="进入对抗验证，生产前要求人工复核来源与授权。",
                                evidence_refs=evidence,
                            )
                        )
                        break

        if not cleaned:
            self.fallback_reasons.append("no_clean_source_after_guard")
        return cleaned, source_map, risks

    def _m02_market_radar(
        self,
        capsule: ProjectCapsule,
        sources: List[Dict[str, Any]],
        source_map: List[SourceConfidenceItem],
        risk_signals: List[RiskItem],
    ) -> MarketContextPack:
        text = "\n".join(str(item.get("content", "")) for item in sources)
        avg_conf = sum(item.confidence for item in source_map) / max(len(source_map), 1)
        lane_heatmap: List[HeatmapItem] = []
        for lane, keywords in LANE_KEYWORDS.items():
            count = sum(text.count(keyword) for keyword in keywords)
            topic_bonus = 2 if any(tag in keywords for tag in capsule.theme_tags) else 0
            score = min(100, int(38 + count * 7 + topic_bonus * 8 + avg_conf * 22))
            trend = TrendDirection.UP if score >= 72 else TrendDirection.FLAT if score >= 50 else TrendDirection.DOWN
            refs = self._evidence_for_keywords(sources, keywords)
            lane_heatmap.append(
                HeatmapItem(
                    label=lane.value,
                    score=score,
                    trend=trend,
                    confidence=min(1.0, avg_conf + count * 0.03),
                    evidence_refs=refs,
                )
            )
        lane_heatmap.sort(key=lambda item: item.score, reverse=True)

        format_fit = self._format_fit(capsule, text, avg_conf)
        risk_heat = self._risk_heatmap(risk_signals)
        opportunity = [
            HeatmapItem(
                label=f"{lane_heatmap[0].label}差异化窗口" if lane_heatmap else "基础网文窗口",
                score=max(45, min(88, (lane_heatmap[0].score if lane_heatmap else 50) - 5)),
                trend=TrendDirection.UP,
                confidence=avg_conf,
                evidence_refs=lane_heatmap[0].evidence_refs if lane_heatmap else [],
            )
        ]

        fallback = sorted(set(self.fallback_reasons))
        return MarketContextPack(
            pack_id=f"mkt_{capsule.project_id}",
            project_id=capsule.project_id,
            as_of_date=datetime.now().strftime("%Y-%m-%d"),
            platform_state_snapshot={
                "platform": "fanqie_novel",
                "source_count": len(sources),
                "clean_source_count": len(source_map),
                "avg_source_confidence": round(avg_conf, 3),
            },
            lane_heatmap=lane_heatmap,
            format_fit_map=format_fit,
            innovation_opportunity_map=opportunity,
            risk_heatmap=risk_heat,
            source_confidence_map=source_map,
            metric_normalization_note={
                "DAU_vs_MAU": "日活/月活不可混用",
                "reads_vs_readers": "阅读量/阅读人数不可混用",
                "heat_vs_retention": "热度值/完读率/追读率不可直接等价",
            },
            fallback_reasons=fallback,
        )

    def _m03_author_memory(
        self, capsule: ProjectCapsule, topic: str, use_rag: bool
    ) -> AuthorMemoryPack:
        query = f"{topic} {capsule.emotion_core.value} 番茄小说 追读钩子 爽点密度 失败模式"
        nodes: List[Dict[str, Any]] = []
        meta: Dict[str, Any] = {
            "source": "local_project_knowledge",
            "query": query,
            "top_k_raw": 5,
            "top_k_final": 0,
        }
        fallback: List[str] = ["cloud_ltm_frozen"]

        local_sources = self._local_knowledge_sources(topic, reason="local_project_memory")
        nodes = [
            {
                "memory_node_id": source.get("url") or f"local_{idx}",
                "content": source.get("content", ""),
                "score": 0.62,
                "source": "local_project_knowledge",
                "title": source.get("title", ""),
            }
            for idx, source in enumerate(local_sources[:5], start=1)
        ]
        meta["top_k_final"] = len(nodes)

        reusable = []
        anti = []
        for node in nodes:
            content = str(node.get("content", ""))
            item = {
                "memory_node_id": node.get("memory_node_id"),
                "content": content,
                "score": node.get("score"),
                "source": node.get("source", meta.get("source", "local_project_knowledge")),
            }
            if any(k in content.lower() for k in ["failure", "失败", "避免", "风险", "anti"]):
                anti.append(item)
            else:
                reusable.append(item)

        lanes = [item.label for item in self._m02_market_radar(capsule, [], [], []).lane_heatmap[:1]]
        return AuthorMemoryPack(
            pack_id=f"mem_{capsule.project_id}",
            author_id=capsule.author_id,
            ltm_snapshot_id="cloud_ltm_frozen",
            profile_version="local_project_knowledge",
            strongest_lanes=lanes or [capsule.theme_tags[0] if capsule.theme_tags else "网文"],
            weakest_lanes=["高概念过载", "缺少追读钩子的伪创新"],
            reusable_pattern_pack=reusable,
            anti_pattern_blacklist=anti,
            author_bias_report=[
                {
                    "bias_name": "新鲜度高估",
                    "description": "如缺少真实读者反馈或可追溯平台证据，默认降低创新方案置信度。",
                    "impact_level": RiskLevel.MEDIUM.value,
                }
            ],
            retrieval_meta=meta,
            fallback_reasons=fallback,
        )

    def _m04_audience_model(
        self,
        capsule: ProjectCapsule,
        market: MarketContextPack,
        author_memory: AuthorMemoryPack,
    ) -> AudiencePriorMatrix:
        top_score = market.lane_heatmap[0].score if market.lane_heatmap else 50
        memory_penalty = 0.08 if author_memory.anti_pattern_blacklist else 0.0
        integratable = max(0.2, min(0.45, top_score / 250 - memory_penalty))
        fatigued = max(0.12, min(0.35, 0.32 - integratable / 3))
        high_sensitive = max(0.2, min(0.4, 0.28 + top_score / 500))
        immune = max(0.05, 1.0 - integratable - fatigued - high_sensitive - 0.08)
        return AudiencePriorMatrix(
            zone_distribution={
                "可整合惊讶带": round(integratable, 3),
                "高敏区": round(high_sensitive, 3),
                "疲惫区": round(fatigued, 3),
                "免疫区": round(immune, 3),
                "过载区": 0.08,
            },
            viewing_mode_scores={
                ViewingMode.REAL_EMOTION.value: 0.82 if capsule.preferred_format == FormatLane.REAL else 0.58,
                ViewingMode.REAL_RELATION.value: 0.76 if capsule.visual_core == VisualCore.REAL_RELATION else 0.52,
                ViewingMode.AI_SPEC.value: 0.78 if capsule.preferred_format == FormatLane.AI else 0.42,
                ViewingMode.SERIES_ADDICT.value: 0.68,
                ViewingMode.SINGLE_BURST.value: 0.55,
            },
            integration_threshold=round(0.62 + memory_penalty, 3),
        )

    def _m05_route(
        self,
        capsule: ProjectCapsule,
        market: MarketContextPack,
        author_memory: AuthorMemoryPack,
        audience: AudiencePriorMatrix,
    ) -> RouteDecisionPack:
        matrix: List[Dict[str, Any]] = []
        lane_scores = {item.label: item.score for item in market.lane_heatmap}
        format_scores = {item.format_lane: item.fit_score for item in market.format_fit_map}
        preferred = capsule.preferred_format
        for lane in ContentLane:
            for fmt in FormatLane:
                market_fit = lane_scores.get(lane.value, 45)
                format_fit = format_scores.get(fmt, 55)
                novelty = 78 if lane == ContentLane.INNOVATION_PREMIUM else 62 if lane == ContentLane.RISING_MIX else 55
                chapter_production = 82 if fmt == FormatLane.REAL else 68 if fmt == FormatLane.MIXED else 60
                compliance = 82 if lane != ContentLane.RISING_MIX else 68
                project_memory_match = 70 + min(len(author_memory.reusable_pattern_pack) * 4, 12)
                preferred_bonus = 8 if fmt == preferred else 0
                total = int(
                    0.24 * market_fit
                    + 0.18 * format_fit
                    + 0.15 * novelty
                    + 0.18 * chapter_production
                    + 0.15 * compliance
                    + 0.10 * project_memory_match
                    + preferred_bonus
                )
                matrix.append(
                    {
                        "route_id": f"{lane.name.lower()}_{fmt.value}",
                        "content_lane": lane.value,
                        "format_lane": fmt.value,
                        "market_fit_score": market_fit,
                        "audience_fit_score": int(audience.viewing_mode_scores.get(ViewingMode.REAL_EMOTION.value, 0.6) * 100),
                        "novelty_score": novelty,
                        "chapter_production_score": chapter_production,
                        "compliance_score": compliance,
                        "project_memory_match_score": project_memory_match,
                        "total_score": max(0, min(100, total)),
                    }
                )
        matrix.sort(key=lambda item: item["total_score"], reverse=True)
        winner = matrix[0]
        content_lane = ContentLane(winner["content_lane"])
        format_lane = FormatLane(winner["format_lane"])
        forbidden = ["五年契约", "失忆洗白", "无代价开挂"]
        if content_lane == ContentLane.RISING_MIX:
            forbidden.append("纯设定堆砌无情绪债")
        return RouteDecisionPack(
            pack_id=f"route_{capsule.project_id}",
            project_id=capsule.project_id,
            content_lane=content_lane,
            format_lane=format_lane,
            route_matrix_scorecard=matrix,
            decision_rationale=(
                f"综合市场证据、章节形态和本地项目知识，当前最优路线为"
                f"{content_lane.value}/{format_lane.label}，评分{winner['total_score']}。"
            ),
            route_confidence=round(winner["total_score"] / 100, 3),
            forbidden_cliche_list=forbidden,
            production_burden_estimate={
                "level": "medium" if winner["chapter_production_score"] >= 65 else "high",
                "reason": "根据章节形态、连载复杂度、合规压力和题材可持续性估算。",
            },
        )

    def _m06_concept_arena(
        self,
        capsule: ProjectCapsule,
        market: MarketContextPack,
        author_memory: AuthorMemoryPack,
        route: RouteDecisionPack,
    ) -> List[BranchScore]:
        top_market = market.lane_heatmap[0].score if market.lane_heatmap else 55
        project_memory_boost = min(10, len(author_memory.reusable_pattern_pack) * 3)
        branch_specs = [
            ("A", "强冲突逆袭线", 82, 78, 72, 84, 22),
            ("B", "高概念反差线", 75, 88, 82, 62, 38),
            ("C", "情感深挖精品线", 70, 70, 76, 88, 18),
        ]
        branches: List[BranchScore] = []
        for branch_id, label, platform, hook, ip, producibility, rights in branch_specs:
            if route.content_lane == ContentLane.INNOVATION_PREMIUM and branch_id == "B":
                hook += 5
                ip += 6
            if route.format_lane == FormatLane.REAL and branch_id == "C":
                producibility += 4
            total = int(
                0.25 * min(100, platform + top_market // 10)
                + 0.25 * hook
                + 0.15 * ip
                + 0.20 * producibility
                + 0.10 * (100 - rights)
                + 0.05 * (70 + project_memory_boost)
            )
            branches.append(
                BranchScore(
                    branch_id=branch_id,
                    branch_description=f"{capsule.project_title}：{label}",
                    platform_fit=min(100, platform + top_market // 10),
                    hook_density=min(100, hook),
                    ip_potential=min(100, ip),
                    producibility=min(100, producibility),
                    rights_risk=rights,
                    ltm_match=70 + project_memory_boost,
                    total_score=max(0, min(100, total)),
                    evidence_refs=market.lane_heatmap[0].evidence_refs if market.lane_heatmap else [],
                )
            )
        branches.sort(key=lambda item: item.total_score, reverse=True)
        for idx, branch in enumerate(branches):
            branch.verdict = "winner" if idx == 0 else "runner_up" if idx == 1 else "kill"
        return branches

    def _m07_narrative_seed(
        self,
        capsule: ProjectCapsule,
        route: RouteDecisionPack,
        branches: List[BranchScore],
    ) -> NarrativeSeedPack:
        winner = branches[0] if branches else None
        runner_up = branches[1] if len(branches) > 1 else None
        graph = [
            NarrativeGraphNode(node_id="motive", node_type="character", content="主角被压迫或误判，建立情绪债与明确欲望", episode_range="第1章"),
            NarrativeGraphNode(node_id="hook_ch1", node_type="hook", content="第一章末给出读者承诺、现实代价与反击方向", episode_range="第1章", dependencies=["motive"]),
            NarrativeGraphNode(node_id="turn_ch3", node_type="plot_point", content="第三章完成第一次身份/关系/目标反转，形成追读理由", episode_range="第2-3章", dependencies=["hook_ch1"]),
            NarrativeGraphNode(node_id="retention_ch6", node_type="cliffhanger", content="第六章前把损失、羞辱或机会推到更高台阶，锁定书架与追读", episode_range="第4-6章", dependencies=["turn_ch3"]),
            NarrativeGraphNode(node_id="series_hook", node_type="cliffhanger", content="中后段打开系列化敌人、阶层天花板或更大真相", episode_range="第10-20章", dependencies=["retention_ch6"]),
        ]
        hooks = [
            HookNode(episode_no=1, hook_type="冲突升级型", hook_text="当场受辱，给出反击承诺", intensity=78, emotional_debt_raised=70),
            HookNode(episode_no=3, hook_type="反转型", hook_text="关键身份/关系误判翻转", intensity=82, emotional_debt_raised=65, emotional_debt_repaid=35),
            HookNode(episode_no=6, hook_type="追读锁定型", hook_text="把代价、机会或敌人压迫推到更高台阶", intensity=90, emotional_debt_raised=85),
            HookNode(episode_no=12, hook_type="长线悬念型", hook_text="揭示更大幕后目标或下一阶段成长天花板", intensity=84, emotional_debt_raised=50, emotional_debt_repaid=40),
        ]
        return NarrativeSeedPack(
            pack_id=f"seed_{capsule.project_id}",
            project_id=capsule.project_id,
            winner_branch=winner,
            runner_up_branch=runner_up,
            narrative_graph_v1=graph,
            knowledge_state_map=[
                {"chapter_no": 1, "actor": "主角", "knows": ["真实目标"], "misbeliefs": [], "audience_knows_more": False},
                {"chapter_no": 3, "actor": "反派", "knows": ["表层身份"], "misbeliefs": ["主角无反击能力"], "audience_knows_more": True},
            ],
            emotional_debt_ledger=[
                {"chapter_no": 1, "debt_open": 70, "debt_close": 0, "repay_ratio": 0.0},
                {"chapter_no": 3, "debt_open": 65, "debt_close": 35, "repay_ratio": 0.54},
                {"chapter_no": 6, "debt_open": 85, "debt_close": 20, "repay_ratio": 0.24},
            ],
            hook_chain_map=hooks,
            format_constraint_sheet={
                "chapter_form": route.format_lane.label,
                "forbidden_cliche": route.forbidden_cliche_list,
                "target_chapter_count": capsule.target_chapter_count,
                "target_chapter_words": capsule.target_chapter_words,
            },
            rights_compliance_stub={
                "originality": "original_required",
                "needs_auth": [],
                "high_risk_scenes": [],
            },
            writing_brief_v1={
                "winner_branch": winner.branch_description if winner else "",
                "route": f"{route.content_lane.value}/{route.format_lane.label}",
                "must_have": ["前三章读者承诺", "每章末追读钩子", "爽点密度与人物成长同步推进"],
            },
        )

    def _m08_adversarial_gate(
        self,
        capsule: ProjectCapsule,
        market: MarketContextPack,
        route: RouteDecisionPack,
        narrative: NarrativeSeedPack,
        risk_signals: List[RiskItem],
    ) -> RiskPack:
        checks = {
            "source_evidence": len(market.source_confidence_map) >= 2,
            "route_confidence": route.route_confidence >= 0.62,
            "hook_chain": len(narrative.hook_chain_map) >= 3,
            "chapter_form_match": route.format_lane == capsule.preferred_format or route.route_confidence >= 0.72,
            "rights_clean": not any(item.category == "rights" and item.level in {RiskLevel.HIGH, RiskLevel.CRITICAL} for item in risk_signals),
            "fallback_transparent": bool(market.fallback_reasons) == bool(self.fallback_reasons),
            "not_over_complex": route.content_lane != ContentLane.RISING_MIX or route.route_confidence >= 0.68,
            "author_bias_checked": True,
            "chapter_production_burden_ok": route.production_burden_estimate.get("level") != "high",
            "worth_writing": (narrative.winner_branch.total_score if narrative.winner_branch else 0) >= 60,
        }
        passed_count = sum(1 for value in checks.values() if value)
        fatal: List[RiskItem] = []
        must_fix: List[str] = []
        if not checks["source_evidence"]:
            must_fix.append("补充至少2条可追溯市场/方法论证据后复评。")
        if not checks["rights_clean"]:
            fatal.extend(risk_signals)
            must_fix.append("人工复核所有 IP、肖像、素材来源授权。")
        if not checks["hook_chain"]:
            fatal.append(RiskItem(category="narrative", level=RiskLevel.HIGH, description="钩子链不足"))
            must_fix.append("补齐前三章读者承诺与章尾追读钩子链。")
        if route.route_confidence < 0.55:
            fatal.append(RiskItem(category="route", level=RiskLevel.HIGH, description="路线置信度过低"))

        if fatal and any(item.level == RiskLevel.CRITICAL for item in fatal):
            decision = RewriteDecision.KILL
        elif passed_count >= 8 and not fatal:
            decision = RewriteDecision.PASS
        elif passed_count >= 6:
            decision = RewriteDecision.REWRITE
        else:
            decision = RewriteDecision.KILL

        return RiskPack(
            pack_id=f"risk_{capsule.project_id}",
            project_id=capsule.project_id,
            rights_risk_pack=[item for item in risk_signals if item.category == "rights"],
            compliance_flags=[item.description for item in risk_signals if item.category == "compliance"],
            route_mismatch_flag=not checks["chapter_form_match"],
            fatal_flaw_list=fatal,
            adversarial_report={"checks": checks, "passed_count": passed_count},
            rewrite_or_kill_decision=decision,
            must_fix_before_prod=must_fix,
        )

    def _m09_admission(
        self,
        capsule: ProjectCapsule,
        market: MarketContextPack,
        author_memory: AuthorMemoryPack,
        route: RouteDecisionPack,
        narrative: NarrativeSeedPack,
        risk: RiskPack,
    ) -> PreflightPassport:
        source_score = int((sum(item.confidence for item in market.source_confidence_map) / max(len(market.source_confidence_map), 1)) * 100)
        market_score = market.lane_heatmap[0].score if market.lane_heatmap else 35
        memory_score = 72 if author_memory.reusable_pattern_pack else 58
        route_score = int(route.route_confidence * 100)
        concept_score = narrative.winner_branch.total_score if narrative.winner_branch else 0
        narrative_score = 82 if len(narrative.hook_chain_map) >= 3 else 50
        adversarial_score = int(risk.adversarial_report.get("passed_count", 0) * 10)
        gate_scores = {
            "信源净化": max(30, source_score),
            "市场雷达": market_score,
            "本地项目知识": memory_score,
            "小说赛道分流": route_score,
            "概念竞技": concept_score,
            "章节钩子图谱": narrative_score,
            "对抗验证": min(100, adversarial_score),
        }
        total = int(
            0.14 * gate_scores["信源净化"]
            + 0.18 * gate_scores["市场雷达"]
            + 0.10 * gate_scores["本地项目知识"]
            + 0.18 * gate_scores["小说赛道分流"]
            + 0.16 * gate_scores["概念竞技"]
            + 0.12 * gate_scores["章节钩子图谱"]
            + 0.12 * gate_scores["对抗验证"]
        )
        if risk.rewrite_or_kill_decision == RewriteDecision.KILL:
            total = min(total, 49)
        elif risk.rewrite_or_kill_decision == RewriteDecision.REWRITE:
            total = min(total, 74)
        is_pass = risk.rewrite_or_kill_decision != RewriteDecision.KILL and total >= 55
        return PreflightPassport(
            passport_id=f"pass_{capsule.project_id}",
            project_id=capsule.project_id,
            **{"pass": is_pass},
            total_score=max(0, min(100, total)),
            gate_scores=gate_scores,
            blocking_issues=[item.description for item in risk.fatal_flaw_list],
            required_actions=risk.must_fix_before_prod,
            fallback_reasons=sorted(set(self.fallback_reasons)),
            signoff={
                "engine": "fanqie_novel_preflight",
                "mode": "auto_with_local_fallback",
                "issued_by": "PreHubOrchestrator",
            },
            expiry_at=utc_now() + timedelta(days=14),
        )

    def _mx1_stage_memory_candidate(self, bundle: ChapterProductionBundle) -> None:
        risk = bundle.risk_pack
        route = bundle.route_decision
        passport = bundle.preflight_passport
        confidence = min(0.90, max(0.45, passport.total_score / 100))
        if risk.rewrite_or_kill_decision == RewriteDecision.REWRITE:
            confidence = min(confidence, 0.72)
        candidate = MemoryCandidatePack(
            candidate_id=f"memcand_{uuid.uuid4().hex[:12]}",
            author_id=bundle.project_capsule.author_id,
            project_id=bundle.project_id,
            memory_type=MemoryType.MARKET_CALIBRATION if bundle.market_context.fallback_reasons else MemoryType.PATTERN_SUCCESS,
            condition=f"题材={bundle.project_capsule.project_title}; 路线={route.content_lane.value}/{route.format_lane.label}",
            action=f"采用{bundle.narrative_seed.winner_branch.branch_description if bundle.narrative_seed.winner_branch else '默认'}并锁定章节追读钩子链",
            result=f"番茄前置准入={passport.is_pass}; 总分={passport.total_score}; 决策={risk.rewrite_or_kill_decision.value}",
            scope={
                "content_lane": route.content_lane.value,
                "chapter_form": route.format_lane.label,
                "platform": bundle.project_capsule.target_platform.value,
            },
            evidence_refs=[
                ref
                for item in bundle.market_context.source_confidence_map[:5]
                for ref in item.evidence_refs[:1]
            ],
            metrics={"passport_score": passport.total_score, "gate_scores": passport.gate_scores},
            candidate_confidence=confidence,
        )
        self.ltm_governance.stage_candidate(candidate)

    def _format_fit(self, capsule: ProjectCapsule, text: str, avg_conf: float) -> List[FormatFitItem]:
        lower = text.lower()
        scores = {
            FormatLane.REAL: 58 + (18 if any(k in text for k in ["都市", "现实", "关系", "爽文", "逆袭"]) else 0),
            FormatLane.AI: 48 + (22 if any(k in lower for k in ["ai", "玄幻", "系统", "异能", "修仙", "末世", "设定"]) else 0),
            FormatLane.MIXED: 56 + (12 if any(k in text for k in ["悬疑", "群像", "多线", "考据", "知识库"]) else 0),
        }
        results = []
        for fmt, score in scores.items():
            if fmt == capsule.preferred_format:
                score += 6
            results.append(
                FormatFitItem(
                    format_lane=fmt,
                    fit_score=min(100, score),
                    reasons=[f"preferred={capsule.preferred_format.label}", f"avg_source_confidence={avg_conf:.2f}"],
                    confidence=min(1.0, avg_conf + 0.1),
                )
            )
        results.sort(key=lambda item: item.fit_score, reverse=True)
        return results

    def _risk_heatmap(self, risks: List[RiskItem]) -> List[HeatmapItem]:
        counter = Counter(item.category for item in risks)
        if not counter:
            return [
                HeatmapItem(label="rights", score=18, trend=TrendDirection.FLAT, confidence=0.5),
                HeatmapItem(label="compliance", score=22, trend=TrendDirection.FLAT, confidence=0.5),
            ]
        return [
            HeatmapItem(
                label=category,
                score=min(100, 35 + count * 18),
                trend=TrendDirection.UP,
                confidence=0.72,
                evidence_refs=[ref for item in risks if item.category == category for ref in item.evidence_refs[:1]],
            )
            for category, count in counter.items()
        ]

    @staticmethod
    def _classify_source(source: str, url: str) -> SourceTier:
        blob = f"{source} {url}".lower()
        if any(k in blob for k in ["官方", "official", "gov", "redfruit", "fanqie", "番茄"]):
            return SourceTier.OFFICIAL
        if any(k in blob for k in ["新浪", "腾讯", "网易", "搜狐", "央视", "新华社", "qq.com", "163.com"]):
            return SourceTier.MAINSTREAM
        if any(k in blob for k in ["研究", "报告", "数据", "咨询", "艾瑞", "questmobile"]):
            return SourceTier.THIRD_PARTY
        if any(k in blob for k in ["36氪", "虎嗅", "媒体", "industry"]):
            return SourceTier.INDUSTRY
        if "local_knowledge_base" in blob:
            return SourceTier.THIRD_PARTY
        return SourceTier.SELF_MEDIA

    @staticmethod
    def _source_confidence(tier: SourceTier, origin: Any) -> float:
        base = {
            SourceTier.OFFICIAL: 0.95,
            SourceTier.MAINSTREAM: 0.80,
            SourceTier.THIRD_PARTY: 0.70,
            SourceTier.INDUSTRY: 0.58,
            SourceTier.SELF_MEDIA: 0.35,
            SourceTier.OTHER: 0.30,
        }[tier]
        if origin and str(origin).startswith("missing_env"):
            base = min(base, 0.62)
        if origin and str(origin).startswith("rag_disabled"):
            base = min(base, 0.58)
        return base

    @staticmethod
    def _parse_date(value: str) -> Optional[datetime]:
        if not value:
            return None
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value[:19], fmt)
            except ValueError:
                continue
        match = re.search(r"(\d+)\s*天前", value)
        if match:
            return datetime.now() - timedelta(days=int(match.group(1)))
        return None

    @staticmethod
    def _extract_tags(topic: str) -> List[str]:
        tags: List[str] = []
        for keyword in sorted({kw for kws in LANE_KEYWORDS.values() for kw in kws}, key=len, reverse=True):
            if keyword.lower() in topic.lower():
                tags.append(keyword)
        for chunk in re.split(r"[\s,，/|、]+", topic.strip()):
            if chunk and chunk not in tags:
                tags.append(chunk[:12])
        return tags[:8] or [topic[:12] or "网文"]

    @staticmethod
    def _evidence_for_keywords(sources: List[Dict[str, Any]], keywords: List[str]) -> List[str]:
        refs: List[str] = []
        for item in sources:
            content = str(item.get("content", ""))
            if any(keyword in content for keyword in keywords):
                refs.extend(item.get("evidence_refs") or [item.get("url") or item.get("title", "")])
            if len(refs) >= 5:
                break
        return [ref for ref in refs if ref][:5]
