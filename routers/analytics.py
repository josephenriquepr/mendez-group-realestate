"""
Endpoints de analíticas y métricas para el CRM.
Todas las queries son de solo lectura sobre los datos existentes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import SessionLocal
from models.crm import Contact, SavedProperty, Oportunidad

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


PROPERTY_STAGES = ["prospecto", "activo", "oferta", "contrato", "cerrado"]
OPO_STAGES = ["prospecto", "contacto", "propuesta", "negociacion", "cerrado_ganado", "cerrado_perdido"]


@router.get("/pipeline-monthly")
def pipeline_monthly(db: Session = Depends(get_db)):
    """
    Conteo de propiedades creadas por etapa y mes (últimos 6 meses).
    """
    rows = (
        db.query(
            func.strftime("%Y-%m", SavedProperty.created_at).label("month"),
            SavedProperty.stage,
            func.count().label("count"),
        )
        .group_by("month", SavedProperty.stage)
        .order_by("month")
        .all()
    )
    return {
        "data": [{"month": r.month, "stage": r.stage, "count": r.count} for r in rows]
    }


@router.get("/revenue-monthly")
def revenue_monthly(db: Session = Depends(get_db)):
    """
    Suma de precios de propiedades cerradas por mes.
    """
    rows = (
        db.query(
            func.strftime("%Y-%m", SavedProperty.created_at).label("month"),
            func.sum(SavedProperty.precio).label("total"),
            func.count().label("count"),
        )
        .filter(SavedProperty.stage == "cerrado")
        .group_by("month")
        .order_by("month")
        .all()
    )
    return {
        "data": [{"month": r.month, "total": r.total or 0, "count": r.count} for r in rows]
    }


@router.get("/contact-sources")
def contact_sources(db: Session = Depends(get_db)):
    """
    Conteo de contactos agrupados por fuente (manual, instagram, facebook, email).
    """
    rows = (
        db.query(Contact.fuente, func.count().label("count"))
        .group_by(Contact.fuente)
        .all()
    )
    return {
        "data": [{"fuente": r.fuente or "manual", "count": r.count} for r in rows]
    }


@router.get("/conversion-rates")
def conversion_rates(db: Session = Depends(get_db)):
    """
    Distribución porcentual de propiedades por etapa del pipeline.
    """
    total = db.query(SavedProperty).count()
    rows = (
        db.query(SavedProperty.stage, func.count().label("count"))
        .group_by(SavedProperty.stage)
        .all()
    )
    data = []
    for r in rows:
        pct = round((r.count / total * 100), 1) if total > 0 else 0
        data.append({"stage": r.stage, "count": r.count, "pct": pct})
    return {"total": total, "data": data}


@router.get("/oportunidades-summary")
def oportunidades_summary(db: Session = Depends(get_db)):
    """
    Valor total del pipeline de oportunidades por etapa.
    """
    rows = (
        db.query(
            Oportunidad.etapa,
            func.count().label("count"),
            func.sum(Oportunidad.valor).label("total_valor"),
        )
        .group_by(Oportunidad.etapa)
        .all()
    )
    total_pipeline = sum(
        (r.total_valor or 0)
        for r in rows
        if r.etapa not in ("cerrado_perdido",)
    )
    return {
        "total_pipeline": total_pipeline,
        "data": [
            {
                "etapa": r.etapa,
                "count": r.count,
                "total_valor": r.total_valor or 0,
            }
            for r in rows
        ],
    }


@router.get("/summary")
def full_summary(db: Session = Depends(get_db)):
    """Dashboard rápido con todos los KPIs en una sola llamada."""
    total_contacts = db.query(Contact).count()
    total_properties = db.query(SavedProperty).count()
    total_oportunidades = db.query(Oportunidad).count()

    closed_value = (
        db.query(func.sum(SavedProperty.precio))
        .filter(SavedProperty.stage == "cerrado")
        .scalar()
        or 0
    )

    pipeline_opo_value = (
        db.query(func.sum(Oportunidad.valor))
        .filter(Oportunidad.etapa.notin_(["cerrado_ganado", "cerrado_perdido"]))
        .scalar()
        or 0
    )

    won_value = (
        db.query(func.sum(Oportunidad.valor))
        .filter(Oportunidad.etapa == "cerrado_ganado")
        .scalar()
        or 0
    )

    sources = (
        db.query(Contact.fuente, func.count().label("count"))
        .group_by(Contact.fuente)
        .all()
    )

    return {
        "total_contacts": total_contacts,
        "total_properties": total_properties,
        "total_oportunidades": total_oportunidades,
        "closed_value": closed_value,
        "pipeline_opo_value": pipeline_opo_value,
        "won_value": won_value,
        "contact_sources": [{"fuente": r.fuente or "manual", "count": r.count} for r in sources],
    }
