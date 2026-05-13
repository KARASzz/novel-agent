import datetime
import json
import os
from collections import Counter
from typing import Dict, List

from core_engine.batch_processor import BatchProcessor, FileProcessResult
from core_engine.config_loader import load_config, resolve_model_config
from core_engine.packager import ProjectPackager


def _load_context_bundle(bundle_path: str) -> Dict[str, object]:
    with open(bundle_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("ContextBundle JSON root must be an object.")
    required = {"project_id", "project_capsule", "preflight_passport"}
    missing = sorted(required - set(payload.keys()))
    if missing:
        raise ValueError(f"Invalid ContextBundle, missing fields: {', '.join(missing)}")
    return payload


def _build_summary(results: List[FileProcessResult]) -> Dict[str, object]:
    total = len(results)
    processed_success = sum(1 for r in results if r.processed_success)
    processed_failed = total - processed_success
    quality_passed = sum(1 for r in results if r.validation_status == "passed")
    quality_failed = sum(1 for r in results if r.validation_status == "failed")
    quality_not_run = sum(1 for r in results if r.validation_status == "not_run")

    error_counter = Counter(r.error_type for r in results if r.error_type)
    quality_error_counter = Counter(r.quality_error_type for r in results if r.quality_error_type)
    avg_total_sec = (
        sum(r.timing.get("total_sec", 0.0) for r in results) / total if total else 0.0
    )

    return {
        "total_files": total,
        "processed_success": processed_success,
        "processed_failed": processed_failed,
        "quality_passed": quality_passed,
        "quality_failed": quality_failed,
        "quality_not_run": quality_not_run,
        "avg_total_sec": round(avg_total_sec, 4),
        "error_breakdown": dict(error_counter),
        "quality_error_breakdown": dict(quality_error_counter),
    }


def _build_markdown(
    results: List[FileProcessResult],
    summary: Dict[str, object],
    generated_at: str,
) -> str:
    lines: List[str] = []
    lines.append("# 红果剧本工业化流水线执行报告")
    lines.append("")
    lines.append(f"**生成时间**: {generated_at}")
    lines.append("**处理统计**: 成功 {0} / 失败 {1} / 总计 {2}".format(
        summary["processed_success"],
        summary["processed_failed"],
        summary["total_files"],
    ))
    lines.append("**质检统计**: 通过 {0} / 不通过 {1} / 未执行 {2}".format(
        summary["quality_passed"],
        summary["quality_failed"],
        summary["quality_not_run"],
    ))

    if summary["error_breakdown"]:
        lines.append(f"**系统处理异常分布**: `{summary['error_breakdown']}`")
    if summary["quality_error_breakdown"]:
        lines.append(f"**业务质检异常分布**: `{summary['quality_error_breakdown']}`")
    lines.append("")
    lines.append("---")

    for item in sorted(results, key=lambda x: x.filename):
        lines.append("")
        lines.append(f"## {item.filename}")
        lines.append(f"- 处理状态: {'成功' if item.processed_success else '失败'}")
        lines.append(f"- 质检结果: {'通过' if item.quality_passed else '不通过'}")
        lines.append(f"- 校验详情: `{item.validation_status}`")
        lines.append(f"- 阶段耗时: `{ {k: round(v, 3) for k, v in item.timing.items()} }`")
        lines.append(f"- 解析指标: `{item.parser_metrics}`")

        if item.validation_report:
            lines.append(f"- 最终质量评分: **{item.validation_report.format_score}**")
            if item.validation_report.errors:
                lines.append("- Errors:")
                for err in item.validation_report.errors:
                    lines.append(f"  - {err}")
            if item.validation_report.warnings:
                lines.append("- Warnings:")
                for wrn in item.validation_report.warnings:
                    lines.append(f"  - {wrn}")

        if item.error_type:
            lines.append(f"- 系统异常类型: `{item.error_type}`")
            lines.append(f"- 错误信息: {item.error_message}")
        if item.quality_error_type:
            lines.append(f"- 质检异常类型: `{item.quality_error_type}`")
            lines.append(f"- 质检信息: {item.quality_error_message}")

        lines.append("")
        lines.append("---")

    return "\n".join(lines).strip() + "\n"


def show_stats(config: dict):
    pipeline_cfg = config.get("pipeline", {})
    drafts_dir = pipeline_cfg.get("drafts_dir", "drafts")
    output_dir = pipeline_cfg.get("output_dir", "scripts_output")
    
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    abs_drafts = os.path.join(workspace_root, drafts_dir)
    abs_output = os.path.join(workspace_root, output_dir)
    
    print("\n" + "=" * 20 + " 流水线资产盘点 " + "=" * 20)
    if os.path.exists(abs_drafts):
        files = [f for f in os.listdir(abs_drafts) if f.endswith((".txt", ".md"))]
        print(f"待处理草草 (drafts/): {len(files)} 篇")
    
    if os.path.exists(abs_output):
        files = [f for f in os.listdir(abs_output) if f.endswith(".txt")]
        print(f"已生成成品 (scripts_output/): {len(files)} 篇")
    
    print("=" * 54 + "\n")


def main(no_cache: bool = False, bundle_path: str = None, model_slot: str = None) -> None:
    """
    红果剧本工业化流水线执行入口 - 满足高并发与高质量双重需求
    """
    print("=" * 60)
    print("红果剧本工业化流水线执行入口 - 自动化开始运行")
    print("=" * 60 + "\n")

    # 优先加载配置，确保后续所有组件共享同一个 config 实例以优化 I/O 与测试性
    config = load_config()
    if model_slot:
        config.setdefault("parser", {})["model_slot"] = model_slot
    pipeline_cfg = config.get("pipeline", {})
    model_cfg = resolve_model_config(config)
    api_key_env = str(model_cfg.get("api_key_env") or "selected model API key")

    if not os.getenv(api_key_env):
        print(f"[环境变量缺失] 请设置当前模型槽位的 API 密钥环境变量: {api_key_env}，否则无法调用 LLM 解析服务。")
        return

    if not model_cfg.get("base_url"):
        print(f"[模型配置缺失] 当前模型槽位 {model_cfg.get('slot_name')} 缺少 Base URL，请先在 config.yaml 中接入真实模型。")
        return

    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    drafts_dir = os.path.join(workspace_root, pipeline_cfg.get("drafts_dir", "drafts"))
    output_dir = os.path.join(workspace_root, pipeline_cfg.get("output_dir", "scripts_output"))
    reports_dir = os.path.join(workspace_root, pipeline_cfg.get("reports_dir", "reports"))
    context_bundle = None
    if bundle_path:
        context_bundle = _load_context_bundle(bundle_path)
        project_id = context_bundle.get("project_id")
        print(f"[PreHub] 已加载 ContextBundle: {project_id}")

    for directory in (drafts_dir, output_dir, reports_dir):
        os.makedirs(directory, exist_ok=True)

    max_workers = int(pipeline_cfg.get("max_workers", 3))
    processor = BatchProcessor(
        drafts_dir,
        output_dir,
        reports_dir,
        config=config,
        no_cache=no_cache,
        context_bundle=context_bundle,
    )
    results = processor.run_batch(max_workers=max_workers)

    if not results:
        print("\n未发现需要处理的文件。请在 drafts/ 目录下放置 .txt 或 .md 草稿。")
        return

    generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = _build_summary(results)
    markdown_report = _build_markdown(results, summary, generated_at)

    md_path = os.path.join(reports_dir, f"BatchReport_V3_{timestamp}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)

    if bool(pipeline_cfg.get("report_json", True)):
        json_payload = {
            "generated_at": generated_at,
            "summary": summary,
            "files": [item.to_summary_dict() for item in sorted(results, key=lambda x: x.filename)],
        }
        json_path = os.path.join(reports_dir, f"BatchReport_V3_{timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"自动化执行完成! 处理成功 {summary['processed_success']} / {summary['total_files']}，质检通过 {summary['quality_passed']} / {summary['total_files']}")
    print(f"生成的分析报告位于: {md_path}")
    
    if summary["processed_success"] > 0 and bool(pipeline_cfg.get("auto_package", False)):
        print("\n" + "-" * 30)
        print("检测到成功处理的剧本，正在根据配置触发自动打包分发流程...")
        packager = ProjectPackager(workspace_root)
        project_name = pipeline_cfg.get("project_name", "默认项目成品")
        genre = pipeline_cfg.get("genre", "短剧")
        author = pipeline_cfg.get("author", "AI编剧助手")
        
        packager.create_submission_package(
            project_name=project_name,
            genre=genre,
            author_name=author
        )
        print("-" * 30)

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
