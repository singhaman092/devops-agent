"""Step protocol, StepContext, and StepResult."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from devops_agent.config.schema import (
    AgentConfig,
    EnvironmentConfig,
    NotificationsConfig,
    RepoConfig,
)
from devops_agent.tasks.models import StepResult


@dataclass
class StepContext:
    """Runtime context passed to every step primitive."""

    task_id: str
    work_dir: Path
    variables: dict[str, str] = field(default_factory=dict)
    agent_config: AgentConfig = field(default_factory=AgentConfig)
    repo: RepoConfig | None = None
    environment: EnvironmentConfig | None = None
    notifications: NotificationsConfig | None = None
    # Accumulated outputs from prior steps (e.g., pr_url, branch_name)
    outputs: dict[str, Any] = field(default_factory=dict)
    # Screenshot storage directory
    screenshot_dir: Path = field(default_factory=lambda: Path("."))
    # Browser session handle (set by executor when browser is needed)
    browser_session: Any = None

    def resolve_var(self, template: str) -> str:
        """Resolve ${var} placeholders in a string using variables and outputs."""
        result = template
        for key, value in {**self.variables, **self.outputs}.items():
            result = result.replace(f"${{{key}}}", str(value))
        return result


@runtime_checkable
class Step(Protocol):
    """Protocol that all step primitives must implement."""

    @property
    def name(self) -> str:
        """Stable name used in YAML (e.g., shell.run, pr.create)."""
        ...

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute the step. Returns a StepResult."""
        ...
