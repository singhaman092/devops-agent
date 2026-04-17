"""Window enumeration helpers via pygetwindow."""

from __future__ import annotations

from typing import Any


def find_window(title: str) -> Any | None:
    """Find a window by title substring."""
    import pygetwindow as gw  # type: ignore[import-untyped]

    windows = gw.getWindowsWithTitle(title)
    return windows[0] if windows else None


def list_windows() -> list[str]:
    """List all visible window titles."""
    import pygetwindow as gw  # type: ignore[import-untyped]

    return [w.title for w in gw.getAllWindows() if w.title.strip()]


def is_lock_screen_active() -> bool:
    """Check if the Windows lock screen is active."""
    try:
        import pygetwindow as gw  # type: ignore[import-untyped]

        windows = gw.getWindowsWithTitle("LockAppHost")
        return len(windows) > 0
    except Exception:
        return False
