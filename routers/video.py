from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from services.video_service  import start_render as remotion_render, get_job as remotion_job
from services.ffmpeg_service import start_render as ffmpeg_render,   get_job as ffmpeg_job

router = APIRouter()

# Prefix job IDs so we know which service owns them
_REMOTION_PREFIX = "r_"
_FFMPEG_PREFIX   = "f_"


class VideoRequest(BaseModel):
    portada_url:  str
    extras_urls:  List[str] = []
    data:         dict
    renderer:     str = "ffmpeg"   # "ffmpeg" | "remotion"
    transition:   str = "fade"     # ffmpeg: fade|slide|zoom|wipe|dissolve|random
    music_path:   Optional[str] = None


@router.post("/generate")
async def generate_video(req: VideoRequest):
    portada_local = req.portada_url.lstrip("/")
    extras_locals = [u.lstrip("/") for u in req.extras_urls]

    if req.renderer == "remotion":
        job_id = await remotion_render(portada_local, extras_locals, req.data)
        return JSONResponse({"job_id": _REMOTION_PREFIX + job_id, "renderer": "remotion"})
    else:
        job_id = await ffmpeg_render(
            portada_local, extras_locals, req.data,
            transition=req.transition,
            music_path=req.music_path,
        )
        return JSONResponse({"job_id": _FFMPEG_PREFIX + job_id, "renderer": "ffmpeg"})


@router.get("/status/{job_id}")
async def video_status(job_id: str):
    if job_id.startswith(_REMOTION_PREFIX):
        job = remotion_job(job_id[len(_REMOTION_PREFIX):])
    elif job_id.startswith(_FFMPEG_PREFIX):
        job = ffmpeg_job(job_id[len(_FFMPEG_PREFIX):])
    else:
        # Legacy fallback
        job = remotion_job(job_id) or ffmpeg_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return JSONResponse(job)
