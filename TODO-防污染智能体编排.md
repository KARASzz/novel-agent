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

## 验收标准

- [ ] `python3 -m pytest tests/test_cli.py -q` 通过。
- [ ] `python3 -m pytest tests/test_prehub_v4.py -q` 通过。
- [ ] `python3 -m pytest tests/test_chapter_orchestrator.py -q` 通过。
- [ ] `python3 -m pytest tests/test_web_ui.py -q` 通过。
- [ ] `python3 -m pytest -q` 全量通过。
- [ ] `python3 -m scripts.cli batch-chapters 第一章` 不再 AttributeError。
- [ ] `rg -n "sk-|api[_-]?key"` 确认没有真实 API key 写入代码。

## 不做

- [ ] 不恢复 Python 规则评分器。
- [ ] 不恢复旧 mock 章节生产。
- [ ] 不引入复杂外部多 Agent 框架。
- [ ] 不让 Agent 共享私有 scratchpad。
