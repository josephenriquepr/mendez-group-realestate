"""
FFmpeg video renderer — produces 1080×1920 portrait reels.
Text/overlay rendering uses Pillow (drawtext unavailable without libfreetype).
FFmpeg handles: Ken Burns zoom, xfade transitions, audio mixing.
"""
from __future__ import annotations

import asyncio
import io
import math
import os
import random
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

import config

_PROJECT_ROOT = Path(__file__).parent.parent
_UPLOADS_DIR  = Path(config.UPLOAD_DIR)
_AUDIO_DIR    = _PROJECT_ROOT / "video" / "public" / "audio"

W, H = 1080, 1920

_jobs: dict[str, dict] = {}


# ─── Public API ───────────────────────────────────────────────────────────────

def get_job(job_id: str) -> Optional[dict]:
    return _jobs.get(job_id)


async def start_render(
    portada_local: str,
    extras_locals: list[str],
    data: dict,
    transition: str = "fade",
    music_path: Optional[str] = None,
) -> str:
    job_id = uuid.uuid4().hex[:10]
    _jobs[job_id] = {"status": "pending", "progress": 0, "video_url": None, "error": None}
    asyncio.create_task(_render(job_id, portada_local, extras_locals, data, transition, music_path))
    return job_id


# ─── Renderer ─────────────────────────────────────────────────────────────────

