from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import subprocess
import uvicorn
import os
import sys
from typing import Any, Dict

from core_engine.config_loader import load_config

try:
    from fastapi.templating import Jinja2Templates
except ImportError:  # pragma: no cover - only used in dependency-incomplete test envs
    class Jinja2Templates:  # type: ignore[no-redef]
        def __init__(self, directory: str):
            self.directory = directory

        def TemplateResponse(self, request: Request, name: str, context: Dict[str, Any]):
            return HTMLResponse(f"Jinja2 is required to render {name}.")

app = FastAPI(title="番茄小说一键制造机 - 控制台")

# 获取当前文件所在目录的绝对路径，以便正确加载模板文件
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "web_templates"))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


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
        "preflight": [py, "-m", "scripts.preflight", "test_demo", "--format", "real"],
        "pipeline": [py, "-m", "scripts.cli", "run"],
        "feed": [py, "-m", "core_engine.update_kb", "test_demo"],
        "packager": [py, "-m", "scripts.cli", "package", "--name", "demo_project", "--genre", "unknown", "--author", "none"],
        "full_flow": [py, "-m", "scripts.preflight", "test_demo", "--format", "real"], # simplified
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
    print("启动极简版网页前端...")
    uvicorn.run("web_ui:app", host="127.0.0.1", port=8543, reload=True)
