from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models.crm import EmailCampaign, EmailSend, Contact
from services.email_service import send_campaign

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Built-in HTML templates ─────────────────────────────────────────────────

TEMPLATES = [
    {
        "id": "bienvenida",
        "nombre": "Bienvenido a nuestros servicios",
        "asunto": "Bienvenido/a a ListaPro Kelitz",
        "html_body": """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
body{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0}
.container{max-width:600px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.1)}
.header{background:linear-gradient(135deg,#1a237e,#283593);padding:40px 32px;text-align:center;color:#fff}
.header h1{margin:0;font-size:26px}
.body{padding:32px;color:#333;line-height:1.7}
.cta{display:inline-block;margin:24px 0;padding:14px 32px;background:#1a237e;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold}
.footer{background:#f9f9f9;padding:20px 32px;text-align:center;font-size:12px;color:#999}
</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>Bienvenido/a a ListaPro Kelitz</h1>
  </div>
  <div class="body">
    <p>Hola <strong>{{nombre}}</strong>,</p>
    <p>Gracias por confiar en nuestros servicios inmobiliarios. Estamos aquí para ayudarte a encontrar la propiedad ideal o a vender tu propiedad al mejor precio.</p>
    <p>Si tienes alguna pregunta o necesitas orientación, no dudes en contactarnos. Nuestro equipo está disponible para ti.</p>
    <a class="cta" href="mailto:{{email_agente}}">Contáctanos ahora</a>
    <p>Con gusto,<br><strong>{{agente}}</strong><br>ListaPro Kelitz</p>
  </div>
  <div class="footer">Este mensaje fue enviado a {{email}}. Para dejar de recibir correos, responde con "Cancelar suscripción".</div>
</div>
</body>
</html>
""",
    },
    {
        "id": "nueva_propiedad",
        "nombre": "Nueva Propiedad Disponible",
        "asunto": "Nueva propiedad disponible para ti",
        "html_body": """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
body{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0}
.container{max-width:600px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.1)}
.header{background:linear-gradient(135deg,#1a237e,#283593);padding:40px 32px;text-align:center;color:#fff}
.header h1{margin:0;font-size:26px}
.body{padding:32px;color:#333;line-height:1.7}
.prop-card{background:#f0f4ff;border-radius:8px;padding:20px;margin:16px 0;border-left:4px solid #1a237e}
.cta{display:inline-block;margin:24px 0;padding:14px 32px;background:#1a237e;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold}
.footer{background:#f9f9f9;padding:20px 32px;text-align:center;font-size:12px;color:#999}
</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>Nueva Propiedad Disponible</h1>
  </div>
  <div class="body">
    <p>Hola <strong>{{nombre}}</strong>,</p>
    <p>Tenemos una propiedad que podría interesarte basado en tu perfil de búsqueda:</p>
    <div class="prop-card">
      <strong>{{tipo_propiedad}}</strong> en <strong>{{pueblo}}</strong><br>
      Precio: <strong>{{precio}}</strong><br>
      {{descripcion_corta}}
    </div>
    <p>¿Te gustaría conocer más detalles o agendar una visita?</p>
    <a class="cta" href="mailto:{{email_agente}}">Quiero más información</a>
    <p>Saludos,<br><strong>{{agente}}</strong><br>ListaPro Kelitz</p>
  </div>
  <div class="footer">Este mensaje fue enviado a {{email}}. Para dejar de recibir correos, responde con "Cancelar suscripción".</div>
</div>
</body>
</html>
""",
    },
    {
        "id": "seguimiento",
        "nombre": "Seguimiento de Cliente",
        "asunto": "Seguimos pensando en ti",
        "html_body": """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
body{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0}
.container{max-width:600px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.1)}
.header{background:linear-gradient(135deg,#1a237e,#283593);padding:40px 32px;text-align:center;color:#fff}
.header h1{margin:0;font-size:26px}
.body{padding:32px;color:#333;line-height:1.7}
.highlight{background:#fff8e1;border-radius:8px;padding:20px;margin:16px 0;border-left:4px solid #ffc107}
.cta{display:inline-block;margin:24px 0;padding:14px 32px;background:#1a237e;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold}
.footer{background:#f9f9f9;padding:20px 32px;text-align:center;font-size:12px;color:#999}
</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>¿Todavía buscando tu hogar ideal?</h1>
  </div>
  <div class="body">
    <p>Hola <strong>{{nombre}}</strong>,</p>
    <p>Hace un tiempo estuvimos en contacto y quería saber cómo va tu búsqueda. El mercado inmobiliario está activo y hay nuevas oportunidades disponibles.</p>
    <div class="highlight">
      <strong>Estamos aquí para ayudarte</strong><br>
      Nuestro equipo tiene acceso a las mejores propiedades en Puerto Rico. Cuéntanos qué necesitas y lo encontramos.
    </div>
    <p>¿Podemos agendar una llamada o reunión esta semana?</p>
    <a class="cta" href="mailto:{{email_agente}}">Hablar con un agente</a>
    <p>Con gusto,<br><strong>{{agente}}</strong><br>ListaPro Kelitz</p>
  </div>
  <div class="footer">Este mensaje fue enviado a {{email}}. Para dejar de recibir correos, responde con "Cancelar suscripción".</div>
</div>
</body>
</html>
""",
    },
]


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    nombre: str
    asunto: str
    html_body: str
    segmento: str = "todos"


