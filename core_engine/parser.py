import hashlib
import json
import os
import random
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import (
    APIConnectionError as _APIConnectionError,
)
from openai import (
    APIStatusError as _APIStatusError,
)
from openai import (
    APITimeoutError as _APITimeoutError,
)
from core_engine.llm_client import LLMClient
from openai import (
    RateLimitError as _RateLimitError,
)

from core_engine.config_loader import load_config
from core_engine.logger import get_logger
from core_engine.schemas import Episode
from core_engine.cache_manager import CacheManager
from core_engine.utils import get_enabled_tools

logger = get_logger(__name__)

try:
    from rag_engine.retriever import LocalRetriever, HybridRetriever
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


ERROR_TIMEOUT = "timeout"
ERROR_RATE_LIMIT = "rate_limit"
ERROR_JSON_FORMAT = "json_format_error"
ERROR_MISSING_FIELDS = "missing_fields"
ERROR_API = "api_error"
ERROR_CONFIG = "config_error"
ERROR_UNKNOWN = "unknown_error"


class MissingFieldsError(Exception):
    def __init__(self, fields: List[str]):
        self.fields = fields
        super().__init__(f"Missing required fields: {', '.join(fields)}")


class RequestRateLimiter:
    """
    自适应速率限制器 (Adaptive Rate Limiter)
    基于 AIMD (加性增/乘性减) 算法，根据 API 429 响应动态调整当前并发请求频率。
    """
    def __init__(self, requests_per_second: float, min_rps: float = 0.2, max_rps: float = 20.0):
        self.rps = max(float(requests_per_second), min_rps)
        self.min_rps = min_rps
        self.max_rps = max(max_rps, self.rps)
        self._lock = threading.Lock()
        self._next_allowed = 0.0
        self._last_429_time = 0.0

    def wait(self) -> None:
        if self.rps <= 0:
            return

        with self._lock:
            now = time.monotonic()
            wait_seconds = max(0.0, self._next_allowed - now)
            self._next_allowed = max(now, self._next_allowed) + (1.0 / self.rps)

        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def report_error(self, error_type: str):
        """记录 429 错误并触发乘性减速 (MD)"""
        if error_type == "rate_limit":
            with self._lock:
                now = time.monotonic()
                if now - self._last_429_time > 2.0:
                    old_rps = self.rps
                    self.rps = max(self.min_rps, self.rps * 0.6)
                    self._last_429_time = now
                    logger.warning(f"⚠️ [RateLimit] 触发 429 限流响应，限制频率: {old_rps:.2f} -> {self.rps:.2f} RPS")

    def report_success(self):
        """记录成功并尝试加性提速 (AI)"""
        with self._lock:
            now = time.monotonic()
            if now - self._last_429_time > 15.0 and self.rps < self.max_rps:
                self.rps = min(self.max_rps, self.rps + 0.1)


@dataclass
class ParseResult:
    episode: Optional[Episode]
    is_success: bool
    error_type: Optional[str]
    error_message: Optional[str]
    attempts: int
    retries: int
    request_count: int
    duration_sec: float
    repaired_json: bool = False
    usage_input_tokens: Optional[int] = None
    usage_output_tokens: Optional[int] = None
    usage_total_tokens: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "is_success": self.is_success,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "attempts": self.attempts,
            "retries": self.retries,
            "request_count": self.request_count,
            "duration_sec": round(self.duration_sec, 4),
            "repaired_json": self.repaired_json,
            "usage": {
                "input_tokens": self.usage_input_tokens,
                "output_tokens": self.usage_output_tokens,
                "total_tokens": self.usage_total_tokens,
            },
        }


