# TODO: 防污染智能体编排优化

## 目标

在保留现有 Hierarchical 模式的基础上增强编排可靠性：

```text
CEO Agent
  ↓
Manager Agent
  ↓
Worker Agent
  ↓
Artifact Store + Audit Log + Human Review Gate
```

核心原则：Agent 不共享私有上下文，只通过结构化工件协作。

## 本轮已关闭回归

最近一次 `python3 -m pytest -q` 已通过；下面这 4 个问题已按本轮审查关闭：

- [x] `tests/test_validator.py::test_fanqie_chapter_validator_passes_strong_chapter`
- [x] `tests/test_validator.py::test_fanqie_chapter_validator_catches_ai_tone_and_missing_hook`
- [x] `tests/test_search_aggregator.py::test_brave_searcher_maps_results`
- [x] `tests/test_search_aggregator.py::test_search_aggregator_falls_back_to_local`

后续 TODO 继续保留为长期收口清单。

## P0: 先修复当前迁移断点

- [x] 修复 `batch-chapters` 仍调用已删除 `run_standard_batch` / `run_production_batch` 的问题。
- [x] 统一 CLI 章节生产入口到 `ChapterOrchestrator.run_chapter` / `run_batch`。
- [x] 明确 `new-book` / `preflight` 缺少 `--model-slot` 时的错误提示。
- [x] 修复 `BEAT_GROUPS` / `SIX_B_ITERATION_ROUNDS` 旧常量引用残留。
- [x] 更新旧测试，不再依赖 mock/模板生产链路。

## P1: 建立防污染标准包

- [x] 新增 `TaskPacket`：描述任务、目标 Agent、允许上下文、禁止上下文。
- [x] 新增 `ArtifactPacket`：描述 Agent 输出、证据、置信度、限制和允许用途。
- [x] 新增 `AgentResult`：统一成功/失败、错误码、raw output 引用。
- [x] 所有 Agent 输出先 schema 校验，再进入 shared artifacts。
- [x] 禁止 default success；失败必须中断、重试或返回结构化失败。

## P2: 改造 PreHub 立项中台

- [ ] 保留 `PreHubOrchestrator.run(...)` 外部接口。
- [ ] 将一次性 LLM 总线拆成 M01-M09 Agent 工序。
- [ ] M01 输出 `source_audit_pack`。
- [ ] M02 输出 `market_context_pack`。
- [ ] M03 输出 `author_memory_pack`。
- [ ] M04 输出 `reader_prior_pack`。
- [ ] M05 输出 `route_decision_pack`。
- [ ] M06 输出 `concept_arena_pack`。
- [ ] M07 输出 `narrative_seed_pack`。
- [ ] M08 输出 `risk_pack`。
- [ ] M09 输出 `preflight_passport`。
- [ ] M09 只能读取已验收 artifact，不读取前序 raw 输出。

## P3: 强化章节生产 Hierarchical 编排

- [ ] CEO 只负责目标拆解、最终裁决和汇总。
- [ ] Manager 负责任务分发、上下文白名单、schema 校验。
- [ ] Worker 只执行单一职责任务，不跨角色判断。
- [ ] Stage 6 保持严格串行，防止节拍迭代互相污染。
- [ ] QA/验收阶段必须基于结构化产物，不允许默认通过。

## P4: 落盘审计与运行目录

- [x] 新增 `runs/preflight/<run_id>/`。
- [x] 新增 `runs/chapter/<run_id>/`。
- [x] 每个 Agent 保存 `input.json`、`output.json`、`raw.txt`、`log.jsonl`。
- [x] `shared_artifacts/` 只保存 schema 校验通过的工件。
- [x] 长期记忆只接受 `memory_candidate`，不允许 Agent 直接写 LTM。

## P5: 控制台可视化增强

- [x] `/api/orchestrator-status` 返回 run、agent、artifact、handoff、failure 信息。
- [x] 前端改成"Agent 工件流转图"，突出 CEO / Manager / Worker 的上下游关系。
- [x] 展示 artifact 是否通过 schema、是否允许下游使用、失败原因和人工裁决点。
- [x] 保留初始化自检弹窗交互。

