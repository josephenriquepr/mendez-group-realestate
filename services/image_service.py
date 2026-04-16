"""
Instagram image generator — 1080×1080 JPEG.
Composites the property cover photo with a dark gradient and text overlay.
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

_LOGO_PATH = Path(__file__).parent.parent / "static" / "img" / "logo-mendez-group.png"

from models.property import PropertyData

SIZE = 1080  # pixels

# ── Font discovery (macOS first, then Linux, then Windows) ────────────────────
_BOLD_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
_REGULAR_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in (_BOLD_PATHS if bold else _REGULAR_PATHS):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Pillow 10.1+ accepts a size parameter for the built-in bitmap font
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_gradient(width: int, height: int) -> Image.Image:
    """
    Returns an RGBA image (black with variable alpha) to use as a dark overlay.
    Top is nearly transparent, bottom is ~95 % opaque.
    """
    col = Image.new("L", (1, height))
    for y in range(height):
        if y < 200:
            a = int(65 * y / 200)           # 0 → 65
        elif y < 580:
            t = (y - 200) / 380
            a = int(65 + 65 * t)            # 65 → 130
        else:
            t = ((y - 580) / (height - 580)) ** 0.65
            a = int(130 + 115 * t)          # 130 → 245
        col.putpixel((0, y), min(245, a))

    gradient_mask = col.resize((width, height), Image.NEAREST)
    black = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    black.putalpha(gradient_mask)
    return black


def _shadow_text(
    draw: ImageDraw.Draw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    shadow: tuple = (0, 0, 0, 170),
    offset: int = 2,
) -> None:
    """Draw text with a subtle drop shadow."""
    x, y = xy
    draw.text((x + offset, y + offset), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def _clip(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[: max_chars - 1] + "\u2026"


# ── Main function ─────────────────────────────────────────────────────────────

def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    """Convert '#rrggbb' to (r, g, b, alpha)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r, g, b, alpha)


