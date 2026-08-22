"""Builds a fixture TranscriptionResult for testdata/messy_test.mp3 so later
pipeline stages (caption rendering, correction UI, export) can be developed
and tested without needing live Whisper model weights.

This is NOT a Whisper output. Segment boundaries are real (re-derived from
the same ffmpeg/espeak steps generate_sample.sh uses), but word-level timing
within each segment is approximated by splitting proportionally to character
length. Treat this strictly as a rendering/UI test fixture — it is not a
stand-in for stage 1's accuracy, which still needs live-model verification
(see task: "Verify stage 1 with live Whisper once model access available").
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline.audio_extract import probe_duration
from app.models.schemas import Segment, TranscriptionResult, Word

TESTDATA = Path(__file__).parent / "testdata"


def synth_duration(text: str, voice: str, speed: int, pitch: int, amp: int, tmp: Path) -> float:
    subprocess.run(
        ["espeak-ng", "-v", voice, "-s", str(speed), "-p", str(pitch), "-a", str(amp), text, "--stdout"],
        stdout=tmp.open("wb"),
        check=True,
    )
    return probe_duration(tmp)


def words_for_line(text: str, start: float, end: float) -> list[Word]:
    tokens = text.split()
    total_chars = sum(len(t) for t in tokens) or 1
    span = end - start
    words = []
    cursor = start
    for tok in tokens:
        frac = len(tok) / total_chars
        w_end = cursor + span * frac
        words.append(Word(text=tok, start=round(cursor, 3), end=round(w_end, 3), score=None))
        cursor = w_end
    return words


def main():
    tmp = TESTDATA / "_tmp.wav"
    verse_lines = TESTDATA.joinpath("verse_lines.txt").read_text().strip().splitlines()
    chorus_line = TESTDATA.joinpath("chorus_line.txt").read_text().strip()

    verse_durations = [synth_duration(l, "en-us", 235, 45, 180, tmp) for l in verse_lines]
    chorus_a_dur = synth_duration(chorus_line, "en-us+m3", 190, 40, 100, tmp)
    chorus_b_dur = synth_duration(chorus_line, "en-us+m4", 205, 60, 100, tmp)
    # chorus_mixed.wav = adelay 150ms on track b, mixed with `duration=longest`
    chorus_duration = max(chorus_a_dur, 0.15 + chorus_b_dur)
    tmp.unlink(missing_ok=True)

    # playback order matches generate_sample.sh's concat_list.txt
    order = [0, 1, 2, 3, "chorus", 1]
    line_text = {0: verse_lines[0], 1: verse_lines[1], 2: verse_lines[2], 3: verse_lines[3], "chorus": chorus_line}
    line_duration = {
        0: verse_durations[0], 1: verse_durations[1], 2: verse_durations[2], 3: verse_durations[3],
        "chorus": chorus_duration,
    }

    segments = []
    cursor = 0.0
    for key in order:
        text = line_text[key]
        dur = line_duration[key]
        start, end = cursor, cursor + dur
        segments.append(Segment(text=text, start=round(start, 3), end=round(end, 3), words=words_for_line(text, start, end)))
        cursor = end

    result = TranscriptionResult(language="en", duration=round(cursor, 3), segments=segments)
    out_path = TESTDATA / "messy_test.fixture.json"
    out_path.write_text(result.model_dump_json(indent=2))
    print(f"Wrote {out_path} ({cursor:.2f}s, {sum(len(s.words) for s in segments)} words)")


if __name__ == "__main__":
    main()
