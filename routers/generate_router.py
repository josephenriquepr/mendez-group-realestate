"""
Router para generar contenido con IA (descripciones e Instagram copies).
Refactorizado para multi-tenant.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import uuid
import os
from datetime import datetime, date

from database import get_db
from auth import get_current_user, get_current_tenant
from models import User, Tenant, Property, PropertyPhoto, UsageLog
from services.openai_service import generate_content as _generate_content_ai

router = APIRouter(prefix="/api", tags=["generate"])


# ============= SCHEMAS =============

class GeneratePropertyRequest(BaseModel):
    """Request para generar contenido de una propiedad"""
    address: str = Field(..., min_length=5, max_length=500)
    price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    sqft: Optional[int] = None
    property_type: Optional[str] = None  # house, condo, land, etc
    listing_type: Optional[str] = None  # for_sale, for_rent

    class Config:
        example = {
            "address": "123 Ocean View Avenue, San Juan, PR 00901",
            "price": 450000.00,
            "bedrooms": 3,
            "bathrooms": 2.5,
            "sqft": 2100,
            "property_type": "house",
            "listing_type": "for_sale"
        }


class PropertyContentResponse(BaseModel):
    """Response con contenido generado"""
    property_id: str
    address: str
    description: str
    instagram_copy: str
    hashtags: str
    usage_remaining: int
    message: str


# ============= HELPERS =============

def check_usage_limit(
    db: Session,
    tenant_id: uuid.UUID,
    tenant: Tenant
) -> tuple[bool, int]:
    """
    Verificar si el tenant puede hacer más generaciones este mes.
    Retorna (puede_generar, uso_restante)
    """
    today = date.today()
    month_start = date(today.year, today.month, 1)

    # Contar generaciones este mes
    usage_this_month = db.query(func.sum(UsageLog.count)).filter(
        UsageLog.tenant_id == tenant_id,
        UsageLog.date >= month_start,
        UsageLog.feature.in_(["generate_description", "generate_instagram"])
    ).scalar() or 0

    remaining = tenant.max_monthly_usage - usage_this_month
    can_generate = remaining > 0

    return can_generate, remaining


def save_uploaded_photo(
    file: UploadFile,
    tenant_id: uuid.UUID,
    property_id: uuid.UUID
) -> Optional[str]:
    """
    Guardar foto subida y retornar URL.
    En producción, esto iría a S3/Cloud Storage.
    """
    try:
        # En desarrollo: guardar localmente
        upload_dir = f"uploads/{str(tenant_id)}/{str(property_id)}"
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = f"{upload_dir}/{filename}"

        # Leer y guardar archivo
        content = file.file.read()
        with open(filepath, "wb") as f:
            f.write(content)

        # Retornar URL relativa (en prod sería URL de S3)
        return f"/uploads/{str(tenant_id)}/{str(property_id)}/{filename}"

    except Exception as e:
        print(f"Error guardando foto: {e}")
        return None


# ============= ENDPOINTS =============

@router.post("/generate", response_model=PropertyContentResponse)
async def generate_property_content(
    request: GeneratePropertyRequest,
    photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Generar descripción profesional y copy de Instagram para una propiedad.

    Incluye:
    - Descripción larga y profesional
    - Copy corto para Instagram
    - Hashtags relevantes

    El usuario debe estar autenticado. Cada generación consume "créditos" del plan.
    """

    # 1. Verificar límite de uso
    can_generate, remaining = check_usage_limit(db, current_tenant.id, current_tenant)

    if not can_generate:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Has alcanzado el límite de generaciones para tu plan ({current_tenant.max_monthly_usage}/mes)"
        )

    try:
        # 2. Guardar foto si existe
        photo_url = None
        if photo and photo.filename:
            photo_url = save_uploaded_photo(photo, current_tenant.id, uuid.uuid4())

        # 3. Crear propiedad en BD
        property_obj = Property(
            tenant_id=current_tenant.id,
            address=request.address,
            price=request.price,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            sqft=request.sqft,
            property_type=request.property_type,
            listing_type=request.listing_type,
            main_photo_url=photo_url,
        )
        db.add(property_obj)
        db.flush()  # Asignar ID

        # 4. Generar contenido con OpenAI
        print(f"🤖 Generando contenido para: {request.address}")

        description = await generate_description_with_ai(
            address=request.address,
            price=request.price,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            sqft=request.sqft,
            property_type=request.property_type,
        )

        instagram_copy = await generate_instagram_copy_with_ai(
            address=request.address,
            price=request.price,
            bedrooms=request.bedrooms,
            property_type=request.property_type,
        )

        # Extraer hashtags (en una fase más avanzada, podríamos generarlos también)
        hashtags = "#puertorigoproperty #realestatepr #costarica #inmobiliaria #property #luxuryrealestate"

        # 5. Guardar contenido
        property_obj.description = description
        property_obj.instagram_copy = instagram_copy
        property_obj.hashtags = hashtags
        db.commit()

        # 6. Registrar uso
        usage_log = UsageLog(
            tenant_id=current_tenant.id,
            feature="generate_description",
            count=1,
            date=date.today()
        )
        db.add(usage_log)

        usage_log2 = UsageLog(
            tenant_id=current_tenant.id,
            feature="generate_instagram",
            count=1,
            date=date.today()
        )
        db.add(usage_log2)
        db.commit()

        # 7. Recalcular uso restante
        _, remaining = check_usage_limit(db, current_tenant.id, current_tenant)

        return PropertyContentResponse(
            property_id=str(property_obj.id),
            address=property_obj.address,
            description=description,
            instagram_copy=instagram_copy,
            hashtags=hashtags,
            usage_remaining=remaining,
            message="✅ Contenido generado exitosamente"
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando contenido: {str(e)}"
        )


@router.get("/properties")
async def list_properties(
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
):
    """
    Listar propiedades del tenant actual.
    """
    query = db.query(Property).filter(Property.tenant_id == current_tenant.id)

    if status:
        query = query.filter(Property.status == status)

    total = query.count()
    properties = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "properties": [
            {
                "id": str(p.id),
                "address": p.address,
                "price": p.price,
                "bedrooms": p.bedrooms,
                "bathrooms": p.bathrooms,
                "status": p.status,
                "created_at": p.created_at,
            }
            for p in properties
        ]
    }


@router.get("/properties/{property_id}")
async def get_property(
    property_id: str,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    Obtener detalles de una propiedad específica.
    El usuario solo puede ver propiedades de su tenant.
    """
    try:
        prop_uuid = uuid.UUID(property_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")

    prop = db.query(Property).filter(
        Property.id == prop_uuid,
        Property.tenant_id == current_tenant.id
    ).first()

    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propiedad no encontrada"
        )

    return {
        "id": str(prop.id),
        "address": prop.address,
        "price": prop.price,
        "bedrooms": prop.bedrooms,
        "bathrooms": prop.bathrooms,
        "sqft": prop.sqft,
        "description": prop.description,
        "instagram_copy": prop.instagram_copy,
        "hashtags": prop.hashtags,
        "status": prop.status,
        "created_at": prop.created_at,
        "updated_at": prop.updated_at,
    }
