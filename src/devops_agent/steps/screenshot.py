"""screenshot.capture step primitive — OS-level screenshots via mss + pywin32."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class ScreenshotCapture:
    @property
    def name(self) -> str:
        return "screenshot.capture"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        mode = params.get("mode", "full")  # full | region | window
        filename = params.get("filename", f"os_screenshot_{ctx.task_id}.png")
        path = ctx.screenshot_dir / filename

        try:
            import mss  # type: ignore[import-untyped]

            with mss.mss() as sct:
                if mode == "full":
                    monitor = sct.monitors[0]
                    sct_img = sct.grab(monitor)
                elif mode == "region":
                    region = params.get("region", {})
                    monitor = {
                        "left": region.get("left", 0),
                        "top": region.get("top", 0),
                        "width": region.get("width", 1920),
                        "height": region.get("height", 1080),
                    }
                    sct_img = sct.grab(monitor)
                elif mode == "window":
                    # Use pywin32 PrintWindow for occluded-safe capture
                    # TODO: implement pywin32 PrintWindow backend
                    monitor = sct.monitors[0]
                    sct_img = sct.grab(monitor)
                else:
                    result.mark_failed(f"Unknown screenshot mode: {mode}")
                    return result

                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(path))

            result.screenshot_paths.append(str(path))
            result.mark_success({"screenshot_path": str(path)})
        except Exception as e:
            result.mark_failed(f"Screenshot capture failed: {e}")

        return result
