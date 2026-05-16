import argparse
import json
import os
import sys
from typing import Optional, Sequence

from core_engine.runtime_env import bootstrap_runtime_environment


def _configure_stdio() -> None:
    """Force UTF-8 output so Windows console commands don't crash on Unicode."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _get_workspace() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_default_model_slot() -> Optional[str]:
    """从配置层加载默认模型槽位"""
    try:
        from core_engine.config_loader import load_config
        cfg = load_config()
        default_slot = cfg.get("models", {}).get("default_slot")
        if default_slot:
            return default_slot
        llm_slot = cfg.get("llm", {}).get("model_slot")
        if llm_slot:
            return llm_slot
    except Exception:
        pass
    return None


def _get_cache_manager(workspace: str):
    from core_engine.cache_manager import CacheManager

    cache_dir = os.path.join(workspace, ".cache", "chapter_snapshots")
    return CacheManager(cache_dir)


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
    model_slot: Optional[str] = None,
    output: Optional[str] = None,
    save_bundle: Optional[str] = None,
) -> int:
    from scripts.preflight import main as run_preflight

    argv = [topic, "--format", format_lane, "--author", author]
    if model_slot:
        argv.extend(["--model-slot", model_slot])
    if no_rag:
        argv.append("--no-rag")
    if output:
        argv.extend(["--output", output])
    if save_bundle:
        argv.extend(["--save-bundle", save_bundle])
    return run_preflight(argv)


def _full_flow_command(
    topic: str,
    format_lane: str,
    author: str,
    no_rag: bool,
    model_slot: str,
) -> int:
    exit_code = _new_book_command(
        topic=topic,
        format_lane=format_lane,
        author=author,
        no_rag=no_rag,
        model_slot=model_slot,
    )
    if exit_code != 0:
        print("❌ 前置立项未通过，终止后续大纲生成。")
        return exit_code
        
    print("\n✅ 前置立项通过，即将进入大纲中台...")
    from scripts.outline_generator import generate_outline_and_setting
    try:
        generate_outline_and_setting(model_slot=model_slot, topic=topic)
    except Exception as e:
        print(f"❌ 大纲与设定集生成失败: {e}")
        return 1
    return 0


def _next_chapter_command(
    title: str,
    chapter_index: int,
    project_id: str,
    previous_writeback: str,
    model_slot: Optional[str],
    output_root: str,
    production: bool = False,
) -> int:
    from chapter_pipeline import ChapterOrchestrator, ChapterPipelineInput
    from scripts.outline_generator import get_model_credentials
    from core_engine.llm_client import LLMClient

    orchestrator = ChapterOrchestrator()
    chapter_input = ChapterPipelineInput(
        project_bundle={"project_id": project_id, "project_title": project_id},
        current_chapter=title,
        previous_chapter_writeback=previous_writeback,
        local_kb_reference="CLI: 使用本地知识库与搜索摘要占位。",
        search_summary="CLI: 搜索摘要占位。",
        chapter_index=chapter_index,
        model_slot=model_slot or "",
    )

    if production and not model_slot:
        print("❌ 章节生产必须指定 --model-slot（模板模式已废弃）")
        return 1

    if production:
        try:
            base_url, model_id, api_key = get_model_credentials(model_slot)
            client = LLMClient(api_key=api_key, base_url=base_url)
            orchestrator.llm_client = client
            output = orchestrator.run_chapter(
                project_goal="番茄小说章节生产",
                chapter_input=chapter_input,
                model_id=model_id,
                output_root=output_root,
            )
        except Exception as e:
            print(f"❌ 章节生产失败: {e}")
            return 1
    else:
        print("❌ 章节生产必须启用 --production 模式")
        print("   示例: python3 -m scripts.cli next-chapter 第一章 --production --model-slot model_slot_1")
        return 1

    print(json.dumps(output.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _batch_chapters_command(
    titles: Sequence[str],
    project_id: str,
    start_index: int,
    previous_writeback: str,
    model_slot: Optional[str],
    output_root: str,
    production: bool = False,
) -> int:
    from chapter_pipeline import ChapterOrchestrator
    from scripts.outline_generator import get_model_credentials
    from core_engine.llm_client import LLMClient

    orchestrator = ChapterOrchestrator()
    if production:
        if not model_slot:
            print("❌ 批量生产模式必须指定 --model-slot")
            return 1
        try:
            base_url, model_id, api_key = get_model_credentials(model_slot)
            orchestrator.llm_client = LLMClient(api_key=api_key, base_url=base_url)
            outputs = orchestrator.run_batch(
                project_goal="番茄小说批量生产",
                chapter_titles=titles,
                model_id=model_id,
                project_bundle={"project_id": project_id, "project_title": project_id},
                initial_previous_writeback=previous_writeback,
                local_kb_reference="CLI: 批量生产模式下由 Orchestrator 内部维护 RAG。",
                search_summary="CLI: 批量生产模式下由 Orchestrator 内部维护搜索。",
                output_root=output_root,
                start_index=start_index,
            )
        except Exception as e:
            print(f"❌ 批量生产失败: {e}")
            return 1
    else:
        print("❌ 批量章节生产必须启用 --production 模式并指定 --model-slot")
        print("   示例: python3 -m scripts.cli batch-chapters 第一章 第二章 --production --model-slot model_slot_1")
        return 1
    print(json.dumps([item.to_dict() for item in outputs], ensure_ascii=False, indent=2))
    return 0


def _search_diagnose_command(query: str, max_results: int) -> int:
    bootstrap_runtime_environment()
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


def _self_test_command(target: str) -> None:
    if target != "validator":
        raise ValueError(f"未知自检目标: {target}")

    from core_engine.validator import run_self_test

    run_self_test()


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
    new_book_parser.add_argument("--model-slot", help="模型槽位，用于动态生成剧情钩子（可省略，将从配置层读取默认值）")

    full_flow_parser = subparsers.add_parser("full-flow", help="一键立项并全自动生成大纲与设定集")
    full_flow_parser.add_argument("topic", help="项目题材/关键词")
    full_flow_parser.add_argument(
        "--format",
        "-f",
        choices=["real", "ai", "mixed"],
        default="real",
        help="章节形态: real=正文连载型, ai=设定辅助型, mixed=混合增强型",
    )
    full_flow_parser.add_argument("--author", default="default", help="作者ID")
    full_flow_parser.add_argument("--no-rag", action="store_true", help="禁用搜索聚合，仅使用本地知识库")
    full_flow_parser.add_argument("--model-slot", required=True, help="模型槽位，用于生成大纲")

    next_parser = subparsers.add_parser("next-chapter", help="生成下一章章节产物并写入 novel_outputs")
    next_parser.add_argument("title", help="当前章标题，例如 第一章：旧城来信")
    next_parser.add_argument("--chapter-index", type=int, default=1, help="章节序号")
    next_parser.add_argument("--project-id", default="console_demo", help="项目ID")
    next_parser.add_argument("--previous-writeback", default="", help="上一章回写")
    next_parser.add_argument("--model-slot", help="模型槽位")
    next_parser.add_argument("--output-root", default="novel_outputs", help="输出根目录")
    next_parser.add_argument("--production", action="store_true", help="启用真实模型生产")

    batch_parser = subparsers.add_parser("batch-chapters", help="批量生成章节产物")
    batch_parser.add_argument("titles", nargs="+", help="章节标题列表")
    batch_parser.add_argument("--project-id", default="cli_demo", help="项目ID/书名 slug")
    batch_parser.add_argument("--start-index", type=int, default=1, help="起始章节序号")
    batch_parser.add_argument("--previous-writeback", default="新书开局，无上一章回写。", help="第一章前置回写")
    batch_parser.add_argument("--model-slot", help="模型槽位")
    batch_parser.add_argument("--output-root", default="novel_outputs", help="输出目录")
    batch_parser.add_argument("--production", action="store_true", help="启用真实模型生产")

    search_parser = subparsers.add_parser("search-diagnose", help="搜索诊断：Brave/Tavily/本地知识库聚合")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("--max-results", type=int, default=2, help="每个来源最多返回条数")

    subparsers.add_parser("model-diagnose", help="模型诊断：查看 5 个 OpenAI Chat Completions 槽位")

    clear_parser = subparsers.add_parser("clear-cache", help="清理章节生产缓存数据")
    clear_parser.add_argument("--filter", type=str, help="根据关键词筛选清理特定题材或章节快照")
    clear_parser.add_argument("--yes", action="store_true", help="跳过交互式确认，直接执行清理")

    package_parser = subparsers.add_parser("package", help="将 novel_outputs 中的章节产物封装为投稿/存稿包")
    package_parser.add_argument("--name", required=True, help="项目名/书名")
    package_parser.add_argument("--genre", required=True, help="题材或投稿赛道")
    package_parser.add_argument("--author", required=True, help="笔名或工作室名")

    export_parser = subparsers.add_parser("export-fanqie", help="导出番茄小说存稿包")
    export_parser.add_argument("--name", required=True, help="项目名/书名")
    export_parser.add_argument("--genre", required=True, help="题材或投稿赛道")
    export_parser.add_argument("--author", required=True, help="笔名或工作室名")

    subparsers.add_parser("verify-rag", help=argparse.SUPPRESS)

    self_test_parser = subparsers.add_parser("self-test", help="运行内置诊断自检")
    self_test_parser.add_argument("target", choices=["validator"], help="选择要运行的自检目标")

    ltm_parser = subparsers.add_parser("ltm-review", help=argparse.SUPPRESS)
    ltm_parser.add_argument("--project-id", help="只处理指定项目ID")
    ltm_parser.add_argument("--apply-approved", action="store_true", help="将已批准候选写回云端 LTM")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "new-book":
        model_slot = getattr(args, "model_slot", None)
        # 对于 new-book，model_slot 可以省略（会从配置层读取默认值）
        return _new_book_command(
            topic=args.topic,
            format_lane=args.format,
            author=args.author,
            no_rag=args.no_rag,
            model_slot=model_slot,
            output=args.output,
            save_bundle=args.save_bundle,
        )

    if args.command == "full-flow":
        return _full_flow_command(
            topic=args.topic,
            format_lane=args.format,
            author=args.author,
            no_rag=args.no_rag,
            model_slot=args.model_slot,
        )

    if args.command == "next-chapter":
        return _next_chapter_command(
            title=args.title,
            chapter_index=args.chapter_index,
            project_id=args.project_id,
            previous_writeback=args.previous_writeback,
            model_slot=args.model_slot,
            output_root=args.output_root,
            production=args.production,
        )

    if args.command == "batch-chapters":
        return _batch_chapters_command(
            titles=args.titles,
            project_id=args.project_id,
            start_index=args.start_index,
            previous_writeback=args.previous_writeback,
            model_slot=args.model_slot,
            output_root=args.output_root,
            production=args.production,
        )

    if args.command == "search-diagnose":
        return _search_diagnose_command(query=args.query, max_results=args.max_results)

    if args.command == "model-diagnose":
        return _model_diagnose_command()

    if args.command == "clear-cache":
        if not args.yes:
            message = "确定要清理所有章节生产缓存快照吗？"
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
        _self_test_command(target=args.target)
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
