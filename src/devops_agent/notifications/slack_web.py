"""Slack web driver — post messages via browser automation."""

from __future__ import annotations

import time
from typing import Any

# Multiple selectors tried in order — handles Slack web UI changes
COMPOSER_SELECTORS = [
    '[data-qa="message_input"] [contenteditable="true"]',
    '.ql-editor[contenteditable="true"]',
    '[aria-label="Message"] [contenteditable="true"]',
    'div[role="textbox"][contenteditable="true"]',
]


async def send_slack_message(page: Any, message: str) -> None:
    """Post a message in the currently visible Slack channel.

    Tries multiple selectors for the message composer to handle UI changes.
    """
    composer = None
    for selector in COMPOSER_SELECTORS:
        try:
            locator = page.locator(selector).first
            await locator.wait_for(state="visible", timeout=5000)
            composer = locator
            break
        except Exception:
            continue

    if composer is None:
        raise RuntimeError(
            "Could not find Slack message composer. "
            f"Tried selectors: {COMPOSER_SELECTORS}"
        )

    await composer.click()

    # Use clipboard paste for multi-line messages to avoid autocomplete
    if "\n" in message:
        await page.evaluate(
            "text => navigator.clipboard.writeText(text)",
            message,
        )
        modifier = "Meta" if page.context.browser.browser_type.name == "webkit" else "Control"
        await page.keyboard.press(f"{modifier}+v")
    else:
        await page.keyboard.insert_text(message)

    # Small delay to let the message render
    await page.wait_for_timeout(500)
    await page.keyboard.press("Enter")

    # Wait for the message to appear
    await page.wait_for_timeout(2000)
