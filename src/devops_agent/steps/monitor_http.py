"""monitor.http_check step primitive — poll a URL for expected status/body."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class MonitorHttpCheck:
    @property
    def name(self) -> str:
        return "monitor.http_check"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        url = ctx.resolve_var(params.get("url", ""))
        if not url:
            result.mark_failed("No URL specified")
            return result

        expected_status = int(params.get("expected_status", 200))
        expected_body = params.get("expected_body", "")
        interval = int(params.get("interval_seconds", 30))
        timeout = int(params.get("timeout_seconds", 300))
        elapsed = 0

        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            while elapsed < timeout:
                try:
                    resp = await client.get(url)
                    status_ok = resp.status_code == expected_status
                    body_ok = expected_body in resp.text if expected_body else True

                    if status_ok and body_ok:
                        result.mark_success({
                            "status_code": resp.status_code,
                            "elapsed_seconds": elapsed,
                        })
                        return result
                except httpx.HTTPError:
                    pass

                await asyncio.sleep(interval)
                elapsed += interval

        result.mark_failed(
            f"Health check timed out after {timeout}s. "
            f"Expected status {expected_status}" +
            (f" with body containing '{expected_body}'" if expected_body else "")
        )
        return result
