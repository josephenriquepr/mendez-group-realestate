"""
Base models y mixins para arquitectura multi-tenant
"""
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, DateTime, UUID, func
from datetime import datetime
import uuid

Base = declarative_base()

class TimestampMixin:
    """Agregar created_at y updated_at automáticamente a todos los modelos"""
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class UUIDMixin:
    """Usar UUID como primary key en lugar de integers"""
    id = Column(UUID(), primary_key=True, default=uuid.uuid4)

class TenantMixin:
    """Agregar tenant_id a modelos para multi-tenant"""
    tenant_id = Column(UUID(), nullable=False)
