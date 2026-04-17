"""Azure DevOps PR page filler."""

from __future__ import annotations

from typing import Any


class AzureDevOpsPrFiller:
    async def create_pr(
        self,
        page: Any,
        url: str,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str,
        reviewers: list[str],
        labels: list[str],
    ) -> str:
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Fill title
        title_input = page.locator('input[aria-label="Enter a title"]')
        await title_input.fill(title)

        # Fill description (rich editor)
        desc_editor = page.locator('.repos-pr-description .ql-editor, [role="textbox"]').first
        await desc_editor.click()
        await page.keyboard.insert_text(description)

        # Add reviewers
        for reviewer in reviewers:
            reviewer_input = page.locator('[aria-label="Add required reviewers"]')
            await reviewer_input.fill(reviewer)
            await page.wait_for_timeout(500)
            await page.keyboard.press("Enter")

        # Submit
        create_btn = page.locator('button:has-text("Create")')
        await create_btn.click()
        await page.wait_for_timeout(3000)

        return page.url
