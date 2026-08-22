from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Word(BaseModel):
    """A single transcribed word with frame-accurate timing."""

    text: str
    start: float = Field(..., description="Start time in seconds, float precision")
    end: float = Field(..., description="End time in seconds, float precision")
    score: Optional[float] = Field(
        None, description="Alignment confidence (0-1); low scores flag words worth manual review"
    )


class Segment(BaseModel):
    """A sentence/phrase-level grouping of words, as produced by Whisper."""

    text: str
    start: float
    end: float
    words: list[Word]


class TranscriptionResult(BaseModel):
    language: str
    duration: float
    segments: list[Segment]


class JobStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    ALIGNING = "aligning"
    DONE = "done"
    FAILED = "failed"


class RenderStatus(str, Enum):
    PENDING = "pending"
    RENDERING = "rendering"
    DONE = "done"
    FAILED = "failed"


class Job(BaseModel):
    id: str
    status: JobStatus
    filename: str
    error: Optional[str] = None
    result: Optional[TranscriptionResult] = None

    # Stage 4: chosen background, either "preset:<name>" or "upload" (an
    # uploaded file stored under BACKGROUNDS_DIR/{job_id}.<ext>).
    background: Optional[str] = None

    render_status: Optional[RenderStatus] = None
    render_error: Optional[str] = None

    # Stage 5: final export (higher quality / configurable resolution &
    # codec than the quick preview render above).
    export_status: Optional[RenderStatus] = None
    export_error: Optional[str] = None
    export_resolution: Optional[str] = None
    export_codec: Optional[str] = None
