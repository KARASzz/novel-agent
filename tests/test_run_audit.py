"""测试运行审计模块 (Run Audit)"""
import pytest
from core_engine.run_audit import RunAuditor, RunType


class TestRunAuditorTaskTracking:
    """测试任务状态追踪的准确性"""

    def test_completed_task_not_in_failed_tasks(self):
        """成功的任务不应该出现在 failed_tasks 中"""
        auditor = RunAuditor()
        auditor.start_run(RunType.CHAPTER, project_id="test-project")
        
        # 记录一个成功任务
        auditor.record_agent_execution(
            agent_id="ceo_agent",
            agent_level="CEO",
            task_id="task-1",
            input_payload={"task": "test"},
            status="completed",
        )
        
        assert "task-1" in auditor.current_run.completed_tasks
        assert "task-1" not in auditor.current_run.failed_tasks
        
        auditor.end_run()

    def test_failed_task_in_failed_tasks_only(self):
        """失败的任务只应该出现在 failed_tasks 中，不在 completed_tasks 中"""
        auditor = RunAuditor()
        auditor.start_run(RunType.CHAPTER, project_id="test-project")
        
        # 记录一个失败任务
        auditor.record_agent_execution(
            agent_id="worker_agent",
            agent_level="WORKER",
            task_id="task-2",
            input_payload={"task": "test"},
            status="failed",
            error_message="Something went wrong",
        )
        
        assert "task-2" not in auditor.current_run.completed_tasks
        assert "task-2" in auditor.current_run.failed_tasks
        
        auditor.end_run()

    def test_mixed_success_and_failure_tasks(self):
        """混合成功和失败任务时的追踪准确性"""
        auditor = RunAuditor()
        auditor.start_run(RunType.PREFLIGHT, project_id="test-project")
        
        # 记录成功任务
        auditor.record_agent_execution(
            agent_id="manager_agent",
            agent_level="MANAGER",
            task_id="task-success-1",
            input_payload={},
            status="completed",
        )
        
        # 记录失败任务
        auditor.record_agent_execution(
            agent_id="worker_agent",
            agent_level="WORKER",
            task_id="task-fail-1",
            input_payload={},
            status="failed",
            error_message="Error",
        )
        
        # 记录另一个成功任务
        auditor.record_agent_execution(
            agent_id="manager_agent",
            agent_level="MANAGER",
            task_id="task-success-2",
            input_payload={},
            status="completed",
        )
        
        # 验证状态追踪
        assert len(auditor.current_run.completed_tasks) == 2
        assert "task-success-1" in auditor.current_run.completed_tasks
        assert "task-success-2" in auditor.current_run.completed_tasks
        assert "task-success-1" not in auditor.current_run.failed_tasks
        assert "task-success-2" not in auditor.current_run.failed_tasks
        
        assert len(auditor.current_run.failed_tasks) == 1
        assert "task-fail-1" in auditor.current_run.failed_tasks
        assert "task-fail-1" not in auditor.current_run.completed_tasks
        
        auditor.end_run()

    def test_no_duplicate_task_ids(self):
        """同一任务重复记录不应该产生重复项"""
        auditor = RunAuditor()
        auditor.start_run(RunType.CHAPTER, project_id="test-project")
        
        # 多次记录同一任务（模拟重试场景）
        for _ in range(3):
            auditor.record_agent_execution(
                agent_id="worker_agent",
                agent_level="WORKER",
                task_id="task-retry",
                input_payload={},
                status="failed",
            )
        
        # task-retry 应该在 failed_tasks 中，且不重复
        assert auditor.current_run.failed_tasks.count("task-retry") == 1
        
        auditor.end_run()

    def test_run_status_reflects_correct_state(self):
        """运行状态 API 应该正确反映任务完成和失败情况"""
        auditor = RunAuditor()
        auditor.start_run(RunType.CHAPTER, project_id="test-project")
        
        auditor.record_agent_execution(
            agent_id="ceo_agent",
            agent_level="CEO",
            task_id="task-1",
            input_payload={},
            status="completed",
        )
        
        auditor.record_agent_execution(
            agent_id="worker_agent",
            agent_level="WORKER",
            task_id="task-2",
            input_payload={},
            status="failed",
        )
        
        status = auditor.get_run_status()
        
        assert status["completed_tasks"] == ["task-1"]
        assert status["failed_tasks"] == ["task-2"]
        
        auditor.end_run()


class TestRunAuditorRunLifecycle:
    """测试运行生命周期"""

    def test_start_and_end_run(self):
        """测试运行开始和结束"""
        auditor = RunAuditor()
        context = auditor.start_run(RunType.PREFLIGHT, project_id="test-project")
        
        assert context is not None
        assert context.project_id == "test-project"
        assert auditor.current_run is not None
        
        auditor.end_run()
        
        assert auditor.current_run is None

    def test_run_directory_creation(self):
        """测试运行目录创建"""
        auditor = RunAuditor()
        context = auditor.start_run(RunType.CHAPTER, project_id="test-project")
        
        run_dir = context.run_dir
        assert run_dir.exists()
        assert (run_dir / "agents").exists()
        assert (run_dir / "shared_artifacts").exists()
        assert (run_dir / "logs").exists()
        
        auditor.end_run()

    def test_agent_sequence_tracking(self):
        """测试 Agent 序列追踪"""
        auditor = RunAuditor()
        auditor.start_run(RunType.CHAPTER, project_id="test-project")
        
        auditor.record_agent_execution(
            agent_id="ceo",
            agent_level="CEO",
            task_id="task-1",
            input_payload={},
            status="completed",
        )
        
        auditor.record_agent_execution(
            agent_id="manager",
            agent_level="MANAGER",
            task_id="task-2",
            input_payload={},
            status="completed",
        )
        
        assert "ceo" in auditor.current_run.agent_sequence
        assert "manager" in auditor.current_run.agent_sequence
        assert auditor.current_run.agent_sequence == ["ceo", "manager"]
        
        auditor.end_run()