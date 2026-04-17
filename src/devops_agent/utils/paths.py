"""General path utilities."""

from __future__ import annotations

from pathlib import Path


def ensure_parent(path: Path) -> Path:
    """Ensure the parent directory of a path exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