class CampaignUpdate(BaseModel):
    nombre: Optional[str] = None
    asunto: Optional[str] = None
    html_body: Optional[str] = None
    segmento: Optional[str] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _serialize(c: EmailCampaign) -> dict:
    return {
        "id": c.id,
        "nombre": c.nombre,
        "asunto": c.asunto,
        "segmento": c.segmento,
        "status": c.status,
        "total_enviados": c.total_enviados,
        "total_fallidos": c.total_fallidos,
        "programado_para": c.programado_para,
        "enviado_en": c.enviado_en,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/templates")
def get_templates():
    return {"templates": [{"id": t["id"], "nombre": t["nombre"], "asunto": t["asunto"]} for t in TEMPLATES]}


@router.get("/templates/{template_id}")
def get_template(template_id: str):
    tpl = next((t for t in TEMPLATES if t["id"] == template_id), None)
    if not tpl:
        raise HTTPException(404, "Template no encontrado")
    return tpl


@router.get("")
def list_campaigns(db: Session = Depends(get_db)):
    items = db.query(EmailCampaign).order_by(EmailCampaign.created_at.desc()).all()
    return {"items": [_serialize(c) for c in items]}


@router.post("", status_code=201)
def create_campaign(data: CampaignCreate, db: Session = Depends(get_db)):
    campaign = EmailCampaign(**data.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return _serialize(campaign)


@router.get("/{campaign_id}")
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(EmailCampaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaña no encontrada")
    result = _serialize(campaign)
    result["html_body"] = campaign.html_body
    result["sends"] = [
        {
            "id": s.id,
            "email": s.email,
            "contact_id": s.contact_id,
            "status": s.status,
            "error_msg": s.error_msg,
            "sent_at": s.sent_at.isoformat() if s.sent_at else None,
        }
        for s in campaign.sends
    ]
    return result


@router.patch("/{campaign_id}")
def update_campaign(campaign_id: int, data: CampaignUpdate, db: Session = Depends(get_db)):
    campaign = db.get(EmailCampaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaña no encontrada")
    if campaign.status not in ("borrador", "error"):
        raise HTTPException(400, "Solo se pueden editar campañas en borrador")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)
    db.commit()
    db.refresh(campaign)
    return _serialize(campaign)


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(EmailCampaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaña no encontrada")
    if campaign.status == "enviando":
        raise HTTPException(400, "No se puede eliminar una campaña en progreso")
    db.delete(campaign)
    db.commit()


@router.post("/{campaign_id}/send")
async def trigger_send(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    campaign = db.get(EmailCampaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaña no encontrada")
    if campaign.status == "enviando":
        raise HTTPException(400, "La campaña ya está en proceso de envío")

    # Verificar que SMTP está configurado
    import config as cfg
    if not cfg.SMTP_USER or not cfg.SMTP_PASSWORD:
        raise HTTPException(400, "SMTP no configurado. Agrega SMTP_USER y SMTP_PASSWORD en el archivo .env")

    # Construir lista de destinatarios según segmento
    q = db.query(Contact).filter(Contact.email != "", Contact.email.isnot(None))
    if campaign.segmento != "todos":
        q = q.filter(Contact.tipo == campaign.segmento)
    contacts = q.all()

    if not contacts:
        raise HTTPException(400, "No hay contactos con email para este segmento")

    # Limpiar envíos anteriores si se está reintentando
    db.query(EmailSend).filter(EmailSend.campaign_id == campaign_id).delete()

    for c in contacts:
        db.add(EmailSend(
            campaign_id=campaign_id,
            contact_id=c.id,
            email=c.email,
            status="pendiente",
        ))
    db.commit()

    background_tasks.add_task(send_campaign, campaign_id)

    return {"ok": True, "total_recipients": len(contacts), "status": "enviando"}


@router.get("/{campaign_id}/status")
def campaign_status(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(EmailCampaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaña no encontrada")
    total = db.query(EmailSend).filter(EmailSend.campaign_id == campaign_id).count()
    enviados = db.query(EmailSend).filter(
        EmailSend.campaign_id == campaign_id, EmailSend.status == "enviado"
    ).count()
    fallidos = db.query(EmailSend).filter(
        EmailSend.campaign_id == campaign_id, EmailSend.status == "fallido"
    ).count()
    return {
        "status": campaign.status,
        "total": total,
        "enviados": enviados,
        "fallidos": fallidos,
        "enviado_en": campaign.enviado_en,
    }