async def _render(job_id, portada_local, extras_locals, data, transition, music_path):
    tmp_dir = _UPLOADS_DIR / f"_tmp_{job_id}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        _jobs[job_id]["status"] = "preparing"
        _jobs[job_id]["progress"] = 3

        # Collect valid photos
        photos: list[Path] = []
        for p in [portada_local] + [e for e in extras_locals if e]:
            path = _PROJECT_ROOT / p if not os.path.isabs(p) else Path(p)
            if path.exists():
                photos.append(path)

        if not photos:
            _jobs[job_id].update(status="error", error="No se encontraron fotos válidas.")
            return

        # ── 1. Create overlay PNGs with Pillow ────────────────────────────
        _jobs[job_id]["status"] = "rendering"
        _jobs[job_id]["progress"] = 8

        primary = data.get("color_primario") or "#1a6b8a"
        accent  = data.get("color_acento")   or "#f4a623"

        hero_overlay   = _draw_hero_overlay(data, primary, accent)
        contact_slide  = _draw_contact_slide(data, primary, accent)

        hero_path    = tmp_dir / "hero_overlay.png"
        contact_path = tmp_dir / "contact_slide.png"
        hero_overlay.save(hero_path,    "PNG")
        contact_slide.save(contact_path, "PNG")

        # Badge overlays for extra photos
        badge_paths: list[Path] = []
        for i, _ in enumerate(photos[1:], start=1):
            badge = _draw_badge(i + 1, len(photos), primary)
            p = tmp_dir / f"badge_{i}.png"
            badge.save(p, "PNG")
            badge_paths.append(p)

        # ── 2. Build + run FFmpeg ─────────────────────────────────────────
        _jobs[job_id]["progress"] = 12

        output_name = f"{int(time.time()*1000)}_{job_id}_ffmpeg.mp4"
        output_path = _UPLOADS_DIR / output_name

        music_file = _find_music(music_path)
        cmd = _build_cmd(
            photos, hero_path, badge_paths, contact_path,
            output_path, transition, music_file, data
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        total_dur = _estimate_duration(photos)
        stderr_lines: list[str] = []

        async for raw in _read_lines(proc.stderr):
            stderr_lines.append(raw)
            if "time=" in raw:
                try:
                    t_str = raw.split("time=")[1].split()[0]
                    t_sec = _parse_time(t_str)
                    pct = min(95, 12 + int((t_sec / total_dur) * 83))
                    _jobs[job_id]["progress"] = pct
                except Exception:
                    pass

        await proc.wait()

        if proc.returncode == 0 and output_path.exists():
            _jobs[job_id].update(status="done", progress=100,
                                  video_url=f"/uploads/{output_name}")
        else:
            err = "".join(stderr_lines[-25:])
            _jobs[job_id].update(status="error",
                                  error=err or f"returncode={proc.returncode}")

    except Exception as exc:
        _jobs[job_id].update(status="error", error=str(exc))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─── FFmpeg command ───────────────────────────────────────────────────────────

PD  = 4    # photo display seconds
TD  = 1    # transition seconds
CD  = 4    # contact slide seconds
FPS = 30


def _build_cmd(
    photos: list[Path],
    hero_overlay: Path,
    badge_paths: list[Path],
    contact_path: Path,
    output: Path,
    transition: str,
    music: Optional[Path],
    data: dict,
) -> list[str]:
    n   = len(photos)
    cmd = ["ffmpeg", "-y"]

    # ── Inputs ─────────────────────────────────────────────────────────────
    # Photo inputs (looped to cover duration with transition overlap)
    for p in photos:
        cmd += ["-loop", "1", "-t", str(PD + TD + 1), "-i", str(p)]

    # Hero overlay (transparent PNG)
    cmd += ["-loop", "1", "-t", str(PD + TD + 1), "-i", str(hero_overlay)]
    hero_idx = n

    # Badge overlays for slides 1..n-1
    badge_idx_start = n + 1
    for bp in badge_paths:
        cmd += ["-loop", "1", "-t", str(PD + TD + 1), "-i", str(bp)]

    # Contact slide (full image)
    contact_idx = n + 1 + len(badge_paths)
    cmd += ["-loop", "1", "-t", str(CD + 1), "-i", str(contact_path)]

    # Music
    music_idx = contact_idx + 1
    has_music = music is not None
    if has_music:
        cmd += ["-i", str(music)]

    # ── Filter complex ──────────────────────────────────────────────────────
    fc: list[str] = []
    frames_pp = (PD + TD + 1) * FPS

    # 1. Zoompan Ken Burns on each photo
    for i in range(n):
        if i % 2 == 0:
            zoom = f"zoom+0.0008"
            xexpr = f"iw/2-(iw/zoom/2)"
            yexpr = f"ih/2-(ih/zoom/2)"
        else:
            zoom = f"if(eq(on\\,1)\\,1.08\\,max(1\\,zoom-0.0008))"
            xexpr = f"iw/2-(iw/zoom/2)"
            yexpr = f"ih/4-(ih/zoom/4)"

        fc.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},"
            f"zoompan=z='{zoom}':x='{xexpr}':y='{yexpr}':d={frames_pp}:s={W}x{H}:fps={FPS},"
            f"setsar=1[kb{i}]"
        )

    # 2. Overlay hero text on slide 0
    fc.append(
        f"[kb0][{hero_idx}:v]overlay=0:0[ov0]"
    )

    # 3. Overlay badges on slides 1..n-1
    for i in range(1, n):
        badge_input = badge_idx_start + (i - 1)
        fc.append(
            f"[kb{i}][{badge_input}:v]overlay=0:0[ov{i}]"
        )

    # 4. Contact slide (scale to 1080x1920)
    fc.append(
        f"[{contact_idx}:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1[contact]"
    )

    # 5. xfade chain: ov0, ov1, ..., ov{n-1}, contact
    xt = _map_transition(transition)
    sources = [f"[ov{i}]" for i in range(n)] + ["[contact]"]
    total = len(sources)

    if total == 1:
        fc.append("[ov0]copy[vout]")
    else:
        prev = sources[0]
        for i in range(1, total):
            nxt  = sources[i]
            off  = i * PD  # start transition at this second
            lbl  = "[vout]" if i == total - 1 else f"[xf{i}]"
            fc.append(f"{prev}{nxt}xfade=transition={xt}:duration={TD}:offset={off}{lbl}")
            prev = f"[xf{i}]"

    # 6. Audio
    total_s = n * PD + CD
    if has_music:
        fc.append(
            f"[{music_idx}:a]atrim=0:{total_s},"
            f"afade=t=in:st=0:d=2,"
            f"afade=t=out:st={total_s-2}:d=2,"
            f"volume=0.32[aout]"
        )
        cmd += ["-filter_complex", ";".join(fc)]
        cmd += ["-map", "[vout]", "-map", "[aout]"]
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-filter_complex", ";".join(fc)]
        cmd += ["-map", "[vout]", "-an"]

    cmd += [
        "-c:v", "libx264", "-preset", "fast",
        "-crf", "23", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-movflags", "+faststart",
        str(output),
    ]
    return cmd


