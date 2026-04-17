"""Bitbucket PR page filler."""

from __future__ import annotations

from typing import Any


class BitbucketPrFiller:
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
        title_input = page.locator('#pullrequest-title, [name="title"]').first
        await title_input.fill(title)

        # Fill description
        desc_input = page.locator('#pullrequest-description, [name="description"]').first
        await desc_input.fill(description)

        # Add reviewers
        if reviewers:
            reviewer_btn = page.locator('[data-testid="reviewer-select"]').first
            await reviewer_btn.click()
            for reviewer in reviewers:
                search = page.locator('input[placeholder*="reviewer"], input[placeholder*="Reviewer"]').first
                await search.fill(reviewer)
                await page.wait_for_timeout(500)
                item = page.locator(f'[role="option"]:has-text("{reviewer}")').first
                await item.click()

        # Submit
        submit_btn = page.locator('button:has-text("Create pull request")').first
        await submit_btn.click()
        await page.wait_for_timeout(3000)

        return page.url
