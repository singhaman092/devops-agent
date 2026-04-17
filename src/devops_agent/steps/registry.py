"""Step primitive registry — maps names to Step classes."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step

_REGISTRY: dict[str, type[Step]] = {}


def register_step(cls: type[Step]) -> type[Step]:
    """Decorator to register a step class by its name."""
    # Instantiate to get the name property
    instance = cls()  # type: ignore[call-arg]
    _REGISTRY[instance.name] = cls
    return cls


def get_step(name: str) -> Step:
    """Look up a step by name and return an instance."""
    cls = _REGISTRY.get(name)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise KeyError(f"Unknown step primitive '{name}'. Available: {available}")
    return cls()  # type: ignore[call-arg]


def list_steps() -> list[str]:
    """Return sorted list of registered step names."""
    return sorted(_REGISTRY.keys())
