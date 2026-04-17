"""Tests for notification template rendering."""

from __future__ import annotations

from devops_agent.notifications.templates import render_template


class TestRenderTemplate:
    def test_basic_substitution(self) -> None:
        result = render_template(
            "Task ${task_id} is ${status}",
            {"task_id": "abc123", "status": "complete"},
        )
        assert result == "Task abc123 is complete"

    def test_missing_var_kept(self) -> None:
        result = render_template("Hello ${name}", {})
        assert result == "Hello ${name}"

    def test_multiple_same_var(self) -> None:
        result = render_template("${x} and ${x}", {"x": "foo"})
        assert result == "foo and foo"

    def test_empty_template(self) -> None:
        result = render_template("", {"key": "val"})
        assert result == ""
