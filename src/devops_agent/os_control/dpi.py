"""DPI awareness setup for Windows."""

from __future__ import annotations


def set_dpi_awareness() -> bool:
    """Set per-monitor DPI awareness. Call at process startup.

    Returns True if successfully set.
    """
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # type: ignore[attr-defined]
        return True
    except (AttributeError, OSError):
        return False
