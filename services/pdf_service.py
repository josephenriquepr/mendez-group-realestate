import os
import time

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Image as RLImage, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from models.property import PropertyData
import config

# ── Register Unicode-capable fonts (macOS system fonts) ───────────
_FONT_REGISTERED = False

def _register_fonts():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    candidates = [
        # macOS — Arial Unicode covers all Spanish characters
        ("/Library/Fonts/Arial Unicode.ttf", "UniRegular"),
        ("/System/Library/Fonts/Helvetica.ttc", "UniRegular"),
        ("/Library/Fonts/Arial.ttf", "UniRegular"),
        # Linux
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "UniRegular"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "UniRegular"),
    ]
    bold_candidates = [
        # macOS — ArialHB = Arial Helvetica Bold variant
        ("/System/Library/Fonts/ArialHB.ttc", "UniBold"),
        ("/Library/Fonts/Arial Bold.ttf", "UniBold"),
        # Linux
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "UniBold"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "UniBold"),
    ]
    for path, name in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                break
            except Exception:
                continue
    for path, name in bold_candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                break
            except Exception:
                continue
    _FONT_REGISTERED = True

# Fall back to Helvetica if TTF registration fails
def _font(bold=False):
    try:
        name = "UniBold" if bold else "UniRegular"
        pdfmetrics.getFont(name)
        return name
    except Exception:
        return "Helvetica-Bold" if bold else "Helvetica"


# ── Colors ────────────────────────────────────────────────────────
C_PRIMARY    = colors.HexColor("#1a6b8a")
C_PRIMARY_DK = colors.HexColor("#135470")
C_PRIMARY_LT = colors.HexColor("#e8f4f8")
C_ACCENT     = colors.HexColor("#f4a623")
C_TEXT       = colors.HexColor("#1c2b35")
C_MUTED      = colors.HexColor("#6b7f8a")
C_BORDER     = colors.HexColor("#dce3e8")
C_DETAIL_BG  = colors.HexColor("#f0f7fa")
C_WHITE      = colors.white


