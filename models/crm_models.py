"""
Modelos CRM - Contact, Campaign, Task, UsageLog
"""
from sqlalchemy import Column, String, Text, Date, ForeignKey, Index, Integer, func
from sqlalchemy.orm import relationship
from models.base import Base, UUIDMixin, TimestampMixin, TenantMixin
from uuid import UUID
from datetime import datetime, date

class Contact(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """
    Un Contact es un lead o cliente asociado a un tenant.
    Puede estar vinculado a una Property.
    """
    __tablename__ = "contacts"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True)

    # Información de contacto
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True)

    # Estado del lead
    status = Column(String(50), default="new", index=True)  # new, interested, negotiating, won, lost, archived

    # Metadata
    contact_type = Column(String(50), nullable=True)  # buyer, seller, renter, investor
    notes = Column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="contacts")
    property = relationship("Property", back_populates="contacts")

    __table_args__ = (
        Index('idx_contact_tenant_status', 'tenant_id', 'status'),
        Index('idx_contact_email', 'email'),
    )

    def __repr__(self):
        return f"<Contact {self.name} ({self.status})>"


class Campaign(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """
    Una Campaign es una campaña de marketing/ventas.
    Agrupa múltiples acciones y properties.
    """
    __tablename__ = "campaigns"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Información
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Estado y timing
    status = Column(String(50), default="draft", index=True)  # draft, active, paused, completed, archived
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Metadata
    campaign_type = Column(String(50), nullable=True)  # email, social_media, flyers, open_house, etc
    budget = Column(Integer, nullable=True)  # En centavos para precisión

    # Relationships
    tenant = relationship("Tenant", back_populates="campaigns")

    __table_args__ = (
        Index('idx_campaign_tenant_status', 'tenant_id', 'status'),
    )

    def __repr__(self):
        return f"<Campaign {self.name}>"


class Task(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """
    Una Task es una tarea/acción en el CRM.
    Puede estar asignada a un usuario.
    """
    __tablename__ = "tasks"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Información
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Estado
    status = Column(String(50), default="pending", index=True)  # pending, in_progress, completed, cancelled
    priority = Column(String(20), default="normal")  # low, normal, high, urgent

    # Timing
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="tasks")
    assigned_user = relationship("User", back_populates="tasks", foreign_keys=[assigned_to])

    __table_args__ = (
        Index('idx_task_tenant_status', 'tenant_id', 'status'),
        Index('idx_task_assigned', 'assigned_to'),
        Index('idx_task_due_date', 'due_date'),
    )

    def __repr__(self):
        return f"<Task {self.title} ({self.status})>"


class UsageLog(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """
    UsageLog rastrea el uso de features por tenant.
    Esencial para billing y plan limits.
    """
    __tablename__ = "usage_logs"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Feature tracking
    feature = Column(String(100), nullable=False)  # 'generate_description', 'generate_instagram', etc
    count = Column(Integer, default=1)  # Número de usos

    # Fecha
    date = Column(Date, server_default=func.current_date(), nullable=False)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="usage_logs")

    __table_args__ = (
        Index('idx_usage_tenant_date', 'tenant_id', 'date'),
        Index('idx_usage_feature', 'feature'),
        Index('idx_usage_tenant_feature_date', 'tenant_id', 'feature', 'date', unique=True),
    )

    def __repr__(self):
        return f"<UsageLog {self.feature} ({self.date})>"
