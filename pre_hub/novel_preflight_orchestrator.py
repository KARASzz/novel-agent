# pre_hub/novel_preflight_orchestrator.py
"""
番茄小说前置立项中台 - LLM 驱动评审总线。

定位：
  这不是规则引擎。
  这不是关键词评分器。
  这不是短剧评审器。

  这是一个小说立项前置中台：
    - Python 负责收集、拼装、解析、校验、打包
    - LLM 负责判断、分流、竞技、风险审查、准入决策

核心流程：
  1. _collect_sources      → 搜索 / RAG / 本地 KB，收集市场材料
  2. _collect_memory       → 本地知识库 / LTM，提取作者经验和禁用模式
  3. _llm_preflight        → 一次 LLM 完成 M00-M09 全部立项评审
  4. run                  → 返回 dict 标准包；你可自行接 ChapterProductionBundle

禁止：
  - 不做硬编码题材评分
  - 不用关键词判断优劣
  - 不在 Python 里写死 pass/rewrite/kill 规则
  - 不把短剧字段原样套到小说字段
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple


class NovelPreflightOrchestrator:
    """番茄小说立项中台。LLM 负责评审，Python 只做总线。"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        workspace_root: Optional[str] = None,
        bundle_adapter: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> None:
        self.config = config or {}
        self.workspace_root = workspace_root or os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        self.run_id = uuid.uuid4().hex[:10]
        self.fallback_reasons: List[str] = []
        self.bundle_adapter = bundle_adapter

    # ---------------------------------------------------------------------
    # 主入口
    # ---------------------------------------------------------------------

    def run(
        self,
        topic: str,
        author_id: str = "default",
        model_slot: Optional[str] = None,
        use_rag: bool = True,
        novel_form: str = "长篇连载",
        target_platform: str = "番茄小说",
        extra_constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any] | Any:
        """
        对外主入口。

        返回：
          默认返回 dict 标准包。
          如果传入 bundle_adapter，则返回 adapter 转换后的对象。

        你后续可以把 adapter 接到：
          - ChapterProductionBundle
          - Pydantic PreHubArtifacts
          - context_bundle_for_parser
        """
        if not model_slot:
            raise RuntimeError("model_slot 必须指定。前置评审全程由 LLM 驱动。")

        topic = topic.strip()
        if not topic:
            raise ValueError("topic 不能为空。")

        print(f"[Novel Preflight] 开始: topic={topic}, form={novel_form}")

        raw_sources = self._collect_sources(topic=topic, use_rag=use_rag)
        source_text = self._pack_sources(raw_sources)

        print(f"[Novel Preflight] 来源收集完成: {len(raw_sources)} 条")

        memory_text, anti_text = self._collect_memory(
            topic=topic,
            author_id=author_id,
        )

        print(
            f"[Novel Preflight] 记忆收集完成: reusable={len(memory_text)} chars, "
            f"anti={len(anti_text)} chars"
        )

        payload = self._llm_preflight(
            topic=topic,
            author_id=author_id,
            model_slot=model_slot,
            novel_form=novel_form,
            target_platform=target_platform,
            raw_sources=raw_sources,
            source_text=source_text,
            memory_text=memory_text,
            anti_text=anti_text,
            extra_constraints=extra_constraints or {},
        )

        payload["_meta"] = {
            "engine": "novel_preflight_orchestrator",
            "mode": "llm_driven",
            "run_id": self.run_id,
            "topic": topic,
            "author_id": author_id,
            "model_slot": model_slot,
            "generated_at": self._now_iso(),
            "fallback_reasons": sorted(set(self.fallback_reasons)),
        }

        print(
            "[Novel Preflight] 完成: "
            f"decision={payload.get('preflight_passport', {}).get('decision')} "
            f"score={payload.get('preflight_passport', {}).get('total_score')}"
        )

        if self.bundle_adapter:
            return self.bundle_adapter(payload)

        return payload

    # ---------------------------------------------------------------------
    # Step 1: 来源收集
    # ---------------------------------------------------------------------

    def _collect_sources(self, topic: str, use_rag: bool) -> List[Dict[str, Any]]:
        """
        收集市场文本。

        注意：
          这里不做题材优劣判断。
          只负责把外部材料拿回来。
        """
        if not use_rag:
            self.fallback_reasons.append("rag_disabled")
            return self._local_kb_sources(reason="rag_disabled")

        try:
            from rag_engine.search_aggregator import SearchAggregator

            search_cfg = self.config.get("pre_hub", {}).get("search", {})
            max_results = int(search_cfg.get("max_results_per_source", 6))
            
            kb_dir = os.path.join(self.workspace_root, "knowledge_base")
            aggregator = SearchAggregator(
                local_kb_dir=kb_dir,
                enable_brave=bool(search_cfg.get("enable_brave", True)),
                enable_tavily=bool(search_cfg.get("enable_tavily", True)),
                brave_params=search_cfg.get("brave", {}),
                tavily_params=search_cfg.get("tavily", {}),
            )
            aggregated = aggregator.search(topic, max_results_per_source=max_results)

            self.fallback_reasons.extend(aggregated.get("fallback_reasons", []))

            results = aggregated.get("results", [])
            if results:
                return [
                    {
                        "title": item.get("title", ""),
                        "content": item.get("content", ""),
                        "url": item.get("url", ""),
                        "source": item.get("source") or item.get("origin") or "search",
                        "published_at": item.get("published_at")
                        or item.get("date")
                        or self._today(),
                    }
                    for item in results
                ]

            self.fallback_reasons.append("search_empty")

        except Exception as exc:
            self.fallback_reasons.append(f"search_failed:{type(exc).__name__}")

        return self._local_kb_sources(reason="search_fallback")

    def _local_kb_sources(self, reason: str) -> List[Dict[str, Any]]:
        """
        本地兜底来源。

        不做关键词排名。
        只读取 knowledge_base 下的 md 文档。
        真正判断交给 LLM。
        """
        kb_dir = os.path.join(self.workspace_root, "knowledge_base")
        if not os.path.isdir(kb_dir):
            self.fallback_reasons.append(f"{reason}:kb_dir_missing")
            return [
                {
                    "title": "local_fallback",
                    "content": "未找到本地知识库。请基于输入题材进行保守立项评审。",
                    "url": "local://fallback",
                    "source": "local_fallback",
                    "published_at": self._today(),
                }
            ]

        docs: List[Dict[str, Any]] = []

        for root, _, files in os.walk(kb_dir):
            for filename in files:
                if not filename.endswith(".md"):
                    continue

                path = os.path.join(root, filename)

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    continue

                try:
                    mtime = datetime.fromtimestamp(
                        os.path.getmtime(path),
                        tz=timezone.utc,
                    ).date().isoformat()
                except OSError:
                    mtime = self._today()

                docs.append(
                    {
                        "title": filename,
                        "content": text[:3000],
                        "url": f"local://{os.path.relpath(path, self.workspace_root).replace(os.sep, '/')}",
                        "source": "local_knowledge_base",
                        "published_at": mtime,
                    }
                )

        if not docs:
            self.fallback_reasons.append(f"{reason}:kb_empty")
            return [
                {
                    "title": "local_empty_fallback",
                    "content": "本地知识库为空。请基于题材进行保守立项评审。",
                    "url": "local://empty",
                    "source": "local_fallback",
                    "published_at": self._today(),
                }
            ]

        packing_cfg = self.config.get("pre_hub", {}).get("packing", {})
        max_docs = int(packing_cfg.get("max_docs_to_read", 12))
        return docs[:max_docs]

    def _pack_sources(self, raw_sources: List[Dict[str, Any]]) -> str:
        packing_cfg = self.config.get("pre_hub", {}).get("packing", {})
        max_sources = int(packing_cfg.get("max_sources_to_pack", 12))
        snippet_limit = int(packing_cfg.get("source_snippet_chars", 1200))

        blocks = []
        for i, item in enumerate(raw_sources[:max_sources], start=1):
            blocks.append(
                "\n".join(
                    [
                        f"[source_{i}]",
                        f"title: {item.get('title', '')}",
                        f"source: {item.get('source', '')}",
                        f"url: {item.get('url', '')}",
                        f"published_at: {item.get('published_at', '')}",
                        "content:",
                        str(item.get("content", ""))[:snippet_limit],
                    ]
                )
            )
        return "\n\n".join(blocks)

    # ---------------------------------------------------------------------
    # Step 2: 作者记忆 / 本地方法论
    # ---------------------------------------------------------------------

    def _collect_memory(self, topic: str, author_id: str) -> Tuple[str, str]:
        """
        返回：
          memory_text: 可复用经验
          anti_text: 禁止清单 / 失败模式

        这里不判断“哪些经验一定对”。
        只收集上下文。
        """
        mem_cfg = self.config.get("pre_hub", {}).get("memory", {})
        
        local_memory = self._read_memory_files(
            subdirs=mem_cfg.get("memory_subdirs", [
                "knowledge_base/common",
                "knowledge_base/projects",
                "knowledge_base/memory",
            ]),
            limit_chars=int(mem_cfg.get("memory_limit_chars", 6000)),
        )

        local_anti = self._read_memory_files(
            subdirs=mem_cfg.get("anti_subdirs", [
                "knowledge_base/anti",
                "knowledge_base/risk",
                "knowledge_base/failure",
            ]),
            limit_chars=int(mem_cfg.get("anti_limit_chars", 3000)),
        )

        ltm_text = self._try_collect_ltm(topic=topic, author_id=author_id)

        memory_text = "\n\n".join(
            x for x in [local_memory, ltm_text] if x.strip()
        ).strip()

        anti_text = local_anti.strip()

        return (
            memory_text or "无可用作者记忆。请基于市场材料和题材本身进行评审。",
            anti_text or "无明确禁止清单。请自行识别陈词滥调、同质化、IP风险和追读风险。",
        )

    def _read_memory_files(self, subdirs: List[str], limit_chars: int) -> str:
        chunks: List[str] = []

        for subdir in subdirs:
            path = os.path.join(self.workspace_root, subdir)
            if not os.path.isdir(path):
                continue

            for root, _, files in os.walk(path):
                for filename in files:
                    if not filename.endswith(".md"):
                        continue

                    full_path = os.path.join(root, filename)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            text = f.read()
                    except Exception:
                        continue

                    chunks.append(
                        f"# {filename}\n{text[:1600]}"
                    )

                    if sum(len(c) for c in chunks) >= limit_chars:
                        return "\n\n".join(chunks)[:limit_chars]

        return "\n\n".join(chunks)[:limit_chars]

    def _try_collect_ltm(self, topic: str, author_id: str) -> str:
        """
        可选 LTM 召回。

        你现有项目里如果已有 LTMClient，可在这里接。
        接不上时，不中断主流程。
        """
        ltm_cfg = self.config.get("pre_hub", {}).get("ltm", {})
        if not ltm_cfg.get("enabled", False):
            return ""

        try:
            from pre_hub.ltm import LTMClient

            client = LTMClient()
            query = (
                f"作者 {author_id} 针对番茄小说题材【{topic}】的强项赛道、"
                f"高ROI钩子、常见失败模式、伪创新偏差、重写偏好。"
            )

            results = client.search_memory(
                user_id=author_id,
                query=query,
                top_k=int(ltm_cfg.get("top_k", 5)),
            )

            if not results:
                return ""

            return "# LTM 召回结果\n" + json.dumps(
                results,
                ensure_ascii=False,
                indent=2,
            )[:4000]

        except Exception as exc:
            self.fallback_reasons.append(f"ltm_failed:{type(exc).__name__}")
            return ""

    # ---------------------------------------------------------------------
    # Step 3: LLM 前置评审
    # ---------------------------------------------------------------------

    def _llm_preflight(
        self,
        topic: str,
        author_id: str,
        model_slot: str,
        novel_form: str,
        target_platform: str,
        raw_sources: List[Dict[str, Any]],
        source_text: str,
        memory_text: str,
        anti_text: str,
        extra_constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        from scripts.outline_generator import get_model_credentials
        from core_engine.llm_client import LLMClient

        base_url, model_id, api_key = get_model_credentials(model_slot)
        client = LLMClient(api_key=api_key, base_url=base_url)

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            topic=topic,
            author_id=author_id,
            novel_form=novel_form,
            target_platform=target_platform,
            raw_sources=raw_sources,
            source_text=source_text,
            memory_text=memory_text,
            anti_text=anti_text,
            extra_constraints=extra_constraints,
        )

        res = client.create_response(model_id, system_prompt, user_prompt)
        raw = getattr(res, "output_text", str(res))

        try:
            data = self._parse_json_or_raise(raw)
        except ValueError as exc:
            print(f"[Novel Preflight] JSON 解析初步失败，尝试自动修复... ({exc})")
            data = self._repair_json_with_llm(raw, model_slot)

        if not isinstance(data, dict):
            raise ValueError("LLM 返回不是 JSON object。")

        return data

    def _build_system_prompt(self) -> str:
        return """
你是【番茄小说前置立项中台】的 LLM 评审引擎。

你的任务不是写正文。
你的任务是判断一个小说题材是否值得立项，并把它打包成可交给后续写作流水线的标准上下文包。

你必须按 M00-M09 工序完成评审：

M00 项目接入与规范化：
- 把散装题材拆成题材、核心冲突、情绪核心、读者承诺、篇幅形态。
- 区分“脑洞亮点”和“可连载发动机”。

M01 信源净化与时效校准：
- 区分事实、观点、营销话术、过期信息。
- 不得把来源数量等同于市场确定性。
- 对来源质量给出保守判断。

M02 小说市场雷达：
- 判断该题材在番茄小说里的读者入口、爽点机制、追读潜力、同质化程度。
- 不要套用短剧字段。

M03 作者记忆校准：
- 只把作者记忆当偏好和经验信号，不得当市场事实。
- 可复用模式、禁用模式、作者偏差要分开。

M04 读者先验建模：
- 判断读者已经看腻什么、还愿意为什么追读、前三章需要兑现什么。
- 必须给出免疫区、高敏区、可整合惊讶带、过载区。

M05 小说赛道分流：
- 在小说语境中判断路线。
- 可用路线：保底爆款、上升混搭、创新精品。
- 可用篇幅形态：长篇连载、中篇精品、短篇强爽、系列单元、试验型。
- 不要输出真人/AI/短剧制作路线，除非用户明确要求。

M06 高概念竞技场：
- 生成 3 个真正不同的小说分支。
- 每个分支必须有：读者承诺、核心冲突、追读发动机、前三章钩子、连载续航风险。
- 必须选 winner、runner_up、kill。

M07 叙事图谱与生产约束锁定：
- 生成可以交给后续写作系统的 narrative_seed_pack。
- 必须包含：主角欲望、反派压力、核心秘密、信息差、情绪负债、章节钩子链、前三章承诺、三十章阶段目标。

M08 对抗验证：
- 专门找死穴。
- 检查：旧题材换皮、角色降智、开局强后续空、爽点兑现太快、金手指无代价、IP/平台合规风险、番茄读者入口不清。
- 必须给 rewrite/pass/kill。

M09 准入门：
- 只输出可执行结论。
- pass 表示可以进后续写作流水线。
- rewrite 表示题材可救，但必须修改。
- kill 表示不建议投入生产。

硬规则：
1. 只输出 JSON。
2. 不输出 markdown。
3. 不输出解释性前后缀。
4. 不要出现 <think>。
5. 不要把短剧术语原样套进小说。
6. 所有字段必须服务于小说立项和后续章节生产。
7. 分数由你基于材料综合判断，不允许空泛给高分。
8. 如果来源不足，必须在 source_audit 和 fallback_reasons 里说明。
""".strip()

    def _build_user_prompt(
        self,
        topic: str,
        author_id: str,
        novel_form: str,
        target_platform: str,
        raw_sources: List[Dict[str, Any]],
        source_text: str,
        memory_text: str,
        anti_text: str,
        extra_constraints: Dict[str, Any],
    ) -> str:
        return f"""
请对小说题材【{topic}】进行完整前置立项评审。

基础参数：
- target_platform: {target_platform}
- novel_form: {novel_form}
- author_id: {author_id}
- source_count: {len(raw_sources)}

额外约束：
{json.dumps(extra_constraints, ensure_ascii=False, indent=2)}

市场/搜索/知识库来源：
{source_text[:9000]}

作者可复用经验：
{memory_text[:5000]}

禁用模式 / 失败模式 / 风险提醒：
{anti_text[:3000]}

请严格输出下面 JSON 结构。
字段名不得改。
缺少信息时，用保守判断，不要编造具体数据。
所有文本必须围绕【{topic}】。

{{
  "project_capsule": {{
    "project_id": "自动生成占位即可",
    "author_id": "{author_id}",
    "project_title": "针对题材生成的暂定书名",
    "one_line_premise": "25字以内，一句话小说核心冲突",
    "theme_tags": ["1-8个小说题材标签"],
    "emotion_core": "复仇|代偿|亲情修复|身份跃迁|求真|成长|生存|权力|救赎",
    "reader_promise": "读者点开这本书，期待被满足的核心承诺",
    "target_platform": "{target_platform}",
    "novel_form": "{novel_form}",
    "target_chapter_count": 120,
    "target_chapter_words": 2200,
    "hard_constraints": [
      "不得抄袭或套用未授权IP",
      "前三章必须建立清晰读者承诺",
      "每章结尾必须有追读推力"
    ]
  }},

  "source_audit": {{
    "source_quality_summary": "本次来源质量判断",
    "fact_items": [
      {{"claim": "可作为事实的内容", "evidence_refs": ["source_1"], "confidence": 0.0}}
    ],
    "opinion_items": [
      {{"claim": "观点或推测", "evidence_refs": ["source_2"], "confidence": 0.0}}
    ],
    "weaknesses": ["来源不足、过期、同源转载、口径不明等"],
    "fallback_reasons": []
  }},

  "market_context_pack": {{
    "platform_state_snapshot": {{
      "summary": "番茄小说当前语境下，该题材的市场位置",
      "market_window": "稳定|上升|过热|衰退|不确定",
      "confidence": 0.0
    }},
    "lane_heatmap": [
      {{
        "label": "赛道名",
        "score": 0,
        "trend": "up|flat|down|unknown",
        "reason": "为什么"
      }}
    ],
    "reader_prior_matrix": {{
      "immune_zone": ["读者已经免疫的套路"],
      "fatigue_zone": ["能看但不值钱的内容"],
      "sensitive_zone": ["轻微触发就可能追读的刺激点"],
      "integratable_surprise_zone": ["新鲜但能理解的设计"],
      "overload_zone": ["会劝退的复杂度或雷点"]
    }},
    "risk_heatmap": [
      {{
        "category": "同质化|合规|IP|节奏|人设|金手指|世界观",
        "level": "low|medium|high|critical",
        "reason": "风险原因",
        "mitigation": "规避方式"
      }}
    ]
  }},

  "author_memory_pack": {{
    "strongest_lanes": ["结合作者记忆判断的强项"],
    "weakest_lanes": ["结合作者记忆判断的弱项"],
    "reusable_pattern_pack": [
      {{
        "title": "可复用模式名",
        "condition": "什么情况下可用",
        "action": "怎么用",
        "result": "预期效果",
        "confidence": 0.0
      }}
    ],
    "anti_pattern_blacklist": [
      {{
        "title": "禁用模式名",
        "condition": "什么情况下容易踩坑",
        "risk": "为什么危险",
        "fix_hint": "怎么避开"
      }}
    ],
    "author_bias_report": [
      {{
        "bias_name": "可能偏差",
        "impact": "对本题材的影响",
        "mitigation": "对冲方式"
      }}
    ]
  }},

  "route_decision_pack": {{
    "content_lane": "保底爆款|上升混搭|创新精品",
    "novel_lane": "男频|女频|现实向|幻想向|悬疑向|混合向",
    "form_lane": "长篇连载|中篇精品|短篇强爽|系列单元|试验型",
    "route_confidence": 0.0,
    "decision_rationale": "为什么走这条小说路线",
    "why_not_others": [
      "为什么不走其他路线"
    ],
    "forbidden_cliche_list": [
      "本题材必须避开的套路"
    ],
    "production_burden_estimate": {{
      "level": "low|medium|high",
      "reason": "连载生产负担原因"
    }}
  }},

  "concept_arena_pack": {{
    "concept_branches": [
      {{
        "branch_id": "A",
        "title": "分支名",
        "one_line_pitch": "一句话卖点",
        "reader_promise": "读者承诺",
        "core_conflict": "核心冲突",
        "protagonist_engine": "主角持续行动发动机",
        "antagonist_pressure": "持续压力来源",
        "first_3_chapters_hook": "前三章主要钩子",
        "long_serial_engine": "能支撑长线连载的机制",
        "risk": "最大风险",
        "scorecard": {{
          "platform_fit": 0,
          "reader_pull": 0,
          "novelty": 0,
          "clarity": 0,
          "hook_density": 0,
          "serial_sustainability": 0,
          "rights_risk_reverse_score": 0,
          "total_score": 0
        }}
      }}
    ],
    "winner_branch_id": "A",
    "runner_up_branch_id": "B",
    "kill_branch_id": "C",
    "kill_reason": "被淘汰原因"
  }},

  "narrative_seed_pack": {{
    "winner_branch": {{
      "branch_id": "A",
      "title": "优胜方案名",
      "one_line_pitch": "一句话卖点",
      "core_reader_hook": "最核心追读钩子"
    }},
    "narrative_graph_v1": {{
      "protagonist": {{
        "name_placeholder": "主角占位名",
        "desire": "主角想要什么",
        "wound": "主角缺口",
        "misbelief": "主角误信什么",
        "growth_direction": "成长方向"
      }},
      "antagonistic_force": {{
        "type": "人物|组织|制度|命运|环境|自我缺陷",
        "pressure": "如何持续施压"
      }},
      "core_secret": "推动追读的核心秘密",
      "conflict_nodes": [
        {{"node": "冲突节点", "function": "它在连载中的作用"}}
      ],
      "payoff_nodes": [
        {{"node": "兑现节点", "expected_chapter": 0, "payoff_type": "爽点|情绪|真相|关系"}}
      ]
    }},
    "knowledge_state_map": [
      {{
        "chapter_range": "1-3",
        "reader_knows": ["读者知道什么"],
        "protagonist_knows": ["主角知道什么"],
        "misbeliefs": ["谁误以为什么"],
        "information_gap_usage": "如何制造追读"
      }}
    ],
    "emotional_debt_ledger": [
      {{
        "chapter_range": "1-3",
        "debt_created": "建立什么情绪负债",
        "partial_payoff": "局部兑现什么",
        "new_debt_seeded": "新埋什么债"
      }}
    ],
    "chapter_hook_chain": [
      {{
        "chapter": 1,
        "hook_type": "冲突启动|身份揭示|代价压迫|反转|真相缺口|爽点兑现",
        "hook_text": "该章结尾追读钩子，不超过60字",
        "reader_question": "读者会想问什么"
      }},
      {{
        "chapter": 2,
        "hook_type": "冲突升级",
        "hook_text": "不超过60字",
        "reader_question": "读者会想问什么"
      }},
      {{
        "chapter": 3,
        "hook_type": "承诺兑现+新债",
        "hook_text": "不超过60字",
        "reader_question": "读者会想问什么"
      }},
      {{
        "chapter": 10,
        "hook_type": "阶段反转",
        "hook_text": "不超过60字",
        "reader_question": "读者会想问什么"
      }},
      {{
        "chapter": 30,
        "hook_type": "长线升级",
        "hook_text": "不超过60字",
        "reader_question": "读者会想问什么"
      }}
    ],
    "writing_brief_v1": {{
      "opening_strategy": "前三章怎么开",
      "pacing_rule": "章节节奏规则",
      "scene_rule": "场景写法规则",
      "dialogue_rule": "对话写法规则",
      "forbidden_moves": ["正文生产时禁止动作"],
      "must_keep_promises": ["必须兑现的读者承诺"]
    }}
  }},

  "risk_pack": {{
    "rights_risk_pack": [
      {{
        "category": "IP|肖像|真实人物影射|设定撞车|平台敏感",
        "level": "low|medium|high|critical",
        "description": "风险描述",
        "mitigation": "规避方式"
      }}
    ],
    "fatal_flaw_list": [
      {{
        "category": "题材|人设|节奏|爽点|追读|合规|同质化",
        "severity": "low|medium|high|critical",
        "description": "致命问题",
        "fix_hint": "怎么修"
      }}
    ],
    "adversarial_report": {{
      "summary": "对抗验证总评",
      "old_wine_new_bottle_risk": 0,
      "reader_dropoff_risk": 0,
      "character_logic_risk": 0,
      "serial_collapse_risk": 0,
      "rights_risk": 0,
      "recommendations": ["具体修订建议"]
    }},
    "rewrite_or_kill_decision": "pass|rewrite|kill",
    "must_fix_before_prod": ["进入正文生产前必须修复的问题"]
  }},

  "preflight_passport": {{
    "pass": false,
    "decision": "pass|rewrite|kill",
    "total_score": 0,
    "gate_scores": {{
      "信源净化": 0,
      "市场雷达": 0,
      "作者记忆": 0,
      "读者先验": 0,
      "小说赛道分流": 0,
      "概念竞技": 0,
      "叙事图谱": 0,
      "对抗验证": 0,
      "生产准入": 0
    }},
    "blocking_issues": ["阻断项"],
    "required_actions": ["下一步必做动作"],
    "expiry_days": 14,
    "signoff": {{
      "engine": "novel_preflight_orchestrator",
      "mode": "llm_driven",
      "issued_by": "LLM"
    }}
  }},

  "context_bundle_for_parser": {{
    "prompt_injection_payload": {{
      "system_rules": [
        "后续正文必须服从 narrative_seed_pack",
        "不得绕开 risk_pack 中的必修项",
        "前三章必须兑现 project_capsule.reader_promise"
      ],
      "writing_constraints": ["小说正文生产约束"],
      "forbidden_list": ["禁用套路"],
      "required_outputs": [
        "前三章详细大纲",
        "第1章正文",
        "章尾钩子自检",
        "读者承诺兑现检查"
      ]
    }},
    "token_budget_plan": {{
      "prehub_injection_chars": 5000,
      "rag_context_chars": 3000,
      "draft_chars": 12000
    }}
  }},

  "memory_candidate_pack": {{
    "should_stage": false,
    "reason": "本轮是否值得形成LTM候选",
    "candidates": [
      {{
        "memory_type": "pattern_success|pattern_failure|risk_alert|market_calibration|style_preference",
        "condition": "在什么条件下",
        "action": "采用什么策略",
        "result": "得到什么结果或预期",
        "scope": {{
          "platform": "{target_platform}",
          "topic": "{topic}",
          "content_lane": "路线"
        }},
        "candidate_confidence": 0.0,
        "evidence_refs": ["source_1"]
      }}
    ]
  }}
}}
""".strip()

    # ---------------------------------------------------------------------
    # JSON 解析
    # ---------------------------------------------------------------------

    def _parse_json_or_raise(self, raw: str) -> Dict[str, Any]:
        """提取并解析 JSON。"""
        # 1. 移除思考过程
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        # 2. 尝试从 Markdown 围栏提取
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if fence:
            raw = fence.group(1).strip()

        # 3. 贪婪匹配第一个 { 到最后一个 }
        obj_match = re.search(r"\{[\s\S]*\}", raw)
        if not obj_match:
            raise ValueError(f"未找到 JSON 对象。")

        text = obj_match.group()

        # 4. 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试“截断式”解析（解决 Extra data 问题）
            return self._attempt_progressive_parse(text)

    def _attempt_progressive_parse(self, text: str) -> Dict[str, Any]:
        """
        处理 Extra data 错误。
        通过逐个尝试可能的闭合括号位置来找到合法的 JSON。
        """
        # 寻找所有的 '}' 位置
        indices = [i for i, char in enumerate(text) if char == "}"]
        # 从后往前尝试（因为我们通常想要最完整的对象）
        for idx in reversed(indices):
            candidate = text[:idx + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        
        raise ValueError("截断式解析依然无法找到合法 JSON。")

    def _repair_json_with_llm(self, malformed_text: str, model_slot: str) -> Dict[str, Any]:
        """
        利用 LLM 对损坏的 JSON 进行结构性修复。
        这也是《改造方法.txt》中要求的韧性增强。
        """
        from scripts.outline_generator import get_model_credentials
        from core_engine.llm_client import LLMClient

        base_url, model_id, api_key = get_model_credentials(model_slot)
        client = LLMClient(api_key=api_key, base_url=base_url)

        system_prompt = "你是一个 JSON 修复专家。你的任务是修复一段损坏的小说立项 JSON 文本，确保其完全符合 JSON 规范。只输出修复后的 JSON，不要任何解释。"
        user_prompt = f"以下是一段损坏的 JSON，请修复它。如果是截断了，请补全或删除残缺字段：\n\n{malformed_text}"

        try:
            res = client.create_response(model_id, system_prompt, user_prompt)
            raw = getattr(res, "output_text", str(res))
            
            # 递归调用解析（不再尝试修复）
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if fence:
                raw = fence.group(1).strip()
            obj_match = re.search(r"\{[\s\S]*\}", raw)
            if obj_match:
                return json.loads(obj_match.group())
        except Exception as e:
            print(f"[Novel Preflight] LLM 自动修复失败: {e}")

        raise ValueError("LLM 自动修复 JSON 失败，无法继续流程。")

    # ---------------------------------------------------------------------
    # 工具
    # ---------------------------------------------------------------------

    def _today(self) -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()
