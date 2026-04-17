"""Load and validate global configs and task-configs from ~/.devops-agent/."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml

T = TypeVar("T")
from pydantic import ValidationError

from devops_agent.config.paths import get_config_dir, get_task_configs_dir
from devops_agent.config.schema import (
    Activation,
    AgentConfig,
    EnvironmentsConfig,
    NotificationsConfig,
    ReposConfig,
    TaskConfig,
)


class ConfigError(Exception):
    """Raised when config loading or validation fails."""

    def __init__(self, path: Path, message: str, details: str = "") -> None:
        self.path = path
        self.details = details
        super().__init__(f"{path}: {message}" + (f"\n{details}" if details else ""))


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning an empty dict if file is missing or empty."""
    if not path.exists():
        raise ConfigError(path, "File not found")
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(path, "Invalid YAML", str(e)) from e
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(path, f"Expected a YAML mapping, got {type(data).__name__}")
    return data


def _validate_model(model_cls: type[T], data: dict[str, Any], path: Path) -> T:
    """Validate data against a Pydantic model with clear error reporting."""
    try:
        return model_cls(**data)  # type: ignore[call-arg]
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            errors.append(f"  {loc}: {err['msg']}")
        detail = "\n".join(errors)
        raise ConfigError(path, "Validation failed", detail) from e


def load_agent_config(config_dir: Path | None = None) -> AgentConfig:
    """Load config.yaml."""
    config_dir = config_dir or get_config_dir()
    path = config_dir / "config.yaml"
    if not path.exists():
        return AgentConfig()
    data = _load_yaml(path)
    return _validate_model(AgentConfig, data, path)


def load_repos_config(config_dir: Path | None = None) -> ReposConfig:
    """Load repos.yaml."""
    config_dir = config_dir or get_config_dir()
    agent_cfg = load_agent_config(config_dir)
    path = config_dir / agent_cfg.repos_file
    if not path.exists():
        return ReposConfig()
    data = _load_yaml(path)
    return _validate_model(ReposConfig, data, path)


def load_environments_config(config_dir: Path | None = None) -> EnvironmentsConfig:
    """Load environments.yaml."""
    config_dir = config_dir or get_config_dir()
    agent_cfg = load_agent_config(config_dir)
    path = config_dir / agent_cfg.environments_file
    if not path.exists():
        return EnvironmentsConfig()
    data = _load_yaml(path)
    return _validate_model(EnvironmentsConfig, data, path)


def load_notifications_config(config_dir: Path | None = None) -> NotificationsConfig:
    """Load notifications.yaml."""
    config_dir = config_dir or get_config_dir()
    agent_cfg = load_agent_config(config_dir)
    path = config_dir / agent_cfg.notifications_file
    if not path.exists():
        return NotificationsConfig()
    data = _load_yaml(path)
    return _validate_model(NotificationsConfig, data, path)


def load_task_config(path: Path) -> TaskConfig:
    """Load and validate a single task-config YAML file."""
    data = _load_yaml(path)
    return _validate_model(TaskConfig, data, path)


def load_all_task_configs(config_dir: Path | None = None) -> dict[str, TaskConfig]:
    """Load all task-configs from the task-configs/ directory."""
    tc_dir = config_dir / "task-configs" if config_dir else get_task_configs_dir()
    if not tc_dir.exists():
        return {}
    configs: dict[str, TaskConfig] = {}
    for f in sorted(tc_dir.glob("*.yaml")):
        tc = load_task_config(f)
        configs[tc.name] = tc
    return configs


def load_activation(path: Path) -> Activation:
    """Load and validate an activation file."""
    data = _load_yaml(path)
    return _validate_model(Activation, data, path)


def validate_file(path: Path) -> str:
    """Validate any config file. Returns 'ok' or raises ConfigError."""
    data = _load_yaml(path)
    name = path.stem.lower()

    if name == "config":
        _validate_model(AgentConfig, data, path)
    elif name == "repos":
        _validate_model(ReposConfig, data, path)
    elif name == "environments":
        _validate_model(EnvironmentsConfig, data, path)
    elif name == "notifications":
        _validate_model(NotificationsConfig, data, path)
    else:
        # Try as task-config first, then activation
        try:
            _validate_model(TaskConfig, data, path)
        except ConfigError:
            _validate_model(Activation, data, path)

    return "ok"
