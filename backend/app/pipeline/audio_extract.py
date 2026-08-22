"""Stage 1a: pull a clean mono 16kHz PCM track out of any uploaded audio/video file."""

import subprocess
from pathlib import Path

from app.config import TARGET_SAMPLE_RATE


class AudioExtractionError(RuntimeError):
    pass


def extract_audio(input_path: Path, output_path: Path, sample_rate: int = TARGET_SAMPLE_RATE) -> Path:
    """Extract (or transcode) the audio track of `input_path` into a mono WAV
    at `sample_rate`, using ffmpeg. Works for both audio and video containers
    since ffmpeg demuxes whichever audio stream is present.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vn",                       # drop video stream if present
        "-ac", "1",                  # mono
        "-ar", str(sample_rate),     # resample
        "-acodec", "pcm_s16le",      # uncompressed PCM, no lossy re-encode
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AudioExtractionError(
            f"ffmpeg failed extracting audio from {input_path}:\n{proc.stderr[-4000:]}"
        )
    return output_path


def probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AudioExtractionError(f"ffprobe failed on {path}:\n{proc.stderr}")
    return float(proc.stdout.strip())
