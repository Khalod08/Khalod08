"""Stage 1b: word-level, frame-accurate transcription.

Two-pass approach (this is what sets WhisperX apart from vanilla Whisper):

  1. ASR pass — faster-whisper (large-v3 by default) transcribes the audio
     into text + rough segment/word timestamps. Whisper's own timestamps are
     derived from cross-attention and are only accurate to ~1s, which is not
     good enough for beat-synced captions.
  2. Forced-alignment pass — a phoneme-level wav2vec2 CTC model is forced-
     aligned against the transcribed text using the actual audio waveform,
     producing word boundaries accurate to the audio frame. This is the step
     that gets us "synced to actual transients, not rounded".

Both passes run on CPU by default (WHISPER_DEVICE=cpu); set WHISPER_DEVICE=cuda
if a GPU is available for materially faster iteration.
"""

from pathlib import Path
from typing import Optional

import whisperx

from app.config import (
    WHISPER_BATCH_SIZE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    WHISPER_MODEL,
    MODELS_CACHE_DIR,
)
from app.models.schemas import Segment, TranscriptionResult, Word

_asr_model = None
_align_model_cache: dict[str, tuple] = {}


def _get_asr_model():
    global _asr_model
    if _asr_model is None:
        _asr_model = whisperx.load_model(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
            download_root=str(MODELS_CACHE_DIR),
            # condition_on_prev_text=False is whisperx's default and reduces
            # hallucination looping on noisy/distorted audio.
        )
    return _asr_model


def _get_align_model(language_code: str):
    if language_code not in _align_model_cache:
        model_a, metadata = whisperx.load_align_model(
            language_code=language_code, device=WHISPER_DEVICE
        )
        _align_model_cache[language_code] = (model_a, metadata)
    return _align_model_cache[language_code]


def transcribe(
    audio_path: Path,
    language: Optional[str] = None,
    batch_size: int = WHISPER_BATCH_SIZE,
) -> TranscriptionResult:
    audio = whisperx.load_audio(str(audio_path))

    model = _get_asr_model()
    asr_result = model.transcribe(audio, batch_size=batch_size, language=language)

    detected_language = asr_result["language"]
    model_a, metadata = _get_align_model(detected_language)

    aligned = whisperx.align(
        asr_result["segments"],
        model_a,
        metadata,
        audio,
        WHISPER_DEVICE,
        return_char_alignments=False,
    )

    segments: list[Segment] = []
    for seg in aligned["segments"]:
        words = [
            Word(
                text=w["word"],
                # Words without alignable characters (e.g. bare punctuation)
                # come back without start/end from whisperx; fall back to the
                # segment bounds rather than dropping the word.
                start=w.get("start", seg["start"]),
                end=w.get("end", seg["end"]),
                score=w.get("score"),
            )
            for w in seg.get("words", [])
        ]
        segments.append(
            Segment(text=seg["text"].strip(), start=seg["start"], end=seg["end"], words=words)
        )

    duration = segments[-1].end if segments else 0.0
    return TranscriptionResult(language=detected_language, duration=duration, segments=segments)
