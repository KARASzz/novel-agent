#!/bin/bash
set -e

cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"

PORT="${PORT:-8543}"
URL="http://127.0.0.1:${PORT}"

echo "=============================================="
echo "番茄小说一键制造机 - 网页控制台"
echo "FastAPI + Jinja2 热刷新"
echo "生成文件会在网页右侧清单中呈现，点击“本机打开”调用默认应用，不走浏览器预览或下载。"
echo "地址: ${URL}"
echo "=============================================="
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "[错误] 未找到 python3，请先安装 Python。"
  read -r -p "按回车退出..."
  exit 1
fi

if ! python3 -c "import fastapi, uvicorn, jinja2" >/dev/null 2>&1; then
  echo "[依赖缺失] 正在安装 requirements.txt，包含 FastAPI、Uvicorn、Jinja2 等网页控制台依赖..."
  python3 -m pip install -r requirements.txt
fi

open "${URL}" >/dev/null 2>&1 || true
python3 web_ui.py
