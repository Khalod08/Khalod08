"""Stage 4: background sources for the caption overlay.

Two kinds: a user-uploaded image/video loop, or a built-in preset generated
on the fly via ffmpeg's lavfi sources (no binary assets to ship in the repo).
"""

from pathlib import Path
from typing import Optional

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def _gradients_input(c0: str, c1: str, kind: str, width: int, height: int, fps: int) -> list[str]:
    return [
        "-f", "lavfi",
        "-i", f"gradients=size={width}x{height}:rate={fps}:c0={c0}:c1={c1}:type={kind}:speed=0.02",
    ]


PRESETS: dict[str, dict] = {
    "midnight": {"label": "Midnight", "color": "0x14141a"},
    "charcoal": {"label": "Charcoal", "color": "0x1c1c22"},
    "aurora": {"label": "Aurora", "gradient": ("0x0f2027", "0x2c5364", "linear")},
    "sunset": {"label": "Sunset", "gradient": ("0xff512f", "0x1a1a2e", "radial")},
    "grape": {"label": "Grape", "gradient": ("0x360033", "0x0b8793", "spiral")},
}


def uploaded_background_path(backgrounds_dir: Path, job_id: str) -> Optional[Path]:
    matches = list(backgrounds_dir.glob(f"{job_id}.*"))
    return matches[0] if matches else None


def list_presets() -> list[dict]:
    return [{"id": k, "label": v["label"]} for k, v in PRESETS.items()]


def preset_input(name: str, width: int, height: int, fps: int) -> list[str]:
    preset = PRESETS.get(name)
    if preset is None:
        raise KeyError(f"unknown background preset: {name}")
    if "color" in preset:
        return ["-f", "lavfi", "-i", f"color=c={preset['color']}:s={width}x{height}:r={fps}"]
    c0, c1, kind = preset["gradient"]
    return _gradients_input(c0, c1, kind, width, height, fps)


def resolve_background_input(
    background_media: Optional[Path],
    preset: Optional[str],
    width: int,
    height: int,
    fps: int,
) -> list[str]:
    """ffmpeg input args for whichever background source is configured."""
    if background_media is not None:
        if is_image(background_media):
            return ["-loop", "1", "-i", str(background_media)]
        return ["-stream_loop", "-1", "-i", str(background_media)]
    if preset is not None:
        return preset_input(preset, width, height, fps)
    return preset_input("midnight", width, height, fps)
