# Lyric Video Generator — Backend

FastAPI service for the transcription + rendering pipeline.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Requires `ffmpeg`/`ffprobe` on PATH (`apt-get install ffmpeg` on Debian/Ubuntu).

Whisper/alignment models are downloaded on first use into `backend/.models_cache/`
(gitignored). By default this runs fully on CPU with no paid API calls; set
`WHISPER_DEVICE=cuda` in the environment if a GPU is available.

## Stage 1: transcription smoke test

Before running the API, sanity-check the transcription pipeline directly on a
real audio/video file:

```bash
python scripts/test_transcribe_stage1.py /path/to/song.mp3
```

This extracts a mono 16kHz WAV via ffmpeg, runs Whisper (`large-v3` by
default, see `app/config.py`) for the ASR pass, then forced-aligns the words
against the waveform with a wav2vec2 model for frame-accurate timestamps.
It prints a word/start/end/score table and writes the full transcript JSON to
`backend/storage/outputs/<name>.transcript.json`.

## Running the API

```bash
uvicorn app.main:app --reload --port 8000
```

- `POST /api/transcribe` — multipart upload, returns a job id immediately
  (transcription runs in the background; this is a slow CPU-bound job).
- `GET /api/jobs/{job_id}` — poll for status/result.

## Layout

```
app/
  main.py             FastAPI app + CORS
  config.py            model/paths configuration
  models/schemas.py    Word/Segment/TranscriptionResult/Job pydantic models
  pipeline/
    audio_extract.py   ffmpeg audio extraction
    transcribe.py       Whisper ASR + wav2vec2 forced alignment
  api/
    transcribe.py       upload/job endpoints
scripts/
  test_transcribe_stage1.py   standalone CLI test for the pipeline
storage/
  uploads/  audio/  outputs/   (gitignored, created on demand)
```
