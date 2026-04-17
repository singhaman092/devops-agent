"""Window-specific screenshots via pywin32 PrintWindow (occluded-safe)."""

from __future__ import annotations

from pathlib import Path

# TODO: Full pywin32 PrintWindow implementation for v1.
# For now, falls back to mss region capture of the window rect.


def capture_window(output_path: Path, window_title: str) -> Path:
    """Capture a specific window by title."""
    try:
        import pygetwindow as gw  # type: ignore[import-untyped]

        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            raise ValueError(f"Window not found: {window_title}")
        win = windows[0]
        from devops_agent.capture.mss_backend import capture_region

        return capture_region(
            output_path,
            left=win.left,
            top=win.top,
            width=win.width,
            height=win.height,
        )
    except ImportError:
        raise RuntimeError("pygetwindow is required for window capture")
