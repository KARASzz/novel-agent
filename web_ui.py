import json
import re
import traceback
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import subprocess
import uvicorn
import os
import sys
import asyncio
from typing import Any, Callable, Dict, List, Optional

from core_engine.config_loader import load_config, resolve_model_config
from core_engine.runtime_env import bootstrap_runtime_environment, describe_runtime_environment
from web_file_catalog import GeneratedFileCatalog

try:
    from fastapi.templating import Jinja2Templates
except ImportError:  # pragma: no cover - only used in dependency-incomplete test envs
    class _TemplateEnv:
        auto_reload = True
        cache: Dict[str, Any] = {}

    class Jinja2Templates:  # type: ignore[no-redef]
        def __init__(self, directory: str):
            self.directory = directory
            self.env = _TemplateEnv()

        def TemplateResponse(self, request: Request, name: str, context: Dict[str, Any]):
            return HTMLResponse(f"Jinja2 is required to render {name}.")

app = FastAPI(title="番茄小说一键制造机 - 控制台")

# 获取当前文件所在目录的绝对路径，以便正确加载模板文件
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "web_templates"))
try:
    templates.env.auto_reload = True
    templates.env.cache = {}
except AttributeError:  # pragma: no cover - fallback template shim
    pass

file_catalog = GeneratedFileCatalog(BASE_DIR)

REQUIRED_WEBNOVEL_TEMPLATES = (
    "webnovel_outline_template_v1.md",
    "webnovel_setting_bible_template_v1.md",
    "webnovel_orchestration_template_v1.md",
    "webnovel_volume_story_list_template_v1.md",
    "webnovel_chapter_construction_card_template_v1.md",
    "webnovel_handoff_gate_template_v1.md",
)

REMOVED_LEGACY_FLOW_FILES = (
    "core_engine/parser.py",
    "core_engine/batch_processor.py",
    "core_engine/renderer.py",
    "core_engine/main_pipeline.py",
    "core_engine/schemas.py",
    "core_engine/parser_prompts/chapter_parser_prompt.txt",
    "core_engine/parser_prompts/episode_parser_prompt.txt",
)

REQUIRED_RUNTIME_ENV_VARS = (
    "MINIMAX_API_KEY",
    "TAVILY_API_KEY",
    "BRAVE_SEARCH_API_KEY",
)

MODEL_COMMANDS = {
    "preflight",
    "full_flow",
    "produce_chapter",
    "batch_produce",
    "feed",
    "inspire",
}

SEARCH_COMMANDS = {"feed", "inspire"}


def _command_result(
    *,
    ok: bool,
    output: str = "",
    error: str = "",
    command: str = "",
    **extra: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "ok": ok,
        "output": output,
    }
    if command:
        payload["command"] = command
    if error:
        payload["error"] = error
    payload.update(extra)
    return payload


def _validate_model_command(command: str, selected_model_slot: str) -> Optional[Dict[str, Any]]:
    if command not in MODEL_COMMANDS:
        return None

    cfg = load_config()
    model_cfg = resolve_model_config(cfg, selected_model_slot or None)
    slot_name = str(model_cfg.get("slot_name") or selected_model_slot or "")
    base_url = str(model_cfg.get("base_url") or "").strip()
    model_id = str(model_cfg.get("model_id") or "").strip()
    api_key_env = str(model_cfg.get("api_key_env") or "").strip()
    bootstrap_runtime_environment(
        [name for name in (api_key_env, "TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY") if name]
    )

    missing_fields = [
        field
        for field, value in (
            ("base_url", base_url),
            ("model_id", model_id),
            ("api_key_env", api_key_env),
        )
        if not value
    ]
    missing_env: List[str] = []
    if api_key_env and not os.environ.get(api_key_env):
        missing_env.append(api_key_env)
    if command in SEARCH_COMMANDS and not os.environ.get("TAVILY_API_KEY"):
        missing_env.append("TAVILY_API_KEY")

    if missing_fields or missing_env:
        detail_parts = []
        if missing_fields:
            detail_parts.append("配置缺项: " + ", ".join(missing_fields))
        if missing_env:
            detail_parts.append("缺少环境变量: " + ", ".join(missing_env))
        detail_parts.append(f"当前槽位: {slot_name} -> {api_key_env or 'unknown_env'} -> {model_id or 'unknown_model'}")
        return _command_result(
            ok=False,
            command=command,
            error="; ".join(detail_parts),
            missing_fields=missing_fields,
            missing_env=missing_env,
            model_slot=slot_name,
            model_id=model_id,
            api_key_env=api_key_env,
        )

    return None


