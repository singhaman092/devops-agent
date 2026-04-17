"""Pydantic v2 models for all configuration files."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums ──────────────────────────────────────────────────────────────────────


class PlatformType(str, Enum):
    azure_devops = "azure_devops"
    github = "github"
    gitlab = "gitlab"
    bitbucket = "bitbucket"


class DeployTriggerType(str, Enum):
    portal_click = "portal_click"
    pipeline_url = "pipeline_url"
    cli = "cli"


class MergeDetectionMode(str, Enum):
    poll = "poll"
    suspend = "suspend"


class NotificationPlatform(str, Enum):
    slack = "slack"
    teams = "teams"


class TaskPhase(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    waiting_merge = "waiting_merge"
    blocked = "blocked"
    completed = "completed"
    failed = "failed"


# ── config.yaml ────────────────────────────────────────────────────────────────


class AgentConfig(BaseModel):
    """Global agent behavior configuration (~/.devops-agent/config.yaml)."""

    work_dir: Path = Field(
        default=Path.home() / ".devops-agent" / "work",
        description="Root directory for task working trees",
    )
    edge_profile_dir: Path = Field(
        default=Path.home() / ".devops-agent" / "edge-profile",
        description="Persistent Edge profile directory",
    )

    @field_validator("work_dir", "edge_profile_dir", mode="before")
    @classmethod
    def _expand_home(cls, v: Any) -> Any:
        """Expand ~ to the user's home directory."""
        if isinstance(v, str):
            return Path(v).expanduser()
        if isinstance(v, Path):
            return v.expanduser()
        return v

    default_merge_detection: MergeDetectionMode = Field(
        default=MergeDetectionMode.poll,
        description="Default merge detection mode",
    )
    poll_interval_seconds: int = Field(
        default=60,
        description="Default polling interval in seconds",
        ge=10,
    )
    poll_timeout_seconds: int = Field(
        default=3600,
        description="Default polling timeout in seconds",
        ge=60,
    )
    default_notification_channels: list[str] = Field(
        default_factory=list,
        description="Default notification channel names",
    )
    repos_file: str = Field(
        default="repos.yaml",
        description="Path to repos config (relative to config dir)",
    )
    environments_file: str = Field(
        default="environments.yaml",
        description="Path to environments config (relative to config dir)",
    )
    notifications_file: str = Field(
        default="notifications.yaml",
        description="Path to notifications config (relative to config dir)",
    )
    log_level: str = Field(default="INFO", description="Logging verbosity")
    log_json: bool = Field(default=True, description="Output logs as JSON")
    login_targets: list[str] = Field(
        default_factory=list,
        description="URLs the dev must authenticate against during init",
    )


# ── repos.yaml ─────────────────────────────────────────────────────────────────


class RepoConfig(BaseModel):
    """Single repository definition."""

    clone_url: str = Field(description="Git clone URL")
    platform: PlatformType = Field(description="Hosting platform type")
    pr_create_url_template: str = Field(
        default="",
        description="URL template for creating PRs (supports ${branch} substitution)",
    )
    pr_view_url_template: str = Field(
        default="",
        description="URL template for viewing PRs (supports ${pr_id} substitution)",
    )
    pr_template_path: str = Field(
        default="",
        description="Path to PR template inside the repo",
    )
    title_convention: str = Field(
        default="",
        description="Regex pattern for PR title convention",
    )
    default_reviewers: list[str] = Field(default_factory=list)
    required_labels: list[str] = Field(default_factory=list)


class ReposConfig(BaseModel):
    """All repos (~/.devops-agent/repos.yaml)."""

    repos: dict[str, RepoConfig] = Field(
        default_factory=dict,
        description="Repos keyed by short name",
    )


# ── environments.yaml ──────────────────────────────────────────────────────────


class HealthCheckConfig(BaseModel):
    """Health check definition for an environment."""

    url: str = Field(description="Health check URL")
    expected_status: int = Field(default=200)
    expected_body: str = Field(default="", description="Substring expected in response body")
    timeout_seconds: int = Field(default=300, ge=10)


