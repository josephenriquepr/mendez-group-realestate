"""
Meta Graph API Webhook Handler
Captura DMs de Instagram Business y Facebook Messenger,
crea contactos automáticamente en el CRM.
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime

from database import SessionLocal
from models.crm import Contact, Activity, MetaConversation
import config

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Webhook verification (GET) ──────────────────────────────────────────────

@router.get("/meta")
async def meta_verify(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    """
    Meta llama este endpoint para verificar que la URL es válida.
    Debe responder con hub.challenge como texto plano.
    """
    if hub_mode == "subscribe" and hub_verify_token == config.META_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Token de verificación incorrecto")


# ─── Incoming message handler (POST) ─────────────────────────────────────────

@router.post("/meta")
async def meta_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Recibe eventos de mensajes de Instagram y Facebook Messenger.
    Crea contactos y registra actividades automáticamente.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ok"}  # Always return 200 to Meta

    for entry in payload.get("entry", []):
        platform = _detect_platform(entry)

        # ── Facebook Messenger path ──
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id")
            message = event.get("message", {})
            # Ignore echo messages (sent by the page itself)
            if message.get("is_echo"):
                continue
            text = message.get("text", "")
            if sender_id and text:
                await _handle_inbound_message(db, platform="facebook",
                                              sender_id=sender_id, text=text)

        # ── Instagram path ──
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue
            value = change.get("value", {})
            for msg in value.get("messages", []):
                sender_id = msg.get("from")
                msg_type = msg.get("type", "text")
                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "")
                else:
                    text = f"[{msg_type}]"
                if sender_id and text:
                    await _handle_inbound_message(db, platform="instagram",
                                                  sender_id=sender_id, text=text)

    return {"status": "ok"}


# ─── Config status ────────────────────────────────────────────────────────────

@router.get("/meta/config")
def meta_config():
    """Devuelve si los tokens están configurados (sin exponer los valores)."""
    return {
        "page_access_token_configured": bool(config.META_PAGE_ACCESS_TOKEN),
        "verify_token_configured": bool(config.META_VERIFY_TOKEN),
        "instagram_account_configured": bool(config.META_INSTAGRAM_ACCOUNT_ID),
        "verify_token": config.META_VERIFY_TOKEN,  # necesario para mostrarlo en la UI
    }


@router.get("/meta/conversations")
def list_conversations(db: Session = Depends(get_db)):
    """Lista todas las conversaciones Meta con info del contacto."""
    convs = db.query(MetaConversation).order_by(MetaConversation.created_at.desc()).all()
    return {
        "items": [
            {
                "id": c.id,
                "platform": c.platform,
                "sender_id": c.sender_id,
                "contact_id": c.contact_id,
                "contact_nombre": c.contact.nombre if c.contact else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in convs
        ]
    }


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _detect_platform(entry: dict) -> str:
    """Detecta si el entry es de Facebook o Instagram."""
    # Instagram entries tienen 'changes', Facebook tiene 'messaging'
    if entry.get("changes"):
        return "instagram"
    return "facebook"


async def _handle_inbound_message(db: Session, platform: str, sender_id: str, text: str):
    """
    Lógica central: busca o crea el contacto, registra el mensaje como actividad.
    """
    # 1. ¿Ya conocemos este sender?
    conv = db.query(MetaConversation).filter_by(sender_id=sender_id).first()

    if not conv:
        # 2. Nuevo sender — intentar obtener nombre del Graph API
        display_name = await _fetch_sender_name(platform, sender_id)

        # 3. Crear contacto en el CRM
        contact = Contact(
            nombre=display_name or f"{platform.capitalize()} User ...{sender_id[-6:]}",
            fuente=platform,
            meta_sender_id=sender_id,
            tipo="prospecto",
        )
        db.add(contact)
        db.flush()

        # 4. Registrar conversación
        conv = MetaConversation(
            platform=platform,
            sender_id=sender_id,
            contact_id=contact.id,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    contact_id = conv.contact_id

    # 5. Registrar el mensaje como actividad
    if contact_id:
        platform_label = "INSTAGRAM DM" if platform == "instagram" else "FACEBOOK DM"
        activity = Activity(
            contact_id=contact_id,
            tipo="mensaje_meta",
            descripcion=f"[{platform_label}] {text[:500]}",
            fecha=datetime.utcnow().strftime("%Y-%m-%d"),
        )
        db.add(activity)
        db.commit()


async def _fetch_sender_name(platform: str, sender_id: str) -> str:
    """
    Llama al Graph API para obtener el nombre del usuario.
    Retorna string vacío si falla (graceful degradation).
    Nota: Instagram Graph API no devuelve nombres por privacidad desde 2023.
    """
    if not config.META_PAGE_ACCESS_TOKEN:
        return ""
    try:
        import httpx
        url = f"https://graph.facebook.com/v19.0/{sender_id}"
        params = {"fields": "name", "access_token": config.META_PAGE_ACCESS_TOKEN}
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                return r.json().get("name", "")
    except Exception:
        pass
    return ""
