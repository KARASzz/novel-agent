import glob
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from core_engine.logger import get_logger
from core_engine.parser import DraftParser, RequestRateLimiter
from core_engine.renderer import FormatRenderer
from core_engine.validator import FormatValidator, ValidationReport

logger = get_logger(__name__)

ERROR_FILE_IO = "file_io_error"
ERROR_RENDER = "render_error"
ERROR_SYSTEM = "system_error"
ERROR_BUSINESS_VALIDATION_FAILED = "business_validation_failed"

@dataclass
class FileProcessResult:
    filename: str
    input_path: str
    output_path: Optional[str]
    processed_success: bool
    validation_status: str  # passed / failed / not_run
    quality_passed: bool
    stage_status: Dict[str, str]
    error_type: Optional[str]
    error_message: Optional[str]
    quality_error_type: Optional[str] = None
    quality_error_message: Optional[str] = None
    timing: Dict[str, float] = field(default_factory=dict)
    parser_metrics: Dict[str, Any] = field(default_factory=dict)
    validation_report: Optional[ValidationReport] = None

    def to_summary_dict(self) -> Dict[str, Any]:
        payload = {
            "filename": self.filename,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "processed_success": self.processed_success,
            "validation_status": self.validation_status,
            "quality_passed": self.quality_passed,
            "stage_status": self.stage_status,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "quality_error_type": self.quality_error_type,
            "quality_error_message": self.quality_error_message,
            "timing": {k: round(v, 4) for k, v in self.timing.items()},
            "parser_metrics": self.parser_metrics,
        }
        if self.validation_report:
            payload["validation_report"] = asdict(self.validation_report)
        return payload

