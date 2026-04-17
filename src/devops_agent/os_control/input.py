"""PyAutoGUI wrappers with DPI awareness."""

from __future__ import annotations

import pyautogui  # type: ignore[import-untyped]


def click(x: int, y: int, button: str = "left", clicks: int = 1) -> None:
    """Click at coordinates."""
    pyautogui.click(x=x, y=y, button=button, clicks=clicks)


def type_text(text: str, interval: float = 0.02) -> None:
    """Type text character by character."""
    pyautogui.typewrite(text, interval=interval)


def hotkey(*keys: str) -> None:
    """Press a key combination."""
    pyautogui.hotkey(*keys)


def move_to(x: int, y: int) -> None:
    """Move mouse to coordinates."""
    pyautogui.moveTo(x, y)