def _esc(text: str) -> str:
    """Escape XML special characters for Paragraph markup."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _url_to_path(url: str) -> str:
    """'/uploads/x.jpg' -> 'uploads/x.jpg' resolved against project root."""
    rel = url.lstrip("/")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, rel)


def _fit_image(filepath: str, max_w: float, max_h: float) -> tuple[float, float]:
    """Return (w, h) preserving aspect ratio within max_w x max_h."""
    try:
        ir = ImageReader(filepath)
        iw, ih = ir.getSize()
        scale = min(max_w / iw, max_h / ih)
        return iw * scale, ih * scale
    except Exception:
        return max_w, max_h * 0.6


def _make_styles() -> dict:
    _register_fonts()
    R = _font(False)
    B = _font(True)
    return {
        "hdr_title": ParagraphStyle("hdr_title", fontName=B, fontSize=18,
                                    textColor=C_WHITE, leading=22),
        "hdr_sub": ParagraphStyle("hdr_sub", fontName=R, fontSize=11,
                                  textColor=C_WHITE, leading=14, alignment=TA_CENTER),
        "hdr_addr": ParagraphStyle("hdr_addr", fontName=R, fontSize=9,
                                   textColor=colors.HexColor("#b8d8e5"), leading=11,
                                   alignment=TA_CENTER),
        "hdr_badge": ParagraphStyle("hdr_badge", fontName=B, fontSize=12,
                                    textColor=C_ACCENT, leading=15, alignment=TA_RIGHT),
        "section": ParagraphStyle("section", fontName=B, fontSize=9,
                                  textColor=C_PRIMARY, spaceBefore=14, spaceAfter=5,
                                  leading=11, wordWrap="LTR"),
        "body": ParagraphStyle("body", fontName=R, fontSize=10, textColor=C_TEXT,
                               leading=15, alignment=TA_JUSTIFY),
        "det_label": ParagraphStyle("det_label", fontName=R, fontSize=7.5,
                                    textColor=C_MUTED, alignment=TA_CENTER, leading=9),
        "det_value": ParagraphStyle("det_value", fontName=B, fontSize=13,
                                    textColor=C_PRIMARY_DK, alignment=TA_CENTER, leading=16),
        "det_price": ParagraphStyle("det_price", fontName=B, fontSize=15,
                                    textColor=C_ACCENT, alignment=TA_CENTER, leading=18),
        "amenidad": ParagraphStyle("amenidad", fontName=R, fontSize=10,
                                   textColor=C_TEXT, leading=15),
        "agent_name": ParagraphStyle("agent_name", fontName=B, fontSize=12,
                                     textColor=C_WHITE, leading=15),
        "agent_lic": ParagraphStyle("agent_lic", fontName=R, fontSize=10,
                                    textColor=colors.HexColor("#b8d8e5"), leading=13),
        "agent_contact": ParagraphStyle("agent_contact", fontName=R, fontSize=10,
                                        textColor=C_WHITE, leading=14, alignment=TA_RIGHT),
    }


def generate_pdf(
    data: PropertyData,
    listing_description: str,
    portada_url: str,
    extras_urls: list,
    primary_color: str = "#1a6b8a",
    accent_color: str = "#f4a623",
    nombre_agencia: str = "ListaPro",
) -> str:
    """Generate a property listing PDF. Returns the /uploads/ URL of the generated file."""

    timestamp = int(time.time() * 1000)
    filename = f"{timestamp}_listado.pdf"
    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        config.UPLOAD_DIR,
        filename,
    )

    # Dynamic brand colors
    c_primary    = colors.HexColor(primary_color)
    c_primary_dk = colors.HexColor(primary_color)  # use same for dk; darken if needed
    c_accent     = colors.HexColor(accent_color)

    PAGE_W, _ = LETTER
    MARGIN = 0.55 * inch
    CW = PAGE_W - 2 * MARGIN  # content width

    doc = SimpleDocTemplate(
        out_path, pagesize=LETTER,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )

    S = _make_styles()
    story = []

    # ── 1. HEADER ─────────────────────────────────────────────────
    tipo_op = f"{_esc(data.tipo_propiedad)}  \u00b7  {_esc(data.pueblo)}, Puerto Rico"
    hdr = Table(
        [[
            Paragraph(_esc(nombre_agencia), S["hdr_title"]),
            [Paragraph(tipo_op, S["hdr_sub"]),
             Paragraph(_esc(data.direccion), S["hdr_addr"])],
            Paragraph(_esc(data.operacion).upper(), S["hdr_badge"]),
        ]],
        colWidths=[CW * 0.22, CW * 0.56, CW * 0.22],
    )
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), c_primary_dk),
        ("ALIGN",         (0, 0), (0,  0),  "LEFT"),
        ("ALIGN",         (1, 0), (1,  0),  "CENTER"),
        ("ALIGN",         (2, 0), (2,  0),  "RIGHT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 0.18 * inch))

    # ── 2. COVER PHOTO ────────────────────────────────────────────
    portada_fs = _url_to_path(portada_url)
    if os.path.exists(portada_fs):
        w, h = _fit_image(portada_fs, CW, 3.6 * inch)
        img = RLImage(portada_fs, width=w, height=h)
        img.hAlign = "CENTER"
        story.append(img)
        story.append(Spacer(1, 0.12 * inch))

    # ── 3. EXTRA PHOTOS ───────────────────────────────────────────
    valid_extras = [_url_to_path(u) for u in extras_urls
                    if os.path.exists(_url_to_path(u))]
    if valid_extras:
        show = valid_extras[:4]
        n = len(show)
        GAP = 0.07 * inch
        tw = (CW - GAP * (n - 1)) / n
        th = tw * 0.67

        cells = []
        for ep in show:
            ew, eh = _fit_image(ep, tw, th)
            cells.append(RLImage(ep, width=ew, height=eh))

        xtbl = Table([cells], colWidths=[tw] * n)
        xtbl.setStyle(TableStyle([
            ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (-1, -1), GAP / 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), GAP / 2),
            ("TOPPADDING",   (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
        ]))
        story.append(xtbl)
        story.append(Spacer(1, 0.18 * inch))

    # ── 4. KEY DETAILS ────────────────────────────────────────────
    labels, values = [], []

    labels.append(Paragraph("PRECIO", S["det_label"]))
    values.append(Paragraph(f"${data.precio:,.0f}", S["det_price"]))

    if data.habitaciones is not None:
        labels.append(Paragraph("CUARTOS", S["det_label"]))
        values.append(Paragraph(str(data.habitaciones), S["det_value"]))

    if data.banos is not None:
        ban_str = str(int(data.banos)) if data.banos == int(data.banos) else str(data.banos)
        labels.append(Paragraph("BA\u00d1OS", S["det_label"]))
        values.append(Paragraph(ban_str, S["det_value"]))

    if data.pies_cuadrados_construccion:
        labels.append(Paragraph("SQ FT", S["det_label"]))
        values.append(Paragraph(f"{data.pies_cuadrados_construccion:,}", S["det_value"]))

    if data.metros_o_cuerdas_terreno:
        labels.append(Paragraph("TERRENO", S["det_label"]))
        values.append(Paragraph(_esc(data.metros_o_cuerdas_terreno), S["det_value"]))

    if data.estacionamientos is not None:
        labels.append(Paragraph("ESTAC.", S["det_label"]))
        values.append(Paragraph(str(data.estacionamientos), S["det_value"]))

    if values:
        n = len(values)
        col_w = CW / n
        dtbl = Table([values, labels], colWidths=[col_w] * n)
        dtbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_DETAIL_BG),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, 0),  10),
            ("BOTTOMPADDING", (0, 0), (-1, 0),  4),
            ("TOPPADDING",    (0, 1), (-1, 1),  2),
            ("BOTTOMPADDING", (0, 1), (-1, 1),  10),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("LINEABOVE",     (0, 0), (-1, 0),  2,   c_primary),
        ]))
        story.append(dtbl)

    # ── 5. DESCRIPTION ────────────────────────────────────────────
    story.append(Paragraph("DESCRIPCI\u00d3N PROFESIONAL", S["section"]))
    story.append(HRFlowable(width=CW, thickness=1.5, color=C_PRIMARY, spaceAfter=6))
    for line in listing_description.split("\n"):
        line = line.strip()
        if line:
            story.append(Paragraph(_esc(line), S["body"]))
            story.append(Spacer(1, 3))

    # ── 6. AMENIDADES ─────────────────────────────────────────────
    if data.amenidades:
        story.append(Paragraph("AMENIDADES", S["section"]))
        story.append(HRFlowable(width=CW, thickness=1.5, color=C_PRIMARY, spaceAfter=6))

        items = data.amenidades
        rows = []
        for i in range(0, len(items), 2):
            left = Paragraph(f"- {_esc(items[i])}", S["amenidad"])
            right = (Paragraph(f"- {_esc(items[i + 1])}", S["amenidad"])
                     if i + 1 < len(items) else Paragraph("", S["amenidad"]))
            rows.append([left, right])

        atbl = Table(rows, colWidths=[CW * 0.5, CW * 0.5])
        atbl.setStyle(TableStyle([
            ("ALIGN",        (0, 0), (-1, -1), "LEFT"),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",   (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(atbl)

    # ── 7. AGENT CARD ─────────────────────────────────────────────
    story.append(Spacer(1, 0.22 * inch))

    contact_lines = []
    if data.telefono_agente:
        contact_lines.append(f"Tel: {_esc(data.telefono_agente)}")
    if data.email_agente:
        contact_lines.append(_esc(data.email_agente))

    agent_card = Table(
        [[
            [Paragraph(_esc(data.nombre_agente), S["agent_name"]),
             Paragraph(_esc(data.licencia_agente), S["agent_lic"])],
            Paragraph("<br/>".join(contact_lines), S["agent_contact"]),
        ]],
        colWidths=[CW * 0.58, CW * 0.42],
    )
    agent_card.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), c_primary),
        ("ALIGN",         (0, 0), (0,  0),  "LEFT"),
        ("ALIGN",         (1, 0), (1,  0),  "RIGHT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(KeepTogether(agent_card))

    doc.build(story)
    return f"/uploads/{filename}"
