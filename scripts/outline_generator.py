import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from core_engine.llm_client import LLMClient
from core_engine.config_loader import load_config

def _get_workspace() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_model_credentials(slot_name: str) -> tuple[str, str, str]:
    cfg = load_config()
    slots = cfg.get("models", {}).get("slots", {})
    slot_cfg = slots.get(slot_name, {})
    if not slot_cfg:
        raise ValueError(f"未找到模型槽位: {slot_name}")
    
    base_url = slot_cfg.get("base_url")
    model_id = slot_cfg.get("model_id")
    env_name = slot_cfg.get("api_key_env")
    
    if not base_url or not model_id or not env_name:
        raise ValueError(f"槽位 {slot_name} 配置不完整 (缺少 base_url, model_id 或 api_key_env)")
        
    api_key = os.getenv(env_name)
    if not api_key:
        raise ValueError(f"缺少环境变量: {env_name}")
        
    return base_url, model_id, api_key

def _get_latest_bundle(workspace: str, topic_or_id: Optional[str] = None) -> Dict[str, Any]:
    report_dir = Path(workspace) / "reports" / "preflight"
    if not report_dir.exists():
        raise FileNotFoundError("未找到立项报告目录。请先运行立项预跑。")
    
    candidates = list(report_dir.glob("Preflight_*.json"))
    if not candidates:
        raise FileNotFoundError("未找到任何立项 JSON 报告。请先运行立项预跑。")
    
    # Sort by modification time
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    with open(candidates[0], "r", encoding="utf-8") as f:
        return json.load(f)

def _build_injection_prompt(bundle: Dict[str, Any]) -> str:
    # A simplified reconstruction of bundle.to_injection_prompt()
    capsule = bundle.get("project_capsule", {})
    route = bundle.get("route_decision", {})
    lines = [
        f"项目ID: {capsule.get('project_id', '')}",
        f"标题: {capsule.get('project_title', '')}",
        f"目标字数: {capsule.get('target_chapter_words', 2000)}字/章",
        f"路线: {route.get('content_lane', '')}",
        "核心创意与故事看点:"
    ]
    lines.extend(route.get("core_selling_points", []))
    lines.append("市场证据与参考:")
    market = bundle.get("market_context", {})
    for item in market.get("source_confidence_map", []):
        lines.append(f"- {item.get('source_name', '')}: {item.get('evidence_refs', [])}")
    
    lines.append("避坑黑名单:")
    memory = bundle.get("author_memory", {})
    for item in memory.get("anti_pattern_blacklist", []):
        lines.append(f"- {item.get('content', '')}")
        
    return "\n".join(lines)

def generate_outline_and_setting(model_slot: str, topic: str = "") -> None:
    workspace = _get_workspace()
    base_url, model_id, api_key = get_model_credentials(model_slot)
    client = LLMClient(api_key=api_key, base_url=base_url)
    
    print("⏳ 正在读取最新的立项数据...")
    bundle = _get_latest_bundle(workspace)
    project_id = bundle.get("project_capsule", {}).get("project_id", "unknown_project")
    injection_prompt = _build_injection_prompt(bundle)
    
    outline_tmpl_path = Path(workspace) / "templates" / "webnovel_outline_template_v1.md"
    setting_tmpl_path = Path(workspace) / "templates" / "webnovel_setting_bible_template_v1.md"
    
    if not outline_tmpl_path.exists() or not setting_tmpl_path.exists():
        raise FileNotFoundError("缺失大纲或设定集模板，请检查 templates/ 目录。")
        
    outline_tmpl = outline_tmpl_path.read_text(encoding="utf-8")
    setting_tmpl = setting_tmpl_path.read_text(encoding="utf-8")
    
    # --------------------------
    # 1. 生成全书大纲
    # --------------------------
    print("\n🚀 [1/2] 正在生成全书大纲 (可能需要几分钟，请耐心等待)...")
    outline_sys_prompt = (
        "你是一个顶级的番茄小说责编兼主笔大纲设计师。你的任务是根据提供的《项目立项摘要》，严格按照给定的《大纲模板》填写全书大纲。\n"
        "【要求】\n"
        "1. 绝不改变模板原有的 Markdown 结构、标题级别或 YAML 块结构。\n"
        "2. 你需要将模板中的空字符串 `\"\"`、空数组 `[]` 以及 Markdown 表格中的留空区域全部根据题材创意填写完整。\n"
        "3. 保持文字干练，毒点和爽点必须符合番茄小说等新媒体网文的快节奏调性：核心看点前置、爽点外化、黄金三章直接切入冲突。\n"
        "4. 直接输出 Markdown 文本，不要包含任何多余的解释、开头问候或结尾总结。"
    )
    outline_user_prompt = f"【立项摘要】\n{injection_prompt}\n\n【全书大纲模板】\n{outline_tmpl}\n\n请直接输出填充完毕的完整大纲："
    
    outline_res = client.create_response(
        model=model_id,
        instructions=outline_sys_prompt,
        input_text=outline_user_prompt,
        temperature=0.7
    )
    outline_content = outline_res.output_text
    
    # 去除可能包含的 markdown 代码块包裹
    if outline_content.startswith("```markdown"):
        outline_content = outline_content[11:]
    if outline_content.startswith("```"):
        outline_content = outline_content[3:]
    if outline_content.endswith("```"):
        outline_content = outline_content[:-3]
    outline_content = outline_content.strip()
    
    out_dir = Path(workspace) / "novel_outputs" / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    outline_path = out_dir / "1_全书大纲.md"
    outline_path.write_text(outline_content, encoding="utf-8")
    print(f"✅ 大纲生成完成，已保存至: {outline_path}")
    
    # --------------------------
    # 2. 生成设定集
    # --------------------------
    print("\n🚀 [2/2] 正在基于大纲生成设定集...")
    setting_sys_prompt = (
        "你是一个顶级的番茄小说世界观架构师。你的任务是基于《项目立项摘要》与刚刚写好的《全书大纲》，严格按照《设定集模板》扩写并细化设定。\n"
        "【要求】\n"
        "1. 绝不改变模板原有的 Markdown 结构或 YAML 块。\n"
        "2. 设定必须以“推动冲突”为核心，不能做无效的百科全书式堆砌，每个设定的抛出必须能引发剧情涟漪。\n"
        "3. 直接输出 Markdown 文本，不要包含任何多余的开头或结尾总结。"
    )
    setting_user_prompt = f"【立项摘要】\n{injection_prompt}\n\n【已生成的大纲】\n{outline_content}\n\n【设定集模板】\n{setting_tmpl}\n\n请直接输出填充完毕的完整设定集："
    
    setting_res = client.create_response(
        model=model_id,
        instructions=setting_sys_prompt,
        input_text=setting_user_prompt,
        temperature=0.7
    )
    setting_content = setting_res.output_text
    
    if setting_content.startswith("```markdown"):
        setting_content = setting_content[11:]
    if setting_content.startswith("```"):
        setting_content = setting_content[3:]
    if setting_content.endswith("```"):
        setting_content = setting_content[:-3]
    setting_content = setting_content.strip()
    
    setting_path = out_dir / "2_全书设定集.md"
    setting_path.write_text(setting_content, encoding="utf-8")
    print(f"✅ 设定集生成完成，已保存至: {setting_path}")
    print("\n🎉 大纲与设定集全部生成完毕，已完成大纲中台任务，可随时进入章节生产线！")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.outline_generator <model_slot>")
        sys.exit(1)
    generate_outline_and_setting(sys.argv[1])