## P6: 本次审查暴露的回归修复

### Task 1: 修复章节质检器的判定字段和拦截逻辑

**Files:**
- Modify: `core_engine/validator.py`
- Modify: `tests/test_validator.py`

- [x] **Step 1: 先把失败测试补成精确断言**

重点断言下面这些字段必须存在且语义正确：

```python
assert report.checks["conflict_progression"] is True
assert report.checks["payoff_externalized"] is True
assert report.checks["ending_hook"] is True
```

```python
assert not report.is_valid
assert any("冲突推进不足" in err for err in report.errors)
assert any("章尾追读钩子不足" in err for err in report.errors)
assert any("AI腔风险" in warn for warn in report.warnings)
assert any("设定连续性风险" in warn for warn in report.warnings)
```

- [x] **Step 2: 把 `validate()` 的判定拆成“硬错误”和“软告警”**

`is_valid` 不能只看字数和空文本；冲突推进、章尾钩子、人物显化、设定连续性必须进入硬判定或至少进入可配置的拒稿门槛。

- [x] **Step 3: 保留当前启发式分数，但不要拿它代替门禁**

`score` 可以作为仪表盘参考，不能决定放行。

- [x] **Step 4: 跑定向测试**

Run: `python3 -m pytest tests/test_validator.py -q`
Expected: PASS

### Task 2: 收口 Brave / 搜索聚合的运行时与测试契约

**Files:**
- Modify: `rag_engine/brave_search.py`
- Modify: `rag_engine/search_aggregator.py`
- Modify: `tests/test_search_aggregator.py`

- [x] **Step 1: 给 Brave adapter 加稳定的可注入调用点**

当前 `BraveSearcher.search_hot_trends()` 直接走 `asyncio.run(call_mcp_tool(...))`，测试无法只 patch 一个稳定入口。需要补一个可注入的 runner 参数，或者拆成独立的 transport 方法，让单测不碰真实网络。

- [x] **Step 2: 把测试里的环境前置条件收紧**

`SearchAggregator._search_brave()` 同时支持 `BRAVE_SEARCH_API_KEY` 和 `BRAVE_API_KEY`。测试要清空两个变量，否则 `missing_env:BRAVE_SEARCH_API_KEY` 这个断言会被 `BRAVE_API_KEY` 覆盖。

```python
monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
monkeypatch.delenv("BRAVE_API_KEY", raising=False)
```

- [x] **Step 3: 把失败原因改成可预测、可断言的输出**

`fallback_reasons` 需要稳定反映 `disabled / missing_env / failed / empty_result` 四类状态，不能因为外部环境残留就变成不相关的 `*_empty_result`。

- [x] **Step 4: 跑定向测试**

Run: `python3 -m pytest tests/test_search_aggregator.py -q`
Expected: PASS

### Task 3: 修正运行审计里“失败任务也算完成”的账本错误

**Files:**
- Modify: `core_engine/run_audit.py`
- Create: `tests/test_run_audit.py`

- [x] **Step 1: 先补一个只看账本状态的单测**

测试要覆盖下面这个行为：

```python
record_agent_execution(..., status="failed")
assert task_id not in current_run.completed_tasks
assert task_id in current_run.failed_tasks
```

- [x] **Step 2: 让 `record_agent_execution()` 只把成功任务写入 `completed_tasks`**

失败任务只能进入 `failed_tasks`，不能同时出现在成功列表里。

- [x] **Step 3: 如果同一任务重复记录，账本不能产生重复项**

`completed_tasks` 和 `failed_tasks` 都要保持可解释、可回溯。

- [x] **Step 4: 跑定向测试**

Run: `python3 -m pytest tests/test_run_audit.py -q`
Expected: PASS

### Task 4: 关掉章节编排里的默认成功路径和隐式校验旁路

**Files:**
- Modify: `chapter_pipeline/orchestrator.py`
- Modify: `core_engine/agent_models.py`
- Modify: `tests/test_chapter_orchestrator.py`
- Create: `tests/test_agent_models.py`

- [x] **Step 1: 让 QA 任务缺 prompt 时失败，而不是伪装成 pass**

