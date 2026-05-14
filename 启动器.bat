@echo off
if "%~1"=="utf8" goto main
chcp 65001 >nul
cmd /c "%~f0" utf8
exit /b

:main
setlocal EnableExtensions DisableDelayedExpansion
color 0B
cd /d "%~dp0"
set "PYTHONPATH=%~dp0"

:header
cls
echo ╔════════════════════════════════════════════════════════════╗
echo ║ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❈ ✧ ❈ ✦ ❈ ✧ ❈  ║
echo ║ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❈ ✧ ❈ ✦ ❈ ✧ ❈  ║
echo ║                                                            ║
echo ║        ██╗  ██╗  ████╗  █████╗    ████╗  ███████╗          ║
echo ║        ██║ ██╔╝ ██╔═██╗ ██╔═██╗  ██╔═██╗ ██╔════╝          ║
echo ║        █████╔╝  ██████║ █████╔╝  ██████║ ███████╗          ║
echo ║        ██╔═██╗  ██╔═██║ ██╔═██╗  ██╔═██╗ ╚════██║          ║
echo ║        ██║  ██╗ ██║ ██║ ██║  ██║ ██║ ██║ ███████║          ║
echo ║        ╚═╝  ╚═╝ ╚═╝ ╚═╝ ╚═╝  ╚═╝ ╚═╝ ╚═╝ ╚══════╝          ║
echo ║                                                            ║
echo ║ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❈ ✧ ❈  ║
echo ║ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❉ ✧ ❈ ✦ ❈ ✧ ❈  ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║              ⚛️⚛️【番茄小说一键制造机】⚛️⚛️              ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║                   🐉 工业化控制台 V3.0 🐉                  ║
echo ╚════════════════════════════════════════════════════════════╝

:menu
echo.
echo ╔══════════【 核心工作流 】════════════╗
echo ║                                      ║
echo ║  [1] 🧭 新书立项评审 (Preflight)     ║
echo ║  [2] ✍️  生成下一章   (Next Chapter) ║
echo ║  [3] 🌾 本地知识库   (KB Feed)       ║
echo ║  [4] 📦 番茄存稿导出 (Export)        ║
echo ║  [5] 🧩 立项产物预跑 (Preflight)     ║
echo ║                                      ║
echo ╠════════════【 辅助工具 】════════════╣
echo ║                                      ║
echo ║  [6] 🛰️ 灵感探针     (Trend Radar)   ║
echo ║  [7] 🧹 缓存管理     (Cache Tools)   ║
echo ║  [8] 🌐 网页控制台   (Jinja2 Hot)   ║
echo ║                                      ║
echo ╠══════════【 诊断与测试项 】══════════╣
echo ║                                      ║
echo ║  [9] 🧪 诊断工具箱   (Diagnostics)  ║
echo ║                                      ║
echo ╠════════════【 系统控制 】════════════╣
echo ║                                      ║
echo ║  [0] 🚪 退出程序     (Exit)          ║
echo ║                                      ║
echo ╚══════════════════════════════════════╝
echo.
set /p opt="请输入编号并回车: "

if "%opt%"=="1" goto run_preflight
if "%opt%"=="2" goto run_next_chapter
if "%opt%"=="3" goto run_feed
if "%opt%"=="4" goto run_packager
if "%opt%"=="5" goto run_full_flow
if "%opt%"=="6" goto run_inspire
if "%opt%"=="7" goto cache_menu
if "%opt%"=="8" goto run_web_ui
if "%opt%"=="9" goto diagnostics_menu
if "%opt%"=="0" exit /b
echo ⚠️ 输入错误，请重新选择 (0-9)
timeout /t 2 >nul
goto header

