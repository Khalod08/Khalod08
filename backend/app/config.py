import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BACKEND_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
AUDIO_DIR = STORAGE_DIR / "audio"
OUTPUTS_DIR = STORAGE_DIR / "outputs"
BACKGROUNDS_DIR = STORAGE_DIR / "backgrounds"
MODELS_CACHE_DIR = BACKEND_DIR / ".models_cache"

for d in (UPLOADS_DIR, AUDIO_DIR, OUTPUTS_DIR, BACKGROUNDS_DIR, MODELS_CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Whisper transcription settings. "large-v3" gives the best accuracy on
# messy/lo-fi/overlapping vocals; drop to "medium" or "small" for faster
# iteration on constrained (CPU-only) hardware.
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "large-v3")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_BATCH_SIZE = int(os.environ.get("WHISPER_BATCH_SIZE", "8"))

# Target sample rate Whisper/wav2vec2 expect.
TARGET_SAMPLE_RATE = 16000

# Tracks longer than this are rejected after extraction (before the slow
# transcription/alignment pass) — MVP scope is short-form (up to 5 min).
MAX_DURATION_SECONDS = int(os.environ.get("MAX_DURATION_SECONDS", "300"))
