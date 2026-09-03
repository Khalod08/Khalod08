from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import AUDIO_DIR, BACKGROUNDS_DIR, OUTPUTS_DIR
from app.models.schemas import RenderStatus
from app.pipeline.backgrounds import uploaded_background_path
from app.pipeline.captions import CaptionStyle, write_ass
from app.pipeline.export import CODEC_QUALITY, RESOLUTIONS, export_video
from app.pipeline.render import RenderError
from app.state import get_ready_job, jobs as _jobs

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/export/options")
async def get_export_options():
    return {"resolutions": list(RESOLUTIONS.keys()), "codecs": list(CODEC_QUALITY.keys())}


class ExportRequest(BaseModel):
    resolution: str = "1080p"
    codec: str = "h264"


def _run_export(job_id: str, resolution: str, codec: str):
    job = _jobs[job_id]
    try:
        job.export_status = RenderStatus.RENDERING
        ass_path = OUTPUTS_DIR / f"{job_id}.export.ass"
        write_ass(job.result, ass_path, CaptionStyle())

        background_media = None
        background_preset = None
        if job.background == "upload":
            background_media = uploaded_background_path(BACKGROUNDS_DIR, job_id)
        elif job.background and job.background.startswith("preset:"):
            background_preset = job.background.split(":", 1)[1]

        video_path = OUTPUTS_DIR / f"{job_id}.export.mp4"
        export_video(
            AUDIO_DIR / f"{job_id}.wav",
            ass_path,
            video_path,
            background_media=background_media,
            background_preset=background_preset,
            resolution=resolution,
            codec=codec,
        )
        job.export_status = RenderStatus.DONE
    except (RenderError, ValueError) as e:
        job.export_status = RenderStatus.FAILED
        job.export_error = str(e)
    except Exception as e:  # noqa: BLE001 - surface any export failure to the client
        job.export_status = RenderStatus.FAILED
        job.export_error = f"{type(e).__name__}: {e}"


@router.post("/jobs/{job_id}/export")
async def start_export(job_id: str, req: ExportRequest, background_tasks: BackgroundTasks):
    job = get_ready_job(job_id)
    if job.background_status in (RenderStatus.PENDING, RenderStatus.RENDERING):
        raise HTTPException(status_code=409, detail="background is still building")
    if req.resolution not in RESOLUTIONS:
        raise HTTPException(status_code=400, detail=f"unknown resolution: {req.resolution}")
    if req.codec not in CODEC_QUALITY:
        raise HTTPException(status_code=400, detail=f"unknown codec: {req.codec}")
    job.export_status = RenderStatus.PENDING
    job.export_error = None
    job.export_resolution = req.resolution
    job.export_codec = req.codec
    background_tasks.add_task(_run_export, job_id, req.resolution, req.codec)
    return job


@router.get("/jobs/{job_id}/export/video")
async def get_export_video(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.export_status != RenderStatus.DONE:
        raise HTTPException(status_code=409, detail="export not ready")
    video_path = OUTPUTS_DIR / f"{job_id}.export.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="export output missing")
    return FileResponse(video_path, media_type="video/mp4", filename=f"lyric-video-{job_id}.mp4")
