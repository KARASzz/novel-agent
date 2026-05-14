from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from pre_hub.pre_hub import PreHubOrchestrator
from pre_hub.schemas.pre_hub_models import ChapterProductionBundle, FormatLane


def _workspace_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_output_path(path_or_dir: str, default_name: str) -> str:
    if path_or_dir.lower().endswith((".json", ".md")):
        os.makedirs(os.path.dirname(os.path.abspath(path_or_dir)) or ".", exist_ok=True)
        return path_or_dir
    os.makedirs(path_or_dir, exist_ok=True)
    return os.path.join(path_or_dir, default_name)


def _default_report_paths(bundle: ChapterProductionBundle) -> tuple[str, str]:
    report_dir = os.path.join(_workspace_root(), "reports", "preflight")
    os.makedirs(report_dir, exist_ok=True)
    stamp = bundle.created_at.strftime("%Y%m%d_%H%M%S")
    base = f"Preflight_{bundle.project_id}_{stamp}"
    return os.path.join(report_dir, f"{base}.json"), os.path.join(report_dir, f"{base}.md")


def _write_json(bundle: ChapterProductionBundle, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundle.model_dump(mode="json"), f, ensure_ascii=False, indent=2)


def _build_markdown(bundle: ChapterProductionBundle) -> str:
    capsule = bundle.project_capsule
    passport = bundle.preflight_passport
    route = bundle.route_decision
    risk = bundle.risk_pack
    market = bundle.market_context
    memory = bundle.author_memory

    lines = [
        "# 番茄小说前置立项报告",
        "",
        "## 项目信息",
        f"- 项目ID: {capsule.project_id}",
        f"- 标题: {capsule.project_title}",
        f"- 作者: {capsule.author_id}",
        f"- 章节形态: {capsule.preferred_format.label}",
        f"- 目标平台: {capsule.target_platform.value}",
        f"- 目标章节: {capsule.target_chapter_count} 章",
        f"- 单章字数: {capsule.target_chapter_words} 字",
        f"- 路由: {route.content_lane.value} / {route.format_lane.label}",
        "",
        "## 准入结果",
        f"- 状态: {'PASS' if passport.is_pass else 'FAIL'}",
        f"- 总分: {passport.total_score}/100",
        f"- 决策: {risk.rewrite_or_kill_decision.value}",
        f"- 过期时间: {passport.expiry_at.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 各关卡得分",
    ]
    lines.extend(f"- {gate}: {score}" for gate, score in passport.gate_scores.items())
    lines.extend(["", "## Fallback 状态"])
    if bundle.fallback_reasons:
        lines.extend(f"- {reason}" for reason in bundle.fallback_reasons)
    else:
        lines.append("- 无")
    lines.extend(["", "## 市场证据"])
    if market.source_confidence_map:
        for item in market.source_confidence_map[:8]:
            ref = item.evidence_refs[0] if item.evidence_refs else item.source_name
            lines.append(f"- {item.source_name} / {item.source_tier.value} / conf={item.confidence:.2f} / {ref}")
    else:
        lines.append("- 无可用证据")
    lines.extend(["", "## 本地项目知识参考"])
    if memory.reusable_pattern_pack or memory.anti_pattern_blacklist:
        for item in memory.reusable_pattern_pack[:3]:
            lines.append(f"- 可复用: {str(item.get('content', ''))[:160]}")
        for item in memory.anti_pattern_blacklist[:3]:
            lines.append(f"- 风险: {str(item.get('content', ''))[:160]}")
    else:
        lines.append("- 未召回可用本地项目知识")
    lines.extend(["", "## 必须修复项"])
    if passport.required_actions:
        lines.extend(f"- {item}" for item in passport.required_actions)
    else:
        lines.append("- 无")
    lines.extend(["", "## 流水线注入内容", "```text", bundle.to_injection_prompt(), "```"])
    return "\n".join(lines).strip() + "\n"


def _write_markdown(bundle: ChapterProductionBundle, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(_build_markdown(bundle))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="番茄小说前置立项中台 - 新书准入评审")
    parser.add_argument("topic", type=str, help="项目题材/关键词")
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["real", "ai", "mixed"],
        default="real",
        help="章节形态: real=正文连载型, ai=设定辅助型, mixed=混合增强型",
    )
    parser.add_argument("--author", type=str, default="default", help="作者ID")
    parser.add_argument("--no-rag", action="store_true", help="禁用 Brave/Tavily 搜索聚合，仅使用本地知识库")
    parser.add_argument("--output", "-o", type=str, help="额外保存 Markdown 报告到指定路径")
    parser.add_argument("--save-bundle", type=str, help="保存 ChapterProductionBundle JSON 到指定目录或文件")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    format_lane = {
        "real": FormatLane.REAL,
        "ai": FormatLane.AI,
        "mixed": FormatLane.MIXED,
    }[args.format]

    print(f"[Novel Preflight] topic={args.topic}, chapter_form={args.format}, author={args.author}")
    print("=" * 60)
    bundle = PreHubOrchestrator().run(
        topic=args.topic,
        format_lane=format_lane,
        author_id=args.author,
        use_rag=not args.no_rag,
    )

    passport = bundle.preflight_passport
    capsule = bundle.project_capsule
    print("\n" + "=" * 60)
    print("[NOVEL PREFLIGHT PASSPORT]")
    print("=" * 60)
    print(f"项目ID: {capsule.project_id}")
    print(f"项目标题: {capsule.project_title}")
    print(f"准入状态: {'[PASS] 通过' if passport.is_pass else '[FAIL] 拒绝'}")
    print(f"总分: {passport.total_score}/100")
    print(f"决策: {bundle.risk_pack.rewrite_or_kill_decision.value}")
    print(f"过期时间: {passport.expiry_at.strftime('%Y-%m-%d %H:%M')}")
    print("\n各关卡得分:")
    for gate, score in passport.gate_scores.items():
        bar = "#" * max(0, min(10, score // 10)) + "-" * max(0, 10 - score // 10)
        print(f"  {gate}: {bar} {score}")

    if bundle.fallback_reasons:
        print("\nFallback:")
        for reason in bundle.fallback_reasons:
            print(f"  - {reason}")

    if passport.required_actions:
        print("\n必须修复项:")
        for action in passport.required_actions:
            print(f"  - {action}")

    print("\n" + "=" * 60)
    print("[NOVEL CONTEXT BUNDLE] 注入摘要")
    print("=" * 60)
    prompt = bundle.to_injection_prompt()
    print(prompt[:700] + "..." if len(prompt) > 700 else prompt)

    default_json, default_md = _default_report_paths(bundle)
    _write_json(bundle, default_json)
    _write_markdown(bundle, default_md)
    print(f"\nJSON报告: {default_json}")
    print(f"Markdown报告: {default_md}")

    if args.save_bundle:
        bundle_path = _resolve_output_path(args.save_bundle, f"bundle_{capsule.project_id}.json")
        _write_json(bundle, bundle_path)
        print(f"Bundle已保存: {bundle_path}")

    if args.output:
        _write_markdown(bundle, args.output)
        print(f"额外报告已保存: {args.output}")

    print("\n" + "=" * 60)
    print("[SUCCESS] 项目通过准入，可以进入流水线。" if passport.is_pass else "[WARNING] 项目未通过准入。")
    return 0 if passport.is_pass else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
