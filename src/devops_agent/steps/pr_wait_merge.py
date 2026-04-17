"""pr.wait_merge step primitive — poll or suspend for PR merge."""

from __future__ import annotations

import asyncio
from typing import Any

from devops_agent.config.schema import MergeDetectionMode
from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class PrWaitMerge:
    @property
    def name(self) -> str:
        return "pr.wait_merge"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        pr_url = ctx.resolve_var(params.get("pr_url", ctx.outputs.get("pr_url", "")))
        mode = params.get("mode", ctx.agent_config.default_merge_detection.value)

        if not pr_url:
            result.mark_failed("No PR URL available")
            return result

        if mode == MergeDetectionMode.suspend.value:
            # Suspend mode: return immediately with special status
            # Executor will move task to waiting/
            result.mark_success({"mode": "suspend", "pr_url": pr_url, "_suspend": True})
            return result

        # Poll mode
        interval = int(params.get("interval_seconds", ctx.agent_config.poll_interval_seconds))
        timeout = int(params.get("timeout_seconds", ctx.agent_config.poll_timeout_seconds))

        if ctx.browser_session is None:
            result.mark_failed("No browser session available for PR status polling")
            return result

        page = ctx.browser_session
        elapsed = 0

        while elapsed < timeout:
            try:
                await page.goto(pr_url, wait_until="domcontentloaded")
                content = await page.content()

                # Platform-specific merge detection
                merged = (
                    "merged" in content.lower()
                    or "pull request successfully merged" in content.lower()
                    or "this pull request was successfully merged" in content.lower()
                )

                if merged:
                    screenshot_path = ctx.screenshot_dir / f"pr_merged_{ctx.task_id}.png"
                    await page.screenshot(path=str(screenshot_path))
                    result.screenshot_paths.append(str(screenshot_path))
                    result.mark_success({
                        "pr_url": pr_url,
                        "merged": True,
                        "elapsed_seconds": elapsed,
                    })
                    return result
            except Exception:
                pass

            await asyncio.sleep(interval)
            elapsed += interval

        result.mark_failed(f"PR merge detection timed out after {timeout}s")
        return result
