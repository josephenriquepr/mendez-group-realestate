import os
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import config

router = APIRouter()


class PublishRequest(BaseModel):
    image_url: str   # e.g. "/uploads/xxx.jpg"
    caption: str     # Instagram copy text


@router.post("/instagram")
async def publish_instagram(req: PublishRequest):
    if not config.UPLOADPOST_API_KEY or config.UPLOADPOST_API_KEY == "your-uploadpost-api-key-here":
        raise HTTPException(
            status_code=503,
            detail="UPLOADPOST_API_KEY no configurada. Agrégala al archivo .env y reinicia el servidor.",
        )
    if not config.UPLOADPOST_USER or config.UPLOADPOST_USER == "your-uploadpost-user-id-here":
        raise HTTPException(
            status_code=503,
            detail="UPLOADPOST_USER no configurado. Agrégalo al archivo .env y reinicia el servidor.",
        )

    image_local = req.image_url.lstrip("/")
    image_path = Path(image_local)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Imagen no encontrada en el servidor.")

    image_bytes = image_path.read_bytes()
    filename = image_path.name
    mime = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "https://api.upload-post.com/api/upload",
                headers={"Authorization": f"Apikey {config.UPLOADPOST_API_KEY}"},
                data={
                    "user": config.UPLOADPOST_USER,
                    "platform[]": "instagram",
                    "title": req.caption,
                },
                files={"image": (filename, image_bytes, mime)},
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Error de red al contactar Upload-Post: {exc}")

    if response.status_code in (200, 201):
        try:
            return JSONResponse({"success": True, "data": response.json()})
        except Exception:
            return JSONResponse({"success": True, "data": {}})

    raise HTTPException(
        status_code=response.status_code,
        detail=f"Upload-Post respondió {response.status_code}: {response.text[:400]}",
    )
