"""
运行审计与运行目录模块 (Run Audit & Runs Directory)

落盘审计标准：
- 每个 Agent 保存 input.json、output.json、raw.txt、log.jsonl
- shared_artifacts/ 只保存 schema 校验通过的工件
- 长期记忆只接受 memory_candidate，不允许 Agent 直接写 LTM
- runs/preflight/<run_id>/
- runs/chapter/<run_id>/
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class RunType(str, Enum):
    PREFLIGHT = "preflight"
    CHAPTER = "chapter"
    OUTLINE = "outline"


class AgentArtifactType(str, Enum):
    INPUT = "input.json"
    OUTPUT = "output.json"
    RAW = "raw.txt"
    LOG = "log.jsonl"


@dataclass
class RunContext:
    """一次运行会话的上下文"""
    run_id: str
    run_type: RunType
    workspace_root: str
    
    # 运行元数据
    project_id: Optional[str] = None
    topic: Optional[str] = None
    chapter_title: Optional[str] = None
    chapter_index: Optional[int] = None
    
    # Agent 执行轨迹
    agent_sequence: List[str] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    
    # 时间戳
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    
    # 配置
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()
    
    @property
    def run_dir(self) -> Path:
        """获取运行目录路径"""
        base_dir = Path(self.workspace_root) / "runs" / self.run_type.value
        return base_dir / self.run_id
    
    def finalize(self) -> None:
        """结束运行会话"""
        self.ended_at = datetime.now(timezone.utc).isoformat()


@dataclass
class AgentExecutionRecord:
    """单个 Agent 执行记录"""
    agent_id: str
    agent_level: str
    task_id: str
    
    # 输入输出
    input_payload: Dict[str, Any] = field(default_factory=dict)
    output_payload: Dict[str, Any] = field(default_factory=dict)
    raw_output: Optional[str] = None
    
    # 状态
    status: str = "pending"
    error_message: Optional[str] = None
    
    # 时间
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    execution_time_ms: Optional[int] = None
    
    # Schema 校验
    schema_validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    def to_log_dict(self) -> Dict[str, Any]:
        """序列化为日志格式"""
        return {
            "agent_id": self.agent_id,
            "agent_level": self.agent_level,
            "task_id": self.task_id,
            "status": self.status,
            "error_message": self.error_message,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "execution_time_ms": self.execution_time_ms,
            "schema_validated": self.schema_validated,
            "validation_errors": self.validation_errors,
        }


class RunAuditor:
    """
    运行审计器。
    
    负责：
    - 创建和管理运行目录
    - 保存 Agent 执行记录
    - 落盘 Artifact 文件
    - 生成审计日志
    """
    
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        self.current_run: Optional[RunContext] = None
        self._execution_records: List[AgentExecutionRecord] = []
        self._shared_artifacts: Dict[str, Dict[str, Any]] = {}
    
    def start_run(
        self,
        run_type: RunType,
        project_id: Optional[str] = None,
        topic: Optional[str] = None,
        chapter_title: Optional[str] = None,
        chapter_index: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> RunContext:
        """开始新的运行会话"""
        run_id = uuid.uuid4().hex[:10]
        self.current_run = RunContext(
            run_id=run_id,
            run_type=run_type,
            workspace_root=self.workspace_root,
            project_id=project_id,
            topic=topic,
            chapter_title=chapter_title,
            chapter_index=chapter_index,
            config=config or {},
        )
        self._execution_records = []
        self._shared_artifacts = {}
        
        # 创建运行目录
        run_dir = self.current_run.run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (run_dir / "agents").mkdir(exist_ok=True)
        (run_dir / "shared_artifacts").mkdir(exist_ok=True)
        (run_dir / "logs").mkdir(exist_ok=True)
        
        # 写入运行元数据
        metadata = {
            "run_id": run_id,
            "run_type": run_type.value,
            "project_id": project_id,
            "topic": topic,
            "chapter_title": chapter_title,
            "chapter_index": chapter_index,
            "started_at": self.current_run.started_at,
            "config": config or {},
        }
        (run_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        return self.current_run
    
    def end_run(self) -> None:
        """结束当前运行会话"""
        if not self.current_run:
            return
        
        self.current_run.finalize()
        
        # 更新元数据
        run_dir = self.current_run.run_dir
        metadata = {
            "run_id": self.current_run.run_id,
            "run_type": self.current_run.run_type.value,
            "project_id": self.current_run.project_id,
            "started_at": self.current_run.started_at,
            "ended_at": self.current_run.ended_at,
            "agent_sequence": self.current_run.agent_sequence,
            "completed_tasks": self.current_run.completed_tasks,
            "failed_tasks": self.current_run.failed_tasks,
        }
        (run_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 保存审计日志
        self._flush_audit_log()
        
        self.current_run = None
    
    def record_agent_execution(
        self,
        agent_id: str,
        agent_level: str,
        task_id: str,
        input_payload: Dict[str, Any],
        output_payload: Optional[Dict[str, Any]] = None,
        raw_output: Optional[str] = None,
        status: str = "completed",
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        schema_validated: bool = False,
        validation_errors: Optional[List[str]] = None,
    ) -> None:
        """记录 Agent 执行"""
        if not self.current_run:
            return
        
        record = AgentExecutionRecord(
            agent_id=agent_id,
            agent_level=agent_level,
            task_id=task_id,
            input_payload=input_payload,
            output_payload=output_payload or {},
            raw_output=raw_output,
            status=status,
            error_message=error_message,
            started_at=datetime.now(timezone.utc).isoformat(),
            ended_at=datetime.now(timezone.utc).isoformat(),
            execution_time_ms=execution_time_ms,
            schema_validated=schema_validated,
            validation_errors=validation_errors or [],
        )
        self._execution_records.append(record)
        
        # 更新运行上下文 - 只根据 status 决定添加到哪个列表
        if agent_id not in self.current_run.agent_sequence:
            self.current_run.agent_sequence.append(agent_id)
        
        # 只有成功状态才添加到 completed_tasks（且不重复）
        if status == "completed" and task_id not in self.current_run.completed_tasks:
            self.current_run.completed_tasks.append(task_id)
        # 只有失败状态才添加到 failed_tasks（且不重复）
        elif status == "failed" and task_id not in self.current_run.failed_tasks:
            self.current_run.failed_tasks.append(task_id)
        
        # 落盘文件
        self._persist_agent_files(record)
    
    def store_shared_artifact(
        self,
        artifact_id: str,
        content: Dict[str, Any],
        source_task_id: str,
        schema_validated: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        存储共享工件。
        
        只存储 schema 校验通过的工件。
        """
        if not self.current_run:
            return False
        
        if not schema_validated:
            # 未校验的工件不进入共享区
            return False
        
        artifact = {
            "artifact_id": artifact_id,
            "source_task_id": source_task_id,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        self._shared_artifacts[artifact_id] = artifact
        
        # 落盘到 shared_artifacts 目录
        artifact_path = self.current_run.run_dir / "shared_artifacts" / f"{artifact_id}.json"
        artifact_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        return True
    
    def get_shared_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """获取共享工件"""
        return self._shared_artifacts.get(artifact_id)
    
    def _persist_agent_files(self, record: AgentExecutionRecord) -> None:
        """持久化 Agent 文件"""
        if not self.current_run:
            return
        
        agent_dir = self.current_run.run_dir / "agents" / record.task_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # input.json
        input_path = agent_dir / "input.json"
        input_path.write_text(
            json.dumps(record.input_payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # output.json
        output_path = agent_dir / "output.json"
        output_path.write_text(
            json.dumps(record.output_payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # raw.txt
        if record.raw_output:
            raw_path = agent_dir / "raw.txt"
            raw_path.write_text(record.raw_output, encoding="utf-8")
        
        # metadata.json
        meta_path = agent_dir / "metadata.json"
        meta_path.write_text(
            json.dumps(record.to_log_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    def _flush_audit_log(self) -> None:
        """刷新审计日志到文件"""
        if not self.current_run:
            return
        
        log_path = self.current_run.run_dir / "logs" / "audit.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            for record in self._execution_records:
                f.write(json.dumps(record.to_log_dict(), ensure_ascii=False) + "\n")
        
        self._execution_records = []
    
    def get_run_status(self) -> Dict[str, Any]:
        """获取运行状态"""
        if not self.current_run:
            return {"status": "no_active_run"}
        
        return {
            "run_id": self.current_run.run_id,
            "run_type": self.current_run.run_type.value,
            "run_dir": str(self.current_run.run_dir),
            "project_id": self.current_run.project_id,
            "started_at": self.current_run.started_at,
            "agent_sequence": self.current_run.agent_sequence,
            "completed_tasks": self.current_run.completed_tasks,
            "failed_tasks": self.current_run.failed_tasks,
            "shared_artifacts_count": len(self._shared_artifacts),
        }


# =============================================================================
# 导出符号
# =============================================================================

__all__ = [
    "RunContext",
    "RunAuditor",
    "AgentExecutionRecord",
    "RunType",
    "AgentArtifactType",
]