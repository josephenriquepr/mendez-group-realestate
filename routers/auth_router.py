"""
Router para autenticación: registro, login, refresh token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from database import get_db
from auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
)
from models import User, Tenant

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============= SCHEMAS =============

class RegisterRequest(BaseModel):
    """Schema para registrar un nuevo usuario/tenant"""
    company_name: str = Field(..., min_length=2, max_length=255)
    company_slug: str = Field(..., min_length=3, max_length=100, pattern="^[a-z0-9-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)

    class Config:
        example = {
            "company_name": "Kelitza Méndez Bienes Raíces",
            "company_slug": "kelitza-mendez",
            "email": "kelitza@mendezgroup.com",
            "password": "SecurePassword123!",
            "full_name": "Kelitza Méndez"
        }


class LoginRequest(BaseModel):
    """Schema para login"""
    email: str
    password: str

    class Config:
        example = {
            "email": "kelitza@mendezgroup.com",
            "password": "SecurePassword123!"
        }


class TokenResponse(BaseModel):
    """Schema para response de token"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """Schema para usuario en response"""
    id: str
    email: str
    full_name: str
    role: str

    class Config:
        from_attributes = True


# ============= ENDPOINTS =============

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Registrar una nueva empresa/tenant y crear el usuario owner.

    - **company_name**: Nombre de la empresa (ej: "Kelitza Méndez Bienes Raíces")
    - **company_slug**: URL-friendly slug (ej: "kelitza-mendez")
    - **email**: Email del owner
    - **password**: Mínimo 8 caracteres
    - **full_name**: Nombre completo del owner
    """

    # Validar que el slug sea único
    existing_tenant = db.query(Tenant).filter(Tenant.slug == request.company_slug).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El slug '{request.company_slug}' ya está en uso"
        )

    # Validar que el email sea único
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ya registrado"
        )

    try:
        # 1. Crear tenant
        tenant = Tenant(
            company_name=request.company_name,
            slug=request.company_slug,
            plan="starter",  # Plan inicial gratis/trial
            status="active",
            owner_email=request.email,
        )
        db.add(tenant)
        db.flush()  # Asignar ID al tenant

        # 2. Crear usuario owner
        user = User(
            tenant_id=tenant.id,
            email=request.email,
            full_name=request.full_name,
            role="owner",
            is_active=True,
        )
        user.set_password(request.password)  # Hash password
        db.add(user)
        db.commit()

        # 3. Generar tokens
        access_token = create_access_token(str(user.id), str(tenant.id))
        refresh_token = create_refresh_token(str(user.id), str(tenant.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "tenant_id": str(tenant.id),
                "company_name": tenant.company_name,
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en registro: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login con email y password.
    Retorna access_token y refresh_token.
    """

    # Buscar usuario
    user = db.query(User).filter(User.email == request.email).first()

    if not user or not user.verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password incorrecto"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado"
        )

    # Validar que el tenant esté activo
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or tenant.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant no está activo"
        )

    try:
        # Actualizar last_login
        user.last_login = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1
        db.commit()

        # Generar tokens
        access_token = create_access_token(str(user.id), str(tenant.id))
        refresh_token = create_refresh_token(str(user.id), str(tenant.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "tenant_id": str(tenant.id),
                "company_name": tenant.company_name,
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en login: {str(e)}"
        )


@router.post("/refresh")
async def refresh_token(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Usar refresh_token para obtener un nuevo access_token.
    Body: {"refresh_token": "..."}
    """
    # TODO: Implementar en Fase 2
    pass


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener información del usuario actual.
    Requiere autenticación.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "last_login": current_user.last_login,
        },
        "tenant": {
            "id": str(tenant.id),
            "company_name": tenant.company_name,
            "slug": tenant.slug,
            "plan": tenant.plan,
            "status": tenant.status,
        } if tenant else None
    }
