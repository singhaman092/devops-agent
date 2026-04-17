"""Task lifecycle state machine — folder moves and phase transitions."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from devops_agent.config.paths import get_tasks_subdir
from devops_agent.config.schema import TaskPhase
from devops_agent.tasks.models import TaskState
from devops_agent.tasks.state_store import read_state, state_file_path, write_state


def generate_task_id() -> str:
    """Generate a unique task ID."""
    return uuid.uuid4().hex[:12]


def create_task(
    task_config_name: str,
    activation_file: str,
    variables: dict[str, str],
    task_id: str = "",
) -> TaskState:
    """Create a new task in pending state."""
    tid = task_id or generate_task_id()
    state = TaskState(
        task_id=tid,
        activation_file=activation_file,
        task_config_name=task_config_name,
        phase=TaskPhase.pending,
        variables=variables,
    )
    pending_dir = get_tasks_subdir("pending")
    write_state(state_file_path(pending_dir, tid), state)
    return state


def transition_task(task_id: str, from_phase: str, to_phase: TaskPhase) -> TaskState:
    """Move a task from one phase folder to another."""
    from_dir = get_tasks_subdir(from_phase)
    to_dir = get_tasks_subdir(to_phase.value)

    src = state_file_path(from_dir, task_id)
    if not src.exists():
        raise FileNotFoundError(f"Task {task_id} not found in {from_phase}/")

    state = read_state(src)
    state.phase = to_phase

    dst = state_file_path(to_dir, task_id)
    write_state(dst, state)
    src.unlink()
    return state


def move_to_in_progress(task_id: str) -> TaskState:
    return transition_task(task_id, "pending", TaskPhase.in_progress)


def move_to_waiting(task_id: str) -> TaskState:
    return transition_task(task_id, "in_progress", TaskPhase.blocked)


def move_to_done(task_id: str) -> TaskState:
    """Move task to done/ archive directory."""
    from_dir = get_tasks_subdir("in_progress")
    done_dir = get_tasks_subdir("done") / task_id
    done_dir.mkdir(parents=True, exist_ok=True)

    src = state_file_path(from_dir, task_id)
    state = read_state(src)
    state.phase = TaskPhase.completed

    dst = done_dir / f"{task_id}.state.json"
    write_state(dst, state)
    src.unlink()
    return state


def move_to_failed(task_id: str, from_phase: str = "in_progress") -> TaskState:
    """Move task to failed/ archive directory."""
    from_dir = get_tasks_subdir(from_phase)
    failed_dir = get_tasks_subdir("failed") / task_id
    failed_dir.mkdir(parents=True, exist_ok=True)

    src = state_file_path(from_dir, task_id)
    state = read_state(src)
    state.phase = TaskPhase.failed

    dst = failed_dir / f"{task_id}.state.json"
    write_state(dst, state)
    src.unlink()
    return state


def find_task(task_id: str) -> tuple[TaskState, str] | None:
    """Find a task by ID across all phase directories. Returns (state, phase_name)."""
    for phase in ["pending", "in_progress", "waiting", "done", "failed"]:
        d = get_tasks_subdir(phase)
        # Check direct state file
        sf = state_file_path(d, task_id)
        if sf.exists():
            return read_state(sf), phase
        # Check archive subdirectory (done/failed)
        archive_sf = d / task_id / f"{task_id}.state.json"
        if archive_sf.exists():
            return read_state(archive_sf), phase
    return None
