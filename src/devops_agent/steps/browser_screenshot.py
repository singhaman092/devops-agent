"""browser.screenshot step primitive."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class BrowserScreenshot:
    @property
    def name(self) -> str:
        return "browser.screenshot"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        if ctx.browser_session is None:
            result.mark_failed("No browser session available")
            return result

        try:
            page = ctx.browser_session
            filename = params.get("filename", f"screenshot_{ctx.task_id}.png")
            path = ctx.screenshot_dir / filename

            selector = params.get("selector")
            if selector:
                element = await page.query_selector(ctx.resolve_var(selector))
                if element:
                    await element.screenshot(path=str(path))
                else:
                    result.mark_failed(f"Element not found: {selector}")
                    return result
            else:
                full_page = params.get("full_page", True)
                await page.screenshot(path=str(path), full_page=full_page)

            result.screenshot_paths.append(str(path))
            result.mark_success({"screenshot_path": str(path)})
        except Exception as e:
            result.mark_failed(f"Screenshot failed: {e}")

        return result
