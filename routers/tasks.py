from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from database import SessionLocal
from models.crm import Task, Contact

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TaskCreate(BaseModel):
    contact_id: int
    titulo: str
    descripcion: str = ""
    fecha_vencimiento: Optional[str] = None


class TaskUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    completada: Optional[bool] = None


def _serialize(t: Task) -> dict:
    return {
        "id": t.id,
        "contact_id": t.contact_id,
        "titulo": t.titulo,
        "descripcion": t.descripcion,
        "fecha_vencimiento": t.fecha_vencimiento,
        "completada": t.completada,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.get("")
def list_tasks(
    contact_id: Optional[int] = None,
    completada: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Task)
    if contact_id:
        q = q.filter(Task.contact_id == contact_id)
    if completada is not None:
        q = q.filter(Task.completada == completada)
    tasks = q.order_by(Task.completada, Task.fecha_vencimiento).all()
    return {"items": [_serialize(t) for t in tasks]}


@router.post("", status_code=201)
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    if not db.get(Contact, data.contact_id):
        raise HTTPException(404, "Contacto no encontrado")
    task = Task(**data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return _serialize(task)


@router.patch("/{task_id}")
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Tarea no encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return _serialize(task)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Tarea no encontrada")
    db.delete(task)
    db.commit()
