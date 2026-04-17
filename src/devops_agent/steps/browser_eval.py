"""browser.eval step primitive — execute JavaScript in the browser page."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class BrowserEval:
    @property
    def name(self) -> str:
        return "browser.eval"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        expression = ctx.resolve_var(params.get("expression", ""))
        if not expression:
            result.mark_failed("No expression specified")
            return result

        if ctx.browser_session is None:
            result.mark_failed("No browser session available")
            return result

        try:
            page = ctx.browser_session
            ret = await page.evaluate(expression)
            result.mark_success({"return_value": str(ret) if ret is not None else ""})
        except Exception as e:
            result.mark_failed(f"JS eval failed: {e}")

        return result
