"""
Importar todos los modelos para que estén disponibles globalmente
"""
from models.base import Base, UUIDMixin, TimestampMixin, TenantMixin
from models.tenant import Tenant
from models.user import User
from models.property_models import Property, PropertyPhoto

# crm_models NO se importa aquí para evitar conflicto de tabla con models/crm.py (legacy).
# Cuando se migre a multi-tenant, se unificará en un solo modelo.

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "TenantMixin",
    "Tenant",
    "User",
    "Property",
    "PropertyPhoto",
]