def _latest_execution_plan_path() -> Optional[Path]:
    output_root = Path(BASE_DIR) / "novel_outputs"
    if not output_root.exists():
        return None
    candidates = [path for path in output_root.rglob("execution_plan.json") if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _load_or_build_plan_snapshot() -> Dict[str, Any]:
    latest_plan = _latest_execution_plan_path()
    if latest_plan:
        try:
            return {
                "source": "latest_execution_plan",
                "source_label": "最近一次章节运行",
                "source_path": str(latest_plan),
                "plan": json.loads(latest_plan.read_text(encoding="utf-8")),
            }
        except (OSError, json.JSONDecodeError):
            pass

    from chapter_pipeline import ChapterOrchestrator

    plan = ChapterOrchestrator().build_plan(
        project_goal="番茄小说章节生产",
        current_chapter="第一章：控制台预览章",
        previous_chapter_script="控制台预览：上一章第9步回写占位。",
        project_bundle={"project_id": "console_preview", "project_title": "控制台预览"},
        local_kb_reference="控制台预览：本地知识库摘要占位。",
        search_summary="控制台预览：Brave/Tavily 搜索摘要占位。",
        chapter_index=1,
    )
    return {
        "source": "preview_plan",
        "source_label": "待执行预览计划",
        "source_path": "",
        "plan": plan.to_dict(),
    }


def _task_card(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_id": task.get("task_id", ""),
        "title": task.get("title", ""),
        "agent_level": task.get("agent_level", ""),
        "manager": task.get("manager", ""),
        "worker": task.get("worker") or "",
        "status": task.get("status", "pending"),
        "retry_count": task.get("retry_count", 0),
        "failure_reason": task.get("failure_reason") or "",
        "depends_on": task.get("depends_on", []),
        "execution_mode": task.get("execution_mode", "serial"),
        "can_run_parallel": bool(task.get("can_run_parallel", False)),
        "final_decision": task.get("final_decision") or "",
        "summary": str((task.get("output_payload") or {}).get("summary", "")),
        "content": str((task.get("output_payload") or {}).get("content", "")),
    }


def _diff_note(previous_content: str, current_content: str, round_name: str) -> str:
    if not current_content:
        return "待执行：本轮尚未产生产物。"
    if not previous_content:
        return f"本轮首次形成 {round_name} 迭代产物。"
    if previous_content == current_content:
        return f"本轮聚焦 {round_name}，但产物尚未体现显著文本差异。"
    return f"相对上一轮，本轮只处理 {round_name}，不混合改写其他五个要素。"


def _orchestrator_status_payload() -> Dict[str, Any]:
    from chapter_pipeline.orchestrator import DEFAULT_BEAT_GROUPS, DEFAULT_SIX_B_ROUNDS

    snapshot = _load_or_build_plan_snapshot()
    plan = snapshot["plan"]
    tasks: List[Dict[str, Any]] = [_task_card(task) for task in plan.get("tasks", [])]
    task_map = {task["task_id"]: task for task in tasks}
    ledger = dict(plan.get("ledger", {}))
    completed = list(ledger.get("completed", []))
    pending = list(ledger.get("pending", []))
    running = [task["task_id"] for task in tasks if task["status"] == "running"]
    failed = [task["task_id"] for task in tasks if task["status"] == "failed"]
    if running:
        current_task = running[0]
    elif pending:
        current_task = pending[0]
    elif completed:
        current_task = completed[-1]
    else:
        current_task = str(ledger.get("current_stage", "not_started"))

    agent_levels = ["CEO Agent", "Manager Agent", "Worker Agent"]
    agents = []
    for level in agent_levels:
        level_tasks = [task for task in tasks if task["agent_level"] == level]
        agents.append(
            {
                "level": level,
                "total": len(level_tasks),
                "completed": sum(1 for task in level_tasks if task["status"] == "completed"),
                "running": sum(1 for task in level_tasks if task["status"] == "running"),
                "failed": sum(1 for task in level_tasks if task["status"] == "failed"),
                "pending": sum(1 for task in level_tasks if task["status"] == "pending"),
                "tasks": level_tasks,
            }
        )

    # 动态获取节拍分组和迭代轮次
    current_six_b_rounds = plan.get("six_b_rounds") or list(DEFAULT_SIX_B_ROUNDS)
    
    # 从任务中提取实际的节拍分组
    actual_beat_groups = []
    for task_id in task_map:
        if task_id.startswith("stage_6a_beats_"):
            m = re.search(r"beats_(\d+)_(\d+)", task_id)
            if m:
                actual_beat_groups.append((int(m.group(1)), int(m.group(2))))
    actual_beat_groups.sort()
    if not actual_beat_groups:
        actual_beat_groups = list(DEFAULT_BEAT_GROUPS)

    stage6_groups = []
    for left, right in actual_beat_groups:
        group_id = f"beats_{left}_{right}"
        draft = task_map.get(f"stage_6a_{group_id}", {})
        draft_content = str(draft.get("content", ""))
        previous_content = draft_content
        rounds = []
        for round_index, round_name in enumerate(current_six_b_rounds, start=1):
            task = task_map.get(f"stage_6b_{group_id}_round_{round_index}", {})
            content = str(task.get("content", ""))
            rounds.append(
                {
                    "round_index": round_index,
                    "round_name": round_name,
                    "task_id": task.get("task_id", ""),
                    "status": task.get("status", "pending"),
                    "summary": task.get("summary", ""),
                    "content": content,
                    "diff_note": _diff_note(previous_content, content, round_name),
                }
            )
            if content:
                previous_content = content
        stage6_groups.append(
            {
                "label": f"{left}-{right}",
                "draft": draft,
                "rounds": rounds,
            }
        )

    ledger.update(
        {
            "completed_count": len(completed),
            "pending_count": len(pending),
            "running_count": len(running),
            "failed_count": len(failed),
            "current_task": current_task,
        }
    )
    return {
        "source": snapshot["source"],
        "source_label": snapshot["source_label"],
        "source_path": snapshot["source_path"],
        "ledger": ledger,
        "agents": agents,
        "stage6": {
            "beat_groups": stage6_groups,
            "six_b_rounds": list(current_six_b_rounds),
        },
    }


def _initialization_self_check_payload() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    errors: List[str] = []
    warnings: List[str] = []

    def add_check(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": detail})
        if status == "fail":
            errors.append(f"{name}: {detail}")
        elif status == "warning":
            warnings.append(f"{name}: {detail}")

    try:
        cfg = load_config()
        add_check("配置读取", "pass", "config.yaml 已成功加载。")
    except Exception as exc:
        return {
            "status": "fail",
            "title": "初始化自检失败",
            "summary": f"配置读取失败: {exc}",
            "checks": [{"name": "配置读取", "status": "fail", "detail": str(exc)}],
            "errors": [str(exc)],
            "warnings": [],
        }

    bootstrap_runtime_environment(REQUIRED_RUNTIME_ENV_VARS)
    runtime_env_status = describe_runtime_environment(REQUIRED_RUNTIME_ENV_VARS)
    missing_runtime_env = [item["name"] for item in runtime_env_status if item["status"] == "missing"]
    if missing_runtime_env:
        add_check("运行时环境变量", "fail", "缺失: " + ", ".join(missing_runtime_env))
    else:
        add_check("运行时环境变量", "pass", "MINIMAX_API_KEY、TAVILY_API_KEY、BRAVE_SEARCH_API_KEY 均可读取。")

    registry = cfg.get("models", {})
    slots = registry.get("slots", {}) if isinstance(registry.get("slots"), dict) else {}
    enabled_slots = [slot for slot, item in slots.items() if isinstance(item, dict) and item.get("enabled", True)]
    if slots:
        add_check("模型槽位", "pass", f"已发现 {len(slots)} 个槽位，启用 {len(enabled_slots)} 个。")
    else:
        add_check("模型槽位", "fail", "未发现 models.slots 配置。")
    for slot_name in enabled_slots:
        slot_cfg = slots.get(slot_name, {})
        env_name = str(slot_cfg.get("api_key_env") or "").strip()
        base_url = str(slot_cfg.get("base_url") or "").strip()
        model_id = str(slot_cfg.get("model_id") or "").strip()
        if not base_url or not model_id or not env_name:
            add_check(slot_name, "fail", "启用槽位缺少 base_url、model_id 或 api_key_env。")
        elif os.getenv(env_name):
            add_check(slot_name, "pass", f"{model_id} 已配置，环境变量 {env_name} 可读取。")
        else:
            add_check(slot_name, "warning", f"{model_id} 已配置，但当前进程未读取到环境变量 {env_name}。")

    template_dir = Path(BASE_DIR) / "templates"
    missing_templates = [name for name in REQUIRED_WEBNOVEL_TEMPLATES if not (template_dir / name).is_file()]
    if missing_templates:
        add_check("大纲中台模板", "fail", "缺失: " + ", ".join(missing_templates))
    else:
        add_check("大纲中台模板", "pass", "6 个 webnovel_* 模板齐备。")

    legacy_present = [path for path in REMOVED_LEGACY_FLOW_FILES if (Path(BASE_DIR) / path).exists()]
    if legacy_present:
        add_check("旧草稿清洗链路", "fail", "仍存在: " + ", ".join(legacy_present))
    else:
        add_check("旧草稿清洗链路", "pass", "旧 parser/batch/renderer/main_pipeline 文件未发现。")

    try:
        snapshot = _load_or_build_plan_snapshot()
        task_count = len(snapshot["plan"].get("tasks", []))
        add_check("九步编排初始化", "pass", f"{snapshot['source_label']} 可读取，任务数 {task_count}。")
    except Exception as exc:
        add_check("九步编排初始化", "fail", str(exc))

    try:
        from core_engine.validator import FanqieChapterValidator

        sample = (
            "第一章：旧站台的电话\n"
            "上一章留下的证据还在掌心发烫，林照刚踏进旧站台，就被债主的人堵在检票口。"
            "对方逼他交出名单，还当众夺走母亲留下的怀表。林照没有退，他反手把录音笔按开，"
            "让所有人都听见对方威胁孤儿院的证据。人群一下炸开，债主脸色铁青。"
            "林照完成反击，可电话突然响起，屏幕上只有一句话：真正的名单，在你父亲坟前。"
        )
        report = FanqieChapterValidator(min_words=80, max_words=1000).validate(sample)
        if report.is_valid:
            add_check("章节质检器", "pass", f"番茄章节质检器可用，样章评分 {report.score}。")
        else:
            add_check("章节质检器", "fail", "样章未通过: " + "; ".join(report.errors))
    except Exception as exc:
        add_check("章节质检器", "fail", str(exc))

    writable_targets = [Path(BASE_DIR) / "novel_outputs", Path(BASE_DIR) / "reports"]
    for target in writable_targets:
        try:
            target.mkdir(parents=True, exist_ok=True)
            probe = target / ".self_check_write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            add_check(f"目录写入 {target.name}", "pass", f"{target} 可写。")
        except Exception as exc:
            add_check(f"目录写入 {target.name}", "fail", str(exc))

    if errors:
        status = "fail"
        title = "初始化自检未通过"
        summary = f"{len(errors)} 项失败，{len(warnings)} 项警告。"
    elif warnings:
        status = "warning"
        title = "初始化自检完成，有警告"
        summary = f"核心链路可初始化，存在 {len(warnings)} 项警告。"
    else:
        status = "pass"
        title = "初始化自检通过"
        summary = "配置、模板、九步编排、质检器和输出目录均可用。"

    return {
        "status": status,
        "title": title,
        "summary": summary,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }


DASHBOARD_SECTIONS = [
    {
        "title": "立项与项目包",
        "tone": "module-preflight",
        "description": "前置立项、项目包和新书入口。",
        "commands": [
            {"id": "preflight", "label": "新书立项评审", "icon": "🧭"},
            {"id": "full_flow", "label": "一键立项预跑", "icon": "🧩"},
        ],
    },
    {
        "title": "工业化章节生产",
        "tone": "module-chapter",
        "description": "九步章节生产线与连续章节生产执行。",
        "commands": [
            {"id": "produce_chapter", "label": "生成下一章", "icon": "✍️"},
            {"id": "batch_produce", "label": "批量生成章节", "icon": "📚"},
        ],
    },
    {
        "title": "搜索与知识库",
        "tone": "module-knowledge",
        "description": "本地知识库、Tavily/Brave 搜索诊断与素材更新。",
        "commands": [
            {"id": "feed", "label": "本地知识库更新", "icon": "🌾"},
            {"id": "search_diag", "label": "搜索诊断", "icon": "🔎"},
            {"id": "inspire", "label": "灵感探针", "icon": "🛰️"},
        ],
    },
    {
        "title": "质检与导出",
        "tone": "module-export",
        "description": "章节质检、自检和番茄小说存稿包导出。",
        "commands": [
            {"id": "diag_validator", "label": "番茄章节质检自检", "icon": "🧪"},
            {"id": "export_fanqie", "label": "导出番茄存稿", "icon": "📦"},
        ],
    },
    {
        "title": "系统工具",
        "tone": "module-system",
        "description": "缓存、模型诊断和控制台进程管理。",
        "commands": [
            {"id": "init_self_check", "label": "一键初始化自检", "icon": "🧪"},
            {"id": "model_diag", "label": "模型诊断", "icon": "🧬"},
            {"id": "cache", "label": "清理缓存", "icon": "🧹"},
            {"id": "exit", "label": "关闭网页控制台", "icon": "🚪", "danger": True},
        ],
    },
]

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "sections": DASHBOARD_SECTIONS,
            "dev_reload_enabled": True,
            "file_groups": file_catalog.list_files(),
            "orchestrator_status": _orchestrator_status_payload(),
        },
    )


