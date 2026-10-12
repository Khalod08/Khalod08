"""Voiceover for Manim via free Microsoft Edge TTS (``edge-tts``).

manim-voiceover has no Edge TTS service built in, so this is a small custom
``SpeechService``. It asks Edge TTS for *word boundaries*, which lets
``self.wait_until_bookmark(...)`` sync animations to words exactly, with no
speech-recognition model needed.

Voice: ``en-CA-LiamNeural`` (calm Canadian). If that voice is unavailable the
next calm voice in ``FALLBACK_VOICES`` is tried.

``GOATVEX_VOICE`` picks the voice:

* ``edge`` (default on your PC): Edge TTS, the real GoatVex voice.
* ``auto`` (default in Claude Code on the web): Edge TTS if it can be reached,
  otherwise the offline voice below. The choice is made once per video, so a
  video never switches voices halfway.
* ``offline``: SVOX Pico (``pico2wave``) or eSpeak NG, installed on the machine.
  Less natural, but needs no internet.
* ``silent``: silent audio of a realistic length, for timing-only previews.

Behind a proxy (cloud sessions), Edge TTS goes through ``HTTPS_PROXY``.
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

    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or None
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary", proxy=proxy)
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
        events = []
        for k, w in enumerate(words):
            events.append({"text": w, "offset": int(k / self.WORDS_PER_SECOND * 1e7), "duration": 0})
        return {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
            "word_boundaries": _word_boundaries(input_text, events),
        }


OFFLINE_TEMPO = 0.94  # pico speaks quickly: slow it a little (calm, never rushed)


def offline_engine() -> str | None:
    for exe in ("pico2wave", "espeak-ng"):
        if shutil.which(exe):
            return exe
    return None


def _duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(path)], capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


class OfflineVoiceService(SpeechService):
    """Offline text-to-speech (SVOX Pico, else eSpeak NG). Word timings are spread over the clip in
    proportion to word length (these engines don't report word boundaries)."""

    def __init__(self, **kwargs):
        initialize_speech_service(self, kwargs)
        self.engine = offline_engine()
        if self.engine is None:
            raise RuntimeError("No offline voice installed (install libttspico-utils or espeak-ng).")

    def generate_from_text(self, text: str, cache_dir=None, path=None, **kwargs):
        cache_dir = Path(cache_dir or self.cache_dir)
        input_text = remove_bookmarks(text)
        input_data = {"input_text": input_text, "service": "offline", "config": {"engine": self.engine}}
        cached = self.get_cached_result(input_data, cache_dir)
        if cached is not None:
            return cached
        audio_path = str(path) if path else self.get_audio_basename(input_data) + ".mp3"
        wav = cache_dir / (Path(audio_path).stem + ".raw.wav")
        if self.engine == "pico2wave":
            subprocess.run(["pico2wave", "-l", "en-US", "-w", str(wav), input_text], check=True)
            tempo = OFFLINE_TEMPO
        else:
            subprocess.run(["espeak-ng", "-v", "en-us", "-s", "150", "-w", str(wav), input_text], check=True)
            tempo = 1.0
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-filter:a", f"atempo={tempo}",
                        "-q:a", "4", str(cache_dir / audio_path)], check=True)
        wav.unlink(missing_ok=True)
        total = _duration(cache_dir / audio_path)
        words = input_text.split()
        weights = [len(w) + 2 for w in words] or [1]
        events, t = [], 0.0
        for w, wt in zip(words, weights):
            events.append({"text": w, "offset": int(t / sum(weights) * total * 1e7), "duration": 0})
            t += wt
        return {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
            "word_boundaries": _word_boundaries(input_text, events),
        }


def edge_reachable(timeout: float = 20.0) -> bool:
    """One short synthesis to see whether Edge TTS answers from here."""
    import tempfile

    async def probe(path):
        await asyncio.wait_for(_synthesize("Hi.", DEFAULT_VOICE, DEFAULT_RATE, path), timeout)

    with tempfile.TemporaryDirectory() as d:
        try:
            asyncio.run(probe(Path(d) / "probe.mp3"))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Edge TTS is not reachable ({type(exc).__name__}: {exc})")
            return False


def get_speech_service(**kwargs) -> SpeechService:
    """See the module docstring for GOATVEX_VOICE (edge | auto | offline | silent)."""
    mode = os.environ.get("GOATVEX_VOICE", "edge").lower()
    if mode == "silent":
        logger.warning("GOATVEX_VOICE=silent → using silent preview audio (not for final renders)")
        return SilentPreviewService(**kwargs)
    if mode == "offline":
        return OfflineVoiceService(**kwargs)
    if mode == "auto" and not edge_reachable():
        if offline_engine():
            logger.warning("Using the offline voice for this video (Edge TTS unreachable)")
            return OfflineVoiceService(**kwargs)
        logger.warning("No offline voice installed either → silent preview audio")
        return SilentPreviewService(**kwargs)
    return EdgeTTSService(**kwargs)
