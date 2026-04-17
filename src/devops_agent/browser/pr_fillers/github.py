"""GitHub PR page filler."""

from __future__ import annotations

from typing import Any


class GitHubPrFiller:
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
        title_input = page.locator('#pull_request_title')
        await title_input.fill(title)

        # Fill description
        body_input = page.locator('#pull_request_body')
        await body_input.fill(description)

        # Add reviewers
        if reviewers:
            reviewer_btn = page.locator('#reviewers-select-menu summary')
            await reviewer_btn.click()
            for reviewer in reviewers:
                search = page.locator('#review-filter-field')
                await search.fill(reviewer)
                await page.wait_for_timeout(500)
                item = page.locator(f'.select-menu-item:has-text("{reviewer}")')
                await item.click()
            await reviewer_btn.click()  # close

        # Add labels
        if labels:
            label_btn = page.locator('#labels-select-menu summary')
            await label_btn.click()
            for label in labels:
                search = page.locator('#label-filter-field')
                await search.fill(label)
                await page.wait_for_timeout(500)
                item = page.locator(f'.select-menu-item:has-text("{label}")')
                await item.click()
            await label_btn.click()  # close

        # Submit
        submit_btn = page.locator('button:has-text("Create pull request")').first
        await submit_btn.click()
        await page.wait_for_timeout(3000)

        return page.url
