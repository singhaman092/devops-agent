"""Tests for config schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from devops_agent.config.schema import (
    Activation,
    AgentConfig,
    EnvironmentConfig,
    EnvironmentsConfig,
    HealthCheckConfig,
    MergeDetection,
    MergeDetectionMode,
    NotificationChannel,
    NotificationsConfig,
    PlatformType,
    RepoConfig,
    ReposConfig,
    StepInvocation,
    TaskConfig,
)


class TestAgentConfig:
    def test_defaults(self) -> None:
        cfg = AgentConfig()
        assert cfg.log_level == "INFO"
        assert cfg.poll_interval_seconds == 60
        assert cfg.default_merge_detection == MergeDetectionMode.poll

    def test_custom_values(self) -> None:
        cfg = AgentConfig(
            log_level="DEBUG",
            poll_interval_seconds=30,
            poll_timeout_seconds=7200,
        )
        assert cfg.log_level == "DEBUG"
        assert cfg.poll_interval_seconds == 30

    def test_poll_interval_minimum(self) -> None:
        with pytest.raises(ValidationError):
            AgentConfig(poll_interval_seconds=5)


class TestRepoConfig:
    def test_minimal(self) -> None:
        repo = RepoConfig(clone_url="https://example.com/repo.git", platform=PlatformType.github)
        assert repo.platform == PlatformType.github
        assert repo.default_reviewers == []

    def test_full(self) -> None:
        repo = RepoConfig(
            clone_url="https://example.com/repo.git",
            platform=PlatformType.azure_devops,
            pr_create_url_template="https://example.com/pr?branch=${branch}",
            default_reviewers=["alice", "bob"],
            required_labels=["deploy"],
        )
        assert len(repo.default_reviewers) == 2


class TestEnvironmentConfig:
    def test_health_checks(self) -> None:
        env = EnvironmentConfig(
            deploy_trigger="portal_click",
            health_checks=[
                HealthCheckConfig(url="https://example.com/health", expected_status=200),
            ],
        )
        assert len(env.health_checks) == 1
        assert env.health_checks[0].expected_status == 200


class TestNotificationsConfig:
    def test_channels_and_templates(self) -> None:
        cfg = NotificationsConfig(
            channels={"dev": NotificationChannel(url="https://slack.com/dev", platform="slack")},
            templates={"task_complete": "Task ${task_id} done"},
        )
        assert "dev" in cfg.channels
        assert "task_complete" in cfg.templates


class TestTaskConfig:
    def test_minimal(self) -> None:
        tc = TaskConfig(
            name="test-task",
            steps=[StepInvocation(step="shell.run", params={"command": "echo hello"})],
        )
        assert tc.name == "test-task"
        assert len(tc.steps) == 1

    def test_empty_steps_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TaskConfig(name="bad", steps=[])

    def test_merge_detection_poll_defaults(self) -> None:
        md = MergeDetection(mode=MergeDetectionMode.poll)
        assert md.interval_seconds == 60
        assert md.timeout_seconds == 3600


class TestActivation:
    def test_minimal(self) -> None:
        a = Activation(task_config="deploy-new-env")
        assert a.task_config == "deploy-new-env"
        assert a.variables == {}

    def test_with_variables(self) -> None:
        a = Activation(
            task_config="deploy-new-env",
            variables={"branch_suffix": "hotfix-123", "pr_title": "Fix bug"},
        )
        assert a.variables["branch_suffix"] == "hotfix-123"
