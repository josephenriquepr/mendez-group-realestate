"""
Autenticación y autorización con JWT.
Valida tokens y asegura que los usuarios solo ven sus datos.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID
import os
from jose import JWTError, jwt

from database import get_db
from models import User, Tenant

# Configuración
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production-min-32-chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

security = HTTPBearer()


def create_access_token(user_id: str, tenant_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crear un JWT token de acceso.
    El token contiene: user_id, tenant_id, rol, exp, iat
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: str, tenant_id: str) -> str:
    """
    Crear un JWT token de refresco (duración más larga).
    Solo se usa para obtener nuevos access tokens.
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validar token JWT y retornar el usuario actual.
    Usa HTTPBearer para obtener el token del header Authorization: Bearer <token>
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")

        if user_id is None or tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Obtener usuario de la BD
    user = db.query(User).filter(
        User.id == UUID(user_id),
        User.tenant_id == UUID(tenant_id)
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado",
        )

    return user


async def get_current_tenant(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Obtener el tenant actual del usuario.
    Útil para queries multi-tenant.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )

    if tenant.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant está {tenant.status}",
        )

    return tenant


def require_role(required_role: str):
    """
    Decorator para verificar que el usuario tiene un rol específico.
    Uso:
        @app.get("/admin")
        async def admin_only(current_user: User = Depends(require_role("admin"))):
            ...
    """
    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        valid_roles = {
            "owner": ["owner"],
            "admin": ["owner", "admin"],
            "agent": ["owner", "admin", "agent"],
            "viewer": ["owner", "admin", "agent", "viewer"],
        }

        if required_role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rol inválido",
            )

        if current_user.role not in valid_roles[required_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol {required_role}",
            )

        return current_user

    return check_role
