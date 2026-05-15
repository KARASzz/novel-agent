结论：
**Agent 编排要做到“不污染但能协作”，核心不是多开几个 Agent，而是把协作方式从“共享上下文”改成“交换标准包”。** ⚙️

一句话：

```text
实例独立靠隔离边界；
协作靠结构化交接；
防污染靠权限、命名空间、审计和人工裁决点。
```

---

# 一、先定义“污染”是什么

Agent 编排里的污染通常有 6 类：

| 污染类型  | 表现                           |
| ----- | ---------------------------- |
| 上下文污染 | A Agent 的任务背景混进 B Agent 判断   |
| 记忆污染  | 临时判断写进长期记忆                   |
| 权限污染  | 一个 Agent 拿到不该用的工具或文件         |
| 状态污染  | 多个实例改同一个变量、文件、缓存             |
| 输出污染  | 未校验结果被下游当事实使用                |
| 角色污染  | 审稿 Agent 开始写稿，写稿 Agent 开始做裁判 |

你真正要防的不是“Agent 之间不说话”，而是：
**不能让未经批准的信息、判断、状态直接进入别人的工作区。**

---

# 二、总架构：独立实例 + 中央编排器 + 共享工件库

推荐结构：

```text
User Request
   ↓
Orchestrator 编排器
   ↓
┌──────────────┬──────────────┬──────────────┐
│ Agent A       │ Agent B       │ Agent C       │
│ 市场分析      │ 叙事设计      │ 风险审查      │
└──────┬───────┴──────┬───────┴──────┬───────┘
       ↓              ↓              ↓
  Artifact 工件库 / Event Bus / Audit Log
       ↓
Final Synthesizer 总结器
       ↓
Human Review / Final Output
```

关键点：

```text
Agent 之间不直接共享完整上下文。
Agent 之间只通过 artifact / event / packet 协作。
```

---

# 三、每个 Agent 实例必须有 7 个隔离边界

## 1. 独立身份

每个 Agent 必须有自己的：

```json
{
  "agent_id": "market_radar_agent",
  "role": "市场雷达",
  "task_scope": "只判断市场和读者入口",
  "forbidden_actions": ["写正文", "做最终准入结论"]
}
```

不要让一个 Agent 又当分析师、又当裁判、又当执行者。

---

## 2. 独立上下文窗口

不要把所有资料塞给所有 Agent。

错误做法：

```text
所有 Agent 共享完整对话 + 全部资料 + 全部历史输出
```

正确做法：

```text
市场 Agent 只看市场材料
叙事 Agent 只看题材、市场摘要、约束
风险 Agent 只看方案包、风险清单、来源证据
总结 Agent 只看通过校验的结构化输出
```

---

## 3. 独立记忆命名空间

记忆要分层：

```text
private_memory      # Agent 私有短期记忆
task_memory         # 本轮任务临时记忆
project_memory      # 当前项目知识库
shared_artifact     # 可协作工件
long_term_memory    # 长期记忆，必须经过写回审核
```

最重要的铁律：

```text
Agent 不能直接写长期记忆。
只能提交 memory_candidate。
```

长期记忆写入必须走：

```text
candidate → 去重 → 证据检查 → 置信度评分 → 人工/规则批准 → 写入
```

---

## 4. 独立工具权限

每个 Agent 只拿完成任务必须的工具。

例子：

| Agent    | 允许工具                   | 禁止工具        |
| -------- | ---------------------- | ----------- |
| 市场 Agent | 搜索、RAG、来源清洗            | 写文件、写长期记忆   |
| 写作 Agent | 读取 narrative_seed、生成正文 | 搜索市场、修改风险包  |
| 风险 Agent | 读取方案、审查风险              | 改写正文、改评分    |
| 总结 Agent | 读取全部合格工件               | 调外部 API 改事实 |

不要图省事给所有 Agent 全权限。
全权限就是污染源。

---

## 5. 独立工作目录

每个 Agent 写自己的目录：

```text
runs/
└── run_20260515_001/
    ├── market_radar_agent/
    │   ├── input.json
    │   ├── output.json
    │   └── log.jsonl
    ├── narrative_agent/
    │   ├── input.json
    │   ├── output.json
    │   └── log.jsonl
    ├── risk_agent/
    │   ├── input.json
    │   ├── output.json
    │   └── log.jsonl
    └── shared_artifacts/
        ├── market_context_pack.json
        ├── narrative_seed_pack.json
        └── risk_pack.json
```

不要让多个 Agent 同时写同一个文件。

---

## 6. 独立输出契约

每个 Agent 输出必须是固定 schema。

比如市场 Agent：