def generate_instagram_image(
    portada_local_path: str,
    data: PropertyData,
    output_path: str,
    logo_path: str | None = None,
    primary_color: str = "#1a6b8a",
    accent_color: str = "#f4a623",
) -> None:
    """
    Generates a 1080×1080 JPEG Instagram post image.
    - portada_local_path : filesystem path to the cover photo
    - data               : PropertyData with all listing info
    - output_path        : where to write the final JPEG
    """

    # ── 1. Crop & resize cover photo to square ────────────────────
    base = Image.open(portada_local_path).convert("RGBA")
    w, h = base.size
    side = min(w, h)
    base = base.crop(((w - side) // 2, (h - side) // 2,
                       (w + side) // 2, (h + side) // 2))
    base = base.resize((SIZE, SIZE), Image.LANCZOS)

    # ── 2. Composite gradient overlay ────────────────────────────
    base = Image.alpha_composite(base, _build_gradient(SIZE, SIZE))
    draw = ImageDraw.Draw(base)

    # ── 3. Color palette ─────────────────────────────────────────
    WHITE      = (255, 255, 255, 255)
    WHITE_DIM  = (210, 210, 210, 215)
    TEAL_BADGE = _hex_to_rgba(primary_color, 230)
    ACCENT     = _hex_to_rgba(accent_color, 255)
    SHADOW     = (0, 0, 0, 180)

    # ── 4. Fonts ─────────────────────────────────────────────────
    f_price  = _get_font(92,  bold=True)
    f_tipo   = _get_font(34,  bold=True)
    f_addr   = _get_font(29)
    f_pueblo = _get_font(26)
    f_stats  = _get_font(30,  bold=True)
    f_badge  = _get_font(28,  bold=True)
    f_agent  = _get_font(23)

    PAD = 52   # left/right margin

    # ── 5. Badge: EN VENTA / EN ALQUILER ─────────────────────────
    badge_label = "EN VENTA" if data.operacion == "Venta" else "EN ALQUILER"
    bpx, bpy = 16, 9
    bb = draw.textbbox((0, 0), badge_label, font=f_badge)
    bw = bb[2] - bb[0] + bpx * 2
    bh = bb[3] - bb[1] + bpy * 2
    bx, by_ = PAD, PAD
    draw.rounded_rectangle(
        [bx, by_, bx + bw, by_ + bh],
        radius=bh // 2,
        fill=TEAL_BADGE,
    )
    draw.text(
        (bx + bpx, by_ + bpy - bb[1]),
        badge_label,
        font=f_badge,
        fill=WHITE,
    )

    # ── 6. Agency logo (top-right) ───────────────────────────────
    resolved_logo = Path(logo_path) if logo_path else _LOGO_PATH
    if resolved_logo.exists():
        logo = Image.open(resolved_logo).convert("RGBA")
        logo_target_w = 260
        logo_h = int(logo.height * logo_target_w / logo.width)
        logo = logo.resize((logo_target_w, logo_h), Image.LANCZOS)
        # Apply semi-transparency: scale alpha channel to 80%
        r_ch, g_ch, b_ch, a_ch = logo.split()
        a_ch = a_ch.point(lambda p: int(p * 0.82))
        logo = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
        logo_x = SIZE - logo_target_w - PAD
        logo_y = PAD - 4
        base.paste(logo, (logo_x, logo_y), logo)

    # ── 7. Price ──────────────────────────────────────────────────
    price_str = f"${data.precio:,.0f}"
    _shadow_text(draw, (PAD, 665), price_str, f_price, WHITE, SHADOW, 3)

    # ── 8. Type + operation (accent color) ───────────────────────
    tipo_op = f"{data.tipo_propiedad} en {data.operacion}"
    draw.text((PAD, 770), tipo_op, font=f_tipo, fill=ACCENT)

    # ── 9. Address ────────────────────────────────────────────────
    addr = _clip(data.direccion, 46)
    _shadow_text(draw, (PAD, 818), addr, f_addr, WHITE_DIM, SHADOW)

    pueblo_line = f"{data.pueblo}, Puerto Rico"
    _shadow_text(draw, (PAD, 856), pueblo_line, f_pueblo,
                 (175, 215, 235, 220), SHADOW)

    # ── 10. Stats row ─────────────────────────────────────────────
    stats: list[str] = []
    if data.habitaciones:
        stats.append(f"{data.habitaciones} Habs")
    if data.banos is not None:
        v = int(data.banos) if data.banos == int(data.banos) else data.banos
        stats.append(f"{v} Ba\u00f1os")   # "Baños"
    if data.pies_cuadrados_construccion:
        stats.append(f"{data.pies_cuadrados_construccion:,} sq ft")
    if data.estacionamientos:
        stats.append(f"{data.estacionamientos} Estac.")

    if stats:
        stats_line = "  \u2022  ".join(stats)   # "  •  "
        _shadow_text(draw, (PAD, 910), stats_line, f_stats, WHITE, SHADOW)

    # ── 11. Divider line ──────────────────────────────────────────
    draw.line(
        [(PAD, 965), (SIZE - PAD, 965)],
        fill=(255, 255, 255, 55),
        width=1,
    )

    # ── 12. Agent footer ──────────────────────────────────────────
    agent_parts = [data.nombre_agente, data.licencia_agente]
    if data.telefono_agente:
        agent_parts.append(data.telefono_agente)
    agent_line = _clip("  \u00b7  ".join(agent_parts), 68)   # "  ·  "
    draw.text((PAD, 978), agent_line, font=f_agent,
              fill=(200, 200, 200, 195))

    # ── 13. Save as JPEG ──────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    base.convert("RGB").save(output_path, "JPEG", quality=93)


# ══════════════════════════════════════════════════════════════════
# Instagram Carousel helpers
# ══════════════════════════════════════════════════════════════════

def _make_contact_bg(primary_color: str) -> Image.Image:
    """Vertical bell-curve gradient for contact slide background."""
    r, g, b = _hex_to_rgba(primary_color)[:3]
    strip = Image.new("RGBA", (1, SIZE))
    for y in range(SIZE):
        t = 1.0 - abs(y - SIZE / 2.0) / (SIZE / 2.0)
        t = t ** 1.4
        strip.putpixel((0, y), (
            min(255, int(6  + r * 0.50 * t)),
            min(255, int(6  + g * 0.50 * t)),
            min(255, int(10 + b * 0.50 * t)),
            255,
        ))
    return strip.resize((SIZE, SIZE), Image.NEAREST)


def _generate_stats_slide(
    portada_local_path: str,
    data: PropertyData,
    output_path: str,
    slide_num: int,
    total_slides: int,
    logo_src: Path,
    primary_color: str,
    accent_color: str,
) -> None:
    """Slide 2: blurred cover photo bg + key stats grid."""
    BADGE_COLOR = _hex_to_rgba(primary_color, 220)
    ACCENT      = _hex_to_rgba(accent_color, 255)
    ACCENT_DIM  = _hex_to_rgba(accent_color, 170)
    CARD_BG     = _hex_to_rgba(primary_color, 70)
    WHITE       = (255, 255, 255, 255)
    WHITE_DIM   = (200, 200, 200, 200)
    SHADOW      = (0, 0, 0, 180)

    base = Image.open(portada_local_path).convert("RGBA")
    w, h = base.size
    side = min(w, h)
    base = base.crop(((w - side) // 2, (h - side) // 2,
                       (w + side) // 2, (h + side) // 2))
    base = base.resize((SIZE, SIZE), Image.LANCZOS)
    base = base.filter(ImageFilter.GaussianBlur(radius=28))
    dark = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 195))
    base = Image.alpha_composite(base, dark)
    draw = ImageDraw.Draw(base)

    PAD = 52
    f_price = _get_font(76, bold=True)
    f_badge = _get_font(26, bold=True)
    f_label = _get_font(24, bold=True)
    f_value = _get_font(48, bold=True)
    f_addr  = _get_font(26)
    f_num   = _get_font(22)

    # Slide counter top-right
    num_text = f"{slide_num}  /  {total_slides}"
    draw.text((SIZE - PAD - 95, PAD + 6), num_text, font=f_num, fill=(255, 255, 255, 110))

    # Operation badge
    badge_label = f"{data.tipo_propiedad.upper()}  \u00b7  {data.operacion.upper()}"
    bb = draw.textbbox((0, 0), badge_label, font=f_badge)
    bpx, bpy = 16, 9
    bw, bh = bb[2] - bb[0] + bpx * 2, bb[3] - bb[1] + bpy * 2
    draw.rounded_rectangle([PAD, PAD, PAD + bw, PAD + bh], radius=bh // 2, fill=BADGE_COLOR)
    draw.text((PAD + bpx, PAD + bpy - bb[1]), badge_label, font=f_badge, fill=WHITE)

    # Price
    price_str = f"${data.precio:,.0f}"
    _shadow_text(draw, (PAD, 130), price_str, f_price, WHITE, SHADOW, 3)

    # Address
    draw.text((PAD, 222), _clip(data.direccion, 46), font=f_addr, fill=WHITE_DIM)
    draw.text((PAD, 257), f"{data.pueblo}, Puerto Rico", font=f_addr, fill=(140, 190, 220, 200))

    # Divider
    draw.line([(PAD, 302), (SIZE - PAD, 302)], fill=ACCENT_DIM, width=2)

    # Stats items
    stats_items: list[tuple[str, str]] = []
    if data.habitaciones:
        stats_items.append(("CUARTOS", str(data.habitaciones)))
    if data.banos is not None:
        v = int(data.banos) if data.banos == int(data.banos) else data.banos
        stats_items.append(("BA\u00d1OS", str(v)))
    if data.pies_cuadrados_construccion:
        stats_items.append(("SQ FT", f"{data.pies_cuadrados_construccion:,}"))
    if data.estacionamientos:
        stats_items.append(("ESTAC.", str(data.estacionamientos)))
    if data.metros_o_cuerdas_terreno:
        stats_items.append(("TERRENO", _clip(data.metros_o_cuerdas_terreno, 12)))

    if stats_items:
        n = len(stats_items[:6])
        cols = 3 if n >= 3 else n
        CARD_W, CARD_H, GAP = 290, 150, 18
        total_grid_w = cols * CARD_W + (cols - 1) * GAP
        grid_x = (SIZE - total_grid_w) // 2
        grid_y = 328

        for i, (label, value) in enumerate(stats_items[:6]):
            col = i % cols
            row = i // cols
            cx = grid_x + col * (CARD_W + GAP)
            cy = grid_y + row * (CARD_H + GAP)
            draw.rounded_rectangle([cx, cy, cx + CARD_W, cy + CARD_H], radius=14, fill=CARD_BG)
            draw.rounded_rectangle([cx, cy, cx + CARD_W, cy + 4], radius=4, fill=ACCENT_DIM)
            vbb = draw.textbbox((0, 0), value, font=f_value)
            draw.text((cx + (CARD_W - (vbb[2] - vbb[0])) // 2, cy + 16), value, font=f_value, fill=WHITE)
            lbb = draw.textbbox((0, 0), label, font=f_label)
            draw.text((cx + (CARD_W - (lbb[2] - lbb[0])) // 2, cy + CARD_H - 38), label, font=f_label, fill=ACCENT)

    # Logo bottom-right
    if logo_src.exists():
        logo = Image.open(logo_src).convert("RGBA")
        lw = 180
        lh = int(logo.height * lw / logo.width)
        logo = logo.resize((lw, lh), Image.LANCZOS)
        r_ch, g_ch, b_ch, a_ch = logo.split()
        a_ch = a_ch.point(lambda p: int(p * 0.60))
        logo = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
        base.paste(logo, (SIZE - lw - PAD, SIZE - lh - PAD), logo)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    base.convert("RGB").save(output_path, "JPEG", quality=93)


def _generate_photo_slide(
    photo_path: str,
    data: PropertyData,
    output_path: str,
    slide_num: int,
    total_slides: int,
    primary_color: str,
    accent_color: str,
) -> None:
    """Middle slides: full-bleed extra photo with minimal overlay."""
    ACCENT    = _hex_to_rgba(accent_color, 255)
    WHITE     = (255, 255, 255, 255)
    WHITE_DIM = (200, 200, 200, 210)
    SHADOW    = (0, 0, 0, 180)

    base = Image.open(photo_path).convert("RGBA")
    w, h = base.size
    side = min(w, h)
    base = base.crop(((w - side) // 2, (h - side) // 2,
                       (w + side) // 2, (h + side) // 2))
    base = base.resize((SIZE, SIZE), Image.LANCZOS)
    base = Image.alpha_composite(base, _build_gradient(SIZE, SIZE))
    draw = ImageDraw.Draw(base)

    PAD    = 52
    f_tipo = _get_font(36, bold=True)
    f_addr = _get_font(28)
    f_num  = _get_font(22)

    # Slide counter top-right
    num_text = f"{slide_num}  /  {total_slides}"
    draw.text((SIZE - PAD - 95, PAD + 6), num_text, font=f_num, fill=(255, 255, 255, 130))

    # Bottom text
    draw.text((PAD, SIZE - 200), f"{data.tipo_propiedad} en {data.operacion}", font=f_tipo, fill=ACCENT)
    _shadow_text(draw, (PAD, SIZE - 155), _clip(data.direccion, 46), f_addr, WHITE, SHADOW)
    draw.text((PAD, SIZE - 118), f"{data.pueblo}, Puerto Rico", font=f_addr, fill=WHITE_DIM)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    base.convert("RGB").save(output_path, "JPEG", quality=93)


def _generate_contact_slide(
    data: PropertyData,
    output_path: str,
    logo_src: Path,
    primary_color: str,
    accent_color: str,
    agencia_tagline: str = "Bienes Ra\u00edces \u00b7 Puerto Rico",
) -> None:
    """Last slide: agent contact card with gradient background."""
    ACCENT = _hex_to_rgba(accent_color, 255)
    WHITE  = (255, 255, 255, 255)

    base = _make_contact_bg(primary_color)

    # Subtle diagonal stripes overlay
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    pd = ImageDraw.Draw(overlay)
    for i in range(-SIZE, SIZE * 2, 28):
        pd.line([(i, 0), (i + SIZE, SIZE)], fill=(255, 255, 255, 10), width=1)
    base = Image.alpha_composite(base, overlay)

    # Paste agency logo centered, capped at 180px tall
    logo_y = 100
    logo_h_actual = 0
    if logo_src.exists():
        logo = Image.open(logo_src).convert("RGBA")
        lw = 320
        lh = int(logo.height * lw / logo.width)
        if lh > 180:
            lw = int(logo.width * 180 / logo.height)
            lh = 180
        logo = logo.resize((lw, lh), Image.LANCZOS)
        base.paste(logo, ((SIZE - lw) // 2, logo_y), logo)
        logo_h_actual = lh

    draw = ImageDraw.Draw(base)

    f_name  = _get_font(62, bold=True)
    f_lic   = _get_font(34)
    f_phone = _get_font(52, bold=True)
    f_tag   = _get_font(26)

    # Accent line below logo
    accent_line_y = logo_y + logo_h_actual + 32
    lx = (SIZE - 80) // 2
    draw.rectangle([lx, accent_line_y, lx + 80, accent_line_y + 4],
                   fill=_hex_to_rgba(accent_color, 220))

    text_y = accent_line_y + 50

    # Agent name
    nbb = draw.textbbox((0, 0), data.nombre_agente, font=f_name)
    draw.text(((SIZE - (nbb[2] - nbb[0])) // 2, text_y), data.nombre_agente, font=f_name, fill=WHITE)
    text_y += nbb[3] - nbb[1] + 18

    # License
    lbb = draw.textbbox((0, 0), data.licencia_agente, font=f_lic)
    draw.text(((SIZE - (lbb[2] - lbb[0])) // 2, text_y), data.licencia_agente, font=f_lic, fill=ACCENT)
    text_y += lbb[3] - lbb[1] + 30

    # Phone
    if data.telefono_agente:
        pbb = draw.textbbox((0, 0), data.telefono_agente, font=f_phone)
        draw.text(((SIZE - (pbb[2] - pbb[0])) // 2, text_y), data.telefono_agente, font=f_phone, fill=WHITE)
        text_y += pbb[3] - pbb[1] + 44

    # Tagline
    tbb = draw.textbbox((0, 0), agencia_tagline, font=f_tag)
    draw.text(((SIZE - (tbb[2] - tbb[0])) // 2, text_y), agencia_tagline, font=f_tag,
              fill=(255, 255, 255, 100))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    base.convert("RGB").save(output_path, "JPEG", quality=93)


def generate_instagram_carousel(
    portada_local_path: str,
    extras_local_paths: list[str],
    data: PropertyData,
    output_dir: str,
    logo_path: str | None = None,
    primary_color: str = "#1a6b8a",
    accent_color: str = "#f4a623",
    agencia_tagline: str = "Bienes Ra\u00edces \u00b7 Puerto Rico",
) -> list[str]:
    """
    Generate a full Instagram carousel.
    Returns list of output file paths (absolute).

    Slide order:
      1. Hero (cover photo + price + badge)
      2. Stats/Details (if any numeric stats available)
      3–N. One slide per extra photo (up to 7)
      Last. Agent contact card
    """
    os.makedirs(output_dir, exist_ok=True)

    logo_src    = Path(logo_path) if logo_path else _LOGO_PATH
    valid_extras = [p for p in extras_local_paths if p and os.path.exists(p)]

    has_stats = any([
        data.habitaciones,
        data.banos is not None,
        data.pies_cuadrados_construccion,
        data.estacionamientos,
        data.metros_o_cuerdas_terreno,
    ])
    total = 1 + (1 if has_stats else 0) + len(valid_extras[:7]) + 1

    slides: list[str] = []
    slide_n = 1

    # Slide 1: Hero
    s1 = os.path.join(output_dir, "slide_01.jpg")
    generate_instagram_image(portada_local_path, data, s1, logo_path, primary_color, accent_color)
    slides.append(s1)
    slide_n += 1

    # Slide 2: Stats (optional)
    if has_stats:
        s2 = os.path.join(output_dir, f"slide_{slide_n:02d}.jpg")
        _generate_stats_slide(portada_local_path, data, s2, slide_n, total,
                               logo_src, primary_color, accent_color)
        slides.append(s2)
        slide_n += 1

    # Photo slides
    for extra_path in valid_extras[:7]:
        sp = os.path.join(output_dir, f"slide_{slide_n:02d}.jpg")
        _generate_photo_slide(extra_path, data, sp, slide_n, total, primary_color, accent_color)
        slides.append(sp)
        slide_n += 1

    # Last slide: Contact
    sc = os.path.join(output_dir, f"slide_{slide_n:02d}.jpg")
    _generate_contact_slide(data, sc, logo_src, primary_color, accent_color, agencia_tagline)
    slides.append(sc)

    return slides