class BatchProcessor:
    """
    批处理流水线核心组件 (工厂流水线)
    职责：遍历 drafts 目录下所有的剧本草稿，串联 [读取 -> 智能解析 -> 商业质检 -> 格式渲染 -> 落盘输出] 全生命周期。
    特性：支持多线程并发处理，实现对几十集短剧的秒级工业流水线打包。
    """
    def __init__(
        self,
        drafts_dir: str,
        output_dir: str,
        reports_dir: str,
        config: dict,
        no_cache: bool = False,
        context_bundle: Optional[Dict[str, Any]] = None,
    ):
        self.drafts_dir = drafts_dir
        self.output_dir = output_dir
        self.reports_dir = reports_dir
        self.config = config
        self.context_bundle = context_bundle
        self.pipeline_cfg = self.config.get("pipeline", {})
        rate_limit_cfg = self.pipeline_cfg.get("rate_limit", {})
        requests_per_second = float(rate_limit_cfg.get("requests_per_second", 0) or 0)

        self.rate_limiter: Optional[RequestRateLimiter] = None
        if requests_per_second > 0:
            self.rate_limiter = RequestRateLimiter(requests_per_second)

        self.parser = DraftParser(
            config=self.config,
            no_cache=no_cache,
            rate_limiter=self.rate_limiter,
        )
        self.validator = FormatValidator(config=self.config)
        self.renderer = FormatRenderer()

        # 单文件处理超时（秒）。0 表示不限时。
        self.file_timeout_sec: float = float(
            self.pipeline_cfg.get("file_timeout_sec", 300) or 0
        ) or None  # type: ignore[assignment]

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

    def _base_result(self, file_path: str) -> FileProcessResult:
        return FileProcessResult(
            filename=os.path.basename(file_path),
            input_path=file_path,
            output_path=None,
            processed_success=False,
            validation_status="not_run",
            quality_passed=False,
            stage_status={
                "read": "pending",
                "parse": "pending",
                "validate": "pending",
                "render": "pending",
                "write": "pending",
            },
            error_type=None,
            error_message=None,
        )

    def _process_single_file(self, file_path: str) -> FileProcessResult:
        result = self._base_result(file_path)
        total_start = time.perf_counter()

        try:
            read_start = time.perf_counter()
            with open(file_path, "r", encoding="utf-8") as f:
                draft_content = f.read()
            result.stage_status["read"] = "success"
            result.timing["read_sec"] = time.perf_counter() - read_start
        except Exception as exc:
            result.stage_status["read"] = "failed"
            result.error_type = ERROR_FILE_IO
            result.error_message = str(exc)
            result.timing["total_sec"] = time.perf_counter() - total_start
            return result

        parse_start = time.perf_counter()
        parse_result = self.parser.parse_draft(
            draft_content,
            total_timeout_sec=self.file_timeout_sec,
            context_bundle=self.context_bundle,
        )
        result.timing["parse_sec"] = time.perf_counter() - parse_start
        result.parser_metrics = parse_result.to_dict()

        if not parse_result.is_success or parse_result.episode is None:
            result.stage_status["parse"] = "failed"
            result.stage_status["validate"] = "skipped"
            result.stage_status["render"] = "skipped"
            result.stage_status["write"] = "skipped"
            result.error_type = parse_result.error_type
            result.error_message = parse_result.error_message
            result.timing["total_sec"] = time.perf_counter() - total_start
            return result
        result.stage_status["parse"] = "success"

        if self.file_timeout_sec and (time.perf_counter() - total_start) > self.file_timeout_sec:
            result.stage_status["validate"] = "skipped"
            result.stage_status["render"] = "skipped"
            result.stage_status["write"] = "skipped"
            result.error_type = ERROR_SYSTEM
            result.error_message = "file_timeout"
            result.timing["total_sec"] = time.perf_counter() - total_start
            return result

        try:
            validate_start = time.perf_counter()
            # validate 和 render 无依赖，并行执行以节省时间
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_validate = executor.submit(self.validator.validate, parse_result.episode)
                future_render = executor.submit(
                    self.renderer.render_episode, asdict(parse_result.episode)
                )
                report = future_validate.result()
                rendered_text = future_render.result()
            result.timing["validate_sec"] = time.perf_counter() - validate_start
            result.timing["render_sec"] = 0  # 已合并到并行执行

            result.validation_report = report
            result.stage_status["validate"] = "success"
            result.stage_status["render"] = "success"

            if report.is_valid:
                result.validation_status = "passed"
                result.quality_passed = True
            else:
                result.validation_status = "failed"
                result.quality_passed = False
                result.quality_error_type = ERROR_BUSINESS_VALIDATION_FAILED
                if report.errors:
                    result.quality_error_message = "; ".join(report.errors[:3])
                elif report.warnings:
                    result.quality_error_message = "; ".join(report.warnings[:3])
        except Exception as exc:
            result.stage_status["validate"] = "failed"
            result.validation_status = "not_run"
            result.error_type = ERROR_SYSTEM
            result.error_message = f"validator failure: {exc}"
            result.stage_status["render"] = "skipped"
            result.stage_status["write"] = "skipped"
            result.timing["total_sec"] = time.perf_counter() - total_start
            return result

        try:
            out_filename = f"{os.path.splitext(result.filename)[0]}_成品剧本.txt"
            out_path = os.path.join(self.output_dir, out_filename)
            write_start = time.perf_counter()
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(rendered_text)
            result.timing["write_sec"] = time.perf_counter() - write_start
            result.stage_status["write"] = "success"
            result.output_path = out_path
            result.processed_success = True
        except Exception as exc:
            result.stage_status["render"] = "failed"
            result.stage_status["write"] = "skipped"
            result.error_type = ERROR_RENDER
            result.error_message = str(exc)
            result.processed_success = False

        result.timing["total_sec"] = time.perf_counter() - total_start
        return result

    def run_batch(self, max_workers: int = 3) -> List[FileProcessResult]:
        search_pattern = os.path.join(self.drafts_dir, "*.*")
        all_files = sorted([
            f for f in glob.glob(search_pattern)
            if f.endswith((".txt", ".md"))
        ])

        if not all_files:
            logger.warning("No draft files found under %s", self.drafts_dir)
            return []

        logger.info(
            "Batch start: %s files, max_workers=%s",
            len(all_files),
            max_workers,
        )
        first_pass_results: List[FileProcessResult] = []
        retry_files: List[str] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(self._process_single_file, f): f for f in all_files}

            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                filename = os.path.basename(file_path)
                try:
                    res = future.result()
                    first_pass_results.append(res)
                    if res.processed_success:
                        logger.info(
                            "[%s] processed=%s validation=%s",
                            filename,
                            res.processed_success,
                            res.validation_status,
                        )
                    else:
                        logger.error(
                            "[%s] failed type=%s msg=%s",
                            filename,
                            res.error_type,
                            res.error_message,
                        )
                        if res.error_type == ERROR_SYSTEM:
                            retry_files.append(file_path)
                except Exception as exc:
                    logger.exception("[%s] worker crashed: %s", filename, exc)
                    crashed = self._base_result(file_path)
                    crashed.stage_status.update(
                        {
                            "read": "failed",
                            "parse": "skipped",
                            "validate": "skipped",
                            "render": "skipped",
                            "write": "skipped",
                        }
                    )
                    crashed.error_type = ERROR_SYSTEM
                    crashed.error_message = f"worker crash: {exc}"
                    crashed.timing["total_sec"] = 0.0
                    first_pass_results.append(crashed)
                    retry_files.append(file_path)

        # --- 系统级失败：单次重试 ---
        retry_results: List[FileProcessResult] = []
        if retry_files:
            logger.info("开始重试 %d 个系统级失败文件 (单次)", len(retry_files))
            for file_path in retry_files:
                filename = os.path.basename(file_path)
                logger.info("[%s] 重试中...", filename)
                try:
                    res = self._process_single_file(file_path)
                    retry_results.append(res)
                    if res.processed_success:
                        logger.info("[%s] 重试成功", filename)
                    else:
                        logger.error("[%s] 重试仍失败 type=%s", filename, res.error_type)
                except Exception as exc:
                    logger.exception("[%s] 重试 worker crash: %s", filename, exc)
                    crashed = self._base_result(file_path)
                    crashed.error_type = ERROR_SYSTEM
                    crashed.error_message = f"retry crash: {exc}"
                    retry_results.append(crashed)

        # 合并：用重试结果替换原始失败记录
        if retry_results:
            retry_paths = {r.input_path for r in retry_results}
            results = [
                r for r in first_pass_results if r.input_path not in retry_paths
            ] + retry_results
        else:
            results = first_pass_results

        return results
