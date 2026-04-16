"""
Video render service — runs the Remotion CLI in a background asyncio task
and tracks per-job progress in memory.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional

import config

_PROJECT_ROOT = Path(__file__).parent.parent
_VIDEO_DIR    = _PROJECT_ROOT / "video"
_PUBLIC_DIR   = _VIDEO_DIR / "public"
_RENDER_JS    = _VIDEO_DIR / "render.js"
_UPLOADS_DIR  = Path(config.UPLOAD_DIR)

# In-memory job registry  {job_id: {...}}
_jobs: dict[str, dict] = {}


def _make_job(status: str = "pending") -> dict:
    return {"status": status, "progress": 0, "video_url": None, "error": None}


def get_job(job_id: str) -> Optional[dict]:
    return _jobs.get(job_id)


async def start_render(portada_local: str, extras_locals: list[str], data: dict) -> str:
    """Copy assets, queue a background render task, return the job_id."""
    job_id = uuid.uuid4().hex[:10]
    _jobs[job_id] = _make_job("pending")
    asyncio.create_task(_render(job_id, portada_local, extras_locals, data))
    return job_id


async def _install_if_needed() -> None:
    """Run npm install inside video/ the first time (node_modules absent)."""
    if (_VIDEO_DIR / "node_modules").exists():
        return
    proc = await asyncio.create_subprocess_exec(
        "npm", "install", "--prefer-offline",
        cwd=str(_VIDEO_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    await proc.wait()


async def _render(
    job_id: str,
    portada_local: str,
    extras_locals: list[str],
    data: dict,
) -> None:
    assets_dir = _PUBLIC_DIR / "assets" / job_id
    assets_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── 1. Copy photos into Remotion public/assets/{job_id}/ ──
        _jobs[job_id]["status"] = "preparing"
        photos: list[str] = []
        for i, src_str in enumerate([portada_local] + [e for e in extras_locals if e]):
            src = Path(src_str)
            if src.exists():
                dest = assets_dir / f"photo_{i}{src.suffix}"
                shutil.copy2(src, dest)
                photos.append(f"assets/{job_id}/photo_{i}{src.suffix}")

        if not photos:
            _jobs[job_id].update(status="error", error="No se encontraron fotos válidas.")
            return

        # ── 2. Copy agency logo if provided ───────────────────────
        logo_agencia_local = data.get("logo_agencia_local")
        if logo_agencia_local:
            logo_src = _PROJECT_ROOT / logo_agencia_local
            if logo_src.exists():
                logo_ext = logo_src.suffix
                logo_dest = assets_dir / f"logo{logo_ext}"
                shutil.copy2(logo_src, logo_dest)
                logo_prop = f"assets/{job_id}/logo{logo_ext}"
            else:
                logo_prop = None
        else:
            logo_prop = None

        # ── 3. Write props JSON ────────────────────────────────────
        has_music = (_PUBLIC_DIR / "audio" / "music.mp3").exists()
        props = {
            "photos":            photos,
            "precio":            data.get("precio", 0),
            "tipo":              data.get("tipo_propiedad", "Casa"),
            "operacion":         data.get("operacion", "Venta"),
            "direccion":         data.get("direccion", ""),
            "pueblo":            data.get("pueblo", ""),
            "habitaciones":      data.get("habitaciones"),
            "banos":             data.get("banos"),
            "pies_cuadrados":    data.get("pies_cuadrados_construccion"),
            "estacionamientos":  data.get("estacionamientos"),
            "agente_nombre":     data.get("nombre_agente", ""),
            "agente_licencia":   data.get("licencia_agente", ""),
            "agente_telefono":   data.get("telefono_agente", ""),
            "hasMusic":          has_music,
            "seed":              random.randint(0, 2_147_483_647),
            "tema":              data.get("tema", 0),
            "agencia_tagline":   data.get("tagline_agencia") or None,
            "color_primario":    data.get("color_primario") or None,
            "color_acento":      data.get("color_acento") or None,
            "logo_path":         logo_prop,
        }
        props_file = assets_dir / "props.json"
        props_file.write_text(json.dumps(props, ensure_ascii=False))

        output_name = f"{int(time.time() * 1000)}_{job_id}_reel.mp4"
        output_path = _UPLOADS_DIR / output_name

        # ── 4. npm install if first run ────────────────────────────
        _jobs[job_id].update(status="installing", progress=2)
        await _install_if_needed()

        # ── 5. Run render.js ───────────────────────────────────────
        _jobs[job_id].update(status="rendering", progress=5)

        proc = await asyncio.create_subprocess_exec(
            "node",
            str(_RENDER_JS.resolve()),
            str(props_file.resolve()),
            str(output_path.resolve()),
            cwd=str(_VIDEO_DIR.resolve()),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "FORCE_COLOR": "0"},
        )

        # Read stdout for progress signals
        assert proc.stdout is not None
        while True:
            raw = await proc.stdout.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").strip()
            if line.startswith("PROGRESS:"):
                try:
                    pct = int(line.split(":")[1])
                    # Map 0-100 render progress to 20-95 overall
                    _jobs[job_id]["progress"] = 20 + int(pct * 0.75)
                except ValueError:
                    pass
            elif line == "STATUS:bundling":
                _jobs[job_id].update(status="bundling", progress=8)
            elif line == "STATUS:composing":
                _jobs[job_id].update(status="composing", progress=15)
            elif line == "STATUS:rendering":
                _jobs[job_id].update(status="rendering", progress=20)
            elif line == "STATUS:done":
                _jobs[job_id].update(status="finalizing", progress=97)

        await proc.wait()

        if proc.returncode == 0 and output_path.exists():
            _jobs[job_id].update(status="done", progress=100, video_url=f"/uploads/{output_name}")
        else:
            stderr_bytes = await proc.stderr.read()
            err_text = stderr_bytes.decode("utf-8", errors="replace")[-600:]
            _jobs[job_id].update(status="error", error=err_text or f"returncode={proc.returncode}")

    except Exception as exc:
        _jobs[job_id].update(status="error", error=str(exc))

    finally:
        shutil.rmtree(assets_dir, ignore_errors=True)
