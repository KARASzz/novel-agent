# 🍅 番茄小说一键制造机 (Novel Agent)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **面向番茄小说的网文立项、章节生产、质检与导出全自动流水线。**

**番茄小说一键制造机** 是一款专为网文创作者设计的工业级自动化生产工具。采用**前置立项决策中台 + 小说大纲中台 + 九步章节生产线**架构：
所有底层引擎默认接入统一的 **OpenAI Chat Completions** 兼容协议，支持多种开源/闭源模型切换。

---

## 🚀 核心优势 (Core Advantages)

### 1. 🎛️ 灵活的 5 个模型占位符
网页控制台内置 5 个模型配置槽位（`model_slot_1` 至 `model_slot_5`）。接入真实模型时，只需在配置中填写对应 `Base URL`、`模型 ID`，并在系统环境变量中配置对应的 `API Key`。
- 如果所选模型槽位缺少对应的 Key，系统会明确提示你需要设置该槽位绑定的环境变量名，不会隐式报错。
- 默认运行链路只依赖所选的 OpenAI Chat Completions 兼容模型、本地知识库以及可选的搜索引擎。

### 2. 🧠 降级与兜底机制
系统支持集成 Tavily 和 Brave 作为在线搜索引擎以补充设定库。
- 如果系统中**缺少 Tavily 或 Brave API Key**，搜索聚合模块会自动**降级到本地知识库**，提供本地参考支持，**绝对不会中断主生产流程**。

### 3. 🧱 小说大纲中台
立项通过后不再直接开写章节，而是先生成全书骨架与设定仓库：
- **正式源模板**：`templates/webnovel_outline_template_v1.md` 和 `templates/webnovel_setting_bible_template_v1.md`。
- **分层产物**：全书大纲、设定集、4个卷Agent的每卷100章极简故事清单、按需生成的章级施工卡。
- **结构约束**：全书400章；4卷；每卷4弧；每弧25章；每弧4单元，单元章数固定为 `6/6/6/7`。
- **交接原则**：章级施工卡只进入九步流程第1步，第2-9步保持母版流程不变。

### 4. ✍️ 严谨的九步章节生产线
不再使用简化的提示词，严格执行工业级“九步章节生产线”标准母版：
- **Hierarchical Agent 编排模式**：CEO 负责任务调度与裁决，Manager 负责检索与工作包，Worker 执行单步写作与六轮要素迭代（事件推进、身体感受、环境变化、旁人反应、流程卡点、去AI腔）。
- **状态账本**：对章节生成中每一环均有细致的监控、重试和风险检查机制。

### 5. 🧪 深度番茄网文质检
提供详尽的番茄小说章节质检器，包含：
- 检查章节字数区间、开章承接、冲突推进、爽点外化、章尾追读钩子、人物行为一致性等。
- 严查 AI 腔、空话、解释过度、节奏拖沓。

---

## 🕹️ 快速启动 (Quick Start)

### 1. 环境初始化
```bash
# 推荐使用 Python 3.11+
python -m pip install -e .
```

### 2. 配置环境变量
所有的模型 Key 和搜索 Key 都可以且仅可以通过环境变量注入：

```powershell
# 模型 API Key（按你的配置文件设置）
$env:MODEL_SLOT_1_API_KEY="sk-..."
$env:MODEL_SLOT_2_API_KEY="sk-..."

# 在线搜索 API Key（可选）
$env:TAVILY_API_KEY="..."
$env:BRAVE_SEARCH_API_KEY="..."
```

### 3. 启动控制台
使用网页前端进行交互操作：
```bash
启动网页前端.bat
# 或者手动启动：
# uvicorn web_ui:app --reload
```
打开浏览器访问即可体验番茄小说立项与章节生产。

### 4. 命令行调用 (CLI)
也可以使用内置 CLI 处理批量任务：
```bash
# 新书立项
python -m scripts.cli new-book "都市重生" --author "Author_X"

# 生成下一章
python -m scripts.cli next-chapter "第一章：重回1998" --chapter-index 1 --project-id "demo" --model-slot "model_slot_1"

# 导出番茄小说存稿
python -m scripts.cli export-fanqie --name "重生之大亨" --genre "男频都市" --author "Author_X"
```

---

## 📂 目录结构 (Architecture)

```text
.
├── chapter_pipeline/     # 九步章节生产线 Orchestrator
├── core_engine/          # 核心引擎 (解析、缓存、渲染封装)
├── pre_hub/              # 前置决策立项中台
├── rag_engine/           # 搜索引擎（Brave/Tavily/本地知识库）
├── scripts/              # CLI入口
├── novel_outputs/        # 章节成文、分章输出
├── templates/            # 预设提示词母版资产与小说大纲中台模板
├── web_templates/        # Jinja2 网页控制台模板
├── config.yaml           # 全局与模型槽位配置
└── web_ui.py             # FastAPI 控制台服务
```

> **冻结说明**：
> 本系统已将“阿里云百炼向量库”和“LTM 云端记忆库”设为冻结状态，默认流程中不触发、不强制配置对应环境变量。

---
*Developed with ❤️ for Novel Writers.*