:choose_format
echo.
echo 请选择章节形态:
echo   [1] 正文连载型 real
echo   [2] 设定辅助型 ai
echo   [3] 混合增强型 mixed
set "FORMAT="
set /p FORMAT_OPT="请输入编号，直接回车默认 [1]: "
if "%FORMAT_OPT%"=="" set "FORMAT=real"
if "%FORMAT_OPT%"=="1" set "FORMAT=real"
if "%FORMAT_OPT%"=="2" set "FORMAT=ai"
if "%FORMAT_OPT%"=="3" set "FORMAT=mixed"
if not defined FORMAT (
	echo ⚠️ 形态编号无效，请重新选择。
	timeout /t 2 >nul
	goto choose_format
)
exit /b

:run_preflight
echo.
set "TOPIC="
set /p TOPIC="请输入要立项评审的题材/关键词: "
if "%TOPIC%"=="" goto header

call :choose_format

set "NO_RAG="
set /p RAG_OPT="如需禁用 RAG，请输入 N 并回车；直接回车默认启用: "
if /I "%RAG_OPT%"=="N" set "NO_RAG=--no-rag"

echo.
echo 🧭 正在启动前置中台评审...
python -m scripts.cli new-book "%TOPIC%" --format %FORMAT% %NO_RAG%
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:run_full_flow
echo.
set "TOPIC="
set /p TOPIC="请输入要完整生产的题材/关键词: "
if "%TOPIC%"=="" goto header

call :choose_format

set "NO_RAG="
set /p RAG_OPT="如需禁用 Brave/Tavily 搜索，请输入 N；直接回车默认启用: "
if /I "%RAG_OPT%"=="N" set "NO_RAG=--no-rag"

set "BUNDLE_DIR=reports\preflight"
if not exist "%BUNDLE_DIR%" mkdir "%BUNDLE_DIR%"

echo.
echo 🧭 [1/2] 正在执行番茄小说前置立项...
python -m scripts.cli new-book "%TOPIC%" --format %FORMAT% %NO_RAG% --save-bundle "%BUNDLE_DIR%"
set "LAST_ERROR=%ERRORLEVEL%"
if not "%LAST_ERROR%"=="0" goto end_action

set "BUNDLE_PATH="
for /f "delims=" %%F in ('dir /b /a:-d /o:-d "%BUNDLE_DIR%\bundle_prj_*.json" 2^>nul') do (
	set "BUNDLE_PATH=%BUNDLE_DIR%\%%F"
	goto full_flow_bundle_found
)

:full_flow_bundle_found
if "%BUNDLE_PATH%"=="" (
	echo [任务执行异常] 未找到 Pre-Hub Bundle。
	set "LAST_ERROR=1"
	goto end_action
)

echo.
echo ✅ 已生成立项产物。下一步请按 templates/webnovel_outline_template_v1.md 生成全书大纲，再生成设定集与章级施工卡。
set "LAST_ERROR=0"
goto end_action

:run_next_chapter
echo.
set "CHAPTER_TITLE="
set /p CHAPTER_TITLE="请输入章节标题（直接回车默认 第一章：控制台试运行）: "
if "%CHAPTER_TITLE%"=="" set "CHAPTER_TITLE=第一章：控制台试运行"
set "CHAPTER_INDEX="
set /p CHAPTER_INDEX="请输入章节序号（直接回车默认 1）: "
if "%CHAPTER_INDEX%"=="" set "CHAPTER_INDEX=1"
set "PROJECT_ID="
set /p PROJECT_ID="请输入项目ID/书名slug（直接回车默认 console_demo）: "
if "%PROJECT_ID%"=="" set "PROJECT_ID=console_demo"
echo ✍️ 正在生成下一章 mock 产物...
python -m scripts.cli next-chapter "%CHAPTER_TITLE%" --chapter-index %CHAPTER_INDEX% --project-id "%PROJECT_ID%"
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:run_packager
echo.
set "PROJECT_NAME="
set /p PROJECT_NAME="请输入项目名/书名: "
if "%PROJECT_NAME%"=="" goto header

set "GENRE="
set /p GENRE="请输入投稿赛道/题材标签: "
if "%GENRE%"=="" goto header

