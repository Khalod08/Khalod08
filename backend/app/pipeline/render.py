"""Burns an ASS caption track onto a background (static color/image for now;
video loops and user uploads land in stage 4) and muxes in the source audio.
"""

import subprocess
from pathlib import Path
from typing import Optional

from app.pipeline.backgrounds import resolve_background_input


class RenderError(RuntimeError):
    pass


def render_burn_in(
    audio_path: Path,
    ass_path: Path,
    output_path: Path,
    background_media: Optional[Path] = None,
    background_preset: Optional[str] = None,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ass= needs the path escaped for ffmpeg's filter-arg parser (colons and
    # backslashes are special there).
    ass_arg = str(ass_path).replace("\\", "\\\\").replace(":", "\\:")
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},ass='{ass_arg}'"

    bg_input = resolve_background_input(background_media, background_preset, width, height, fps)

    cmd = [
        "ffmpeg", "-y",
        *bg_input,
        "-i", str(audio_path),
        "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RenderError(f"ffmpeg caption burn-in failed:\n{proc.stderr[-4000:]}")
    return output_path


def extract_frame(video_path: Path, timestamp: float, output_path: Path) -> Path:
    """Grab a single still frame at `timestamp` seconds, for spot-checking sync."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{timestamp:.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RenderError(f"ffmpeg frame extraction failed:\n{proc.stderr[-4000:]}")
    return output_path
