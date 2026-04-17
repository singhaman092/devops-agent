"""pr.create step primitive — composite: navigate + fill PR template + submit."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


def _load_pr_template(ctx: StepContext, clone_subdir: str = "repo") -> str:
    """Load PR template from the cloned repo if configured."""
    if ctx.repo is None or not ctx.repo.pr_template_path:
        return ""

    # Check multiple possible clone locations
    candidates = [
        ctx.work_dir / clone_subdir / ctx.repo.pr_template_path,
        ctx.work_dir / ctx.repo.pr_template_path,
    ]
    # Also check outputs for clone_dir
    clone_dir = ctx.outputs.get("clone_dir", "")
    if clone_dir:
        candidates.insert(0, Path(clone_dir) / ctx.repo.pr_template_path)

    for path in candidates:
        if path.exists():
            return ctx.resolve_var(path.read_text(encoding="utf-8"))

    return ""


def _validate_title_convention(title: str, pattern: str) -> bool:
    """Check if a PR title matches the repo's convention pattern."""
    if not pattern:
        return True
    return bool(re.match(pattern, title))


@register_step
class PrCreate:
    @property
    def name(self) -> str:
        return "pr.create"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        if ctx.repo is None:
            result.mark_failed("No repo configured in task references")
            return result

        if ctx.browser_session is None:
            result.mark_failed("No browser session available")
            return result

        title = ctx.resolve_var(params.get("title", ""))
        description = ctx.resolve_var(params.get("description", ""))
        source_branch = ctx.resolve_var(params.get("source_branch", ""))
        target_branch = ctx.resolve_var(params.get("target_branch", "main"))
        reviewers = params.get("reviewers", ctx.repo.default_reviewers)
        labels = params.get("labels", ctx.repo.required_labels)

        if not title:
            result.mark_failed("PR title is required")
            return result

        # Validate title convention
        if ctx.repo.title_convention:
            if not _validate_title_convention(title, ctx.repo.title_convention):
                result.mark_failed(
                    f"PR title '{title}' does not match convention: {ctx.repo.title_convention}"
                )
                return result

        # Load PR template from repo if no description provided
        if not description:
            description = _load_pr_template(ctx)

        # Build PR creation URL
        pr_url = ctx.resolve_var(ctx.repo.pr_create_url_template)
        if not pr_url:
            result.mark_failed("No pr_create_url_template configured for repo")
            return result

        try:
            page = ctx.browser_session

            from devops_agent.browser.pr_fillers import get_pr_filler

            filler = get_pr_filler(ctx.repo.platform)
            pr_result_url = await filler.create_pr(
                page=page,
                url=pr_url,
                title=title,
                description=description,
                source_branch=source_branch,
                target_branch=target_branch,
                reviewers=reviewers,
                labels=labels,
            )

            # Screenshot
            screenshot_path = ctx.screenshot_dir / f"pr_create_{ctx.task_id}.png"
            await page.screenshot(path=str(screenshot_path))
            result.screenshot_paths.append(str(screenshot_path))

            result.mark_success({
                "pr_url": pr_result_url,
                "pr_title": title,
                "source_branch": source_branch,
                "target_branch": target_branch,
            })

        except Exception as e:
            # Check for auth redirect
            try:
                current_url = page.url
                if "login" in current_url.lower() or "signin" in current_url.lower():
                    result.mark_failed(
                        "auth_required: Redirected to login page during PR creation. "
                        "Re-run 'devops-agent init'."
                    )
                    return result
            except Exception:
                pass
            result.mark_failed(f"PR creation failed: {e}")

        return result
