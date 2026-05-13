from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import subprocess
import uvicorn
import os

app = FastAPI(title="短剧智能体 - 控制台")

# 获取当前文件所在目录的绝对路径，以便正确加载模板文件
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "web_templates"))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html", {})

@app.post("/api/run/{command}")
async def run_command(command: str):
    # Map API commands to actual python CLI commands
    cmd_map = {
        "preflight": ["python", "-m", "scripts.preflight", "test_demo", "--format", "real"],
        "pipeline": ["python", "-m", "scripts.cli", "run"],
        "feed": ["python", "-m", "core_engine.update_kb", "test_demo"],
        "packager": ["python", "-m", "scripts.cli", "package", "--name", "demo_project", "--genre", "unknown", "--author", "none"],
        "full_flow": ["python", "-m", "scripts.preflight", "test_demo", "--format", "real"], # simplified
        "stats": ["python", "-m", "scripts.cli", "stats"],
        "inspire": ["python", "-m", "core_engine.inspire", "test_demo"],
        "cache": ["python", "-m", "scripts.cli", "clear-cache", "--yes"],
        "ltm": ["python", "-m", "scripts.cli", "ltm-review"],
        "diag_rag": ["python", "-m", "scripts.cli", "verify-rag"],
        "diag_validator": ["python", "-m", "scripts.cli", "self-test", "validator"],
        "diag_renderer": ["python", "-m", "scripts.cli", "self-test", "renderer"]
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
        
    try:
        # Run command and capture output
        # cwd ensures scripts find their relative paths (e.g. data folders) correctly
        result = subprocess.run(
            cmd_map[command], 
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
