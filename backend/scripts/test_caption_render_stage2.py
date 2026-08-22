"""Stage 2 smoke test: burn word-synced captions from a transcript JSON onto
a static background and verify the render is frame-accurate by pulling still
frames at chosen word midpoints for visual inspection.

Usage:
    python scripts/test_caption_render_stage2.py \
        --transcript scripts/testdata/messy_test.fixture.json \
        --audio scripts/testdata/messy_test.mp3
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import OUTPUTS_DIR
from app.models.schemas import TranscriptionResult
from app.pipeline.captions import CaptionStyle, write_ass
from app.pipeline.render import extract_frame, render_burn_in


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--check-words", type=int, default=4, help="how many word midpoints to spot-check")
    args = parser.parse_args()

    transcript = TranscriptionResult(**json.loads(args.transcript.read_text()))
    stem = args.audio.stem

    ass_path = OUTPUTS_DIR / f"{stem}.ass"
    write_ass(transcript, ass_path, CaptionStyle())
    print(f"[1/3] Wrote ASS captions -> {ass_path}")

    video_path = OUTPUTS_DIR / f"{stem}.stage2.mp4"
    render_burn_in(args.audio, ass_path, video_path)
    print(f"[2/3] Rendered burned-in captions -> {video_path}")

    all_words = [w for seg in transcript.segments for w in seg.words]
    step = max(1, len(all_words) // args.check_words)
    picks = all_words[::step][: args.check_words]

    print(f"[3/3] Extracting {len(picks)} verification frames at word midpoints:")
    for w in picks:
        mid = (w.start + w.end) / 2
        frame_path = OUTPUTS_DIR / f"{stem}.check_{mid:.2f}s.png"
        extract_frame(video_path, mid, frame_path)
        print(f"      t={mid:6.2f}s  expected active word: {w.text!r:<12} -> {frame_path}")


if __name__ == "__main__":
    main()
