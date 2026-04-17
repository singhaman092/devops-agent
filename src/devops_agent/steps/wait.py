"""wait.sleep step primitive — explicit delays."""

from __future__ import annotations

import asyncio
from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class WaitSleep:
    @property
    def name(self) -> str:
        return "wait.sleep"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        seconds = int(params.get("seconds", 5))
        await asyncio.sleep(seconds)
        result.mark_success({"slept_seconds": seconds})
        return result
