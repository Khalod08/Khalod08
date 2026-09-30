"""Voiceover for Manim via free Microsoft Edge TTS (``edge-tts``).

manim-voiceover has no Edge TTS service built in, so this is a small custom
``SpeechService``. It asks Edge TTS for *word boundaries*, which lets
``self.wait_until_bookmark(...)`` sync animations to words exactly, with no
speech-recognition model needed.

Voice: ``en-CA-LiamNeural`` (calm Canadian). If that voice is unavailable the
next calm voice in ``FALLBACK_VOICES`` is tried.

For offline previews (no internet) set ``GOATVEX_VOICE=silent``: the
:class:`SilentPreviewService` produces silent audio of a realistic length so
timing and captions can still be checked. It is never used for final renders.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

from manim import logger
from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import SpeechService, initialize_speech_service

DEFAULT_VOICE = "en-CA-LiamNeural"
FALLBACK_VOICES = ("en-CA-LiamNeural", "en-US-AndrewNeural", "en-GB-RyanNeural", "en-US-GuyNeural")
DEFAULT_RATE = "-6%"  # a touch slower than normal: calm, never rushed


def _word_boundaries(text: str, events: list[dict]) -> list[dict]:
    """Convert Edge TTS WordBoundary events to manim-voiceover's format.

    Both use 100-nanosecond ticks for audio offsets. ``text_offset`` is the
    character position of the word in the bookmark-free text.
    """
    out, cursor = [], 0
    for ev in events:
        word = ev["text"]
        pos = text.find(word, cursor)
        if pos < 0:
            pos = cursor
        out.append({
            "audio_offset": int(ev["offset"]),
            "duration_milliseconds": int(ev["duration"]) // 10_000,
            "text_offset": pos,
            "word_length": len(word),
            "text": word,
            "boundary_type": "Word",
        })
        cursor = pos + len(word)
    return out


async def _synthesize(text: str, voice: str, rate: str, out_path: Path) -> list[dict]:
    import edge_tts

    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    events: list[dict] = []
    with open(out_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                events.append(chunk)
    return events


class EdgeTTSService(SpeechService):
    """SpeechService backed by Microsoft Edge's free online TTS voices."""

    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE, **kwargs):
        initialize_speech_service(self, kwargs)
        self.voice = voice
        self.rate = rate

    def generate_from_text(self, text: str, cache_dir=None, path=None, **kwargs):
        cache_dir = Path(cache_dir or self.cache_dir)
        input_text = remove_bookmarks(text)
        input_data = {"input_text": input_text, "service": "edge-tts", "config": {"voice": self.voice, "rate": self.rate}}
        cached = self.get_cached_result(input_data, cache_dir)
        if cached is not None:
            return cached

        audio_path = str(path) if path else self.get_audio_basename(input_data) + ".mp3"
        voices = [self.voice] + [v for v in FALLBACK_VOICES if v != self.voice]
        last_error: Exception | None = None
        for voice in voices:
            try:
                events = asyncio.run(_synthesize(input_text, voice, self.rate, cache_dir / audio_path))
            except Exception as exc:  # voice unavailable, network hiccup, ...
                last_error = exc
                logger.warning(f"Edge TTS voice {voice} failed ({type(exc).__name__}: {exc}); trying the next voice")
                continue
            if voice != self.voice:
                logger.warning(f"Using fallback voice {voice} instead of {self.voice}")
            return {
                "input_text": text,
                "input_data": input_data,
                "original_audio": audio_path,
                "word_boundaries": _word_boundaries(input_text, events),
            }
        raise RuntimeError(
            "Edge TTS could not produce audio with any voice. Check your internet connection. "
            f"Last error: {last_error}"
        )


class SilentPreviewService(SpeechService):
    """Offline stand-in: silent audio whose length matches calm speech (~2.4 words/s)."""

    WORDS_PER_SECOND = 2.4

    def __init__(self, **kwargs):
        initialize_speech_service(self, kwargs)

    def generate_from_text(self, text: str, cache_dir=None, path=None, **kwargs):
        cache_dir = Path(cache_dir or self.cache_dir)
        input_text = remove_bookmarks(text)
        input_data = {"input_text": input_text, "service": "silent-preview"}
        cached = self.get_cached_result(input_data, cache_dir)
        if cached is not None:
            return cached
        audio_path = str(path) if path else self.get_audio_basename(input_data) + ".mp3"
        words = input_text.split()
        seconds = max(1.0, len(words) / self.WORDS_PER_SECOND)
        ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
             "-t", f"{seconds:.2f}", "-q:a", "9", str(cache_dir / audio_path)],
            check=True,
        )
        # evenly spaced word timings so bookmarks still work in previews
        events, cursor = [], 0
        for k, w in enumerate(words):
            events.append({"text": w, "offset": int(k / self.WORDS_PER_SECOND * 1e7), "duration": 0})
        return {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
            "word_boundaries": _word_boundaries(input_text, events),
        }


def get_speech_service(**kwargs) -> SpeechService:
    """Edge TTS by default; ``GOATVEX_VOICE=silent`` for offline previews."""
    if os.environ.get("GOATVEX_VOICE", "").lower() == "silent":
        logger.warning("GOATVEX_VOICE=silent → using silent preview audio (not for final renders)")
        return SilentPreviewService(**kwargs)
    return EdgeTTSService(**kwargs)
