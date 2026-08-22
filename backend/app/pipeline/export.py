"""Stage 5: final export — same burn-in pipeline as the preview render, but
at export-grade quality settings (slow preset, tight CRF, faststart) and a
choice of resolution up to 4K and codec.

CRF (not a fixed bitrate) drives quality: it's content-adaptive, so it holds
the same visual quality across simple and busy scenes instead of wasting bits
on easy frames or starving hard ones. 16 (h264) / 20 (h265, whose CRF scale
runs lower for equivalent quality) is in the visually-transparent range —
compression artifacts shouldn't be visible on typical short-form footage.
"""

from pathlib import Path
from typing import Optional

from app.pipeline.render import render_burn_in

RESOLUTIONS: dict[str, tuple[int, int]] = {
    "1080p": (1080, 1920),
    "1440p": (1440, 2560),
    "4k": (2160, 3840),
}

CODEC_QUALITY: dict[str, dict] = {
    "h264": {"preset": "slow", "crf": 16},
    "h265": {"preset": "slow", "crf": 20},
}


def export_video(
    audio_path: Path,
    ass_path: Path,
    output_path: Path,
    background_media: Optional[Path] = None,
    background_preset: Optional[str] = None,
    resolution: str = "1080p",
    codec: str = "h264",
    fps: int = 30,
) -> Path:
    if resolution not in RESOLUTIONS:
        raise ValueError(f"unknown resolution: {resolution} (choices: {list(RESOLUTIONS)})")
    if codec not in CODEC_QUALITY:
        raise ValueError(f"unknown codec: {codec} (choices: {list(CODEC_QUALITY)})")

    width, height = RESOLUTIONS[resolution]
    quality = CODEC_QUALITY[codec]

    return render_burn_in(
        audio_path,
        ass_path,
        output_path,
        background_media=background_media,
        background_preset=background_preset,
        width=width,
        height=height,
        fps=fps,
        codec=codec,
        preset=quality["preset"],
        crf=quality["crf"],
        audio_bitrate="256k",
    )
