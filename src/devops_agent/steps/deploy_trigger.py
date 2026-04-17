"""deploy.trigger step primitive — navigate deploy portal and trigger."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class DeployTrigger:
    @property
    def name(self) -> str:
        return "deploy.trigger"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        if ctx.environment is None:
            result.mark_failed("No environment configured in task references")
            return result

        if ctx.browser_session is None:
            result.mark_failed("No browser session available")
            return result

        deploy_url = ctx.resolve_var(
            params.get("url", ctx.environment.deploy_portal_url)
        )
        if not deploy_url:
            result.mark_failed("No deploy portal URL configured")
            return result

        trigger_type = ctx.environment.deploy_trigger.value

        try:
            page = ctx.browser_session
            await page.goto(deploy_url, wait_until="domcontentloaded")

            if trigger_type == "portal_click":
                # Execute click sequence defined in params
                click_selectors = params.get("click_selectors", [])
                for selector in click_selectors:
                    resolved = ctx.resolve_var(selector)
                    await page.click(resolved, timeout=15000)
                    await page.wait_for_timeout(1000)

            elif trigger_type == "pipeline_url":
                pipeline_url = ctx.resolve_var(params.get("pipeline_url", ""))
                if pipeline_url:
                    await page.goto(pipeline_url, wait_until="domcontentloaded")
                    run_btn = params.get("run_button_selector", "")
                    if run_btn:
                        await page.click(ctx.resolve_var(run_btn), timeout=15000)

            elif trigger_type == "cli":
                # Fall back to shell command
                from devops_agent.steps.shell import ShellRun

                shell = ShellRun()
                cmd = ctx.resolve_var(params.get("command", ""))
                if not cmd:
                    result.mark_failed("No deploy command specified for CLI trigger")
                    return result
                shell_result = await shell.execute(ctx, {"command": cmd})
                if shell_result.status != "success":
                    result.mark_failed(shell_result.error_message, shell_result.stderr)
                    return result

            # Screenshot after trigger
            screenshot_path = ctx.screenshot_dir / f"deploy_trigger_{ctx.task_id}.png"
            await page.screenshot(path=str(screenshot_path))
            result.screenshot_paths.append(str(screenshot_path))

            result.mark_success({"deploy_url": deploy_url, "trigger_type": trigger_type})

        except Exception as e:
            result.mark_failed(f"Deploy trigger failed: {e}")

        return result
