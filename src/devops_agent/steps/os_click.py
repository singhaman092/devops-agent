"""os.click step primitive — PyAutoGUI click with DPI awareness."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class OsClick:
    @property
    def name(self) -> str:
        return "os.click"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        x = params.get("x")
        y = params.get("y")
        button = params.get("button", "left")
        clicks = params.get("clicks", 1)

        if x is None or y is None:
            result.mark_failed("x and y coordinates required")
            return result

        try:
            import pyautogui  # type: ignore[import-untyped]

            pyautogui.click(x=int(x), y=int(y), button=button, clicks=clicks)
            result.mark_success({"x": x, "y": y, "button": button})
        except Exception as e:
            result.mark_failed(f"OS click failed: {e}")

        return result