class DraftParser:
    """
    剧本草稿解析器 (核心智能引擎)
    职责：利用大语言模型将非结构化的剧本草稿转化为标准化的 SceneData JSON 模型。
    特性：支持 JSON Schema 强制规范约束、RAG 知识辅助增强、多级退避重试以及 JSON 容错修复逻辑。
    """

    PARSER_VERSION = "3.3"  # 缓存协议版本，用于 SHA-256 缓存哈希校验
    def __init__(
        self,
        config: Optional[dict] = None,
        no_cache: bool = False,
        rate_limiter: Optional[RequestRateLimiter] = None,
    ):
        """
        初始化解析器。建议从外部传入统一加载好的 config 实例以优化重复 I/O。
        """
        self.config = config if config else load_config()
        self.no_cache = no_cache
        parser_cfg = self.config.get("parser", {})
        retry_cfg = parser_cfg.get("retry", {})
        pipeline_cfg = self.config.get("pipeline", {})
        rate_limit_cfg = pipeline_cfg.get("rate_limit", {})

        self.api_key_env = parser_cfg.get("api_key_env", "DASHSCOPE_API_KEY")
        self.api_key = parser_cfg.get("api_key") or os.getenv(self.api_key_env)
        self.base_url = parser_cfg.get(
            "base_url",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.model = parser_cfg.get("model", "qwen-max")
        self.max_retries = int(parser_cfg.get("max_retries", 3))
        self.timeout = float(parser_cfg.get("timeout", 300))
        self.strict_validation = bool(parser_cfg.get("strict_validation", True))
        self.base_retry_delay_sec = float(retry_cfg.get("base_delay_sec", 1.0))
        self.max_retry_delay_sec = float(retry_cfg.get("max_delay_sec", 8.0))
        self.retry_jitter_sec = float(retry_cfg.get("jitter_sec", 0.25))

        self.tools_cfg = parser_cfg.get("tools", {})
        self.enable_thinking = bool(self.tools_cfg.get("enable_thinking", True))
        rag_cfg = self.config.get("rag", {})
        cache_cfg = self.config.get("cache", {})
        self.rag_top_k = int(rag_cfg.get("top_k", 2))
        self.cache_ttl_seconds = int(cache_cfg.get("parser_result_ttl_days", 180)) * 24 * 60 * 60

        self.rate_limiter: Optional[RequestRateLimiter] = rate_limiter
        requests_per_second = float(rate_limit_cfg.get("requests_per_second", 0))
        if self.rate_limiter is None and requests_per_second > 0:
            self.rate_limiter = RequestRateLimiter(requests_per_second)

        self._client: Optional[LLMClient] = None
        if self.api_key:
            self._client = LLMClient(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )

        workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(workspace, ".cache", "parser_results")
        self.cache_manager = CacheManager(cache_dir)
        
        self.enable_rag = bool(parser_cfg.get("enable_rag", False))

        prompt_path = os.path.join(
            os.path.dirname(__file__), "parser_prompts", "episode_parser_prompt.txt"
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        except FileNotFoundError:
            logger.warning("Prompt template file not found, fallback to default prompt.")
            self.prompt_template = (
                "Please parse the following draft into strict JSON:\n{{DRAFT_CONTENT}}"
            )

        self.retriever = None
        self.index_id = None
        if self.enable_rag and RAG_AVAILABLE:
            workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            kb_dir = os.path.join(workspace, "knowledge_base")
            rag_cfg = self.config.get("rag", {})
            rag_backend = rag_cfg.get("backend", "local")
            
            index_id_env = rag_cfg.get("index_id_env", "BAILIAN_INDEX_ID")
            self.index_id = os.environ.get(index_id_env)

            if rag_backend == "bailian":
                remote_retriever = None
                try:
                    from rag_engine.bailian_retriever import BailianRetriever
                    remote_retriever = BailianRetriever()
                except Exception as e:
                    logger.error("Failed to initialize BailianRetriever: %s", str(e))
                
                if os.path.isdir(kb_dir):
                    self.retriever = HybridRetriever(kb_dir, remote_retriever=remote_retriever)
            else:
                if os.path.isdir(kb_dir):
                    self.retriever = LocalRetriever(kb_dir)
                    self.retriever.build_index()

    def _build_cache_salt(self, context_bundle: Optional[Dict[str, Any]] = None) -> str:
        prompt_hash = hashlib.sha256(self.prompt_template.encode("utf-8")).hexdigest()
        bundle_hash = ""
        if context_bundle:
            bundle_seed = (
                context_bundle.get("integrity_hash")
                or context_bundle.get("bundle_id")
                or context_bundle.get("project_id")
                or json.dumps(context_bundle, ensure_ascii=False, sort_keys=True, default=str)
            )
            bundle_hash = hashlib.sha256(str(bundle_seed).encode("utf-8")).hexdigest()
        fingerprint_obj = {
            "model": self.model,
            "strict_validation": self.strict_validation,
            "enable_thinking": self.enable_thinking,
            "enable_rag": self.enable_rag,
            "rag_top_k": self.rag_top_k,
            "context_bundle": bundle_hash,
        }
        cfg_fingerprint = hashlib.sha256(
            json.dumps(fingerprint_obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return f"v{self.PARSER_VERSION}:{prompt_hash}:{cfg_fingerprint}"

    @staticmethod
    def _episode_json_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["episode_number", "title", "is_paywall", "scenes"],
            "additionalProperties": True,
            "properties": {
                "episode_number": {"type": "integer"},
                "title": {"type": "string"},
                "is_paywall": {"type": "boolean"},
                "core_conflict": {"type": ["string", "null"]},
                "hook": {"type": ["string", "null"]},
                "cliffhanger_type": {"type": ["string", "null"]},
                "estimated_duration_sec": {"type": ["integer", "null"]},
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "scene_id",
                            "time",
                            "location_type",
                            "location",
                            "characters",
                            "plots",
                        ],
                        "additionalProperties": True,
                        "properties": {
                            "scene_id": {"type": "string"},
                            "time": {"type": "string"},
                            "location_type": {"type": "string"},
                            "location": {"type": "string"},
                            "characters": {"type": "array", "items": {"type": "string"}},
                            "plots": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["type", "content", "is_cliffhanger"],
                                    "additionalProperties": True,
                                    "properties": {
                                        "type": {"type": "string"},
                                        "character": {"type": ["string", "null"]},
                                        "content": {"type": "string"},
                                        "emotion": {"type": ["string", "null"]},
                                        "duration_sec": {"type": ["integer", "null"]},
                                        "is_cliffhanger": {"type": "boolean"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def _clean_json_string(text: str) -> str:
        text = text.strip()
        match = re.search(r"```(?:json)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        return text

    @staticmethod
    def _extract_first_json_object(text: str) -> str:
        start = text.find("{")
        if start < 0:
            return text

        depth = 0
        in_string = False
        escaped = False
        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]
        return text[start:]

    @classmethod
    def _repair_json_string(cls, text: str) -> str:
        candidate = cls._extract_first_json_object(cls._clean_json_string(text))
        candidate = candidate.replace(chr(0x201c), chr(0x22)).replace(chr(0x201d), chr(0x22))
        candidate = candidate.replace(chr(0x2018), chr(0x27)).replace(chr(0x2019), chr(0x27))
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        return candidate.strip()


    def _build_bundle_prompt(self, context_bundle: Dict[str, Any]) -> str:
        lines = ["[PreHub Injection - Strictly Follow Constraints Below]"]

        capsule = context_bundle.get("project_capsule", {})
        if capsule:
            lines.append("")
            lines.append("## Project Background")
            lines.append(f"- ProjectID: {capsule.get('project_id', 'N/A')}")
            lines.append(f"- Title: {capsule.get('project_title', 'N/A')}")
            lines.append(f"- OneLiner: {capsule.get('one_line_premise', 'N/A')}")
            lines.append(f"- EmotionCore: {capsule.get('emotion_core', 'N/A')}")
            lines.append(f"- VisualCore: {capsule.get('visual_core', 'N/A')}")
            lines.append(f"- Platform: {capsule.get('target_platform', 'redfruit')}")
            fmt = capsule.get('preferred_format', {})
            if isinstance(fmt, dict):
                fmt_val = fmt.get('value', 'auto')
            else:
                fmt_val = str(fmt)
            lines.append(f"- Format: {fmt_val}")

        market = context_bundle.get("market_context", {})
        if market:
            lines.append("")
            lines.append("## Market Context")
            lines.append(f"- DataDate: {market.get('as_of_date', 'N/A')}")
            bs = market.get("bayesian_scores", {})
            if bs:
                lines.append(f"- BayesScore: surprise={bs.get('surprise_score', 0):.2f}, confusion={bs.get('confusion_score', 0):.2f}, integration={bs.get('integration_score', 0):.2f}")

        seed = context_bundle.get("narrative_seed", {})
        if seed:
            winner = seed.get("winner_branch", {})
            if winner:
                lines.append("")
                lines.append("## Route Decision")
                lines.append(f"- WinnerBranch: {winner.get('branch_description', 'N/A')}")
                lines.append(f"- PlatformFit: {winner.get('platform_fit', 0)}")
                lines.append(f"- HookDensity: {winner.get('hook_density', 0)}")

            constraints = seed.get("format_constraint", {})
            if constraints:
                forbidden = constraints.get("forbidden_cliche", [])
                if forbidden:
                    lines.append(f"- ForbiddenCliches: {', '.join(forbidden)}")

        risk = context_bundle.get("risk_pack", {})
        if risk:
            flags = risk.get("compliance_flags", [])
            if flags:
                lines.append("")
                lines.append("## Compliance Notes")
                for flag in flags:
                    lines.append(f"- {flag}")

            must_fix = risk.get("must_fix_before_prod", [])
            if must_fix:
                lines.append("")
                lines.append("## MustFixBeforeProduction")
                for mf in must_fix:
                    lines.append(f"- {mf}")

        passport = context_bundle.get("preflight_passport", {})
        if passport:
            lines.append("")
            is_pass = passport.get("is_pass", False)
            lines.append(f"## AdmissionStatus: {'PASS' if is_pass else 'FAIL'}")
            lines.append(f"- TotalScore: {passport.get('total_score', 0)}/100")

        lines.append("")
        lines.append("[End of PreHub Injection]")

        return "\n".join(lines)


    def _validate_required_fields(self, data: Dict[str, Any]) -> None:
        if not self.strict_validation:
            return

        missing: List[str] = []
        for field in ("episode_number", "title", "is_paywall", "scenes"):
            if field not in data:
                missing.append(field)

        scenes = data.get("scenes")
        if not isinstance(scenes, list):
            missing.append("scenes(list)")
            scenes = []

        for i, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                missing.append(f"scenes[{i}]")
                continue
            for field in ("scene_id", "time", "location_type", "location", "characters", "plots"):
                if field not in scene:
                    missing.append(f"scenes[{i}].{field}")
            plots = scene.get("plots", [])
            if isinstance(plots, list):
                for j, plot in enumerate(plots):
                    if not isinstance(plot, dict):
                        missing.append(f"scenes[{i}].plots[{j}]")
                        continue
                    for field in ("type", "content", "is_cliffhanger"):
                        if field not in plot:
                            missing.append(f"scenes[{i}].plots[{j}].{field}")

        if missing:
            raise MissingFieldsError(missing)

    @staticmethod
    def _extract_usage(response: Any) -> Dict[str, Optional[int]]:
        usage_obj = getattr(response, "usage", None)
        if usage_obj is None:
            return {"input_tokens": None, "output_tokens": None, "total_tokens": None}

        if isinstance(usage_obj, dict):
            usage = usage_obj
        elif hasattr(usage_obj, "model_dump"):
            usage = usage_obj.model_dump()
        elif hasattr(usage_obj, "__dict__"):
            usage = dict(usage_obj.__dict__)
        else:
            usage = {}

        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
        total_tokens = usage.get("total_tokens")
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    @staticmethod
    def _is_schema_mode_unsupported(exc: Exception) -> bool:
        msg = str(exc).lower()
        keywords = (
            "response_format",
            "json_schema",
            "text.format",
            "unknown field",
            "unsupported",
            "invalid parameter",
        )
        return any(word in msg for word in keywords)

    def _request_model(
        self,
        instructions: str,
        user_input: str,
        strict_mode: bool,
        request_timeout: Optional[float] = None,
    ) -> Any:
        """调用模型请求接口，返回 response 对象"""
        if self._client is None:
            raise RuntimeError(f"Missing API key in env: {self.api_key_env}")

        enabled_tools = get_enabled_tools(self.tools_cfg, self.index_id)

        if strict_mode:
            strict_kwargs = {
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "episode_schema",
                        "strict": True,
                        "schema": self._episode_json_schema(),
                    }
                }
            }
            try:
                return self._client.create_response(
                    instructions=instructions,
                    input_text=user_input,
                    model=self.model,
                    tools=enabled_tools,
                    enable_thinking=self.enable_thinking,
                    timeout=request_timeout,
                    **strict_kwargs
                )
            except Exception as exc:
                if self._is_schema_mode_unsupported(exc):
                    logger.warning("Strict schema mode unsupported, fallback to best-effort JSON mode.")
                else:
                    raise

        return self._client.create_response(
            instructions=instructions,
            input_text=user_input,
            model=self.model,
            tools=enabled_tools,
            enable_thinking=self.enable_thinking,
            timeout=request_timeout,
        )

    def _compute_backoff(self, attempt_index: int) -> float:
        base = self.base_retry_delay_sec * (2 ** attempt_index)
        bounded = min(base, self.max_retry_delay_sec)
        jitter = random.uniform(0.0, self.retry_jitter_sec) if self.retry_jitter_sec > 0 else 0.0
        return bounded + jitter

    @staticmethod
    def _classify_exception(exc: Exception) -> str:
        msg = str(exc).lower()
        if isinstance(exc, (TimeoutError, _APITimeoutError)) or "timeout" in msg:
            return ERROR_TIMEOUT
        if isinstance(exc, _RateLimitError) or "rate limit" in msg or "429" in msg:
            return ERROR_RATE_LIMIT
        if isinstance(exc, _APIConnectionError):
            return ERROR_TIMEOUT
        if isinstance(exc, _APIStatusError):
            if "429" in msg:
                return ERROR_RATE_LIMIT
            return ERROR_API
        if "api key" in msg or "unauthorized" in msg or "authentication" in msg:
            return ERROR_CONFIG
        return ERROR_UNKNOWN

    def parse_draft(
        self,
        draft_content: str,
        rag_query: Optional[str] = None,
        use_cache: bool = True,
        context_bundle: Optional[Dict[str, Any]] = None,
        total_timeout_sec: Optional[float] = None,
    ) -> ParseResult:
        """解析剧本草稿核心入口逻辑"""
        started = time.perf_counter()
        use_cache = bool(use_cache and not self.no_cache)
        
        if use_cache:
            salt = self._build_cache_salt(context_bundle=context_bundle)
            cached_data = self.cache_manager.get_cache(draft_content, salt=salt, rag_query=rag_query)
            if cached_data:
                logger.info("🚀 [Cache Hit] 发现有效缓存，跳过 LLM 调用")
                episode_obj = Episode.from_dict(cached_data)
                return ParseResult(
                    episode=episode_obj,
                    is_success=True,
                    error_type=None,
                    error_message=None,
                    attempts=1,
                    retries=0,
                    request_count=0,
                    duration_sec=time.perf_counter() - started,
                    repaired_json=False,
                    usage_input_tokens=0,
                    usage_output_tokens=0,
                    usage_total_tokens=0,
                )

        if self._client is None:
            return ParseResult(
                episode=None,
                is_success=False,
                error_type=ERROR_CONFIG,
                error_message=f"Missing API key env var: {self.api_key_env}",
                attempts=0,
                retries=0,
                request_count=0,
                duration_sec=time.perf_counter() - started,
            )

        # RAG 增强逻辑
        system_prompt = self.prompt_template
        use_builtin_rag = bool(self.tools_cfg.get("file_search", False))
        
        if self.retriever and not use_builtin_rag:
            match = re.search(r"^\s*\[RAG:\s*(.*?)\]", draft_content, re.IGNORECASE | re.MULTILINE)
            extracted_query = match.group(1).strip() if match else None
            
            default_query = self.config.get("rag", {}).get("default_query", "爆款短剧剧本编写原则与商业化禁忌")
            
            if extracted_query:
                query = rag_query or extracted_query
            else:
                title_match = re.match(r"^\s*(.+)", draft_content)
                first_line = title_match.group(1).strip()[:30] if title_match else draft_content[:30]
                query = rag_query or f"{first_line} {default_query}"
                
            rag_context = self.retriever.get_rag_context(query, top_k=self.rag_top_k)
            if "未检索到" not in rag_context:
                system_prompt = f"[业务约束与知识库参考 (RAG)]\n{rag_context}\n\n---\n\n{system_prompt}"
            fallback_reason = getattr(self.retriever, "last_fallback_reason", None)
            if fallback_reason:
                logger.info("[RAG Fallback] %s", fallback_reason)

        # Tavily 增强
        tavily_match = re.search(r"^\s*\[Tavily:\s*(.*?)\]", draft_content, re.IGNORECASE | re.MULTILINE)
        if tavily_match:
            try:
                from rag_engine.tavily_search import TavilySearcher
                t_query = tavily_match.group(1).strip()
                searcher = TavilySearcher()
                if searcher.api_key:
                    logger.info("🔍 [Tavily] 正在联网检索最新热点: [%s]", t_query)
                    t_results = searcher.search_hot_trends(t_query, max_results=3)
                    if t_results:
                        t_context = "\n\n".join([f"- 标题: {r.get('title')}\n  内容: {r.get('content')}" for r in t_results])
                        system_prompt = f"[联网热点参考 (Tavily)]\n基于用户提供的关键词 {t_query} 检索到的实时情报：\n{t_context}\n\n---\n\n{system_prompt}"
            except Exception as e:
                logger.warning("⚠️ Tavily 搜寻失败，但不中断主解析流程: %s", str(e))

        # ContextBundle 增强（来自前置决策中台）
        if context_bundle:
            bundle_prompt = self._build_bundle_prompt(context_bundle)
            if bundle_prompt:
                system_prompt = f"{bundle_prompt}\n\n---\n\n{system_prompt}"
                logger.info("[PreHub] ContextBundle injected into system prompt")

        last_error_type: Optional[str] = None
        last_error_message: Optional[str] = None
        repaired_json = False
        usage: Dict[str, Optional[int]] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        deadline = (started + total_timeout_sec) if total_timeout_sec else None

        # 重试循环
        for attempt in range(self.max_retries):
            if deadline is not None:
                remaining_budget = deadline - time.perf_counter()
                if remaining_budget <= 0:
                    return ParseResult(
                        episode=None,
                        is_success=False,
                        error_type=ERROR_TIMEOUT,
                        error_message="parser_total_timeout",
                        attempts=max(attempt, 1),
                        retries=max(attempt - 1, 0),
                        request_count=attempt,
                        duration_sec=time.perf_counter() - started,
                        repaired_json=repaired_json,
                        usage_input_tokens=usage["input_tokens"],
                        usage_output_tokens=usage["output_tokens"],
                        usage_total_tokens=usage["total_tokens"],
                    )

            if self.rate_limiter is not None:
                self.rate_limiter.wait()

            try:
                instructions = (
                    "You are a professional script parser for short dramas.\n"
                    "Please parse the provided script text into a structured JSON object based on the following rules:\n"
                    f"{system_prompt}\n\n"
                    "IMPORTANT: Return pure JSON ONLY. Do not include markdown fences or extra text."
                )
                user_input = f"### [待解析剧本草稿原文] ###\n{draft_content}"
                request_timeout = self.timeout
                if deadline is not None:
                    request_timeout = max(1.0, min(self.timeout, deadline - time.perf_counter()))

                response = self._request_model(
                    instructions,
                    user_input,
                    strict_mode=self.strict_validation,
                    request_timeout=request_timeout,
                )
                raw_content = getattr(response, "output_text", None)
                if not raw_content:
                    raise ValueError("Empty model output.")

                payload = self._clean_json_string(raw_content)
                try:
                    data_dict = json.loads(payload)
                except json.JSONDecodeError:
                    payload = self._repair_json_string(raw_content)
                    data_dict = json.loads(payload)
                    repaired_json = True

                self._validate_required_fields(data_dict)
                episode_obj = Episode.from_dict(data_dict)
                usage_update = self._extract_usage(response)
                usage.update({k: (v or 0) for k, v in usage_update.items()})

                if self.rate_limiter:
                    self.rate_limiter.report_success()

                if use_cache:
                    salt = self._build_cache_salt(context_bundle=context_bundle)
                    self.cache_manager.set_cache(
                        draft_content,
                        data_dict,
                        salt=salt,
                        rag_query=rag_query,
                        ttl_seconds=self.cache_ttl_seconds,
                    )

                return ParseResult(
                    episode=episode_obj,
                    is_success=True,
                    error_type=None,
                    error_message=None,
                    attempts=attempt + 1,
                    retries=attempt,
                    request_count=attempt + 1,
                    duration_sec=time.perf_counter() - started,
                    repaired_json=repaired_json,
                    usage_input_tokens=usage["input_tokens"],
                    usage_output_tokens=usage["output_tokens"],
                    usage_total_tokens=usage["total_tokens"],
                )
            except MissingFieldsError as exc:
                last_error_type = ERROR_MISSING_FIELDS
                last_error_message = str(exc)
            except json.JSONDecodeError as exc:
                last_error_type = ERROR_JSON_FORMAT
                last_error_message = str(exc)
            except Exception as exc:
                last_error_type = self._classify_exception(exc)
                last_error_message = str(exc)
                if self.rate_limiter:
                    self.rate_limiter.report_error(last_error_type)

            if attempt < self.max_retries - 1:
                wait_seconds = self._compute_backoff(attempt)
                if deadline is not None:
                    remaining_budget = deadline - time.perf_counter()
                    if remaining_budget <= 0:
                        break
                    wait_seconds = min(wait_seconds, max(0.0, remaining_budget))
                logger.warning(
                    "[Parser Retry %s/%s] type=%s wait=%.2fs err=%s",
                    attempt + 1, self.max_retries, last_error_type, wait_seconds, last_error_message,
                )
                if wait_seconds > 0:
                    time.sleep(wait_seconds)

        return ParseResult(
            episode=None,
            is_success=False,
            error_type=last_error_type or ERROR_UNKNOWN,
            error_message=last_error_message or "Unknown failure.",
            attempts=self.max_retries,
            retries=max(self.max_retries - 1, 0),
            request_count=self.max_retries,
            duration_sec=time.perf_counter() - started,
            repaired_json=repaired_json,
            usage_input_tokens=usage["input_tokens"],
            usage_output_tokens=usage["output_tokens"],
            usage_total_tokens=usage["total_tokens"],
        )
