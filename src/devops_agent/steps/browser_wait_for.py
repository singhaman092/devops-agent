"""browser.wait_for step primitive — wait for a selector or condition."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class BrowserWaitFor:
    @property
    def name(self) -> str:
        return "browser.wait_for"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        selector = ctx.resolve_var(params.get("selector", ""))
        text = ctx.resolve_var(params.get("text", ""))
        state = params.get("state", "visible")  # visible | hidden | attached | detached
        timeout = int(params.get("timeout", 30000))

        if not selector and not text:
            result.mark_failed("Either selector or text is required")
            return result

        if ctx.browser_session is None:
            result.mark_failed("No browser session available")
            return result

        try:
            page = ctx.browser_session
            if selector:
                await page.wait_for_selector(selector, state=state, timeout=timeout)
            elif text:
                await page.wait_for_selector(f"text={text}", state=state, timeout=timeout)
            result.mark_success()
        except Exception as e:
            result.mark_failed(f"Wait failed: {e}")

        return result
