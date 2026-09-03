# Lyric Video Generator — Backend

FastAPI service for the transcription, editing, and rendering pipeline. Pair
with `../frontend` for the editor UI.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Requires `ffmpeg`/`ffprobe` on PATH:
- macOS: `brew install ffmpeg`
- Debian/Ubuntu: `apt-get install ffmpeg`
- Windows: install a build from ffmpeg.org and add it to PATH

Whisper/alignment models are downloaded from Hugging Face on first use into
`backend/.models_cache/` (gitignored) — needs normal internet access. By
default this runs fully on CPU with no paid API calls; set
`WHISPER_DEVICE=cuda` if a GPU is available (materially faster).

Optional env vars (see `app/config.py` for defaults):
- `WHISPER_MODEL` (default `large-v3`; try `medium` or `small` for faster iteration)
- `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`, `WHISPER_BATCH_SIZE`
- `MAX_DURATION_SECONDS` (default `300` — tracks longer than this are rejected)

## Running the API

```bash
uvicorn app.main:app --reload --port 8000
```

Then run the frontend (`../frontend`, `npm run dev`) and open
`http://localhost:5173` — it proxies `/api` to this server.

## Stage 1 smoke test (optional)

Sanity-check just the transcription pipeline, no server needed:

```bash
python scripts/test_transcribe_stage1.py /path/to/song.mp3
```

Prints a word/start/end/score table and writes the full transcript JSON to
`backend/storage/outputs/<name>.transcript.json`.

## API overview

Everything is job-centric: upload creates a job, background tasks advance
it, the frontend polls `GET /api/jobs/{id}` for status/result.

- `POST /api/transcribe` — multipart upload (audio or video, up to
  `MAX_DURATION_SECONDS`). Returns a job immediately; extraction +
  transcription run in the background.
- `PUT /api/jobs/{id}/transcript` — save manual corrections.
- `GET /api/jobs/{id}/audio` — the extracted track, for the editor's player.
- `GET /api/backgrounds/presets` — built-in gradient/solid presets.
- `POST /api/jobs/{id}/background/preset` — `{"preset": "<id>"}`.
- `POST /api/jobs/{id}/background/upload` — multipart `files`. One file:
  used directly (image loops, video plays/loops). More than one: must all
  be images, built into a crossfaded slideshow spanning the track — this is
  itself a background job (`background_status`/`background_error` on the
  job; poll before rendering).
- `POST /api/jobs/{id}/render` → `GET /api/jobs/{id}/render/video` — quick
  1080p preview render.
- `GET /api/export/options`, `POST /api/jobs/{id}/export` → `GET
  /api/jobs/{id}/export/video` — final export, `{"resolution": "1080p" |
  "1440p" | "4k", "codec": "h264" | "h265"}`.

## Layout

```
app/
  main.py               FastAPI app + CORS
  config.py              paths, model, and duration-cap configuration
  state.py                shared in-memory job store + get_ready_job helper
  models/schemas.py      Word/Segment/TranscriptionResult/Job pydantic models
  pipeline/
    audio_extract.py     ffmpeg audio extraction + duration probing
    transcribe.py         Whisper ASR + wav2vec2 forced alignment
    captions.py            transcript -> ASS captions (eased pop-in animation)
    backgrounds.py         preset/upload background resolution
    slideshow.py            multi-image -> crossfaded slideshow video
    render.py               ffmpeg burn-in (preview quality)
    export.py               ffmpeg burn-in (export quality, up to 4K)
  api/
    transcribe.py          upload/job/transcript/audio endpoints
    render.py                background + preview render endpoints
    export.py                final export endpoints
scripts/
  test_transcribe_stage1.py    standalone transcription CLI test
  test_caption_render_stage2.py  standalone caption burn-in CLI test
  testdata/                    synthetic messy-audio fixture + generator
storage/
  uploads/ audio/ outputs/ backgrounds/   (gitignored, created on demand)
```
