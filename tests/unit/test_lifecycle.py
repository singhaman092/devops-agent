"""Tests for task lifecycle state machine."""

from __future__ import annotations

from pathlib import Path

import pytest

from devops_agent.config.schema import TaskPhase
from devops_agent.tasks.lifecycle import create_task, find_task, generate_task_id
from devops_agent.tasks.state_store import list_states


@pytest.fixture(autouse=True)
def tmp_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up temporary task dirs."""
    tasks_dir = tmp_path / "tasks"
    for d in ("pending", "in_progress", "waiting", "done", "failed"):
        (tasks_dir / d).mkdir(parents=True)

    def patched_subdir(name: str) -> Path:
        d = tasks_dir / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    monkeypatch.setattr("devops_agent.tasks.lifecycle.get_tasks_subdir", patched_subdir)
    return tasks_dir


class TestGenerateTaskId:
    def test_length(self) -> None:
        tid = generate_task_id()
        assert len(tid) == 12

    def test_unique(self) -> None:
        ids = {generate_task_id() for _ in range(100)}
        assert len(ids) == 100


class TestCreateTask:
    def test_creates_in_pending(self, tmp_config: Path) -> None:
        state = create_task(
            task_config_name="my-task",
            activation_file="test.yaml",
            variables={"key": "val"},
        )
        assert state.phase == TaskPhase.pending
        assert state.task_config_name == "my-task"
        assert state.variables["key"] == "val"

        # Verify state file exists in pending/
        pending_states = list_states(tmp_config / "pending")
        assert len(pending_states) == 1
        assert pending_states[0].task_id == state.task_id

    def test_explicit_task_id(self, tmp_config: Path) -> None:
        state = create_task(
            task_config_name="my-task",
            activation_file="test.yaml",
            variables={},
            task_id="custom-id",
        )
        assert state.task_id == "custom-id"


class TestFindTask:
    def test_find_existing(self, tmp_config: Path) -> None:
        state = create_task(
            task_config_name="my-task",
            activation_file="test.yaml",
            variables={},
            task_id="findme",
        )
        result = find_task("findme")
        assert result is not None
        found_state, phase = result
        assert found_state.task_id == "findme"
        assert phase == "pending"

    def test_find_nonexistent(self, tmp_config: Path) -> None:
        assert find_task("nonexistent") is None
