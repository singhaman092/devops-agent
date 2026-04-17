"""browser.click step primitive."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class BrowserClick:
    @property
    def name(self) -> str:
        return "browser.click"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        selector = ctx.resolve_var(params.get("selector", ""))
        if not selector:
            result.mark_failed("No selector specified")
            return result

        if ctx.browser_session is None:
            result.mark_failed("No browser session available")
            return result

        try:
            page = ctx.browser_session
            timeout = int(params.get("timeout", 30000))
            force = bool(params.get("force", False))
            await page.click(selector, timeout=timeout, force=force)
            result.mark_success()
        except Exception as e:
            result.mark_failed(f"Click failed: {e}")

        return result
