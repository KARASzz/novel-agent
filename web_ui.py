import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
import subprocess
import uvicorn
import os
import sys
from typing import Any, Callable, Dict, List, Optional

from core_engine.config_loader import load_config
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
        return f"本轮聚焦 {round_name}，但 mock 产物未体现文本差异。"
    return f"相对上一轮，本轮只处理 {round_name}，不混合改写其他五个要素。"


def _orchestrator_status_payload() -> Dict[str, Any]:
    from chapter_pipeline.orchestrator import BEAT_GROUPS, SIX_B_ITERATION_ROUNDS

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

    stage6_groups = []
    for left, right in BEAT_GROUPS:
        group_id = f"beats_{left}_{right}"
        draft = task_map.get(f"stage_6a_{group_id}", {})
        draft_content = str(draft.get("content", ""))
        previous_content = draft_content
        rounds = []
        for round_index, round_name in enumerate(SIX_B_ITERATION_ROUNDS, start=1):
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
            "six_b_rounds": list(SIX_B_ITERATION_ROUNDS),
        },
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
        "title": "章节生产",
        "tone": "module-chapter",
        "description": "九步章节生产线与连续章节 mock 执行。",
        "commands": [
            {"id": "mock_chapter", "label": "生成下一章", "icon": "✍️"},
            {"id": "mock_batch", "label": "批量生成章节", "icon": "📚"},
            {"id": "pipeline", "label": "运行核心流水线", "icon": "🚀"},
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
            {"id": "diag_renderer", "label": "渲染引擎自检", "icon": "🎨"},
            {"id": "export_fanqie", "label": "导出番茄存稿", "icon": "📦"},
        ],
    },
    {
        "title": "系统工具",
        "tone": "module-system",
        "description": "统计、缓存和控制台进程管理。",
        "commands": [
            {"id": "stats", "label": "查看统计数据", "icon": "📊"},
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


def _run_mock_chapter(selected_model_slot: str) -> str:
    from chapter_pipeline import ChapterOrchestrator, ChapterPipelineInput

    output = ChapterOrchestrator().run_mock_chapter(
        project_goal="番茄小说章节生产",
        chapter_input=ChapterPipelineInput(
            project_bundle={"project_id": "console_demo", "project_title": "控制台试运行"},
            current_chapter="第一章：控制台试运行",
            previous_chapter_writeback="新书开局，无上一章回写。",
            local_kb_reference="控制台 mock：使用本地知识库摘要占位。",
            search_summary="控制台 mock：联网搜索摘要占位。",
            chapter_index=1,
            model_slot=selected_model_slot,
        ),
        output_root=Path(BASE_DIR) / "novel_outputs",
    )
    return "已生成 mock 下一章。\n" + json.dumps(output.to_dict(), ensure_ascii=False, indent=2)


def _run_mock_batch(selected_model_slot: str) -> str:
    from chapter_pipeline import ChapterOrchestrator

    outputs = ChapterOrchestrator().run_mock_batch(
        project_goal="番茄小说章节生产",
        chapter_titles=["第一章：控制台试运行", "第二章：回写承接测试"],
        project_bundle={"project_id": "console_demo", "project_title": "控制台试运行"},
        initial_previous_writeback="新书开局，无上一章回写。",
        local_kb_reference="控制台 mock：使用本地知识库摘要占位。",
        search_summary="控制台 mock：联网搜索摘要占位。",
        output_root=Path(BASE_DIR) / "novel_outputs",
        model_slot=selected_model_slot,
    )
    return "已批量生成 mock 章节。\n" + json.dumps([item.to_dict() for item in outputs], ensure_ascii=False, indent=2)


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
    "mock_chapter": _run_mock_chapter,
    "mock_batch": _run_mock_batch,
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
    py = sys.executable
    # Map API commands to actual python CLI commands
    cmd_map = {
        "preflight": [py, "-m", "scripts.cli", "new-book", "test_demo", "--format", "real"],
        "pipeline": [py, "-m", "scripts.cli", "run"],
        "feed": [py, "-m", "core_engine.update_kb", "test_demo"],
        "export_fanqie": [py, "-m", "scripts.cli", "export-fanqie", "--name", "demo_project", "--genre", "番茄小说", "--author", "none"],
        "full_flow": [py, "-m", "scripts.cli", "new-book", "test_demo", "--format", "real"], # simplified
        "stats": [py, "-m", "scripts.cli", "stats"],
        "inspire": [py, "-m", "core_engine.inspire", "test_demo"],
        "cache": [py, "-m", "scripts.cli", "clear-cache", "--yes"],
        "diag_validator": [py, "-m", "scripts.cli", "self-test", "validator"],
        "diag_renderer": [py, "-m", "scripts.cli", "self-test", "renderer"]
    }
    
    if command == "exit":
        # Start background task to kill process so the response still returns
        import threading
        import signal
        def shutdown():
            import time
            time.sleep(0.5)
            os.kill(os.getpid(), signal.SIGTERM)
        threading.Thread(target=shutdown).start()
        return {"output": "正在关闭网页控制台服务，请关闭此浏览器标签页。"}
    
    if command in INTERNAL_COMMANDS:
        try:
            return {"output": INTERNAL_COMMANDS[command](selected_model_slot)}
        except Exception as exc:
            return {"output": f"执行异常: {str(exc)}"}

    if command not in cmd_map:
        return {"output": "未知命令"}

    cmd = list(cmd_map[command])
    if selected_model_slot and command in {"pipeline"}:
        cmd.extend(["--model-slot", selected_model_slot])
        
    try:
        # Run command and capture output
        # cwd ensures scripts find their relative paths (e.g. data folders) correctly
        result = subprocess.run(
            cmd,
            capture_output=True, 
            text=True, 
            cwd=BASE_DIR, 
            encoding="utf-8", 
            errors="replace"
        )
        
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
            
        if not output.strip():
            output = f"命令执行完成，无输出 (退出码: {result.returncode})"
            
    except Exception as e:
        output = f"执行异常: {str(e)}"
        
    return {"output": output}

if __name__ == "__main__":
    print("启动番茄小说网页控制台（Jinja2 auto_reload + uvicorn reload）...")
    uvicorn.run("web_ui:app", host="127.0.0.1", port=8543, reload=True)