set "AUTHOR_NAME="
set /p AUTHOR_NAME="请输入笔名/工作室名（直接回车默认 未署名）: "
if "%AUTHOR_NAME%"=="" set "AUTHOR_NAME=未署名"

echo.
echo 📦 正在导出番茄小说存稿包...
python -m scripts.cli export-fanqie --name "%PROJECT_NAME%" --genre "%GENRE%" --author "%AUTHOR_NAME%"
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:cache_menu
cls
echo ╔══════════【 缓存管理 】══════════╗
echo ║                                  ║
echo ║  [1] 全量清理章节生产缓存        ║
echo ║  [2] 按关键词筛选清理            ║
echo ║  [0] 返回主菜单                  ║
echo ║                                  ║
echo ╚══════════════════════════════════╝
echo.
set /p cache_opt="请输入编号并回车: "

if "%cache_opt%"=="1" goto clear_cache_all
if "%cache_opt%"=="2" goto clear_cache_filter
if "%cache_opt%"=="0" goto header
echo ⚠️ 输入错误，请重新选择 (0-2)
timeout /t 2 >nul
goto cache_menu

:clear_cache_all
echo.
python -m scripts.cli clear-cache --yes
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:clear_cache_filter
echo.
set "CACHE_FILTER="
set /p CACHE_FILTER="请输入要匹配的关键词: "
if "%CACHE_FILTER%"=="" goto cache_menu
python -m scripts.cli clear-cache --filter "%CACHE_FILTER%" --yes
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:run_inspire
echo.
set /p TOPIC="请输入您想探测的题材/关键词: "
if "%TOPIC%"=="" goto header
python -m core_engine.inspire "%TOPIC%"
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:run_feed
echo.
set /p TOPIC="请输入要导入知识库的主题: "
if "%TOPIC%"=="" goto header
python -m core_engine.update_kb "%TOPIC%"
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:run_web_ui
echo.
echo 🌐 正在启动番茄小说网页控制台...
echo    地址: http://127.0.0.1:8543
echo    已启用 Jinja2/uvicorn 热刷新；生成文件在网页右侧清单中用本机默认应用打开。
start "" "http://127.0.0.1:8543"
python web_ui.py
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:run_ltm_review
echo.
set "PROJECT_ID="
set /p PROJECT_ID="请输入项目ID筛选（直接回车查看全部）: "
set "APPLY_FLAG="
set /p APPLY_OPT="如需把已批准候选写回云端 LTM，请输入 Y；直接回车仅查看: "
if /I "%APPLY_OPT%"=="Y" set "APPLY_FLAG=--apply-approved"
if "%PROJECT_ID%"=="" (
	python -m scripts.cli ltm-review %APPLY_FLAG%
) else (
	python -m scripts.cli ltm-review --project-id "%PROJECT_ID%" %APPLY_FLAG%
)
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:diagnostics_menu
cls
echo ╔══════════【 诊断工具箱 】══════════╗
echo ║                                    ║
echo ║  [1] 🧪 运行番茄章节质检自检       ║
echo ║  [0] 返回主菜单                    ║
echo ║                                    ║
echo ╚════════════════════════════════════╝
echo.
set /p diag_opt="请输入编号并回车: "

if "%diag_opt%"=="1" goto run_validator
if "%diag_opt%"=="0" goto header
echo ⚠️ 输入错误，请重新选择 (0-1)
timeout /t 2 >nul
goto diagnostics_menu

:run_validator
echo.
echo 🧪 正在执行番茄小说章节质检自检...
python -m scripts.cli self-test validator
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:end_action
echo.
echo ---------------------------------------
if "%LAST_ERROR%"=="0" (
	echo [任务处理完成]
) else (
	echo [任务执行异常] 退出码: %LAST_ERROR%
)
set "LAST_ERROR="
echo 按任意键返回主菜单...
pause >nul
goto header
