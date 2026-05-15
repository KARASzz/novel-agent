"""测试 Agent 模型和 Schema 门禁"""
import pytest
from core_engine.agent_models import (
    AgentResult,
    ArtifactPacket,
    ArtifactStatus,
    AgentRole,
    validate_artifact_schema,
)


class TestAgentResultSchemaGate:
    """测试 AgentResult 不会自动校验 artifacts"""

    def test_success_does_not_auto_validate(self):
        """AgentResult.success() 不应该自动校验 artifacts"""
        artifact = ArtifactPacket(
            artifact_id="test-artifact-1",
            source_task_id="task-1",
            source_agent=AgentRole.WORKER,
            content={"data": "test"},
        )
        
        # 创建成功结果时，artifact 应该保持 PENDING 状态
        result = AgentResult.success("task-1", [artifact])
        
        # 关键断言：artifact.status 不应该是 VALIDATED
        assert artifact.status == ArtifactStatus.PENDING
        assert not artifact.schema_validated
        assert result.is_success

    def test_success_with_multiple_artifacts(self):
        """成功结果可以有多个未校验的 artifacts"""
        artifact1 = ArtifactPacket(
            artifact_id="art-1",
            source_task_id="task-1",
            source_agent=AgentRole.WORKER,
            content={"key": "value1"},
        )
        artifact2 = ArtifactPacket(
            artifact_id="art-2",
            source_task_id="task-1",
            source_agent=AgentRole.WORKER,
            content={"key": "value2"},
        )
        
        result = AgentResult.success("task-1", [artifact1, artifact2])
        
        assert len(result.output_artifacts) == 2
        assert all(a.status == ArtifactStatus.PENDING for a in result.output_artifacts)

    def test_failure_result_has_no_artifacts(self):
        """失败结果不应该包含 artifacts"""
        result = AgentResult.failure(
            task_id="task-1",
            error_code="VALIDATION_ERROR",
            error_message="Schema validation failed",
        )
        
        assert result.is_failure
        assert len(result.output_artifacts) == 0
        assert result.error_code == "VALIDATION_ERROR"


class TestValidateArtifactSchema:
    """测试 Schema 校验函数"""

    def test_valid_artifact_passes_validation(self):
        """包含所有必填字段的 artifact 应该通过校验"""
        artifact = ArtifactPacket(
            artifact_id="test-art",
            source_task_id="task-1",
            source_agent=AgentRole.WORKER,
            content={
                "title": "Test Title",
                "content": "Test content",
                "status": "active",
            },
        )
        
        errors = validate_artifact_schema(
            artifact,
            required_fields=["title", "content"],
            field_types={"title": str, "content": str},
        )
        
        assert errors == []
        assert artifact.schema_validated is False  # 校验后需要手动标记

    def test_missing_required_fields(self):
        """缺少必填字段应该返回错误"""
        artifact = ArtifactPacket(
            artifact_id="test-art",
            source_task_id="task-1",
            source_agent=AgentRole.WORKER,
            content={"title": "Only title"},
        )
        
        errors = validate_artifact_schema(
            artifact,
            required_fields=["title", "content", "author"],
            field_types={"title": str},
        )
        
        assert len(errors) >= 1
        assert any("content" in err for err in errors)
        assert any("author" in err for err in errors)

    def test_field_type_mismatch(self):
        """字段类型不匹配应该返回错误"""
        artifact = ArtifactPacket(
            artifact_id="test-art",
            source_task_id="task-1",
            source_agent=AgentRole.WORKER,
            content={
                "title": "Valid string",
                "count": 123,  # 应该是 str 类型
            },
        )
        
        errors = validate_artifact_schema(
            artifact,
            required_fields=["title", "count"],
            field_types={"title": str, "count": str},
        )
        
        assert len(errors) >= 1
        assert any("count" in err and "str" in err for err in errors)

    def test_non_dict_content_fails(self):
        """非 dict 类型的 content 应该直接失败"""
        artifact = ArtifactPacket(
            artifact_id="test-art",
            source_task_id="task-1",
            source_agent=AgentRole.WORKER,
            content="Just a string, not a dict",
        )
        
        errors = validate_artifact_schema(
            artifact,
            required_fields=["title"],
            field_types={},
        )
        
        assert len(errors) >= 1
        assert any("must be a dict" in err for err in errors)


class TestArtifactPacketLifecycle:
    """测试 ArtifactPacket 生命周期"""

    def test_mark_validated_updates_status(self):
        """mark_validated() 应该正确更新状态"""
        artifact = ArtifactPacket(
            artifact_id="test-art",
            source_task_id="task-1",
            source_agent=AgentRole.WORKER,
            content={"key": "value"},
        )
        
        assert artifact.status == ArtifactStatus.PENDING
        assert not artifact.schema_validated
        
        artifact.mark_validated()
        
        assert artifact.status == ArtifactStatus.VALIDATED
        assert artifact.schema_validated

    def test_mark_rejected_updates_status_and_errors(self):
        """mark_rejected() 应该正确更新状态和错误"""
        artifact = ArtifactPacket(
            artifact_id="test-art",
            source_task_id="task-1",
            source_agent=AgentRole.WORKER,
            content={"key": "value"},
        )
        
        errors = ["missing required field", "invalid type"]
        artifact.mark_rejected(errors)
        
        assert artifact.status == ArtifactStatus.REJECTED
        assert not artifact.schema_validated
        assert artifact.validation_errors == errors

    def test_can_be_consumed_by_role_check(self):
        """can_be_consumed_by() 应该正确检查消费者角色"""
        artifact = ArtifactPacket(
            artifact_id="test-art",
            source_task_id="task-1",
            source_agent=AgentRole.WORKER,
            content={"key": "value"},
            allowed_consumers=["MANAGER", "CEO"],
        )
        
        assert artifact.can_be_consumed_by("MANAGER")
        assert artifact.can_be_consumed_by("CEO")
        assert not artifact.can_be_consumed_by("WORKER")

    def test_empty_consumer_list_allows_all(self):
        """空的 allowed_consumers 列表应该允许所有消费者"""
        artifact = ArtifactPacket(
            artifact_id="test-art",
            source_task_id="task-1",
            source_agent=AgentRole.WORKER,
            content={"key": "value"},
            allowed_consumers=[],  # 空列表
        )
        
        # 空列表表示不限制
        assert artifact.can_be_consumed_by("MANAGER")
        assert artifact.can_be_consumed_by("WORKER")
        assert artifact.can_be_consumed_by("CEO")