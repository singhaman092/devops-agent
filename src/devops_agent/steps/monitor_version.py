"""monitor.version_match step primitive — poll a version endpoint."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class MonitorVersionMatch:
    @property
    def name(self) -> str:
        return "monitor.version_match"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        url = ctx.resolve_var(params.get("url", ""))
        expected_version = ctx.resolve_var(params.get("expected_version", ""))
        json_path = params.get("json_path", "version")  # dot-separated path into JSON response

        if not url or not expected_version:
            result.mark_failed("url and expected_version are required")
            return result

        interval = int(params.get("interval_seconds", 30))
        timeout = int(params.get("timeout_seconds", 600))
        elapsed = 0

        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            while elapsed < timeout:
                try:
                    resp = await client.get(url)
                    data = resp.json()

                    # Navigate json_path
                    value = data
                    for key in json_path.split("."):
                        if isinstance(value, dict):
                            value = value.get(key)
                        else:
                            value = None
                            break

                    if str(value) == expected_version:
                        result.mark_success({
                            "version": str(value),
                            "elapsed_seconds": elapsed,
                        })
                        return result
                except (httpx.HTTPError, ValueError, KeyError):
                    pass

                await asyncio.sleep(interval)
                elapsed += interval

        result.mark_failed(f"Version match timed out after {timeout}s. Expected: {expected_version}")
        return result
