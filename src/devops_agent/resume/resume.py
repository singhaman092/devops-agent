"""Re-entry logic from state file — validate and resume a waiting task."""

from __future__ import annotations

from devops_agent.config.loader import load_all_task_configs
from devops_agent.config.paths import get_config_dir
from devops_agent.tasks.lifecycle import find_task


def validate_resume(task_id: str) -> tuple[bool, str]:
    """Check whether a task can be resumed.

    Returns (can_resume, reason).
    """
    found = find_task(task_id)
    if found is None:
        return False, f"Task {task_id} not found"

    state, phase = found
    if phase not in ("waiting",):
        return False, f"Task is in '{phase}', only 'waiting' tasks can be resumed"

    # Verify the task config still exists and is valid
    config_dir = get_config_dir()
    task_configs = load_all_task_configs(config_dir)
    if state.task_config_name not in task_configs:
        return False, f"Task config '{state.task_config_name}' no longer exists"

    tc = task_configs[state.task_config_name]
    if state.resume_from_step >= len(tc.steps):
        return False, f"Resume step index {state.resume_from_step} exceeds step count {len(tc.steps)}"

    return True, "ok"
