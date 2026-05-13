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
echo ║              ⚛️⚛️【红果剧本一键制造机】⚛️⚛️                ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║                   🐉 工业化控制台 V3.0 🐉                  ║
echo ╚════════════════════════════════════════════════════════════╝

:menu
echo.
echo ╔══════════【 核心工作流 】════════════╗
echo ║                                      ║
echo ║  [1] 🧭 前置中台评审 (Preflight)     ║
echo ║  [2] 🚀 全自动流水线 (Build Scripts) ║
echo ║  [3] 🌾 知识饲养员   (KB Feed)       ║
echo ║  [4] 📦 投稿打包封装 (Packager)      ║
echo ║  [5] 🧩 一键全流程   (PreHub+Build)  ║
echo ║                                      ║
echo ╠════════════【 辅助工具 】════════════╣
echo ║                                      ║
echo ║  [6] 📊 查看统计数据 (Show Stats)    ║
echo ║  [7] 🛰️ 灵感探针     (Trend Radar)   ║
echo ║  [8] 🧹 缓存管理     (Cache Tools)   ║
echo ║  [9] 🧠 LTM写回审计 (LTM Review)    ║
echo ║                                      ║
echo ╠══════════【 诊断与测试项 】══════════╣
echo ║                                      ║
echo ║  [10] 🧪 诊断工具箱   (Diagnostics)  ║
echo ║                                      ║
echo ╠════════════【 系统控制 】════════════╣
echo ║                                      ║
echo ║  [0] 🚪 退出程序     (Exit)          ║
echo ║                                      ║
echo ╚══════════════════════════════════════╝
echo.
set /p opt="请输入编号并回车: "

if "%opt%"=="1" goto run_preflight
if "%opt%"=="2" goto run_pipeline
if "%opt%"=="3" goto run_feed
if "%opt%"=="4" goto run_packager
if "%opt%"=="5" goto run_full_flow
if "%opt%"=="6" goto show_stats
if "%opt%"=="7" goto run_inspire
if "%opt%"=="8" goto cache_menu
if "%opt%"=="9" goto run_ltm_review
if "%opt%"=="10" goto diagnostics_menu
if "%opt%"=="0" exit /b
echo ⚠️ 输入错误，请重新选择 (0-10)
timeout /t 2 >nul
goto header

:choose_format
echo.
echo 请选择制作形态:
echo   [1] 真人精品 real
echo   [2] AI奇观   ai
echo   [3] 混合辅助 mixed
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
python -m scripts.preflight "%TOPIC%" --format %FORMAT% %NO_RAG%
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:run_full_flow
echo.
set "TOPIC="
set /p TOPIC="请输入要完整生产的题材/关键词: "
if "%TOPIC%"=="" goto header

call :choose_format

set "NO_RAG="
set /p RAG_OPT="如需禁用 Tavily/LTM 云端召回，请输入 N；直接回车默认启用: "
if /I "%RAG_OPT%"=="N" set "NO_RAG=--no-rag"

set "BUNDLE_DIR=reports\preflight"
if not exist "%BUNDLE_DIR%" mkdir "%BUNDLE_DIR%"

echo.
echo 🧭 [1/2] 正在执行 Pre-Hub V4 前置准入...
python -m scripts.preflight "%TOPIC%" --format %FORMAT% %NO_RAG% --save-bundle "%BUNDLE_DIR%"
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
echo 🚀 [2/2] 正在携带 ContextBundle 启动生产流水线...
python -m scripts.cli run --bundle "%BUNDLE_PATH%"
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:run_pipeline
echo.
set /p PIPELINE_OPT="如需忽略缓存强制重跑，请输入 N；直接回车正常启动: "
if /I "%PIPELINE_OPT%"=="N" (
	echo ☢️ 正在启动全自动流水线（忽略缓存）...
	python -m scripts.cli run --no-cache
) else (
	echo ☢️ 正在启动全自动流水线...
	python -m scripts.cli run
)
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:run_packager
echo.
set "PROJECT_NAME="
set /p PROJECT_NAME="请输入项目名/剧名: "
if "%PROJECT_NAME%"=="" goto header

set "GENRE="
set /p GENRE="请输入投稿赛道/题材标签: "
if "%GENRE%"=="" goto header

set "AUTHOR_NAME="
set /p AUTHOR_NAME="请输入笔名/工作室名（直接回车默认 未署名）: "
if "%AUTHOR_NAME%"=="" set "AUTHOR_NAME=未署名"

echo.
echo 📦 正在封装投稿压缩包...
python -m scripts.cli package --name "%PROJECT_NAME%" --genre "%GENRE%" --author "%AUTHOR_NAME%"
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:show_stats
echo.
python -m scripts.cli stats
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:cache_menu
cls
echo ╔══════════【 缓存管理 】══════════╗
echo ║                                  ║
echo ║  [1] 全量清理解析缓存            ║
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
echo ║  [1] 🔎 百炼 RAG 连接诊断          ║
echo ║  [2] 🧪 运行格式校验自检           ║
echo ║  [3] 🎨 运行渲染引擎自检           ║
echo ║  [0] 返回主菜单                    ║
echo ║                                    ║
echo ╚════════════════════════════════════╝
echo.
set /p diag_opt="请输入编号并回车: "

if "%diag_opt%"=="1" goto verify_rag
if "%diag_opt%"=="2" goto run_validator
if "%diag_opt%"=="3" goto run_renderer
if "%diag_opt%"=="0" goto header
echo ⚠️ 输入错误，请重新选择 (0-3)
timeout /t 2 >nul
goto diagnostics_menu

:verify_rag
echo.
echo 🔎 正在执行百炼 RAG 连接诊断...
python -m scripts.cli verify-rag
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:run_validator
echo.
echo 🧪 正在执行剧本格式逻辑校验自检...
python -m scripts.cli self-test validator
set "LAST_ERROR=%ERRORLEVEL%"
goto end_action

:run_renderer
echo.
echo 🎨 正在执行渲染输出引擎自检...
python -m scripts.cli self-test renderer
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
