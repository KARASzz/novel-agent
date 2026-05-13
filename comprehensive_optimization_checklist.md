# 红果剧本制造机 - 全面项目优化清单 (2026.04.04)

基于对项目所有 23 个核心源码文件、配置文件及启动脚本的深度审查，我为您整理了本份优化清单。

---

## 1. 🏗️ 架构重构与消除冗余 (Architecture & Refactoring)

| 优先级 | 优化项 | 说明 |
| :--- | :--- | :--- |
| 🔴 **高** | **统一工具构造逻辑** | [parser.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/parser.py), [inspire.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/inspire.py), [update_kb.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/update_kb.py) 中重复定义了相同的 `enabled_tools` 构造逻辑。应提取至 `core_engine/utils.py` 或 [config_loader.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/config_loader.py)。 |
| 🔴 **高** | **标准化大模型调用协议** | 三个模块都单独实现了 DashScope 的 `responses.create` 逻辑。建议封装一个统一的 `LLMClient` 代理类，处理 `instructions`/`input` 切分、`enable_thinking` 及 `session-cache` 等通用 Header。 |
| 🟡 **中** | **消除 `sys.path` Hack** | 几乎所有入口脚本都使用了 `sys.path.insert(0, ...)`。应通过标准化的 [pyproject.toml](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/pyproject.toml) 配置和 `pip install -e .` 安装来彻底解决导入路径问题。 |
| 🟡 **中** | **规范 [load_config](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/config_loader.py#25-60) 调用** | [parser.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/parser.py) 等类在初始化时多次调用 [load_config()](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/config_loader.py#25-60)。虽然有简单缓存，但建议将 [config](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/config_loader.py#25-60) 作为参数注入，提高可测试性。 |

---

## 2. ⚡ 性能与成本控制 (Performance & Cost)

| 优先级 | 优化项 | 说明 |
| :--- | :--- | :--- |
| 🟡 **中** | **SHA-256 缓存增强** | [cache_manager.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/cache_manager.py) 目前使用 MD5，由于剧本内容可能极长，建议升级为 SHA-256 加盐，并包含 Prompt 版本号，防止 Prompt 修改后误用旧缓存。 |
| 🟡 **中** | **更精细的 `max_workers` 管理** | [BatchProcessor](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/batch_processor.py#59-238) 的并发数量目前仅由配置决定。建议根据 API 速率限制（Rate Limit）自动动态调节，避免触发 429 报错。 |
| 🟢 **低** | **Session Cache 策略优化** | 在 [update_kb.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/update_kb.py) 生成长报告时，可以更精确地利用缓存来减少重复 Prompt 消耗的 Token 成本。 |

---

## 3. 🛡️ 鲁棒性与异常处理 (Reliability & Robustness)

| 优先级 | 优化项 | 说明 |
| :--- | :--- | :--- |
| 🔴 **高** | **完善 [update_kb.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/update_kb.py) 错误拦截** | 该模块在 `requests.put` (OSS 上传) 失败时直接退出，缺乏自动重试及清理机制。 |
| 🔴 **高** | **依赖补全** | [update_kb.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/update_kb.py) 使用了 `requests`，但 [requirements.txt](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/requirements.txt) 中未列出。应补全，防止环境部署失败。 |
| 🟡 **中** | **Regex 鲁棒性** | `topic_cleaned` 进行文件名清理时，应增加对 Windows 保留关键字（如 CON, NUL）的过滤。 |
| 🟡 **中** | **LocalRetriever 的线程安全** | 缓存 `_INDEX_CACHE` 是类变量，在 [BatchProcessor](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/batch_processor.py#59-238) 并发读取时应加锁。 |

---

## 4. 🔬 测试与 DX (Quality & Dev Experience)

| 优先级 | 优化项 | 说明 |
| :--- | :--- | :--- |
| 🔴 **高** | **LLM & Tool Mocking** | 目前 `tests/` 极薄。应增加 `pytest-mock`，模拟 Qwen 和 Tavily 的返回结果，以便在离线状态下运行自动化测试。 |
| 🟡 **中** | **统一换行符** | 即使在 Windows 开发，也建议将 [validator.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/tests/test_validator.py) 等文件的 CRLF 统一为 LF，避免跨系统对比时产生大量 Diff 噪音。 |
| 🟡 **中** | **增强 CLI 交互** | [scripts/cli.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/scripts/cli.py) 中的 `clear-cache` 可增加 `--filter` 功能（如只清除特定题材的缓存）。 |
| 🟢 **低** | **根目录 [__init__.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/rag_engine/__init__.py)** | 加上 [__init__.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/rag_engine/__init__.py) 可以更方便地将项目作为 Python Package 进行分发。 |

---

## 5. 📖 知识库与 RAG 调优 (RAG & KB)

| 优先级 | 优化项 | 说明 |
| :--- | :--- | :--- |
| 🟡 **中** | **双引擎优先级调度** | 目前 RAG 使用 [bm25](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/rag_engine/retriever.py#147-167) (本地) 和 [Bailian](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/rag_engine/bailian_retriever.py#13-98) (远程)。应在配置中增加逻辑：若远程检索失败，自动回退到本地，确保业务不中断。 |
| 🟡 **中** | **自动索引触发** | 当 [ContentCleaner](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/rag_engine/content_cleaner.py#7-143) 清洗完数据后，应自动触发 [LocalRetriever](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/rag_engine/retriever.py#13-238) 重建索引，而不是等待下次运行。 |

---

### 💡 建议实施建议
建议按照 **[🔴 高]** 的顺序先行修复架构中的冗余逻辑。如果需要，我可以为您开始执行其中任何一项的重构。
