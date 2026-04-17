"""Persistent browser context management for Edge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from devops_agent.config.paths import resolve_edge_binary

# Track Playwright instance so we can stop it on cleanup
_playwright_instance: Any = None


async def create_persistent_context(
    profile_dir: Path,
    headless: bool = False,
) -> Any:
    """Create a Playwright persistent browser context using Edge.

    Returns a BrowserContext.
    """
    global _playwright_instance

    from playwright.async_api import async_playwright

    _playwright_instance = await async_playwright().start()

    edge_path = resolve_edge_binary()
    launch_args = [
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=msEdgeEnhancedSmartScreen",
        "--disable-features=ThirdPartyCookieBlocking",
        "--disable-site-isolation-trials",
    ]

    context = await _playwright_instance.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        channel="msedge" if edge_path is None else None,
        executable_path=str(edge_path) if edge_path else None,
        headless=headless,
        args=launch_args,
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
    )

    return context


async def close_context(context: Any) -> None:
    """Close a browser context and the Playwright instance."""
    global _playwright_instance
    try:
        await context.close()
    except Exception:
        pass
    try:
        if _playwright_instance is not None:
            await _playwright_instance.stop()
            _playwright_instance = None
    except Exception:
        pass