```json
{
  "agent_id": "market_radar_agent",
  "task_id": "task_market_001",
  "output_type": "market_context_pack",
  "claims": [],
  "confidence": 0.72,
  "evidence_refs": [],
  "uncertainties": [],
  "handoff_to": ["router_agent", "risk_agent"]
}
```

没有 schema 的自然语言输出，不能直接进入下游。

---

## 7. 独立失败机制

Agent 失败不能伪装成功。

禁止：

```json
{
  "success": true,
  "reason": "default_success"
}
```

必须：

```json
{
  "success": false,
  "error_code": "LLM_JSON_PARSE_FAILED",
  "recoverable": true,
  "failed_stage": "market_radar_agent",
  "message": "模型返回 JSON 不合法",
  "raw_output_ref": "runs/.../raw.txt"
}
```

---

# 四、协作不要靠共享脑子，靠“交接包”

## 推荐交接包格式

```json
{
  "packet_id": "pkt_001",
  "from_agent": "market_radar_agent",
  "to_agent": "router_agent",
  "artifact_type": "market_context_pack",
  "schema_version": "1.0.0",
  "payload": {},
  "evidence_refs": [],
  "confidence": 0.76,
  "known_limits": [
    "来源数量不足",
    "缺少近30天平台数据"
  ],
  "allowed_usage": [
    "可用于赛道分流",
    "不可作为最终准入依据"
  ],
  "created_at": "2026-05-15T08:00:00Z"
}
```

重点是 `allowed_usage`。
不是所有输出都能被下游当事实。

---

# 五、推荐的 Agent 分工

以你的小说立项中台为例，可以这样拆：

```text
M01 SourceGuardAgent
职责：信源净化、事实观点分桶
输出：source_audit_pack

M02 MarketRadarAgent
职责：番茄小说市场语境、题材热度、读者入口
输出：market_context_pack

M03 MemoryAgent
职责：作者记忆召回、偏差提醒
输出：author_memory_pack

M04 PriorAgent
职责：读者先验、免疫区、高敏区、追读心理
输出：reader_prior_pack

M05 RouterAgent
职责：小说赛道分流
输出：route_decision_pack

M06 ConceptArenaAgent
职责：高概念竞技、分支打擂
输出：concept_arena_pack

M07 NarrativeSeedAgent
职责：叙事图谱、前三章承诺、章节钩子
输出：narrative_seed_pack

M08 RiskAgent
职责：同质化、IP、合规、连载崩塌风险
输出：risk_pack

M09 AdmissionAgent
职责：准入护照
输出：preflight_passport
```

注意：
**M09 只能读前面 Agent 的“通过校验的包”，不能读它们的私有推理过程。**

---

# 六、中央编排器怎么写逻辑

编排器不要替 Agent 判断内容。
它只管流程和规则。

## 编排器职责

```text
1. 分配任务
2. 注入最小上下文
3. 调用 Agent
4. 校验输出 schema
5. 存档 artifact
6. 控制哪些 artifact 能进入下游
7. 记录审计日志
8. 失败时中断或重试
```

## 编排器不该做

```text
1. 不写小说判断规则
2. 不篡改 Agent 结论
3. 不用默认成功兜底
4. 不把失败输出当成功包
```

---

# 七、最小可用 Python 结构

```python
# orchestrator/task_packet.py

from pydantic import BaseModel, Field
from typing import Any, Literal
from datetime import datetime, timezone
from uuid import uuid4


class TaskPacket(BaseModel):
    task_id: str = Field(default_factory=lambda: f"task_{uuid4().hex[:10]}")
    run_id: str
    from_agent: str = "orchestrator"
    to_agent: str
    task_type: str
    input_payload: dict[str, Any]
    allowed_context_refs: list[str] = []
    forbidden_context_refs: list[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ArtifactPacket(BaseModel):
    artifact_id: str = Field(default_factory=lambda: f"art_{uuid4().hex[:10]}")
    run_id: str
    from_agent: str
    artifact_type: str
    schema_version: str = "1.0.0"
    payload: dict[str, Any]
    evidence_refs: list[str] = []
    confidence: float = Field(ge=0, le=1)
    known_limits: list[str] = []
    allowed_usage: list[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentResult(BaseModel):
    success: bool
    agent_id: str
    artifact: ArtifactPacket | None = None
    error_code: str | None = None
    error_message: str | None = None
    raw_output_ref: str | None = None
```

---

# 八、Agent 基类建议

