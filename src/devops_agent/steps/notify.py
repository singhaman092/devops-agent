"""notify.send step primitive — post to Slack/Teams via browser."""

from __future__ import annotations

import time
from typing import Any, ClassVar

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult

# Minimum interval between notifications to avoid rate limiting
_MIN_NOTIFICATION_INTERVAL = 3.0  # seconds
_last_send_time: float = 0.0


@register_step
class NotifySend:
    @property
    def name(self) -> str:
        return "notify.send"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        channel_name = params.get("channel", "")
        message = ctx.resolve_var(params.get("message", ""))
        template = params.get("template", "")

        if not channel_name:
            result.mark_failed("No channel specified")
            return result

        # Resolve template if provided
        if template and ctx.notifications:
            tmpl = ctx.notifications.templates.get(template, "")
            if tmpl:
                message = ctx.resolve_var(tmpl)

        if not message:
            result.mark_failed("No message to send (empty message and no template)")
            return result

        # Look up channel
        if ctx.notifications is None:
            result.mark_failed("No notifications config loaded")
            return result

        channel = ctx.notifications.channels.get(channel_name)
        if channel is None:
            result.mark_failed(f"Channel '{channel_name}' not found in notifications config")
            return result

        if ctx.browser_session is None:
            result.mark_failed("No browser session available for notification delivery")
            return result

        try:
            # Rate limiting
            global _last_send_time
            elapsed = time.monotonic() - _last_send_time
            if elapsed < _MIN_NOTIFICATION_INTERVAL:
                import asyncio
                await asyncio.sleep(_MIN_NOTIFICATION_INTERVAL - elapsed)

            page = ctx.browser_session
            # Navigate to channel
            await page.goto(channel.url, wait_until="domcontentloaded", timeout=30000)

            if channel.platform.value == "slack":
                from devops_agent.notifications.slack_web import send_slack_message
                await send_slack_message(page, message)
            else:
                from devops_agent.notifications.teams_web import send_teams_message
                await send_teams_message(page, message)

            _last_send_time = time.monotonic()

            # Screenshot the posted message
            screenshot_path = ctx.screenshot_dir / f"notify_{channel_name}_{ctx.task_id}.png"
            await page.screenshot(path=str(screenshot_path))
            result.screenshot_paths.append(str(screenshot_path))

            result.mark_success({"channel": channel_name, "platform": channel.platform.value})
        except Exception as e:
            # Notification failure is logged but never fails the task
            result.mark_failed(f"Notification delivery failed: {e}")

        return result