def _model_options() -> Dict[str, Any]:
    cfg = load_config()
    registry = cfg.get("models", {})
    slots = registry.get("slots", {}) if isinstance(registry.get("slots"), dict) else {}
    items = []
    for slot_name, slot_cfg in slots.items():
        if not isinstance(slot_cfg, dict):
            continue
        items.append(
            {
                "slot": slot_name,
                "display_name": slot_cfg.get("display_name", slot_name),
                "model_id": slot_cfg.get("model_id", ""),
                "base_url": slot_cfg.get("base_url", ""),
                "api_key_env": slot_cfg.get("api_key_env", ""),
                "enabled": bool(slot_cfg.get("enabled", True)),
                "note": slot_cfg.get("note", ""),
            }
        )
    return {
        "default_slot": registry.get("default_slot", "model_slot_1"),
        "models": items,
    }


@app.get("/api/models")
async def list_models():
    return _model_options()


@app.get("/api/generated-files")
async def generated_files():
    return file_catalog.list_files()


@app.get("/api/orchestrator-status")
async def orchestrator_status():
    return _orchestrator_status_payload()


@app.post("/api/initialization-self-check")
async def initialization_self_check():
    return _initialization_self_check_payload()


@app.post("/api/open-file/{file_id}")
async def open_generated_file(file_id: str):
    try:
        return file_catalog.open_with_default_app(file_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"系统默认打开命令执行失败: {exc}") from exc




