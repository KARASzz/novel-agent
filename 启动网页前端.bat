@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
title Tomato Novel Web Console
echo Starting web console with hot reload...
cmd /c python web_ui.py
exit /b
