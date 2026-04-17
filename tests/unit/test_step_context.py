"""Tests for StepContext variable resolution."""

from __future__ import annotations

from pathlib import Path

from devops_agent.steps.base import StepContext


class TestStepContext:
    def test_resolve_var(self) -> None:
        ctx = StepContext(
            task_id="t1",
            work_dir=Path("/tmp"),
            variables={"branch": "main", "env": "staging"},
        )
        result = ctx.resolve_var("deploy/${branch} to ${env}")
        assert result == "deploy/main to staging"

    def test_resolve_var_with_outputs(self) -> None:
        ctx = StepContext(
            task_id="t1",
            work_dir=Path("/tmp"),
            variables={"branch": "main"},
            outputs={"pr_url": "https://example.com/pr/1"},
        )
        result = ctx.resolve_var("PR: ${pr_url} on ${branch}")
        assert result == "PR: https://example.com/pr/1 on main"

    def test_unresolved_var_kept(self) -> None:
        ctx = StepContext(task_id="t1", work_dir=Path("/tmp"))
        result = ctx.resolve_var("${unknown_var}")
        assert result == "${unknown_var}"
