"""Teams web driver — post messages via browser automation."""

from __future__ import annotations

from typing import Any

# Multiple selectors for Teams message composer
COMPOSER_SELECTORS = [
    '[data-tid="ckeditor"] [contenteditable="true"]',
    '[data-tid="newMessageCommands"] + div [contenteditable="true"]',
    'div[role="textbox"][contenteditable="true"]',
    '.cke_editable[contenteditable="true"]',
]


async def send_teams_message(page: Any, message: str) -> None:
    """Post a message in the currently visible Teams channel.

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
            "Could not find Teams message composer. "
            f"Tried selectors: {COMPOSER_SELECTORS}"
        )

    await composer.click()

    # Use clipboard paste for multi-line messages
    if "\n" in message:
        await page.evaluate(
            "text => navigator.clipboard.writeText(text)",
            message,
        )
        await page.keyboard.press("Control+v")
    else:
        await page.keyboard.insert_text(message)

    await page.wait_for_timeout(500)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(2000)
