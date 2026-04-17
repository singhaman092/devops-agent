"""Tests for task models and state store."""

from __future__ import annotations

import json
from pathlib import Path

from devops_agent.config.schema import TaskPhase
from devops_agent.tasks.models import StepResult, TaskState
from devops_agent.tasks.state_store import read_state, write_state


class TestStepResult:
    def test_mark_started(self) -> None:
        sr = StepResult(step_name="shell.run")
        sr.mark_started()
        assert sr.status == "running"
        assert sr.started_at != ""

    def test_mark_success(self) -> None:
        sr = StepResult(step_name="shell.run")
        sr.mark_started()
        sr.mark_success({"exit_code": 0})
        assert sr.status == "success"
        assert sr.outputs["exit_code"] == 0

    def test_mark_failed(self) -> None:
        sr = StepResult(step_name="shell.run")
        sr.mark_started()
        sr.mark_failed("command failed", stderr="error output")
        assert sr.status == "failed"
        assert sr.error_message == "command failed"
        assert sr.stderr == "error output"


class TestTaskState:
    def test_creation(self) -> None:
        state = TaskState(task_id="abc123", task_config_name="deploy")
        assert state.phase == TaskPhase.pending
        assert state.created_at != ""

    def test_current_step_index(self) -> None:
        state = TaskState(task_id="abc123")
        state.step_results = [
            StepResult(step_name="a", status="success"),
            StepResult(step_name="b", status="pending"),
            StepResult(step_name="c", status="pending"),
        ]
        assert state.current_step_index() == 1


class TestStateStore:
    def test_write_and_read(self, tmp_path: Path) -> None:
        state = TaskState(
            task_id="test123",
            task_config_name="deploy",
            phase=TaskPhase.in_progress,
            variables={"key": "value"},
        )
        path = tmp_path / "test123.state.json"
        write_state(path, state)
        assert path.exists()

        loaded = read_state(path)
        assert loaded.task_id == "test123"
        assert loaded.task_config_name == "deploy"
        assert loaded.variables["key"] == "value"

    def test_atomic_write(self, tmp_path: Path) -> None:
        """Verify no temp files left behind on success."""
        state = TaskState(task_id="test456")
        path = tmp_path / "test456.state.json"
        write_state(path, state)

        # No temp files should remain
        temp_files = list(tmp_path.glob(".state_*.tmp"))
        assert len(temp_files) == 0
