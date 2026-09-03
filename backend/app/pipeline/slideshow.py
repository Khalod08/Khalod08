"""Multi-image backgrounds: turns a set of user-picked images into one
crossfaded slideshow video spanning the full track, which then flows through
the existing single-file background pipeline unchanged (backgrounds.py just
sees a video file to loop/play).
"""

import subprocess
from pathlib import Path

MAX_IMAGES = 30
MIN_SLOT_SECONDS = 0.5  # below this a crossfade would eat the whole slot


class SlideshowError(RuntimeError):
    pass


def build_slideshow_video(
    image_paths: list[Path],
    total_duration: float,
    output_path: Path,
    width: int = 2160,
    height: int = 3840,
    fps: int = 30,
    crossfade_duration: float = 0.6,
) -> Path:
    """Equal-length slot per image, crossfaded at each boundary, total output
    duration exactly `total_duration` (so it drops straight into the existing
    -shortest-trimmed burn-in/export pipeline with no gaps or freeze frames).
    """
    n = len(image_paths)
    if n == 0:
        raise SlideshowError("no images provided")
    if n > MAX_IMAGES:
        raise SlideshowError(f"too many images ({n}); max is {MAX_IMAGES}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if n == 1:
        # nothing to crossfade — a single-image "slideshow" is just that image.
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", f"{total_duration:.3f}",
            "-i", str(image_paths[0]),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps}",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "14",
            str(output_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise SlideshowError(f"ffmpeg single-image slideshow failed:\n{proc.stderr[-4000:]}")
        return output_path

    use_crossfade = (total_duration / n) >= MIN_SLOT_SECONDS
    xf = min(crossfade_duration, (total_duration / n) * 0.4) if use_crossfade else 0.0
    # compensate slot length so N slots minus (N-1) overlaps still sum to
    # total_duration exactly, instead of coming up short by (n-1)*xf.
    slot = (total_duration + (n - 1) * xf) / n if use_crossfade else total_duration / n

    inputs = []
    per_stream_labels = []
    for i, img in enumerate(image_paths):
        inputs += ["-loop", "1", "-t", f"{slot:.3f}", "-i", str(img)]
        per_stream_labels.append(f"[{i}:v]")

    filter_parts = []
    for i, label in enumerate(per_stream_labels):
        filter_parts.append(
            f"{label}scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,fps={fps},format=yuv420p[v{i}]"
        )

    if use_crossfade:
        cumulative = slot
        chain = "[v0]"
        for i in range(1, n):
            offset = max(0.0, cumulative - xf)
            out_label = f"[x{i}]" if i < n - 1 else "[vout]"
            filter_parts.append(
                f"{chain}[v{i}]xfade=transition=fade:duration={xf:.3f}:offset={offset:.3f}{out_label}"
            )
            chain = out_label
            cumulative = offset + slot
    else:
        # slots too short for a crossfade to make sense — hard cuts instead.
        concat_inputs = "".join(f"[v{i}]" for i in range(n))
        filter_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=0[vout]")

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", "14",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SlideshowError(f"ffmpeg slideshow build failed:\n{proc.stderr[-4000:]}")
    return output_path
