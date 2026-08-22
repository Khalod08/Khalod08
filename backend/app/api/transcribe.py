import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile

from app.config import AUDIO_DIR, UPLOADS_DIR
from app.models.schemas import Job, JobStatus
from app.pipeline.audio_extract import AudioExtractionError, extract_audio
from app.pipeline.transcribe import transcribe

router = APIRouter(prefix="/api", tags=["transcription"])

# In-memory job store. Fine for a single-process MVP; swap for Redis/DB
# before running more than one worker.
_jobs: dict[str, Job] = {}


def _run_pipeline(job_id: str, upload_path: Path):
    job = _jobs[job_id]
    try:
        job.status = JobStatus.EXTRACTING_AUDIO
        audio_path = AUDIO_DIR / f"{job_id}.wav"
        extract_audio(upload_path, audio_path)

        job.status = JobStatus.TRANSCRIBING
        result = transcribe(audio_path)

        job.result = result
        job.status = JobStatus.DONE
    except AudioExtractionError as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
    except Exception as e:  # noqa: BLE001 - surface any pipeline failure to the client
        job.status = JobStatus.FAILED
        job.error = f"{type(e).__name__}: {e}"


@router.post("/transcribe", response_model=Job)
async def create_transcription_job(file: UploadFile, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    suffix = Path(file.filename or "upload").suffix
    upload_path = UPLOADS_DIR / f"{job_id}{suffix}"

    with upload_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    job = Job(id=job_id, status=JobStatus.PENDING, filename=file.filename or "upload")
    _jobs[job_id] = job

    background_tasks.add_task(_run_pipeline, job_id, upload_path)
    return job


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
