import argparse
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

    run_parser = subparsers.add_parser("run", help="启动章节流水线处理 drafts/ 文件夹")
    run_parser.add_argument("--no-cache", action="store_true", help="忽略现有解析快照，强制重新调用 LLM")
    run_parser.add_argument("--bundle", help="前置立项 ContextBundle JSON 路径，用于注入新书上下文")
    run_parser.add_argument("--model-slot", help="选择 OpenAI Chat Completions 模型槽位，例如 model_slot_1")

    clear_parser = subparsers.add_parser("clear-cache", help="清理渲染缓存数据")
    clear_parser.add_argument("--filter", type=str, help="根据关键词筛选清理特定题材或章节快照")
    clear_parser.add_argument("--yes", action="store_true", help="跳过交互式确认，直接执行清理")

    subparsers.add_parser("stats", help="查看当前项目统计数据与转换率")

    package_parser = subparsers.add_parser("package", help="将 scripts_output 中的章节产物封装为投稿/存稿包")
    package_parser.add_argument("--name", required=True, help="项目名/书名")
    package_parser.add_argument("--genre", required=True, help="题材或投稿赛道")
    package_parser.add_argument("--author", required=True, help="笔名或工作室名")

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

    if args.command == "run":
        _run_pipeline_command(
            no_cache=args.no_cache,
            bundle_path=args.bundle,
            model_slot=args.model_slot,
        )
        return 0

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
