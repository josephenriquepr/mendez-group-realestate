import os
import time
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from models.property import PropertyData
from services.openai_service import generate_content
from services.pdf_service import generate_pdf
from services.image_service import generate_instagram_image, generate_instagram_carousel
import config

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _int(val: Optional[str]) -> Optional[int]:
    try:
        return int(val) if val and val.strip() else None
    except (ValueError, TypeError):
        return None


def _float(val: Optional[str]) -> Optional[float]:
    try:
        return float(val) if val and val.strip() else None
    except (ValueError, TypeError):
        return None


async def _save_file(file: UploadFile, prefix: str) -> str:
    timestamp = int(time.time() * 1000)
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in file.filename)
    filename = f"{timestamp}_{prefix}_{safe_name}"
    path = os.path.join(config.UPLOAD_DIR, filename)
    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)
    return f"/uploads/{filename}"


@router.post("/generate")
async def generate(
    tipo_propiedad: str = Form(...),
    operacion: str = Form(...),
    direccion: str = Form(...),
    pueblo: str = Form(...),
    precio: str = Form(...),
    descripcion_agente: str = Form(...),
    nombre_agente: str = Form(...),
    licencia_agente: str = Form(...),
    telefono_agente: str = Form(...),
    email_agente: str = Form(""),
    habitaciones: Optional[str] = Form(None),
    banos: Optional[str] = Form(None),
    pies_cuadrados_construccion: Optional[str] = Form(None),
    metros_o_cuerdas_terreno: Optional[str] = Form(None),
    estacionamientos: Optional[str] = Form(None),
    amenidades: List[str] = Form(default=[]),
    nombre_agencia: Optional[str] = Form(None),
    tagline_agencia: Optional[str] = Form(None),
    color_primario: Optional[str] = Form(None),
    color_acento: Optional[str] = Form(None),
    foto_portada: UploadFile = File(...),
    fotos_extras: List[UploadFile] = File(default=[]),
    logo_agencia: Optional[UploadFile] = File(None),
):
    # Validate cover photo
    if foto_portada.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="La foto de portada debe ser una imagen (JPG, PNG, WEBP).")

    # Save cover photo
    portada_url = await _save_file(foto_portada, "portada")

    # Save extra photos
    extras_urls = []
    for extra in fotos_extras:
        if extra.filename and extra.content_type in ALLOWED_IMAGE_TYPES:
            url = await _save_file(extra, "extra")
            extras_urls.append(url)

    # Save agency logo (optional)
    agencia_logo_url = None
    if logo_agencia and logo_agencia.filename and logo_agencia.content_type in ALLOWED_IMAGE_TYPES:
        agencia_logo_url = await _save_file(logo_agencia, "agencia_logo")

    # Build property data object (coerce strings to numbers, empty → None)
    precio_float = _float(precio)
    if precio_float is None:
        raise HTTPException(status_code=422, detail="El precio es requerido y debe ser un número.")

    data = PropertyData(
        tipo_propiedad=tipo_propiedad,
        operacion=operacion,
        direccion=direccion,
        pueblo=pueblo,
        precio=precio_float,
        habitaciones=_int(habitaciones),
        banos=_float(banos),
        pies_cuadrados_construccion=_int(pies_cuadrados_construccion),
        metros_o_cuerdas_terreno=metros_o_cuerdas_terreno or None,
        estacionamientos=_int(estacionamientos),
        amenidades=amenidades,
        descripcion_agente=descripcion_agente,
        nombre_agente=nombre_agente,
        licencia_agente=licencia_agente,
        telefono_agente=telefono_agente,
        email_agente=email_agente,
    )

    try:
        result = await generate_content(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando contenido con IA: {str(e)}")

    # Resolve agency logo local path
    agencia_logo_local = agencia_logo_url.lstrip("/") if agencia_logo_url else None
    portada_local = portada_url.lstrip("/")
    extras_locals = [u.lstrip("/") for u in extras_urls]

    try:
        pdf_url = generate_pdf(
            data, result["listing_description"], portada_url, extras_urls,
            primary_color=color_primario or "#1a6b8a",
            accent_color=color_acento or "#f4a623",
            nombre_agencia=nombre_agencia or "ListaPro",
        )
    except Exception:
        pdf_url = None  # PDF failure is non-fatal

    # ── Instagram carousel (Pillow) ───────────────────────────────────────
    instagram_image_url = None
    carousel_urls: list = []
    try:
        ts = int(time.time() * 1000)
        carousel_dir = os.path.join(config.UPLOAD_DIR, f"carousel_{ts}")
        carousel_paths = generate_instagram_carousel(
            portada_local, extras_locals, data, carousel_dir,
            logo_path=agencia_logo_local,
            primary_color=color_primario or "#1a6b8a",
            accent_color=color_acento or "#f4a623",
            agencia_tagline=tagline_agencia or "Bienes Raíces · Puerto Rico",
        )
        carousel_subdir = os.path.basename(carousel_dir)
        carousel_urls = [
            f"/uploads/{carousel_subdir}/{os.path.basename(p)}"
            for p in carousel_paths
        ]
        instagram_image_url = carousel_urls[0] if carousel_urls else None
    except Exception:
        carousel_urls = []
        instagram_image_url = None

    return JSONResponse({
        "listing_description": result["listing_description"],
        "instagram_copy": result["instagram_copy"],
        "foto_portada_url": portada_url,
        "fotos_extras_urls": extras_urls,
        "pdf_url": pdf_url,
        "instagram_image_url": instagram_image_url,
        "carousel_urls": carousel_urls,
        "agencia_logo_url": agencia_logo_url,
    })


@router.get("/health")
async def health():
    return {"status": "ok"}
