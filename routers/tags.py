from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models.crm import Tag, ContactTag, Contact

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


TAG_COLORS = ["#1a6b8a", "#2e7d32", "#c13584", "#f57f17", "#ad1457",
              "#1565c0", "#6a1b9a", "#00838f", "#4e342e", "#37474f"]


class TagCreate(BaseModel):
    nombre: str
    color: str = "#1a6b8a"


def _serialize(t: Tag) -> dict:
    return {"id": t.id, "nombre": t.nombre, "color": t.color}


@router.get("")
def list_tags(db: Session = Depends(get_db)):
    tags = db.query(Tag).order_by(Tag.nombre).all()
    return {"items": [_serialize(t) for t in tags], "colors": TAG_COLORS}


@router.post("", status_code=201)
def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    existing = db.query(Tag).filter(Tag.nombre == data.nombre.strip()).first()
    if existing:
        return _serialize(existing)
    tag = Tag(nombre=data.nombre.strip(), color=data.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _serialize(tag)


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(404, "Tag no encontrada")
    db.delete(tag)
    db.commit()


# ── Assign / remove tag from contact ─────────────────────────────────────────

@router.post("/contacts/{contact_id}/{tag_id}", status_code=201)
def assign_tag(contact_id: int, tag_id: int, db: Session = Depends(get_db)):
    if not db.get(Contact, contact_id):
        raise HTTPException(404, "Contacto no encontrado")
    if not db.get(Tag, tag_id):
        raise HTTPException(404, "Tag no encontrada")
    existing = db.query(ContactTag).filter_by(
        contact_id=contact_id, tag_id=tag_id
    ).first()
    if not existing:
        db.add(ContactTag(contact_id=contact_id, tag_id=tag_id))
        db.commit()
    return {"ok": True}


@router.delete("/contacts/{contact_id}/{tag_id}", status_code=204)
def remove_tag(contact_id: int, tag_id: int, db: Session = Depends(get_db)):
    ct = db.query(ContactTag).filter_by(
        contact_id=contact_id, tag_id=tag_id
    ).first()
    if ct:
        db.delete(ct)
        db.commit()
