"""os.type and os.hotkey step primitives — PyAutoGUI keyboard input."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class OsType:
    @property
    def name(self) -> str:
        return "os.type"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        text = ctx.resolve_var(params.get("text", ""))
        if not text:
            result.mark_failed("No text specified")
            return result

        try:
            import pyautogui  # type: ignore[import-untyped]

            interval = float(params.get("interval", 0.02))
            pyautogui.typewrite(text, interval=interval)
            result.mark_success()
        except Exception as e:
            result.mark_failed(f"OS type failed: {e}")

        return result


@register_step
class OsHotkey:
    @property
    def name(self) -> str:
        return "os.hotkey"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        keys = params.get("keys", [])
        if not keys:
            result.mark_failed("No keys specified")
            return result

        try:
            import pyautogui  # type: ignore[import-untyped]

            pyautogui.hotkey(*keys)
            result.mark_success({"keys": keys})
        except Exception as e:
            result.mark_failed(f"OS hotkey failed: {e}")

        return result
