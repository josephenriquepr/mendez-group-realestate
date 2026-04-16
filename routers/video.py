from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

from services.video_service import start_render, get_job

router = APIRouter()


class VideoRequest(BaseModel):
    portada_url: str
    extras_urls: List[str] = []
    data: dict  # raw property data fields


@router.post("/generate")
async def generate_video(req: VideoRequest):
    portada_local = req.portada_url.lstrip("/")
    extras_locals = [u.lstrip("/") for u in req.extras_urls]
    job_id = await start_render(portada_local, extras_locals, req.data)
    return JSONResponse({"job_id": job_id})


@router.get("/status/{job_id}")
async def video_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return JSONResponse(job)
