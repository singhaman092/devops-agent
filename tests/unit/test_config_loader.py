"""Tests for config loader."""

from __future__ import annotations

import pytest
from pathlib import Path

from devops_agent.config.loader import (
    ConfigError,
    load_activation,
    load_agent_config,
    load_all_task_configs,
    load_task_config,
    validate_file,
)


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory with sample files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # config.yaml
    (config_dir / "config.yaml").write_text(
        "log_level: DEBUG\npoll_interval_seconds: 30\n"
    )

    # repos.yaml
    (config_dir / "repos.yaml").write_text(
        "repos:\n  test-repo:\n    clone_url: https://example.com/repo.git\n    platform: github\n"
    )

    # environments.yaml
    (config_dir / "environments.yaml").write_text(
        "environments:\n  staging:\n    deploy_trigger: cli\n"
    )

    # notifications.yaml
    (config_dir / "notifications.yaml").write_text(
        "channels: {}\ntemplates: {}\n"
    )

    # task-configs/
    tc_dir = config_dir / "task-configs"
    tc_dir.mkdir()
    (tc_dir / "test-task.yaml").write_text(
        "name: test-task\ndescription: A test\nsteps:\n  - step: shell.run\n    params:\n      command: echo hi\n"
    )

    return config_dir


class TestLoadAgentConfig:
    def test_loads_from_dir(self, tmp_config_dir: Path) -> None:
        cfg = load_agent_config(tmp_config_dir)
        assert cfg.log_level == "DEBUG"
        assert cfg.poll_interval_seconds == 30

    def test_default_when_missing(self, tmp_path: Path) -> None:
        cfg = load_agent_config(tmp_path)
        assert cfg.log_level == "INFO"


class TestLoadTaskConfig:
    def test_loads_task_config(self, tmp_config_dir: Path) -> None:
        tc = load_task_config(tmp_config_dir / "task-configs" / "test-task.yaml")
        assert tc.name == "test-task"
        assert len(tc.steps) == 1
        assert tc.steps[0].step == "shell.run"


class TestLoadAllTaskConfigs:
    def test_loads_all(self, tmp_config_dir: Path) -> None:
        configs = load_all_task_configs(tmp_config_dir)
        assert "test-task" in configs


class TestValidateFile:
    def test_valid_config(self, tmp_config_dir: Path) -> None:
        result = validate_file(tmp_config_dir / "config.yaml")
        assert result == "ok"

    def test_valid_repos(self, tmp_config_dir: Path) -> None:
        result = validate_file(tmp_config_dir / "repos.yaml")
        assert result == "ok"

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text(": [invalid")
        with pytest.raises(ConfigError):
            validate_file(bad)

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="not found"):
            validate_file(tmp_path / "nonexistent.yaml")


class TestLoadActivation:
    def test_load_activation(self, tmp_path: Path) -> None:
        act_file = tmp_path / "my-activation.yaml"
        act_file.write_text(
            "task_config: deploy-new-env\nvariables:\n  branch_suffix: fix-123\n"
        )
        act = load_activation(act_file)
        assert act.task_config == "deploy-new-env"
        assert act.variables["branch_suffix"] == "fix-123"
