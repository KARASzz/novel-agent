"""
防污染智能体协作标准包 (Anti-Pollution Agent Collaboration Package)

核心原则：Agent 不共享私有上下文，只通过结构化工件协作。

数据模型：
- TaskPacket: 描述任务、目标 Agent、允许上下文、禁止上下文
- ArtifactPacket: 描述 Agent 输出、证据、置信度、限制和允许用途
- AgentResult: 统一成功/失败、错误码、raw output 引用

所有 Agent 输出先 schema 校验，再进入 shared artifacts。
禁止 default success；失败必须中断、重试或返回结构化失败。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class TaskPriority(str, Enum):
    CRITICAL = "critical"  # 必须立即执行，失败立即中断
    HIGH = "high"           # 高优先级，失败重试有限次数
    NORMAL = "normal"       # 普通优先级
    LOW = "low"             # 低优先级，可延迟


class AgentRole(str, Enum):
    CEO = "CEO"           # 总调度：目标拆解、最终裁决、汇总
    MANAGER = "MANAGER"   # 经理：任务分发、上下文白名单、schema 校验
    WORKER = "WORKER"     # 执行者：单一职责任务，不跨角色判断


class ResultStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    SKIP = "skip"


class ArtifactStatus(str, Enum):
    PENDING = "pending"         # 待校验
    VALIDATED = "validated"      # 已校验通过
    REJECTED = "rejected"       # 校验拒绝
    CONSUMED = "consumed"        # 已被下游使用


@dataclass
class TaskPacket:
    """
    描述任务的标准化数据包。
    
    用于 Agent 间传递任务时携带完整的上下文约束：
    - 允许 Agent 读取哪些上下文
    - 禁止 Agent 读取哪些上下文
    - 任务目标和验收标准
    """
    task_id: str
    task_type: str                    # 任务类型标识
    description: str                  # 任务描述
    target_agent: AgentRole           # 目标 Agent 角色
    
    # 允许的上下文来源（白名单）
    allowed_contexts: List[str] = field(default_factory=list)
    
    # 禁止的上下文来源（黑名单）
    forbidden_contexts: List[str] = field(default_factory=list)
    
    # 任务输入（由 Manager 校验后注入）
    input_payload: Dict[str, Any] = field(default_factory=dict)
    
    # 验收标准（用于后续校验）
    acceptance_criteria: List[str] = field(default_factory=list)
    
    # 优先级和重试策略
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    
    # 依赖的前置任务
    depends_on: List[str] = field(default_factory=list)
    
    # 元数据
    created_at: Optional[str] = None
    parent_task_id: Optional[str] = None
    
    def validate(self) -> List[str]:
        """校验任务包完整性，返回错误列表"""
        errors = []
        if not self.task_id:
            errors.append("task_id is required")
        if not self.task_type:
            errors.append("task_type is required")
        if not self.description:
            errors.append("description is required")
        return errors


@dataclass
class ArtifactPacket:
    """
    描述 Agent 输出的结构化工件。
    
    每个 Agent 的输出必须封装为 ArtifactPacket：
    - 包含原始输出
    - 包含置信度和证据
    - 包含使用限制
    - 包含允许的下游消费者
    """
    artifact_id: str
    source_task_id: str                # 来源任务
    source_agent: AgentRole            # 来源 Agent
    
    # 核心输出
    content: Any                      # 结构化内容（dict/list/str）
    raw_output: Optional[str] = None  # 原始 LLM 输出（可选）
    
    # 质量指标
    confidence: float = 0.0           # 置信度 0-1
    evidence_refs: List[str] = field(default_factory=list)  # 证据引用
    
    # 使用限制
    allowed_consumers: List[str] = field(default_factory=list)  # 允许的消费者角色
    forbidden_usage: List[str] = field(default_factory=list)   # 禁止的使用场景
    
    # Schema 校验结果
    schema_validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    # 状态追踪
    status: ArtifactStatus = ArtifactStatus.PENDING
    
    # 元数据
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def mark_validated(self) -> None:
        """标记为已校验通过"""
        self.status = ArtifactStatus.VALIDATED
        self.schema_validated = True
    
    def mark_rejected(self, errors: List[str]) -> None:
        """标记为校验拒绝"""
        self.status = ArtifactStatus.REJECTED
        self.schema_validated = False
        self.validation_errors = errors
    
    def can_be_consumed_by(self, consumer: str) -> bool:
        """检查是否可以由指定消费者使用"""
        if not self.allowed_consumers:
            return True  # 空白名单表示不限制
        return consumer in self.allowed_consumers


@dataclass
class AgentResult:
    """
    统一成功/失败结果封装。
    
    所有 Agent 执行结果必须返回 AgentResult：
    - 明确成功或失败
    - 包含错误码和错误信息
    - 引用 raw output 和 artifacts
    - 支持重试决策
    """
    task_id: str
    status: ResultStatus
    
    # 成功时的输出
    output_artifacts: List[ArtifactPacket] = field(default_factory=list)
    
    # 失败时的错误信息
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_context: Dict[str, Any] = field(default_factory=dict)
    
    # 原始输出引用
    raw_output_ref: Optional[str] = None
    
    # 决策信息
    retry_count: int = 0
    should_retry: bool = False
    skip_reason: Optional[str] = None
    
    # 元数据
    executed_at: Optional[str] = None
    execution_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success(
        cls,
        task_id: str,
        artifacts: List[ArtifactPacket],
        raw_ref: Optional[str] = None,
        exec_time_ms: Optional[int] = None,
    ) -> AgentResult:
        """创建成功结果"""
        result = cls(
            task_id=task_id,
            status=ResultStatus.SUCCESS,
            output_artifacts=artifacts,
            raw_output_ref=raw_ref,
            executed_at=None,
            execution_time_ms=exec_time_ms,
        )
        # 自动校验所有 artifacts
        for artifact in artifacts:
            if artifact.status == ArtifactStatus.PENDING:
                artifact.mark_validated()
        return result
    
    @classmethod
    def failure(
        cls,
        task_id: str,
        error_code: str,
        error_message: str,
        retry: bool = True,
        error_context: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """创建失败结果"""
        return cls(
            task_id=task_id,
            status=ResultStatus.FAILURE,
            error_code=error_code,
            error_message=error_message,
            should_retry=retry,
            error_context=error_context or {},
        )
    
    @classmethod
    def skip(cls, task_id: str, reason: str) -> AgentResult:
        """创建跳过结果"""
        return cls(
            task_id=task_id,
            status=ResultStatus.SKIP,
            skip_reason=reason,
        )
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == ResultStatus.SUCCESS
    
    @property
    def is_failure(self) -> bool:
        """是否失败"""
        return self.status == ResultStatus.FAILURE
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "output_artifacts": [
                {
                    "artifact_id": a.artifact_id,
                    "source_task_id": a.source_task_id,
                    "status": a.status.value,
                    "confidence": a.confidence,
                }
                for a in self.output_artifacts
            ],
            "error_code": self.error_code,
            "error_message": self.error_message,
            "should_retry": self.should_retry,
            "skip_reason": self.skip_reason,
            "executed_at": self.executed_at,
            "execution_time_ms": self.execution_time_ms,
        }


# =============================================================================
# Schema 校验工具
# =============================================================================

def validate_artifact_schema(
    artifact: ArtifactPacket,
    required_fields: List[str],
    field_types: Dict[str, type],
) -> List[str]:
    """
    通用 Schema 校验函数。
    
    Args:
        artifact: 待校验的工件
        required_fields: 必填字段列表
        field_types: 字段类型映射 {字段名: 期望类型}
    
    Returns:
        错误列表，空列表表示校验通过
    """
    errors = []
    content = artifact.content
    
    if not isinstance(content, dict):
        errors.append("content must be a dict")
        return errors
    
    # 检查必填字段
    for field_name in required_fields:
        if field_name not in content:
            errors.append(f"required field missing: {field_name}")
    
    # 检查字段类型
    for field_name, expected_type in field_types.items():
        if field_name in content and not isinstance(content[field_name], expected_type):
            errors.append(
                f"field type mismatch: {field_name} "
                f"expected {expected_type.__name__}, "
                f"got {type(content[field_name]).__name__}"
            )
    
    return errors


# =============================================================================
# 导出符号
# =============================================================================

__all__ = [
    "TaskPacket",
    "ArtifactPacket",
    "AgentResult",
    "TaskPriority",
    "AgentRole",
    "ResultStatus",
    "ArtifactStatus",
    "validate_artifact_schema",
]