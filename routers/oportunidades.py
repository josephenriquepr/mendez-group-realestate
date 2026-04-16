from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from database import SessionLocal
from models.crm import Oportunidad, Contact

router = APIRouter()

ETAPAS = ["prospecto", "contacto", "propuesta", "negociacion", "cerrado_ganado", "cerrado_perdido"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class OportunidadCreate(BaseModel):
    nombre: str
    valor: float = 0
    etapa: str = "prospecto"
    fecha_cierre_esperada: Optional[str] = None
    probabilidad: int = 20
    contacto_id: Optional[int] = None
    notas: str = ""


class OportunidadUpdate(BaseModel):
    nombre: Optional[str] = None
    valor: Optional[float] = None
    etapa: Optional[str] = None
    fecha_cierre_esperada: Optional[str] = None
    probabilidad: Optional[int] = None
    contacto_id: Optional[int] = None
    notas: Optional[str] = None


def _serialize(op: Oportunidad) -> dict:
    return {
        "id": op.id,
        "nombre": op.nombre,
        "valor": op.valor,
        "etapa": op.etapa,
        "fecha_cierre_esperada": op.fecha_cierre_esperada,
        "probabilidad": op.probabilidad,
        "contacto_id": op.contacto_id,
        "contacto_nombre": op.contacto.nombre if op.contacto else None,
        "notas": op.notas,
        "created_at": op.created_at.isoformat() if op.created_at else None,
        "updated_at": op.updated_at.isoformat() if op.updated_at else None,
    }


@router.get("")
def list_oportunidades(
    etapa: Optional[str] = None,
    contacto_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Oportunidad)
    if etapa:
        q = q.filter(Oportunidad.etapa == etapa)
    if contacto_id:
        q = q.filter(Oportunidad.contacto_id == contacto_id)
    items = q.order_by(Oportunidad.created_at.desc()).all()
    return {"items": [_serialize(o) for o in items]}


@router.post("", status_code=201)
def create_oportunidad(data: OportunidadCreate, db: Session = Depends(get_db)):
    if data.contacto_id:
        if not db.get(Contact, data.contacto_id):
            raise HTTPException(404, "Contacto no encontrado")
    op = Oportunidad(**data.model_dump())
    db.add(op)
    db.commit()
    db.refresh(op)
    return _serialize(op)


@router.get("/pipeline")
def pipeline(db: Session = Depends(get_db)):
    result = {etapa: [] for etapa in ETAPAS}
    ops = db.query(Oportunidad).order_by(Oportunidad.created_at.desc()).all()
    for op in ops:
        if op.etapa in result:
            result[op.etapa].append(_serialize(op))
    totals = {
        etapa: sum(o["valor"] for o in items)
        for etapa, items in result.items()
    }
    return {"pipeline": result, "totals": totals}


@router.get("/{oportunidad_id}")
def get_oportunidad(oportunidad_id: int, db: Session = Depends(get_db)):
    op = db.get(Oportunidad, oportunidad_id)
    if not op:
        raise HTTPException(404, "Oportunidad no encontrada")
    return _serialize(op)


@router.patch("/{oportunidad_id}")
def update_oportunidad(
    oportunidad_id: int,
    data: OportunidadUpdate,
    db: Session = Depends(get_db),
):
    op = db.get(Oportunidad, oportunidad_id)
    if not op:
        raise HTTPException(404, "Oportunidad no encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(op, field, value)
    op.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(op)
    return _serialize(op)


@router.delete("/{oportunidad_id}", status_code=204)
def delete_oportunidad(oportunidad_id: int, db: Session = Depends(get_db)):
    op = db.get(Oportunidad, oportunidad_id)
    if not op:
        raise HTTPException(404, "Oportunidad no encontrada")
    db.delete(op)
    db.commit()


@router.post("/{oportunidad_id}/close-won")
def close_won(oportunidad_id: int, db: Session = Depends(get_db)):
    op = db.get(Oportunidad, oportunidad_id)
    if not op:
        raise HTTPException(404, "Oportunidad no encontrada")
    op.etapa = "cerrado_ganado"
    op.probabilidad = 100
    op.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(op)
    return _serialize(op)


@router.post("/{oportunidad_id}/close-lost")
def close_lost(oportunidad_id: int, db: Session = Depends(get_db)):
    op = db.get(Oportunidad, oportunidad_id)
    if not op:
        raise HTTPException(404, "Oportunidad no encontrada")
    op.etapa = "cerrado_perdido"
    op.probabilidad = 0
    op.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(op)
    return _serialize(op)
