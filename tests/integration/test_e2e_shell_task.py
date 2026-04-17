"""End-to-end test: run a task-config with only shell steps."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest
import yaml

from devops_agent.config.loader import load_task_config
from devops_agent.config.paths import get_config_dir, get_tasks_subdir, ensure_dirs
from devops_agent.config.schema import TaskPhase
from devops_agent.tasks.executor import execute_task
from devops_agent.tasks.lifecycle import create_task, find_task


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def setup_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a temporary config dir with the shell-only task-config."""
    config_dir = tmp_path / ".devops-agent"
    config_dir.mkdir()

    # Write a minimal config.yaml pointing work_dir inside tmp
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        f"work_dir: '{work_dir.as_posix()}'\nlog_level: DEBUG\n"
    )

    # Copy task-config
    tc_dir = config_dir / "task-configs"
    tc_dir.mkdir()
    shutil.copy(FIXTURE_DIR / "shell-only-task.yaml", tc_dir / "shell-only-test.yaml")

    # Create task dirs
    for d in ("pending", "in_progress", "waiting", "done", "failed"):
        (config_dir / "tasks" / d).mkdir(parents=True)

    # Monkey-patch the config dir resolution
    monkeypatch.setattr(
        "devops_agent.config.paths.get_config_dir",
        lambda: config_dir,
    )
    monkeypatch.setattr(
        "devops_agent.config.paths.get_task_configs_dir",
        lambda: tc_dir,
    )
    monkeypatch.setattr(
        "devops_agent.config.paths.get_tasks_dir",
        lambda: config_dir / "tasks",
    )

    def patched_get_tasks_subdir(name: str) -> Path:
        d = config_dir / "tasks" / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    monkeypatch.setattr(
        "devops_agent.config.paths.get_tasks_subdir",
        patched_get_tasks_subdir,
    )
    # Patch executor's references too
    monkeypatch.setattr(
        "devops_agent.tasks.executor.get_config_dir",
        lambda: config_dir,
    )
    monkeypatch.setattr(
        "devops_agent.tasks.executor.get_tasks_subdir",
        patched_get_tasks_subdir,
    )
    monkeypatch.setattr(
        "devops_agent.tasks.lifecycle.get_tasks_subdir",
        patched_get_tasks_subdir,
    )

    return config_dir


def test_shell_only_task_completes(setup_config: Path) -> None:
    """Run the shell-only task end-to-end and verify it completes."""
    # Import steps so they're registered
    import devops_agent.steps  # noqa: F401

    state = create_task(
        task_config_name="shell-only-test",
        activation_file="test",
        variables={},
        task_id="e2e-shell-test",
    )
    assert state.task_id == "e2e-shell-test"
    assert state.phase == TaskPhase.pending

    # Execute
    final = asyncio.run(execute_task("e2e-shell-test"))

    assert final.phase == TaskPhase.completed
    assert len(final.step_results) == 3

    # All steps succeeded
    for sr in final.step_results:
        assert sr.status == "success", f"Step {sr.step_name} failed: {sr.error_message}"


def test_shell_task_failure_moves_to_waiting(setup_config: Path) -> None:
    """A task with a failing shell command should end up in waiting."""
    import devops_agent.steps  # noqa: F401

    # Create a task-config with a failing command
    tc_dir = setup_config / "task-configs"
    (tc_dir / "fail-test.yaml").write_text(
        "name: fail-test\nsteps:\n  - step: shell.run\n    params:\n      command: exit 1\n"
    )

    state = create_task(
        task_config_name="fail-test",
        activation_file="test",
        variables={},
        task_id="e2e-fail-test",
    )

    final = asyncio.run(execute_task("e2e-fail-test"))

    assert final.phase == TaskPhase.blocked
    assert final.step_results[0].status == "failed"
    assert final.resume_from_step == 0
