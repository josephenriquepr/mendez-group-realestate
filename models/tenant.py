"""
Modelo Tenant - Representa cada cliente/agencia en la plataforma
"""
from sqlalchemy import Column, String, DateTime, Integer, func, Index, UUID
from sqlalchemy.orm import relationship
from models.base import Base, UUIDMixin, TimestampMixin
from datetime import datetime

class Tenant(Base, UUIDMixin, TimestampMixin):
    """
    Un Tenant es una empresa/agencia inmobiliaria.
    Todos los datos del tenant están aislados entre sí.
    """
    __tablename__ = "tenants"

    company_name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # ej: "kelitza-mendez"
    plan = Column(String(50), default="starter")  # starter, pro, premium, enterprise
    status = Column(String(50), default="active")  # active, trial, suspended, cancelled
    subscription_id = Column(String(255), unique=True, nullable=True)  # Stripe subscription ID
    stripe_customer_id = Column(String(255), unique=True, nullable=True)  # Stripe customer ID

    # Tracking de uso (para freemium/limits)
    monthly_usage = Column(Integer, default=0)  # Generaciones este mes
    max_monthly_usage = Column(Integer, default=100)  # Límite según plan

    # Información de contacto
    owner_email = Column(String(255), nullable=True)
    owner_phone = Column(String(20), nullable=True)

    # Relationships (solo modelos multi-tenant activos)
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="tenant", cascade="all, delete-orphan")

    # Índices para queries rápidas
    __table_args__ = (
        Index('idx_tenant_status', 'status'),
        Index('idx_tenant_plan', 'plan'),
    )

    def __repr__(self):
        return f"<Tenant {self.company_name} ({self.slug})>"
