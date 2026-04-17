"""Integration tests for PR primitives (with mocked browser)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from devops_agent.config.schema import PlatformType, RepoConfig
from devops_agent.steps.base import StepContext
from devops_agent.steps.pr_create import PrCreate, _load_pr_template, _validate_title_convention


class TestTitleConvention:
    def test_valid_conventional_commit(self) -> None:
        assert _validate_title_convention("feat(auth): add login", r"^(feat|fix|chore)\(.*\): .+")

    def test_invalid_conventional_commit(self) -> None:
        assert not _validate_title_convention("update stuff", r"^(feat|fix|chore)\(.*\): .+")

    def test_empty_pattern_always_valid(self) -> None:
        assert _validate_title_convention("anything", "")


class TestLoadPrTemplate:
    def test_loads_from_clone_dir(self, tmp_path: Path) -> None:
        repo = RepoConfig(
            clone_url="https://example.com/repo.git",
            platform=PlatformType.github,
            pr_template_path=".github/pull_request_template.md",
        )
        # Create the template file
        clone_dir = tmp_path / "repo"
        template_dir = clone_dir / ".github"
        template_dir.mkdir(parents=True)
        (template_dir / "pull_request_template.md").write_text(
            "## Summary\n${pr_description}\n\n## Testing\n- [ ] Tests pass"
        )

        ctx = StepContext(
            task_id="test",
            work_dir=tmp_path,
            repo=repo,
            variables={"pr_description": "Added new feature"},
        )

        template = _load_pr_template(ctx)
        assert "## Summary" in template
        assert "Added new feature" in template

    def test_returns_empty_when_no_template(self, tmp_path: Path) -> None:
        repo = RepoConfig(
            clone_url="https://example.com/repo.git",
            platform=PlatformType.github,
        )
        ctx = StepContext(task_id="test", work_dir=tmp_path, repo=repo)
        assert _load_pr_template(ctx) == ""


class TestPrCreate:
    def test_fails_without_repo(self) -> None:
        ctx = StepContext(task_id="test", work_dir=Path("/tmp"))
        step = PrCreate()
        result = asyncio.run(step.execute(ctx, {"title": "test"}))
        assert result.status == "failed"
        assert "No repo configured" in result.error_message

    def test_fails_without_browser(self) -> None:
        repo = RepoConfig(
            clone_url="https://example.com/repo.git",
            platform=PlatformType.github,
        )
        ctx = StepContext(task_id="test", work_dir=Path("/tmp"), repo=repo)
        step = PrCreate()
        result = asyncio.run(step.execute(ctx, {"title": "test"}))
        assert result.status == "failed"
        assert "No browser session" in result.error_message

    def test_fails_without_title(self) -> None:
        repo = RepoConfig(
            clone_url="https://example.com/repo.git",
            platform=PlatformType.github,
        )
        mock_page = MagicMock()
        ctx = StepContext(
            task_id="test",
            work_dir=Path("/tmp"),
            repo=repo,
            browser_session=mock_page,
        )
        step = PrCreate()
        result = asyncio.run(step.execute(ctx, {}))
        assert result.status == "failed"
        assert "title is required" in result.error_message

    def test_validates_title_convention(self) -> None:
        repo = RepoConfig(
            clone_url="https://example.com/repo.git",
            platform=PlatformType.github,
            title_convention=r"^(feat|fix)\(.*\): .+",
            pr_create_url_template="https://example.com/pr",
        )
        mock_page = MagicMock()
        ctx = StepContext(
            task_id="test",
            work_dir=Path("/tmp"),
            repo=repo,
            browser_session=mock_page,
        )
        step = PrCreate()
        result = asyncio.run(step.execute(ctx, {"title": "bad title"}))
        assert result.status == "failed"
        assert "convention" in result.error_message
