"""Tests for step registry."""

from __future__ import annotations

import pytest

import devops_agent.steps  # noqa: F401 — triggers registration
from devops_agent.steps.registry import get_step, list_steps


class TestStepRegistry:
    def test_all_steps_registered(self) -> None:
        steps = list_steps()
        expected = [
            "browser.click",
            "browser.fill",
            "browser.navigate",
            "browser.screenshot",
            "browser.wait_for",
            "deploy.trigger",
            "git.branch",
            "git.clone",
            "git.commit",
            "git.push",
            "monitor.http_check",
            "monitor.version_match",
            "notify.send",
            "ocr.find_text",
            "os.click",
            "os.hotkey",
            "os.type",
            "pr.create",
            "pr.wait_merge",
            "screenshot.capture",
            "shell.run",
            "wait.sleep",
        ]
        assert steps == expected

    def test_get_known_step(self) -> None:
        step = get_step("shell.run")
        assert step.name == "shell.run"

    def test_get_unknown_step_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown step primitive"):
            get_step("nonexistent.step")
