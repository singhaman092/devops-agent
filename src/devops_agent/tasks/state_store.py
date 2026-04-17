"""Atomic read/write of .state.json files."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from devops_agent.tasks.models import TaskState


def state_file_path(task_dir: Path, task_id: str) -> Path:
    """Return the path to a task's state file."""
    return task_dir / f"{task_id}.state.json"


def read_state(path: Path) -> TaskState:
    """Read a task state from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return TaskState(**data)


def write_state(path: Path, state: TaskState) -> None:
    """Write task state atomically using temp-file-plus-rename."""
    state.touch()
    data = state.model_dump_json(indent=2)
    # Write to temp file in the same directory, then rename for atomicity
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".state_",
        suffix=".tmp",
    )
    try:
        os.write(fd, data.encode("utf-8"))
        os.close(fd)
        # On Windows, can't rename over existing file — remove first
        if path.exists():
            path.unlink()
        Path(tmp_path).rename(path)
    except BaseException:
        os.close(fd) if not os.get_inheritable(fd) else None  # noqa: E501
        Path(tmp_path).unlink(missing_ok=True)
        raise


def list_states(task_dir: Path) -> list[TaskState]:
    """List all task states in a directory."""
    states = []
    for f in task_dir.glob("*.state.json"):
        try:
            states.append(read_state(f))
        except (json.JSONDecodeError, ValueError):
            continue
    return sorted(states, key=lambda s: s.created_at, reverse=True)
