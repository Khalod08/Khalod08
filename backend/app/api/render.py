import shutil

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import AUDIO_DIR, BACKGROUNDS_DIR, OUTPUTS_DIR
from app.models.schemas import Job, RenderStatus
from app.pipeline.backgrounds import PRESETS, list_presets, uploaded_background_path
from app.pipeline.captions import CaptionStyle, write_ass
from app.pipeline.render import RenderError, render_burn_in
from app.state import get_ready_job, jobs as _jobs

router = APIRouter(prefix="/api", tags=["render"])


@router.get("/backgrounds/presets")
async def get_presets():
    return list_presets()


@router.post("/jobs/{job_id}/background/upload", response_model=Job)
async def upload_background(job_id: str, file: UploadFile):
    job = get_ready_job(job_id)
    suffix = Path(file.filename or "background").suffix or ".bin"
    dest = BACKGROUNDS_DIR / f"{job_id}{suffix}"
    # clear any previously uploaded background under a different extension
    for existing in BACKGROUNDS_DIR.glob(f"{job_id}.*"):
        existing.unlink()
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    job.background = "upload"
    return job


class PresetChoice(BaseModel):
    preset: str


@router.post("/jobs/{job_id}/background/preset", response_model=Job)
async def choose_background_preset(job_id: str, choice: PresetChoice):
    job = get_ready_job(job_id)
    if choice.preset not in PRESETS:
        raise HTTPException(status_code=400, detail=f"unknown preset: {choice.preset}")
    job.background = f"preset:{choice.preset}"
    return job


def _run_render(job_id: str):
    job = _jobs[job_id]
    try:
        job.render_status = RenderStatus.RENDERING
        ass_path = OUTPUTS_DIR / f"{job_id}.ass"
        write_ass(job.result, ass_path, CaptionStyle())

        background_media = None
        background_preset = None
        if job.background == "upload":
            background_media = uploaded_background_path(BACKGROUNDS_DIR, job_id)
        elif job.background and job.background.startswith("preset:"):
            background_preset = job.background.split(":", 1)[1]

        video_path = OUTPUTS_DIR / f"{job_id}.render.mp4"
        render_burn_in(
            AUDIO_DIR / f"{job_id}.wav",
            ass_path,
            video_path,
            background_media=background_media,
            background_preset=background_preset,
        )
        job.render_status = RenderStatus.DONE
    except RenderError as e:
        job.render_status = RenderStatus.FAILED
        job.render_error = str(e)
    except Exception as e:  # noqa: BLE001 - surface any render failure to the client
        job.render_status = RenderStatus.FAILED
        job.render_error = f"{type(e).__name__}: {e}"


@router.post("/jobs/{job_id}/render", response_model=Job)
async def start_render(job_id: str, background_tasks: BackgroundTasks):
    job = get_ready_job(job_id)
    job.render_status = RenderStatus.PENDING
    job.render_error = None
    background_tasks.add_task(_run_render, job_id)
    return job


@router.get("/jobs/{job_id}/render/video")
async def get_render_video(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.render_status != RenderStatus.DONE:
        raise HTTPException(status_code=409, detail="render not ready")
    video_path = OUTPUTS_DIR / f"{job_id}.render.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="render output missing")
    return FileResponse(video_path, media_type="video/mp4")
