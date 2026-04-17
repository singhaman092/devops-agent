"""PR filler selection by platform."""

from __future__ import annotations

from typing import Any, Protocol

from devops_agent.config.schema import PlatformType


class PrFiller(Protocol):
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
        """Fill and submit a PR. Returns the created PR URL."""
        ...


def get_pr_filler(platform: PlatformType) -> PrFiller:
    if platform == PlatformType.azure_devops:
        from devops_agent.browser.pr_fillers.azure_devops import AzureDevOpsPrFiller

        return AzureDevOpsPrFiller()
    elif platform == PlatformType.github:
        from devops_agent.browser.pr_fillers.github import GitHubPrFiller

        return GitHubPrFiller()
    elif platform == PlatformType.gitlab:
        from devops_agent.browser.pr_fillers.gitlab import GitLabPrFiller

        return GitLabPrFiller()
    elif platform == PlatformType.bitbucket:
        from devops_agent.browser.pr_fillers.bitbucket import BitbucketPrFiller

        return BitbucketPrFiller()
    raise ValueError(f"Unknown platform: {platform}")
