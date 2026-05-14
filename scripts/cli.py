import argparse
import json
import os
from typing import Optional, Sequence


def _get_workspace() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_cache_manager(workspace: str):
    from core_engine.cache_manager import CacheManager

    cache_dir = os.path.join(workspace, ".cache", "parser_results")
    return CacheManager(cache_dir)


def _run_pipeline_command(
    no_cache: bool,
    bundle_path: Optional[str] = None,
    model_slot: Optional[str] = None,
) -> None:
    from core_engine.main_pipeline import main as run_pipeline

    run_pipeline(no_cache=no_cache, bundle_path=bundle_path, model_slot=model_slot)


def _show_stats_command() -> None:
    from core_engine.config_loader import load_config
    from core_engine.main_pipeline import show_stats

    show_stats(load_config())


def _clear_cache_command(filter_keyword: Optional[str]) -> int:
    cache_manager = _get_cache_manager(_get_workspace())
    return cache_manager.clear_cache(filter_keyword=filter_keyword)


def _package_command(project_name: str, genre: str, author_name: str) -> str:
    from core_engine.packager import ProjectPackager

    packager = ProjectPackager(_get_workspace())
    return packager.create_submission_package(
        project_name=project_name,
        genre=genre,
        author_name=author_name,
    )


def _new_book_command(
    topic: str,
    format_lane: str,
    author: str,
    no_rag: bool,
    output: Optional[str] = None,
    save_bundle: Optional[str] = None,
) -> int:
    from scripts.preflight import main as run_preflight

    argv = [topic, "--format", format_lane, "--author", author]
    if no_rag:
        argv.append("--no-rag")
    if output:
        argv.extend(["--output", output])
    if save_bundle:
        argv.extend(["--save-bundle", save_bundle])
    return run_preflight(argv)


