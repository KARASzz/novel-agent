@echo off
if "%~1"=="utf8" goto main
chcp 65001 >nul
cmd /c "%~f0" utf8
exit /b

:main
cd /d "%~dp0"
title 番茄小说一键制造机 - 网页控制台
echo 正在启动番茄小说网页控制台 (FastAPI + Jinja2 热刷新)...
echo 文件清单会在网页右侧显示，点击“本机打开”会用默认应用打开，不走浏览器预览或下载。
python web_ui.py
pause
