"""ocr.find_text step primitive — locate text on screen via RapidOCR."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class OcrFindText:
    @property
    def name(self) -> str:
        return "ocr.find_text"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        text = ctx.resolve_var(params.get("text", ""))
        image_path = params.get("image_path", "")

        if not text:
            result.mark_failed("No text specified")
            return result

        try:
            from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-untyped]

            ocr = RapidOCR()

            # If no image path, take a screenshot first
            if not image_path:
                import mss  # type: ignore[import-untyped]

                with mss.mss() as sct:
                    monitor = sct.monitors[0]
                    sct_img = sct.grab(monitor)
                    tmp_path = ctx.screenshot_dir / f"ocr_input_{ctx.task_id}.png"
                    mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(tmp_path))
                    image_path = str(tmp_path)

            ocr_result, _ = ocr(image_path)

            if ocr_result is None:
                result.mark_failed("OCR returned no results")
                return result

            # Search for the text in OCR results
            for item in ocr_result:
                boxes, detected_text, confidence = item
                if text.lower() in detected_text.lower():
                    # Return bounding box center
                    xs = [p[0] for p in boxes]
                    ys = [p[1] for p in boxes]
                    center_x = sum(xs) / len(xs)
                    center_y = sum(ys) / len(ys)
                    result.mark_success({
                        "found": True,
                        "text": detected_text,
                        "center_x": center_x,
                        "center_y": center_y,
                        "confidence": confidence,
                        "bbox": boxes,
                    })
                    return result

            result.mark_failed(f"Text '{text}' not found on screen")

        except ImportError:
            result.mark_failed("RapidOCR not installed. Run: uv add rapidocr-onnxruntime")
        except Exception as e:
            result.mark_failed(f"OCR failed: {e}")

        return result