def _search_diag() -> str:
    from rag_engine.search_aggregator import SearchAggregator

    payload = SearchAggregator(local_kb_dir=os.path.join(BASE_DIR, "knowledge_base")).search(
        "番茄小说 追读钩子 爽点外化",
        max_results_per_source=2,
    )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _model_diag() -> str:
    return json.dumps(_model_options(), ensure_ascii=False, indent=2)


INTERNAL_COMMANDS: Dict[str, Callable[[str], str]] = {
    "search_diag": lambda _slot: _search_diag(),
    "model_diag": lambda _slot: _model_diag(),
}


@app.post("/api/run/{command}")
async def run_command(command: str, request: Request):
    payload: Dict[str, Any] = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    selected_model_slot = str(payload.get("model_slot") or "").strip()
    topic = str(payload.get("topic") or "test_demo").strip()
    bootstrap_runtime_environment()
    py = sys.executable or "python"
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    # Map API commands to actual python CLI commands
    cmd_map = {
        "preflight": [py, "-m", "scripts.cli", "new-book", topic, "--format", "real", "--model-slot", selected_model_slot],
        "feed": [py, "-m", "core_engine.update_kb", topic],
        "export_fanqie": [py, "-m", "scripts.cli", "export-fanqie", "--name", "demo_project", "--genre", "番茄小说", "--author", "none"],
        "full_flow": [py, "-m", "scripts.cli", "full-flow", topic, "--format", "real", "--model-slot", selected_model_slot],
        "produce_chapter": [py, "-m", "scripts.cli", "next-chapter", "第一章：控制台正式生产", "--chapter-index", "1", "--model-slot", selected_model_slot, "--production"],
        "batch_produce": [py, "-m", "scripts.cli", "batch-chapters", "第二章", "第三章", "--model-slot", selected_model_slot, "--production"],
        "inspire": [py, "-m", "core_engine.inspire", topic],
        "cache": [py, "-m", "scripts.cli", "clear-cache", "--yes"],
        "diag_validator": [py, "-m", "scripts.cli", "self-test", "validator"],
    }
    
    # 移除空参数，防止出现 --model-slot (empty) --production 导致 production 被误读为 model_slot 的值
    for k in cmd_map:
        cmd_map[k] = [arg for arg in cmd_map[k] if arg != ""]

    if command == "exit":
        # Start background task to kill process so the response still returns
        import threading
        import signal
        def shutdown():
            import time
            time.sleep(0.5)
            os.kill(os.getpid(), signal.SIGTERM)
        threading.Thread(target=shutdown).start()
        return _command_result(ok=True, output="正在关闭网页控制台服务，请关闭此浏览器标签页。", command=command)

    if command in INTERNAL_COMMANDS:
        try:
            return _command_result(
                ok=True,
                output=INTERNAL_COMMANDS[command](selected_model_slot),
                command=command,
            )
        except Exception as exc:
            return _command_result(
                ok=False,
                output="",
                error=str(exc) or exc.__class__.__name__,
                traceback=traceback.format_exc(),
                command=command,
            )

    if command not in cmd_map:
        return _command_result(ok=False, output="未知命令", error="未知命令", command=command)

    validation_error = _validate_model_command(command, selected_model_slot)
    if validation_error is not None:
        return validation_error

    cmd = list(cmd_map[command])

    import subprocess
    # Use StreamingResponse for shell commands to show real-time progress
    async def process_stream():
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=BASE_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if process.stdout is None or process.stderr is None:
                yield "[CommandError] 子进程未能建立 stdout/stderr 管道。\n"
                return

            queue: asyncio.Queue[tuple[str, Optional[str]]] = asyncio.Queue()

            async def pump(stream: asyncio.StreamReader, label: str) -> None:
                try:
                    while True:
                        chunk = await stream.read(1024)
                        if not chunk:
                            break
                        await queue.put((label, chunk.decode("utf-8", errors="replace")))
                except Exception as exc:
                    await queue.put(("stderr", f"[CommandError] 读取 {label} 失败: {exc}\n"))
                finally:
                    await queue.put((label, None))

            pumps = [
                asyncio.create_task(pump(process.stdout, "stdout")),
                asyncio.create_task(pump(process.stderr, "stderr")),
            ]
            finished_streams = 0
            try:
                while finished_streams < 2:
                    label, text = await queue.get()
                    if text is None:
                        finished_streams += 1
                        continue
                    if label == "stderr":
                        yield f"[stderr] {text}"
                    else:
                        yield text
                await process.wait()
                yield f"\n[CommandExit] code={process.returncode}\n"
            finally:
                for task in pumps:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*pumps, return_exceptions=True)
        except Exception as e:
            yield f"\n[CommandError] {traceback.format_exc()}\n"
            
    return StreamingResponse(process_stream(), media_type="text/plain")

if __name__ == "__main__":
    import threading
    import webbrowser
    import time

    bootstrap_runtime_environment(REQUIRED_RUNTIME_ENV_VARS)
    runtime_env_status = describe_runtime_environment(REQUIRED_RUNTIME_ENV_VARS)
    loaded_env = ", ".join(
        f"{item['name']}({item['source']})"
        for item in runtime_env_status
        if item["status"] == "present"
    )
    missing_env = ", ".join(item["name"] for item in runtime_env_status if item["status"] == "missing")
    
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8543/")
        
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("启动番茄小说网页控制台（Jinja2 auto_reload + uvicorn reload）...")
    print(f"[EnvCheck] 已注入: {loaded_env or '无'}")
    if missing_env:
        print(f"[EnvCheck] 缺少: {missing_env}")
    uvicorn.run("web_ui:app", host="127.0.0.1", port=8543, reload=True)
