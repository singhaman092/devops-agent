"""Task, StepResult, and TaskState models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from devops_agent.config.schema import TaskPhase


class StepResult(BaseModel):
    """Result of executing a single step."""

    step_name: str = ""
    step_index: int = 0
    params: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending | running | success | failed | skipped
    started_at: str = ""
    finished_at: str = ""
    outputs: dict[str, Any] = Field(default_factory=dict)
    screenshot_paths: list[str] = Field(default_factory=list)
    error_message: str = ""
    stderr: str = ""
    stdout: str = ""

    def mark_started(self) -> None:
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()

    def mark_success(self, outputs: dict[str, Any] | None = None) -> None:
        self.status = "success"
        self.finished_at = datetime.now(timezone.utc).isoformat()
        if outputs:
            self.outputs.update(outputs)

    def mark_failed(self, error: str, stderr: str = "") -> None:
        self.status = "failed"
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.error_message = error
        self.stderr = stderr


class MergeContext(BaseModel):
    """Tracks PR merge state when waiting."""

    pr_url: str = ""
    detected_status: str = ""
    last_check_at: str = ""


class TaskState(BaseModel):
    """Full state of a task execution, persisted as .state.json."""

    task_id: str
    activation_file: str = ""
    task_config_name: str = ""
    phase: TaskPhase = TaskPhase.pending
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    step_results: list[StepResult] = Field(default_factory=list)
    resume_from_step: int = 0
    merge_context: MergeContext | None = None
    variables: dict[str, str] = Field(default_factory=dict)
    error_message: str = ""

    def current_step_index(self) -> int:
        """Return the index of the next step to execute."""
        for i, sr in enumerate(self.step_results):
            if sr.status in ("pending", "running", "failed"):
                return i
        return len(self.step_results)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()