class EnvironmentConfig(BaseModel):
    """Single deploy target definition."""

    deploy_portal_url: str = Field(default="", description="URL to deploy portal")
    deploy_trigger: DeployTriggerType = Field(description="How deploys are triggered")
    required_params: dict[str, str] = Field(
        default_factory=dict,
        description="Required parameters for deploy (name -> description)",
    )
    health_checks: list[HealthCheckConfig] = Field(default_factory=list)
    monitor_timeout_seconds: int = Field(default=600, ge=30)
    repos: list[str] = Field(
        default_factory=list,
        description="Associated repo short names",
    )


class EnvironmentsConfig(BaseModel):
    """All environments (~/.devops-agent/environments.yaml)."""

    environments: dict[str, EnvironmentConfig] = Field(
        default_factory=dict,
        description="Environments keyed by short name",
    )


# ── notifications.yaml ─────────────────────────────────────────────────────────


class NotificationChannel(BaseModel):
    """Named notification channel."""

    url: str = Field(description="Slack/Teams web deep-link URL")
    platform: NotificationPlatform = Field(description="Platform type")


class NotificationsConfig(BaseModel):
    """Notification channels and templates (~/.devops-agent/notifications.yaml)."""

    channels: dict[str, NotificationChannel] = Field(
        default_factory=dict,
        description="Channels keyed by name",
    )
    templates: dict[str, str] = Field(
        default_factory=dict,
        description="Message templates keyed by event type (e.g., task_blocked, task_complete)",
    )


# ── task-configs/*.yaml ────────────────────────────────────────────────────────


class StepInvocation(BaseModel):
    """A single step in a task-config's step sequence."""

    step: str = Field(description="Step primitive name (e.g., shell.run, pr.create)")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the step primitive",
    )
    name: str = Field(default="", description="Optional human-readable label for this step")
    on_failure: str = Field(
        default="pause_and_notify",
        description="Failure behavior override (v1: always pause_and_notify)",
    )


class MergeDetection(BaseModel):
    """Merge detection configuration for a task."""

    mode: MergeDetectionMode = Field(description="poll or suspend")
    interval_seconds: int | None = Field(
        default=None,
        description="Poll interval (only for poll mode)",
        ge=10,
    )
    timeout_seconds: int | None = Field(
        default=None,
        description="Poll timeout (only for poll mode)",
        ge=60,
    )

    @model_validator(mode="after")
    def _validate_poll_params(self) -> MergeDetection:
        if self.mode == MergeDetectionMode.poll:
            if self.interval_seconds is None:
                self.interval_seconds = 60
            if self.timeout_seconds is None:
                self.timeout_seconds = 3600
        return self


class TaskConfig(BaseModel):
    """A task type definition (one file in task-configs/)."""

    name: str = Field(description="Unique identifier for this task type")
    description: str = Field(default="", description="Human-readable purpose")
    references: dict[str, str] = Field(
        default_factory=dict,
        description="Referenced config keys (e.g., repo: my-repo, env: staging)",
    )
    merge_detection: MergeDetection | None = Field(
        default=None,
        description="Merge detection config (overrides global default)",
    )
    notifications: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Per-event channel routing (event_type -> [channel_names])",
    )
    steps: list[StepInvocation] = Field(
        description="Ordered list of step invocations",
        min_length=1,
    )
    on_failure: str = Field(
        default="pause_and_notify",
        description="Default failure behavior",
    )


# ── Activation file ───────────────────────────────────────────────────────────


class Activation(BaseModel):
    """What a dev drops into pending/ to trigger a task run."""

    task_config: str = Field(description="Name of the task-config to use")
    variables: dict[str, str] = Field(
        default_factory=dict,
        description="Per-run variables (work_item, summary, branch_suffix, etc.)",
    )
    task_id: str = Field(
        default="",
        description="Optional explicit task ID (auto-generated if empty)",
    )