```python
# orchestrator/base_agent.py

from abc import ABC, abstractmethod
from orchestrator.task_packet import TaskPacket, AgentResult


class BaseAgent(ABC):
    agent_id: str
    role: str
    allowed_tools: list[str]
    output_schema_name: str

    def __init__(self, llm_client, workspace: str):
        self.llm_client = llm_client
        self.workspace = workspace

    @abstractmethod
    def build_prompt(self, task: TaskPacket) -> tuple[str, str]:
        """返回 system_prompt, user_prompt"""
        raise NotImplementedError

    @abstractmethod
    def parse_output(self, raw: str, task: TaskPacket) -> AgentResult:
        """解析并校验输出"""
        raise NotImplementedError

    def run(self, task: TaskPacket) -> AgentResult:
        system_prompt, user_prompt = self.build_prompt(task)

        try:
            raw = self.llm_client.create_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return self.parse_output(raw, task)

        except Exception as exc:
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                error_code=type(exc).__name__,
                error_message=str(exc),
            )
```

核心：
每个 Agent 自己构造 prompt，自己解析自己的 schema。
编排器不参与内容判断。

---

# 九、共享区只能放“已验收工件”

不要搞一个所有 Agent 都能读写的 `global_state`。

危险：

```python
global_state["market_score"] = 85
global_state["risk"] = "low"
global_state["decision"] = "pass"
```

正确：

```text
artifact_store/
├── source_audit_pack.v1.json
├── market_context_pack.v1.json
├── reader_prior_pack.v1.json
├── route_decision_pack.v1.json
├── narrative_seed_pack.v1.json
├── risk_pack.v1.json
└── preflight_passport.v1.json
```

下游读取必须经过：

```text
artifact_exists
→ schema_valid
→ confidence_enough
→ allowed_usage_contains 当前用途
→ not_expired
```

---

# 十、防污染硬规则

你可以直接写进系统规范。

```text
1. Agent 不得读取其他 Agent 的私有 scratchpad。
2. Agent 不得直接写 shared_artifacts。
3. Agent 输出必须先经 schema 校验。
4. Agent 只能通过 ArtifactPacket 交接。
5. 任何 artifact 必须带 from_agent、confidence、evidence_refs、known_limits。
6. 长期记忆只接受 memory_candidate，不接受 Agent 直接写入。
7. 编排器不能用 default_success、fallback_success。
8. 失败必须中断、重试或返回结构化失败。
9. 下游 Agent 只能读取 allowed_context_refs。
10. 最终准入必须保留人工裁决点。
```

---

# 十一、协作模式有三种

## 1. 串行协作

适合强依赖流程：

```text
SourceGuard → MarketRadar → Prior → Router → Concept → Narrative → Risk → Admission
```

优点：稳定。
缺点：慢。

---

## 2. 并行协作

适合互不依赖的任务：

```text
SourceGuard
MemoryAgent
MarketRadar
RiskScanner
```

最后由 Synthesizer 合并。

优点：快。
缺点：需要冲突处理。

---

## 3. 委员会协作

适合关键判断：

```text
ConceptAgent A
ConceptAgent B
ConceptAgent C
        ↓
JudgeAgent
        ↓
RiskAgent
```

注意：JudgeAgent 不能看 A/B/C 的长篇废话，只看结构化分支包。
否则它会被措辞感染。

---

# 十二、最适合你的方案

你现在别一上来搞复杂多 Agent。

先做 **“单 Orchestrator + 多 Prompt Agent + Artifact Store”**。

也就是：

```text
一个 Python 编排器
多个 Agent 类
每个 Agent 一个 prompt
每个 Agent 一个 schema
一个 runs/ 工件目录
一个 audit log
```

先不要上复杂框架。
FastAPI + 自己写 Orchestrator + Pydantic + JSONL 审计日志，够你这个小说立项中台 MVP 用。

---

# 十三、最终原则

你要的不是“Agent 们自由聊天”。
你要的是：

```text
各自独立判断
通过标准包交接
由编排器控制上下游
由 schema 防止乱说
由审计日志追责
由人工裁决关键门
```

一句话：
**Agent 协作不是开群聊，是走公文流转。** 📄

---

## 三个苏格拉底反问

**执行链反问**：
你的小说立项中台里，哪些 Agent 的输出可以直接进入下游，哪些必须先经过 `risk_pack` 或 `preflight_passport` 才能被使用？

**机会成本反问**：
你现在是更需要多 Agent 自由协作，还是先用单编排器把 `TaskPacket → ArtifactPacket → Schema 校验 → Audit Log` 这条硬链路跑稳？

**致命前提反问**：
如果所有 Agent 共用一个上下文和一个全局状态，那它们到底是在独立协作，还是同一个模型换了几个名字自我污染？
