"""Stage 1 smoke test: run audio extraction + word-level transcription on a
real file and print/save the result so timing accuracy can be eyeballed.

Usage:
    python scripts/test_transcribe_stage1.py path/to/song.mp3 [--language en]
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import AUDIO_DIR, OUTPUTS_DIR
from app.pipeline.audio_extract import extract_audio, probe_duration
from app.pipeline.transcribe import transcribe


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--language", default=None, help="force language code, e.g. en")
    args = parser.parse_args()

    if not args.input_file.exists():
        raise SystemExit(f"input file not found: {args.input_file}")

    stem = args.input_file.stem
    audio_path = AUDIO_DIR / f"{stem}.wav"

    print(f"[1/2] Extracting audio -> {audio_path}")
    t0 = time.time()
    extract_audio(args.input_file, audio_path)
    duration = probe_duration(audio_path)
    print(f"      done in {time.time() - t0:.1f}s, source duration: {duration:.1f}s")

    print("[2/2] Transcribing with word-level alignment (this loads the Whisper "
          "+ wav2vec2 models on first run, be patient)...")
    t0 = time.time()
    result = transcribe(audio_path, language=args.language)
    elapsed = time.time() - t0
    print(f"      done in {elapsed:.1f}s ({elapsed / max(duration, 0.01):.2f}x realtime)")

    out_path = OUTPUTS_DIR / f"{stem}.transcript.json"
    out_path.write_text(result.model_dump_json(indent=2))
    print(f"\nSaved full transcript to {out_path}")

    print(f"\nDetected language: {result.language}")
    print(f"Segments: {len(result.segments)}\n")

    print(f"{'word':<20}{'start':>10}{'end':>10}{'score':>10}")
    print("-" * 50)
    shown = 0
    for seg in result.segments:
        for w in seg.words:
            print(f"{w.text:<20}{w.start:>10.3f}{w.end:>10.3f}{(w.score or 0):>10.3f}")
            shown += 1
            if shown >= 40:
                break
        if shown >= 40:
            break
    if shown == 0:
        print("(no words produced — check the input audio)")


if __name__ == "__main__":
    main()
