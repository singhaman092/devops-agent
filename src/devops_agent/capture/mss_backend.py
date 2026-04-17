"""Full-screen and region screenshots via mss."""

from __future__ import annotations

from pathlib import Path


def capture_full_screen(output_path: Path) -> Path:
    """Capture full screen to a PNG file."""
    import mss  # type: ignore[import-untyped]
    import mss.tools  # type: ignore[import-untyped]

    with mss.mss() as sct:
        monitor = sct.monitors[0]
        sct_img = sct.grab(monitor)
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(output_path))
    return output_path


def capture_region(
    output_path: Path, left: int, top: int, width: int, height: int
) -> Path:
    """Capture a screen region to a PNG file."""
    import mss  # type: ignore[import-untyped]
    import mss.tools  # type: ignore[import-untyped]

    with mss.mss() as sct:
        monitor = {"left": left, "top": top, "width": width, "height": height}
        sct_img = sct.grab(monitor)
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(output_path))
    return output_path
