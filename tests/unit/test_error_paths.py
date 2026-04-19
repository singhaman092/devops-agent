"""Tests for error paths — bad configs, edge cases, failure modes."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from devops_agent.config.loader import ConfigError, validate_file
from devops_agent.config.schema import (
    Activation,
    AgentConfig,
    EnvironmentConfig,
    RepoConfig,
    StepInvocation,
    TaskConfig,
)
from devops_agent.steps.base import StepContext
from devops_agent.tasks.models import StepResult, TaskState


class TestBadConfigs:
    def test_invalid_platform_type(self) -> None:
        with pytest.raises(ValidationError):
            RepoConfig(clone_url="https://x.com/r.git", platform="svn")

    def test_negative_poll_interval(self) -> None:
        with pytest.raises(ValidationError):
            AgentConfig(poll_interval_seconds=-1)

    def test_environment_low_timeout(self) -> None:
        with pytest.raises(ValidationError):
            EnvironmentConfig(deploy_trigger="cli", monitor_timeout_seconds=5)

    def test_task_config_no_steps(self) -> None:
        with pytest.raises(ValidationError):
            TaskConfig(name="bad", steps=[])

    def test_activation_missing_task_config(self) -> None:
        with pytest.raises(ValidationError):
            Activation()

    def test_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("{invalid yaml: [")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            validate_file(bad)

    def test_yaml_not_a_mapping(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("- just\n- a\n- list")
        with pytest.raises(ConfigError, match="Expected a YAML mapping"):
            validate_file(bad)


class TestStepErrorPaths:
    def test_shell_run_no_command(self) -> None:
        from devops_agent.steps.shell import ShellRun

        step = ShellRun()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No command" in result.error_message

    def test_git_clone_no_url(self) -> None:
        from devops_agent.steps.git import GitClone

        step = GitClone()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No clone URL" in result.error_message

    def test_git_branch_no_name(self) -> None:
        from devops_agent.steps.git import GitBranch

        step = GitBranch()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No branch name" in result.error_message

    def test_git_commit_no_message(self) -> None:
        from devops_agent.steps.git import GitCommit

        step = GitCommit()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No commit message" in result.error_message

    def test_browser_navigate_no_session(self) -> None:
        from devops_agent.steps.browser_navigate import BrowserNavigate

        step = BrowserNavigate()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {"url": "https://example.com"}))
        assert result.status == "failed"
        assert "No browser session" in result.error_message

    def test_browser_click_no_selector(self) -> None:
        from devops_agent.steps.browser_click import BrowserClick

        step = BrowserClick()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"), browser_session=MagicMock())
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No selector" in result.error_message

    def test_os_click_no_coords(self) -> None:
        from devops_agent.steps.os_click import OsClick

        step = OsClick()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "coordinates required" in result.error_message

    def test_os_type_no_text(self) -> None:
        from devops_agent.steps.os_type import OsType

        step = OsType()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No text" in result.error_message

    def test_os_hotkey_no_keys(self) -> None:
        from devops_agent.steps.os_type import OsHotkey

        step = OsHotkey()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No keys" in result.error_message

    def test_ocr_no_text(self) -> None:
        from devops_agent.steps.ocr_find import OcrFindText

        step = OcrFindText()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No text" in result.error_message

    def test_monitor_http_no_url(self) -> None:
        from devops_agent.steps.monitor_http import MonitorHttpCheck

        step = MonitorHttpCheck()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No URL" in result.error_message

    def test_monitor_version_missing_params(self) -> None:
        from devops_agent.steps.monitor_version import MonitorVersionMatch

        step = MonitorVersionMatch()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "required" in result.error_message

    def test_notify_no_channel(self) -> None:
        from devops_agent.steps.notify import NotifySend

        step = NotifySend()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No channel" in result.error_message

    def test_deploy_trigger_no_environment(self) -> None:
        from devops_agent.steps.deploy_trigger import DeployTrigger

        step = DeployTrigger()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No environment" in result.error_message

    def test_pr_wait_merge_no_url(self) -> None:
        from devops_agent.steps.pr_wait_merge import PrWaitMerge

        step = PrWaitMerge()
        ctx = StepContext(task_id="t", work_dir=Path("/tmp"))
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "No PR URL" in result.error_message


class TestTaskStateEdgeCases:
    def test_current_step_all_done(self) -> None:
        state = TaskState(task_id="t")
        state.step_results = [
            StepResult(step_name="a", status="success"),
            StepResult(step_name="b", status="success"),
        ]
        assert state.current_step_index() == 2

    def test_current_step_empty(self) -> None:
        state = TaskState(task_id="t")
        assert state.current_step_index() == 0

    def test_touch_updates_timestamp(self) -> None:
        state = TaskState(task_id="t")
        old = state.updated_at
        import time
        time.sleep(0.01)
        state.touch()
        assert state.updated_at >= old
