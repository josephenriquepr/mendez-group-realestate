import csv
import io
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models.crm import Contact, SavedProperty, Activity, Oportunidad

router = APIRouter()

STAGES = ["prospecto", "activo", "oferta", "contrato", "cerrado"]

# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class ContactCreate(BaseModel):
    nombre: str
    telefono: str = ""
    email: str = ""
    tipo: str = "prospecto"
    notas: str = ""
    follow_up_date: Optional[str] = None
    fuente: str = "manual"

class ContactUpdate(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    tipo: Optional[str] = None
    notas: Optional[str] = None
    follow_up_date: Optional[str] = None
    fuente: Optional[str] = None

class PropertySave(BaseModel):
    contact_id: Optional[int] = None
    tipo_propiedad: str = ""
    operacion: str = ""
    direccion: str = ""
    pueblo: str = ""
    precio: float = 0
    habitaciones: Optional[int] = None
    banos: Optional[float] = None
    pies_cuadrados: Optional[int] = None
    estacionamientos: Optional[int] = None
    metros_terreno: str = ""
    amenidades: list = []
    listing_description: str = ""
    instagram_copy: str = ""
    foto_portada_url: str = ""
    fotos_extras_urls: list = []
    pdf_url: str = ""
    instagram_image_url: str = ""
    carousel_urls: list = []
    nombre_agente: str = ""
    telefono_agente: str = ""
    stage: str = "prospecto"
    notas_crm: str = ""

class PropertyUpdate(BaseModel):
    contact_id: Optional[int] = None
    stage: Optional[str] = None
    notas_crm: Optional[str] = None

class ActivityCreate(BaseModel):
    contact_id: Optional[int] = None
    property_id: Optional[int] = None
    tipo: str = "nota"
    descripcion: str = ""
    fecha: str = ""


# ── Serializers ───────────────────────────────────────────────────────────────

def _contact_dict(c: Contact, include_relations: bool = False) -> dict:
    d = {
        "id": c.id,
        "nombre": c.nombre,
        "telefono": c.telefono,
        "email": c.email,
        "tipo": c.tipo,
        "notas": c.notas,
        "follow_up_date": c.follow_up_date,
        "fuente": c.fuente or "manual",
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "property_count": len(c.properties) if c.properties is not None else 0,
        "tags": [{"id": ct.tag.id, "nombre": ct.tag.nombre, "color": ct.tag.color}
                 for ct in c.contact_tags] if c.contact_tags else [],
        "task_count": len([t for t in c.tasks if not t.completada]) if c.tasks else 0,
    }
    if include_relations:
        d["properties"] = [_property_dict(p) for p in c.properties]
        d["activities"] = [_activity_dict(a) for a in
                           sorted(c.activities, key=lambda x: x.created_at or datetime.min, reverse=True)]
        d["oportunidades"] = [_opo_dict(o) for o in c.oportunidades]
        d["tasks"] = [_task_dict(t) for t in c.tasks]
    return d


def _opo_dict(o: Oportunidad) -> dict:
    return {
        "id": o.id,
        "nombre": o.nombre,
        "valor": o.valor,
        "etapa": o.etapa,
        "probabilidad": o.probabilidad,
        "fecha_cierre_esperada": o.fecha_cierre_esperada,
    }


def _task_dict(t) -> dict:
    return {
        "id": t.id,
        "titulo": t.titulo,
        "descripcion": t.descripcion,
        "fecha_vencimiento": t.fecha_vencimiento,
        "completada": t.completada,
    }


def _property_dict(p: SavedProperty, full: bool = False) -> dict:
    d = {
        "id": p.id,
        "contact_id": p.contact_id,
        "tipo_propiedad": p.tipo_propiedad,
        "operacion": p.operacion,
        "direccion": p.direccion,
        "pueblo": p.pueblo,
        "precio": p.precio,
        "habitaciones": p.habitaciones,
        "banos": p.banos,
        "pies_cuadrados": p.pies_cuadrados,
        "estacionamientos": p.estacionamientos,
        "metros_terreno": p.metros_terreno,
        "foto_portada_url": p.foto_portada_url,
        "pdf_url": p.pdf_url,
        "instagram_image_url": p.instagram_image_url,
        "carousel_urls": json.loads(p.carousel_urls or "[]"),
        "nombre_agente": p.nombre_agente,
        "telefono_agente": p.telefono_agente,
        "stage": p.stage,
        "notas_crm": p.notas_crm,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
    if full:
        d["listing_description"] = p.listing_description
        d["instagram_copy"] = p.instagram_copy
        d["fotos_extras_urls"] = json.loads(p.fotos_extras_urls or "[]")
        d["amenidades"] = json.loads(p.amenidades or "[]")
        d["contact"] = _contact_dict(p.contact) if p.contact else None
        d["activities"] = [_activity_dict(a) for a in p.activities]
    return d


def _activity_dict(a: Activity) -> dict:
    return {
        "id": a.id,
        "contact_id": a.contact_id,
        "property_id": a.property_id,
        "tipo": a.tipo,
        "descripcion": a.descripcion,
        "fecha": a.fecha,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "contact_nombre": a.contact.nombre if a.contact else None,
        "property_direccion": a.property.direccion if a.property else None,
    }


# ── Contacts ─────────────────────────────────────────────────────────────────

@router.get("/contacts")
def list_contacts(
    q: str = "",
    tipo: str = "",
    fuente: str = "",
    con_followup: Optional[bool] = None,
    tag_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Contact)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Contact.nombre.ilike(like) |
            Contact.telefono.ilike(like) |
            Contact.email.ilike(like)
        )
    if tipo:
        query = query.filter(Contact.tipo == tipo)
    if fuente:
        query = query.filter(Contact.fuente == fuente)
    if con_followup is True:
        query = query.filter(Contact.follow_up_date.isnot(None))
    if con_followup is False:
        query = query.filter(Contact.follow_up_date.is_(None))
    if tag_id:
        from models.crm import ContactTag
        query = query.join(ContactTag, Contact.id == ContactTag.contact_id).filter(
            ContactTag.tag_id == tag_id
        )
    return [_contact_dict(c) for c in query.order_by(Contact.created_at.desc()).all()]


@router.post("/contacts", status_code=201)
def create_contact(body: ContactCreate, db: Session = Depends(get_db)):
    c = Contact(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _contact_dict(c)


@router.get("/contacts/{contact_id}")
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    c = db.get(Contact, contact_id)
    if not c:
        raise HTTPException(404, "Contacto no encontrado")
    return _contact_dict(c, include_relations=True)


@router.patch("/contacts/{contact_id}")
def update_contact(contact_id: int, body: ContactUpdate, db: Session = Depends(get_db)):
    c = db.get(Contact, contact_id)
    if not c:
        raise HTTPException(404, "Contacto no encontrado")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(c, k, v)
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return _contact_dict(c)


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    c = db.get(Contact, contact_id)
    if not c:
        raise HTTPException(404, "Contacto no encontrado")
    db.delete(c)
    db.commit()
    return {"ok": True}


@router.post("/contacts/import-csv")
async def import_contacts_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Importa contactos desde un CSV.
    Columnas soportadas: nombre*, telefono, email, tipo, notas, follow_up_date
    La primera fila debe ser el encabezado.
    """
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    created = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        nombre = (row.get("nombre") or row.get("Nombre") or "").strip()
        if not nombre:
            skipped += 1
            continue
        try:
            c = Contact(
                nombre=nombre,
                telefono=(row.get("telefono") or row.get("Teléfono") or "").strip(),
                email=(row.get("email") or row.get("Email") or "").strip(),
                tipo=(row.get("tipo") or row.get("Tipo") or "prospecto").strip().lower(),
                notas=(row.get("notas") or row.get("Notas") or "").strip(),
                follow_up_date=(row.get("follow_up_date") or row.get("Follow-up") or "").strip() or None,
                fuente="manual",
            )
            db.add(c)
            created += 1
        except Exception as e:
            errors.append(f"Fila {i}: {str(e)}")

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


# ── Properties ────────────────────────────────────────────────────────────────

@router.get("/properties")
def list_properties(
    contact_id: Optional[int] = None,
    stage: Optional[str] = None,
    q: str = "",
    db: Session = Depends(get_db),
):
    query = db.query(SavedProperty)
    if contact_id:
        query = query.filter(SavedProperty.contact_id == contact_id)
    if stage:
        query = query.filter(SavedProperty.stage == stage)
    if q:
        like = f"%{q}%"
        query = query.filter(
            SavedProperty.direccion.ilike(like) |
            SavedProperty.pueblo.ilike(like) |
            SavedProperty.tipo_propiedad.ilike(like)
        )
    return [_property_dict(p) for p in query.order_by(SavedProperty.created_at.desc()).all()]


@router.post("/properties", status_code=201)
def save_property(body: PropertySave, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["amenidades"]       = json.dumps(data.get("amenidades", []))
    data["fotos_extras_urls"] = json.dumps(data.get("fotos_extras_urls", []))
    data["carousel_urls"]    = json.dumps(data.get("carousel_urls", []))
    p = SavedProperty(**data)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _property_dict(p, full=True)


@router.get("/properties/{property_id}")
def get_property(property_id: int, db: Session = Depends(get_db)):
    p = db.get(SavedProperty, property_id)
    if not p:
        raise HTTPException(404, "Propiedad no encontrada")
    return _property_dict(p, full=True)


@router.patch("/properties/{property_id}")
def update_property(property_id: int, body: PropertyUpdate, db: Session = Depends(get_db)):
    p = db.get(SavedProperty, property_id)
    if not p:
        raise HTTPException(404, "Propiedad no encontrada")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return _property_dict(p)


@router.delete("/properties/{property_id}")
def delete_property(property_id: int, db: Session = Depends(get_db)):
    p = db.get(SavedProperty, property_id)
    if not p:
        raise HTTPException(404, "Propiedad no encontrada")
    db.delete(p)
    db.commit()
    return {"ok": True}


# ── Activities ────────────────────────────────────────────────────────────────

@router.get("/activities")
def list_activities(
    contact_id: Optional[int] = None,
    property_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Activity)
    if contact_id:
        query = query.filter(Activity.contact_id == contact_id)
    if property_id:
        query = query.filter(Activity.property_id == property_id)
    return [_activity_dict(a) for a in query.order_by(Activity.created_at.desc()).limit(limit).all()]


@router.post("/activities", status_code=201)
def create_activity(body: ActivityCreate, db: Session = Depends(get_db)):
    data = body.model_dump()
    if not data.get("fecha"):
        data["fecha"] = datetime.utcnow().strftime("%Y-%m-%d")
    a = Activity(**data)
    db.add(a)
    db.commit()
    db.refresh(a)
    return _activity_dict(a)


@router.delete("/activities/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    a = db.get(Activity, activity_id)
    if not a:
        raise HTTPException(404, "Actividad no encontrada")
    db.delete(a)
    db.commit()
    return {"ok": True}


# ── Pipeline ──────────────────────────────────────────────────────────────────

@router.get("/pipeline")
def get_pipeline(db: Session = Depends(get_db)):
    props = db.query(SavedProperty).order_by(SavedProperty.created_at.desc()).all()
    result = {s: [] for s in STAGES}
    for p in props:
        key = p.stage if p.stage in STAGES else "prospecto"
        result[key].append(_property_dict(p))
    return result


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    today = datetime.utcnow().strftime("%Y-%m-%d")

    pipeline_counts = {
        s: db.query(SavedProperty).filter(SavedProperty.stage == s).count()
        for s in STAGES
    }

    closed = db.query(SavedProperty).filter(SavedProperty.stage == "cerrado").all()
    closed_value = sum(p.precio for p in closed)

    upcoming = (
        db.query(Contact)
        .filter(Contact.follow_up_date >= today)
        .order_by(Contact.follow_up_date)
        .limit(8)
        .all()
    )

    recent_acts = (
        db.query(Activity)
        .order_by(Activity.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_contacts":   db.query(Contact).count(),
        "total_properties": db.query(SavedProperty).count(),
        "pipeline_counts":  pipeline_counts,
        "closed_value":     closed_value,
        "upcoming_followups":   [_contact_dict(c) for c in upcoming],
        "recent_activities":    [_activity_dict(a) for a in recent_acts],
    }
