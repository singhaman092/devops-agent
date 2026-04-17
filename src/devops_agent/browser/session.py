"""Browser session management — one active session per task."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from devops_agent.browser.profile import close_context, create_persistent_context


class BrowserSession:
    """Manages a single browser session for a task."""

    def __init__(self, profile_dir: Path) -> None:
        self._profile_dir = profile_dir
        self._context: Any = None
        self._page: Any = None

    async def start(self, headless: bool = False) -> Any:
        """Start the browser session. Returns the active page."""
        self._context = await create_persistent_context(
            self._profile_dir, headless=headless
        )
        pages = self._context.pages
        if pages:
            self._page = pages[0]
        else:
            self._page = await self._context.new_page()
        return self._page

    async def stop(self) -> None:
        """Stop the browser session."""
        if self._context:
            await close_context(self._context)
            self._context = None
            self._page = None

    @property
    def page(self) -> Any:
        return self._page

    @property
    def context(self) -> Any:
        return self._context
