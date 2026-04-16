"""
Importar todos los modelos para que estén disponibles globalmente
"""
from models.base import Base, UUIDMixin, TimestampMixin, TenantMixin
from models.tenant import Tenant
from models.user import User
from models.property_models import Property, PropertyPhoto
from models.crm_models import Contact, Campaign, Task, UsageLog

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "TenantMixin",
    "Tenant",
    "User",
    "Property",
    "PropertyPhoto",
    "Contact",
    "Campaign",
    "Task",
    "UsageLog",
]