def _next_chapter_command(
    title: str,
    chapter_index: int,
    project_id: str,
    previous_writeback: str,
    model_slot: Optional[str],
    output_root: str,
) -> int:
    from chapter_pipeline import ChapterOrchestrator, ChapterPipelineInput

    output = ChapterOrchestrator().run_mock_chapter(
        project_goal="番茄小说章节生产",
        chapter_input=ChapterPipelineInput(
            project_bundle={"project_id": project_id, "project_title": project_id},
            current_chapter=title,
            previous_chapter_writeback=previous_writeback,
            local_kb_reference="CLI: 使用本地知识库与搜索摘要占位。",
            search_summary="CLI: 搜索摘要占位。",
            chapter_index=chapter_index,
            model_slot=model_slot or "",
        ),
        output_root=output_root,
    )
    print(json.dumps(output.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _batch_chapters_command(
    titles: Sequence[str],
    project_id: str,
    start_index: int,
    previous_writeback: str,
    model_slot: Optional[str],
    output_root: str,
) -> int:
    from chapter_pipeline import ChapterOrchestrator

    outputs = ChapterOrchestrator().run_mock_batch(
        project_goal="番茄小说章节生产",
        chapter_titles=titles,
        project_bundle={"project_id": project_id, "project_title": project_id},
        initial_previous_writeback=previous_writeback,
        local_kb_reference="CLI: 使用本地知识库与搜索摘要占位。",
        search_summary="CLI: 搜索摘要占位。",
        output_root=output_root,
        model_slot=model_slot or "",
        start_index=start_index,
    )
    print(json.dumps([item.to_dict() for item in outputs], ensure_ascii=False, indent=2))
    return 0


def _search_diagnose_command(query: str, max_results: int) -> int:
    from rag_engine.search_aggregator import SearchAggregator

    payload = SearchAggregator(local_kb_dir=os.path.join(_get_workspace(), "knowledge_base")).search(
        query,
        max_results_per_source=max_results,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _model_diagnose_command() -> int:
    from core_engine.config_loader import load_config

    cfg = load_config()
    print(json.dumps(cfg.get("models", {}), ensure_ascii=False, indent=2))
    return 0


def _verify_rag_command() -> int:
    from scripts.verify_bailian_rag import verify

    return verify()


def _self_test_command(target: str, output_dir: Optional[str] = None) -> None:
    if target == "validator":
        from core_engine.validator import run_self_test

        run_self_test()
        return

    from core_engine.renderer import run_self_test

    run_self_test(output_dir=output_dir)


def _ltm_review_command(project_id: Optional[str], apply_approved: bool) -> int:
    from pre_hub.ltm import LTMGovernance

    governance = LTMGovernance(_get_workspace())
    candidates = governance.shadow.candidates(project_id=project_id)
    print(f"LTM候选数: {len(candidates)}")
    for candidate in candidates:
        print(
            f"- {candidate.candidate_id} "
            f"{candidate.memory_type.value} "
            f"state={candidate.review_state.value} "
            f"conf={candidate.candidate_confidence:.2f}"
        )
    if apply_approved:
        audits = governance.apply_approved(project_id=project_id)
        print(f"已处理云端写回审计事件: {len(audits)}")
        for audit in audits:
            print(f"- {audit.action.value} {audit.candidate_id}: {audit.reason}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="番茄小说一键制造机 CLI 控制台")
    subparsers = parser.add_subparsers(dest="command", help="选择子命令")

    new_book_parser = subparsers.add_parser("new-book", help="新书立项评审（番茄小说）")
    new_book_parser.add_argument("topic", help="项目题材/关键词")
    new_book_parser.add_argument(
        "--format",
        "-f",
        choices=["real", "ai", "mixed"],
        default="real",
        help="章节形态: real=正文连载型, ai=设定辅助型, mixed=混合增强型",
    )
    new_book_parser.add_argument("--author", default="default", help="作者ID")
    new_book_parser.add_argument("--no-rag", action="store_true", help="禁用 Brave/Tavily 搜索聚合，仅使用本地知识库")
    new_book_parser.add_argument("--output", "-o", help="额外保存 Markdown 报告到指定路径")
    new_book_parser.add_argument("--save-bundle", help="保存 ContextBundle JSON 到指定目录或文件")

    run_parser = subparsers.add_parser("run", help="启动番茄小说章节流水线处理 drafts/ 文件夹")
    run_parser.add_argument("--no-cache", action="store_true", help="忽略现有解析快照，强制重新调用 LLM")
    run_parser.add_argument("--bundle", help="前置立项 ContextBundle JSON 路径，用于注入新书上下文")
    run_parser.add_argument("--model-slot", help="选择 OpenAI Chat Completions 模型槽位，例如 model_slot_1")

    next_parser = subparsers.add_parser("next-chapter", help="生成下一章 mock 产物并写入 novel_outputs")
    next_parser.add_argument("title", help="当前章标题，例如 第一章：旧城来信")
    next_parser.add_argument("--chapter-index", type=int, default=1, help="章节序号")
    next_parser.add_argument("--project-id", default="cli_demo", help="项目ID/书名 slug")
    next_parser.add_argument("--previous-writeback", default="新书开局，无上一章回写。", help="上一章第9步回写")
    next_parser.add_argument("--model-slot", help="模型槽位")
    next_parser.add_argument("--output-root", default="novel_outputs", help="输出目录")

    batch_parser = subparsers.add_parser("batch-chapters", help="批量生成章节 mock 产物")
    batch_parser.add_argument("titles", nargs="+", help="章节标题列表")
    batch_parser.add_argument("--project-id", default="cli_demo", help="项目ID/书名 slug")
    batch_parser.add_argument("--start-index", type=int, default=1, help="起始章节序号")
    batch_parser.add_argument("--previous-writeback", default="新书开局，无上一章回写。", help="第一章前置回写")
    batch_parser.add_argument("--model-slot", help="模型槽位")
    batch_parser.add_argument("--output-root", default="novel_outputs", help="输出目录")

    search_parser = subparsers.add_parser("search-diagnose", help="搜索诊断：Brave/Tavily/本地知识库聚合")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("--max-results", type=int, default=2, help="每个来源最多返回条数")

    subparsers.add_parser("model-diagnose", help="模型诊断：查看 5 个 OpenAI Chat Completions 槽位")

    clear_parser = subparsers.add_parser("clear-cache", help="清理渲染缓存数据")
    clear_parser.add_argument("--filter", type=str, help="根据关键词筛选清理特定题材或章节快照")
    clear_parser.add_argument("--yes", action="store_true", help="跳过交互式确认，直接执行清理")

    subparsers.add_parser("stats", help="查看当前项目统计数据与转换率")

    package_parser = subparsers.add_parser("package", help="将 scripts_output 中的章节产物封装为投稿/存稿包")
    package_parser.add_argument("--name", required=True, help="项目名/书名")
    package_parser.add_argument("--genre", required=True, help="题材或投稿赛道")
    package_parser.add_argument("--author", required=True, help="笔名或工作室名")

    export_parser = subparsers.add_parser("export-fanqie", help="导出番茄小说存稿包")
    export_parser.add_argument("--name", required=True, help="项目名/书名")
    export_parser.add_argument("--genre", required=True, help="题材或投稿赛道")
    export_parser.add_argument("--author", required=True, help="笔名或工作室名")

    subparsers.add_parser("verify-rag", help=argparse.SUPPRESS)

    self_test_parser = subparsers.add_parser("self-test", help="运行内置诊断自检")
    self_test_parser.add_argument("target", choices=["validator", "renderer"], help="选择要运行的自检目标")
    self_test_parser.add_argument("--output-dir", help="renderer 自检输出目录")

    ltm_parser = subparsers.add_parser("ltm-review", help=argparse.SUPPRESS)
    ltm_parser.add_argument("--project-id", help="只处理指定项目ID")
    ltm_parser.add_argument("--apply-approved", action="store_true", help="将已批准候选写回云端 LTM")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "new-book":
        return _new_book_command(
            topic=args.topic,
            format_lane=args.format,
            author=args.author,
            no_rag=args.no_rag,
            output=args.output,
            save_bundle=args.save_bundle,
        )

    if args.command == "run":
        _run_pipeline_command(
            no_cache=args.no_cache,
            bundle_path=args.bundle,
            model_slot=args.model_slot,
        )
        return 0

    if args.command == "next-chapter":
        return _next_chapter_command(
            title=args.title,
            chapter_index=args.chapter_index,
            project_id=args.project_id,
            previous_writeback=args.previous_writeback,
            model_slot=args.model_slot,
            output_root=args.output_root,
        )

    if args.command == "batch-chapters":
        return _batch_chapters_command(
            titles=args.titles,
            project_id=args.project_id,
            start_index=args.start_index,
            previous_writeback=args.previous_writeback,
            model_slot=args.model_slot,
            output_root=args.output_root,
        )

    if args.command == "search-diagnose":
        return _search_diagnose_command(query=args.query, max_results=args.max_results)

    if args.command == "model-diagnose":
        return _model_diagnose_command()

    if args.command == "stats":
        _show_stats_command()
        return 0

    if args.command == "clear-cache":
        if not args.yes:
            message = "确定要清理所有解析快照吗？"
            if args.filter:
                message = f"确定要清理包含关键词 '{args.filter}' 的缓存吗？"
            confirm = input(f"{message} (y/n): ")
            if confirm.lower() != "y":
                print("已取消缓存清理。")
                return 0

        count = _clear_cache_command(filter_keyword=args.filter)
        print(f"✅ 成功清理 {count} 条缓存快照！")
        return 0

    if args.command == "package":
        _package_command(
            project_name=args.name,
            genre=args.genre,
            author_name=args.author,
        )
        return 0

    if args.command == "export-fanqie":
        _package_command(
            project_name=args.name,
            genre=args.genre,
            author_name=args.author,
        )
        return 0

    if args.command == "verify-rag":
        return _verify_rag_command()

    if args.command == "self-test":
        _self_test_command(target=args.target, output_dir=args.output_dir)
        return 0

    if args.command == "ltm-review":
        return _ltm_review_command(
            project_id=args.project_id,
            apply_approved=args.apply_approved,
        )

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
