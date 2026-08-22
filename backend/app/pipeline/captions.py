"""Stage 2: turn a TranscriptionResult into burned-in captions via ffmpeg's
libass filter.

Frame-accuracy note: ASS timestamps are centisecond-precision, and libass
positions each Dialogue event by wall-clock time against the video's actual
presentation timestamps — not by rounding to some fixed caption grid. So as
long as the word timings we feed in are accurate, what's on screen tracks the
audio exactly (only quantized by the output frame rate itself, same as any
video). This module does no timestamp rounding of its own.

Word entrances use ASS's \t animated-transform tag, which interpolates
between two override-tag states over a time window with a power-curve
acceleration parameter (accel < 1 fronts-loads the motion, accel > 1
back-loads it) — chaining a fast eased rise into an eased settle produces a
genuine spring/overshoot pop rather than an instant cut or a linear tween.
Timings are computed per word from its own duration so the pop always
resolves before the word's turn is over, however short.
"""

from dataclasses import dataclass
from pathlib import Path

from app.models.schemas import TranscriptionResult, Word


@dataclass
class CaptionStyle:
    video_width: int = 1080
    video_height: int = 1920
    font: str = "DejaVu Sans"
    font_size: int = 58
    text_color: str = "&H00FFFFFF"       # ASS is &HAABBGGRR; opaque white
    active_color: str = "&H0000E5FF"     # opaque accent (amber/yellow-orange)
    outline_color: str = "&H00000000"    # opaque black outline
    outline_width: int = 4
    shadow: int = 2
    letter_spacing: float = 0.6

    # Active-word entrance pop: starts small/faded, overshoots past 100%,
    # then eases back to rest.
    pop_start_scale_pct: int = 74
    pop_overshoot_scale_pct: int = 122
    pop_rise_ease: float = 0.55          # <1: fast start, eases into the overshoot
    pop_settle_ease: float = 1.7         # >1: eases out of the overshoot into rest
    pop_rise_max_ms: int = 90
    pop_settle_max_ms: int = 80

    # Real short-form captions show a handful of words at a time, not a whole
    # sentence — this bounds how many words share one on-screen line.
    max_words_per_line: int = 4

    # Safe-zone margins (px) so captions clear typical TikTok/Reels/Shorts UI chrome.
    margin_left: int = 90
    margin_right: int = 90
    margin_bottom: int = 480


def _ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    total_cs = round(seconds * 100)
    h, rem = divmod(total_cs, 100 * 60 * 60)
    m, rem = divmod(rem, 100 * 60)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def _pop_in_override(word_duration_s: float, style: CaptionStyle) -> str:
    duration_ms = max(1, round(word_duration_s * 1000))
    rise_ms = min(style.pop_rise_max_ms, max(15, round(duration_ms * 0.5)))
    settle_ms = min(style.pop_settle_max_ms, max(10, round(duration_ms * 0.35)))
    # keep the whole pop inside the word's own on-screen window
    settle_ms = min(settle_ms, max(5, duration_ms - rise_ms))
    settle_end = rise_ms + settle_ms

    initial = f"\\c{style.text_color}\\alpha&H90&\\fscx{style.pop_start_scale_pct}\\fscy{style.pop_start_scale_pct}"
    rise_target = f"\\c{style.active_color}\\alpha&H00&\\fscx{style.pop_overshoot_scale_pct}\\fscy{style.pop_overshoot_scale_pct}"
    settle_target = "\\fscx100\\fscy100"
    return (
        f"{{{initial}"
        f"\\t(0,{rise_ms},{style.pop_rise_ease},{rise_target})"
        f"\\t({rise_ms},{settle_end},{style.pop_settle_ease},{settle_target})}}"
    )


def _line_with_active_word(words: list[Word], active_index: int, style: CaptionStyle) -> str:
    parts = []
    for i, w in enumerate(words):
        escaped = _escape(w.text)
        if i == active_index:
            override = _pop_in_override(w.end - w.start, style)
            parts.append(f"{override}{escaped}{{\\c{style.text_color}\\fscx100\\fscy100}}")
        else:
            parts.append(escaped)
    return " ".join(parts)


def chunk_words(words: list[Word], max_words: int) -> list[list[Word]]:
    return [words[i : i + max_words] for i in range(0, len(words), max_words)]


def build_ass(transcript: TranscriptionResult, style: CaptionStyle = CaptionStyle()) -> str:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {style.video_width}
PlayResY: {style.video_height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font},{style.font_size},{style.text_color},{style.text_color},{style.outline_color},&H00000000,1,0,0,0,100,100,{style.letter_spacing},0,1,{style.outline_width},{style.shadow},2,{style.margin_left},{style.margin_right},{style.margin_bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for seg in transcript.segments:
        for group in chunk_words(seg.words, style.max_words_per_line):
            for i, w in enumerate(group):
                text = _line_with_active_word(group, i, style)
                lines.append(
                    f"Dialogue: 0,{_ass_time(w.start)},{_ass_time(w.end)},Default,,0,0,0,,{text}"
                )
    return header + "\n".join(lines) + "\n"


def write_ass(transcript: TranscriptionResult, out_path: Path, style: CaptionStyle = CaptionStyle()) -> Path:
    out_path.write_text(build_ass(transcript, style))
    return out_path