# ─── Pillow overlay helpers ───────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load the best available system font."""
    candidates_bold = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    candidates_reg = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in (candidates_bold if bold else candidates_reg):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _hex_rgba(hex_color: str, alpha: int = 255) -> tuple:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return (r, g, b, alpha)


def _draw_hero_overlay(data: dict, primary: str, accent: str) -> Image.Image:
    """Semi-transparent overlay image for the hero slide."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    primary_c = _hex_rgba(primary, 230)
    accent_c  = _hex_rgba(accent,  255)
    white     = (255, 255, 255, 255)
    white_dim = (255, 255, 255, 200)

    # Bottom gradient (draw layered semi-transparent rects)
    for i in range(500):
        alpha = int(210 * (i / 500) ** 1.2)
        draw.rectangle([(0, H - 500 + i), (W, H - 500 + i + 1)], fill=(0, 0, 0, alpha))

    # Operation badge (top-left)
    op = (data.get("operacion") or "Venta").upper()
    draw.rounded_rectangle([(40, 55), (320, 130)], radius=40, fill=primary_c)
    draw.text((50, 65), op, font=_font(38, bold=True), fill=white)

    y = H - 520
    pad = 50

    # Price
    price = data.get("precio")
    if price:
        price_str = f"${int(price):,}"
        draw.text((pad, y), price_str, font=_font(86, bold=True), fill=accent_c)
        y += 100

    # Type · Pueblo
    tipo   = data.get("tipo_propiedad") or data.get("tipo") or ""
    pueblo = data.get("pueblo") or ""
    if tipo or pueblo:
        line = f"{tipo}  ·  {pueblo}".strip("  ·  ")
        draw.text((pad, y), line, font=_font(44, bold=True), fill=white)
        y += 58

    # Address
    addr = data.get("direccion") or ""
    if addr:
        if len(addr) > 44:
            addr = addr[:41] + "…"
        draw.text((pad, y), addr, font=_font(32), fill=white_dim)
        y += 50

    # Stats
    parts = []
    hab = data.get("habitaciones")
    ban = data.get("banos")
    m2  = data.get("pies_cuadrados_construccion") or data.get("pies_cuadrados")
    if hab: parts.append(f"🛏 {hab} Hab.")
    if ban: parts.append(f"🚿 {ban} Baños")
    if m2:  parts.append(f"📐 {int(m2):,} p²")

    x = pad
    for part in parts:
        bw = _font(28).getlength(part) + 32
        draw.rounded_rectangle([(x, y), (x + int(bw), y + 52)], radius=14,
                                fill=(255, 255, 255, 45))
        draw.text((x + 12, y + 10), part, font=_font(26, bold=True), fill=white)
        x += int(bw) + 12

    return img


def _draw_contact_slide(data: dict, primary: str, accent: str) -> Image.Image:
    """Full 1080×1920 contact slide."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    p_c = _hex_rgba(primary)
    a_c = _hex_rgba(accent)
    white = (255, 255, 255, 255)
    white_dim = (255, 255, 255, 180)

    # Background gradient bands
    for y in range(H):
        t = y / H
        # primary → dark blue
        r = int(_hex_rgba(primary)[0] * (1-t) + 5 * t)
        g = int(_hex_rgba(primary)[1] * (1-t) + 15 * t)
        b = int(_hex_rgba(primary)[2] * (1-t) + 22 * t)
        draw.line([(0,y),(W,y)], fill=(r,g,b,255))

    # Diagonal stripe accents
    for i in range(7):
        x = -200 + i * 190
        draw.polygon([(x,0),(x+120,0),(x+120+H//2,H),(x+H//2,H)],
                     fill=(255,255,255,8))

    # Center content
    cx = W // 2
    cy = H // 2

    agente  = data.get("nombre_agente") or data.get("agente_nombre") or "Agente ListaPro"
    lic     = data.get("licencia_agente") or data.get("agente_licencia") or ""
    tel     = data.get("telefono_agente") or data.get("agente_telefono") or ""
    tagline = data.get("tagline_agencia") or data.get("agencia_tagline") or "Bienes Raíces · Puerto Rico"

    # Agency name / agent
    name_font = _font(64, bold=True)
    nm_w = name_font.getlength(agente)
    draw.text(((W - nm_w)//2, cy - 280), agente, font=name_font, fill=white)

    if lic:
        lic_str = f"Lic. {lic}"
        lw = _font(30).getlength(lic_str)
        draw.text(((W - lw)//2, cy - 200), lic_str, font=_font(30), fill=white_dim)

    # Accent divider
    draw.rectangle([(cx-60, cy-140), (cx+60, cy-135)], fill=a_c)

    # Tagline
    tw = _font(34).getlength(tagline)
    draw.text(((W - tw)//2, cy - 108), tagline, font=_font(34), fill=white_dim)

    # Phone pill
    if tel:
        phone_str = f"📞 {tel}"
        pw = _font(48, bold=True).getlength(phone_str)
        pill_w = int(pw) + 80
        pill_x = (W - pill_w) // 2
        pill_y = cy - 30
        draw.rounded_rectangle(
            [(pill_x, pill_y), (pill_x + pill_w, pill_y + 90)],
            radius=22, fill=a_c
        )
        draw.text((pill_x + 40, pill_y + 18), phone_str,
                  font=_font(48, bold=True), fill=(28, 43, 53, 255))

    return img.convert("RGB")


def _draw_badge(index: int, total: int, primary: str) -> Image.Image:
    """Transparent counter badge for extra photo slides."""
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    p_c  = _hex_rgba(primary, 210)
    text = f"{index} / {total}"
    tw   = _font(38, bold=True).getlength(text)
    pad  = 24
    x = W - int(tw) - pad*2 - 40
    y = 44
    draw.rounded_rectangle(
        [(x, y), (x + int(tw) + pad*2, y + 72)],
        radius=36, fill=p_c
    )
    draw.text((x + pad, y + 14), text, font=_font(38, bold=True), fill=(255,255,255,255))
    return img


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _map_transition(name: str) -> str:
    mapping = {
        "fade":    "fade",
        "slide":   "slideleft",
        "zoom":    "zoomin",
        "wipe":    "wipeleft",
        "dissolve":"dissolve",
        "random":  random.choice(["fade","slideleft","wipeleft","dissolve"]),
    }
    return mapping.get(name, "fade")


def _find_music(music_path: Optional[str] = None) -> Optional[Path]:
    if music_path:
        p = Path(music_path)
        if p.exists():
            return p
    for name in ["music.mp3","background.mp3","bg.mp3","ambient.mp3"]:
        p = _AUDIO_DIR / name
        if p.exists():
            return p
    return None


def _parse_time(t: str) -> float:
    try:
        parts = t.split(":")
        if len(parts) == 3:
            return float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
        return float(t)
    except Exception:
        return 0.0


def _estimate_duration(photos: list[Path]) -> float:
    return len(photos) * PD + CD


async def _read_lines(stream):
    while True:
        line = await stream.readline()
        if not line:
            break
        yield line.decode("utf-8", errors="replace")
