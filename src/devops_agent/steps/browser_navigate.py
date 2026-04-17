"""browser.navigate step primitive."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class BrowserNavigate:
    @property
    def name(self) -> str:
        return "browser.navigate"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        url = ctx.resolve_var(params.get("url", ""))
        if not url:
            result.mark_failed("No URL specified")
            return result

        if ctx.browser_session is None:
            result.mark_failed("No browser session available. Run 'devops-agent init' first.")
            return result

        try:
            page = ctx.browser_session
            await page.goto(url, wait_until=params.get("wait_until", "domcontentloaded"))
            result.mark_success({"url": page.url, "title": await page.title()})
        except Exception as e:
            # Check for login redirect
            if ctx.browser_session and "login" in str(await ctx.browser_session.url).lower():
                result.mark_failed(f"auth_required: Redirected to login page. Re-run 'devops-agent init'.")
            else:
                result.mark_failed(f"Navigation failed: {e}")

        return result