`qa_acceptance_parallel` 不能再走“跳过但返回 pass”的分支。缺 prompt、缺模型、缺验收条件时都必须回传结构化失败。

- [x] **Step 2: 把 `AgentResult.success()` 的自动 validated 逻辑拿掉**

`ArtifactPacket` 只有在显式通过 `validate_artifact_schema()` 后才能进入 validated 状态。`success()` 只能包装结果，不能替代校验。

- [x] **Step 3: 补一个专门验证 schema 门禁的单测**

```python
result = AgentResult.success("task-1", [artifact])
assert artifact.status != ArtifactStatus.VALIDATED
```

- [x] **Step 4: 跑定向测试**

Run: `python3 -m pytest tests/test_chapter_orchestrator.py tests/test_agent_models.py -q`
Expected: PASS

### Task 5: 把 `new-book` / `preflight` 的模型槽位默认值收回到配置层

**Files:**
- Modify: `pre_hub/novel_preflight_orchestrator.py`
- Modify: `scripts/preflight.py`
- Modify: `scripts/cli.py`
- Modify: `README.md`
- Modify: `config.yaml`

- [x] **Step 1: 先恢复无参数示例的可用性**

`README.md` 里这条命令要能直接跑：

```bash
python -m scripts.cli new-book "都市重生" --author "Author_X"
```

- [x] **Step 2: 让 CLI 优先读取 `config.yaml` 的默认槽位**

当 `--model-slot` 为空时，先读 `models.default_slot` 或 `llm.model_slot`，再允许环境变量 `NOVEL_AGENT_DEFAULT_MODEL_SLOT` 覆盖。

- [x] **Step 3: 保持批量章节生产的强约束不变**

`next-chapter` 和 `batch-chapters` 的 `--production` 路径仍然必须显式传 `--model-slot`，不要把批量生产也放成隐式默认。

- [x] **Step 4: 跑命令级验证**

Run: `python3 -m scripts.cli new-book 测试题材 --format real --author test --no-rag`
Expected: 不再抛 `model_slot 必须指定`

### Task 6: 决定 M01-M09 是真拆分，还是删掉死代码并收口文档

**Files:**
- Modify: `pre_hub/novel_preflight_orchestrator.py`
- Modify: `tests/test_prehub_v4.py`
- Modify: `scripts/test_novel_preflight.py`

- [x] **Step 1: 统一 `_AGENT_PROMPTS` 的真实状态**

要么把 M01-M09 真正拆成多步工序链，要么删掉这组提示词常量，避免代码和架构说明不一致。

- [x] **Step 2: 如果继续保留单次调用，就把文档和测试改成单体 LLM 评审**

不要在注释里写“链式 M01-M09”，运行时却还是单次 `create_response()`。

- [x] **Step 3: 如果改成真拆分，每一步都必须产出可审计 artifact**

每一步要写入输入、输出、校验结果和失败原因，M09 只能读前面已经验收的 artifact。

- [x] **Step 4: 跑前置评审回归**

Run: `python3 -m pytest tests/test_prehub_v4.py scripts/test_novel_preflight.py -q`
Expected: PASS

## 验收标准

- [x] `python3 -m pytest tests/test_validator.py tests/test_search_aggregator.py -q` 通过。
- [x] `python3 -m pytest tests/test_run_audit.py tests/test_agent_models.py -q` 通过。
- [x] `python3 -m pytest tests/test_cli.py -q` 通过。
- [x] `python3 -m pytest tests/test_prehub_v4.py -q` 通过。
- [x] `python3 -m pytest tests/test_chapter_orchestrator.py -q` 通过。
- [x] `python3 -m pytest tests/test_web_ui.py -q` 通过。
- [x] `python3 -m pytest -q` 全量通过。
- [x] `python3 -m scripts.cli batch-chapters 第一章` 不再 AttributeError。
- [x] `rg -n "sk-|api[_-]?key"` 确认没有真实 API key 写入代码。

## 不做

- [ ] 不恢复 Python 规则评分器。
- [ ] 不恢复旧 mock 章节生产。
- [ ] 不引入复杂外部多 Agent 框架。
- [ ] 不让 Agent 共享私有 scratchpad。
