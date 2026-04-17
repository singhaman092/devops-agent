"""browser.press step primitive — press keyboard keys in the browser."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class BrowserPress:
    @property
    def name(self) -> str:
        return "browser.press"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        key = ctx.resolve_var(params.get("key", ""))
        if not key:
            result.mark_failed("No key specified")
            return result

        if ctx.browser_session is None:
            result.mark_failed("No browser session available")
            return result

        try:
            page = ctx.browser_session
            # Support pressing multiple keys in sequence
            keys = params.get("keys", [])
            if keys:
                for k in keys:
                    await page.keyboard.press(k)
            else:
                await page.keyboard.press(key)
            result.mark_success()
        except Exception as e:
            result.mark_failed(f"Key press failed: {e}")

        return result


@register_step
class BrowserType:
    """Type text character by character in the browser (not into a specific selector)."""

    @property
    def name(self) -> str:
        return "browser.type"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        text = ctx.resolve_var(params.get("text", ""))
        if not text:
            result.mark_failed("No text specified")
            return result

        if ctx.browser_session is None:
            result.mark_failed("No browser session available")
            return result

        try:
            page = ctx.browser_session
            await page.keyboard.type(text, delay=int(params.get("delay", 50)))
            result.mark_success()
        except Exception as e:
            result.mark_failed(f"Type failed: {e}")

        return result
