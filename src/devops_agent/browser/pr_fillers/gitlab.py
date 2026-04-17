"""GitLab MR page filler."""

from __future__ import annotations

from typing import Any


class GitLabPrFiller:
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
        title_input = page.locator('#merge_request_title')
        await title_input.fill(title)

        # Fill description
        body_input = page.locator('#merge_request_description')
        await body_input.fill(description)

        # Submit
        submit_btn = page.locator('input[name="commit"], button:has-text("Create merge request")')
        await submit_btn.first.click()
        await page.wait_for_timeout(3000)

        return page.url
