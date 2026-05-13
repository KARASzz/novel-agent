# 红果剧本制造机 - 进一步优化清单

## 一、⚙️ 配置与环境 ([config.yaml](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/config.yaml), `core_engine/`)

| 优先级 | 描述 |
|---|---|
| 🔴 高 | **[update_kb.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/update_kb.py) 内硬编码 `base_url`**：第55行存在 `base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"` 字符串，未从 [config.yaml](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/config.yaml) 读取，与其他模块的配置驱动方式不一致，需修复。 |
| 🟡 中 | **[config.yaml](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/config.yaml) 缺少 `auto_package`/`project_name`/`author` 字段**：[main_pipeline.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/main_pipeline.py) 使用了这些配置，但 [config.yaml](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/config.yaml) 中没有声明，导致自动打包功能无法通过配置文件激活。 |
| 🟡 中 | **关闭不需要的内置工具以节省 Token**：`web_search` 和 `code_interpreter` 对剧本结构化解析（`parser`）意义有限，可考虑在解析任务中关闭，仅在 `inspire` 和 `update_kb` 中保留。 |
| 🟢 低 | **[config.yaml](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/config.yaml) 缺少 `rag.top_k` 配置项**：RAG检索的 `top_k=2` 当前硬编码在 [parse_draft()](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/parser.py#474-661) 中，应提取到配置文件以便调优。 |

---

## 二、🚀 性能与成本 ([parser.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/parser.py), [batch_processor.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/batch_processor.py))

| 优先级 | 描述 |
|---|---|
| 🔴 高 | **[DraftParser](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/parser.py#117-661) 单例重复初始化**：`BatchProcessor.__init__` 创建了 [DraftParser()](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/parser.py#117-661)，包含 RAG 索引构建，但 [main_pipeline.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/main_pipeline.py) 每次运行都会重新初始化。应将 [DraftParser](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/parser.py#117-661) 设为单例或通过依赖注入共享。 |
| 🟡 中 | **`config_loader.load_config()` 多处重复调用**：[FormatValidator](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/validator.py#18-113), [DraftParser](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/parser.py#117-661), [update_kb.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/update_kb.py) 的 [main()](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/scripts/cli.py#12-51) 中都独立调用 [load_config()](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/config_loader.py#25-60)，应利用已有的 `functools.cache` 机制（或确保其生效）避免无效 I/O。 |
| 🟡 中 | **[cache_manager.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/cache_manager.py) 使用 MD5 哈希**：MD5 存在极低碰撞风险，生产环境建议升级为 SHA-256（`hashlib.sha256`）以增强可靠性。 |
| 🟢 低 | **`pipeline.max_workers: 3`**：This value is not tested. If each worker makes a 5s+ API call concurrently to Qwen, the `requests_per_second: 0` (no throttle) could cause API rate limit errors on free tiers. Consider enabling `requests_per_second: 1` as a safe default. |

---

## 三、🧪 测试覆盖 (`tests/`)

| 优先级 | 描述 |
|---|---|
| 🔴 高 | **[parser.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/parser.py) 和 [cache_manager.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/cache_manager.py) 没有单元测试**：这两个是最核心的模块，应覆盖 [_clean_json_string](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/parser.py#271-278)、[_repair_json_string](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/parser.py#309-316)、[_get_hash](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/cache_manager.py#16-20) 等方法的边界条件。 |
| 🔴 高 | **缺少 [inspire.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/inspire.py) 和 [update_kb.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/update_kb.py) 的 Mock 测试**：当前测试中没有对 LLM 调用进行 Mock，无法在无网络/无密钥环境下验证业务逻辑正确性。 |
| 🟡 中 | **[test_validator.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/tests/test_validator.py) 可增加前三集付费集的组合测试**：当前测试覆盖了基础场景，建议补充"第1集+付费集"这类多规则叠加惩罚的测试用例。 |

---

## 四、🖥️ CLI 功能 ([scripts/cli.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/scripts/cli.py))

| 优先级 | 描述 |
|---|---|
| 🔴 高 | **`clear-cache` 未实际传递 `--no-cache` 标志至 Pipeline**：[cli.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/scripts/cli.py) 第36行注释显示 `--no-cache` 尚未实现，只是打印了提示，但实际调用 `run_pipeline()` 时没有任何参数传递。 |
| 🟡 中 | **`stats` 子命令缺失知识库统计**：当前只统计了 `drafts/` 和 `scripts_output/`，可以增加 `knowledge_base/` 的文档数量，让用户了解知识库容量。 |
| 🟢 低 | **可增加 `cli.py rebuild-index` 子命令**：允许用户手动重建本地检索索引（`LocalRetriever.build_index()`），方便维护知识库后的即时刷新。 |

---

## 五、📦 依赖管理 ([requirements.txt](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/requirements.txt), [pyproject.toml](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/pyproject.toml))

| 优先级 | 描述 |
|---|---|
| 🟡 中 | **[requirements.txt](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/requirements.txt) 缺少版本锁定**：`alibabacloud-bailian20231229` 没有版本号约束，可能因为上游破坏性更新导致运行失败，建议锁定版本（如 `alibabacloud-bailian20231229==2.0.0`）。 |
| 🟡 中 | **[update_kb.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/update_kb.py) 顶层导入了 `requests` 库，但未列入 [requirements.txt](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/requirements.txt)**：若未预装，会导致运行时 `ImportError`。 |
| 🟡 中 | **[requirements-optional.txt](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/requirements-optional.txt) 内容未披露**：建议将 `tavily-python` 显式写入此文件并添加安装说明，降低新用户的环境配置门槛。 |
| 🟢 低 | **[pyproject.toml](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/pyproject.toml) 缺少 `[project]` 元数据**：无 `name`, `version`, `description` 等字段，建议补全以支持 `pip install -e .` 的标准安装方式。 |

---

## 六、🛡️ 代码质量与健壮性

| 优先级 | 描述 |
|---|---|
| 🟡 中 | **[validator.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/tests/test_validator.py) 使用 `\r\n` 混合换行符**：文件存在 Windows CRLF 换行，与其他文件的 LF 不一致，建议统一为 LF（`.gitattributes` 配置 `* text=auto`）。 |
| 🟡 中 | **[inspire.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/core_engine/inspire.py) 中的 `system_prompt` 变量遗留但不再使用**：在之前迁移 `instructions`/`input` 后，原始的大型 `system_prompt` f-string (第68-91行) 应检查是否有残留引用。 |
| 🟢 低 | **[rag_engine/retriever.py](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/rag_engine/retriever.py) 的 [get_rag_context()](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/rag_engine/retriever.py#219-238) 方法存在内部 hack 注释**（第229-232行）：应重构 [search()](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/rag_engine/bailian_retriever.py#46-85) 方法使其返回 `doc_id`，消除这段技术债务。 |

---

## 七、📚 文档 ([docs/README.md](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/docs/README.md))

| 优先级 | 描述 |
|---|---|
| 🟡 中 | **`README.md` 缺少 `BAILIAN_INDEX_ID` / `WORKSPACE_ID` 环境变量说明**：新增的知识库检索功能需要这两个环境变量，但文档中目前可能没有记录。 |
| 🟡 中 | **缺少 `file_search` 功能的启用指南**：用户需要了解如何在 [config.yaml](file:///d:/+%E7%BA%A2%E6%9E%9C%E5%89%A7%E6%9C%AC%E4%B8%80%E9%94%AE%E5%88%B6%E9%80%A0%E6%9C%BA/config.yaml) 中设置 `tools.file_search: true` 并提供对应的 Bailian 知识库 ID。 |
