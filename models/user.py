"""
Modelo User - Usuarios dentro de cada Tenant
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from models.base import Base, UUIDMixin, TimestampMixin
from passlib.context import CryptContext
from uuid import UUID

# Contexto para hash de passwords
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Más rondas = más seguro pero más lento
)

class User(Base, UUIDMixin, TimestampMixin):
    """
    Un User es un agente/admin dentro de un Tenant.
    Múltiples usuarios pueden pertenecer a un mismo tenant.
    """
    __tablename__ = "users"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)

    # Roles dentro del tenant
    role = Column(String(50), default="agent")  # owner, admin, agent, viewer

    # Estado
    is_active = Column(Boolean, default=True, index=True)
    last_login = Column(DateTime, nullable=True)

    # Tracking
    login_count = Column(Integer, default=0)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    tasks = relationship("Task", back_populates="assigned_user", foreign_keys="Task.assigned_to")

    # Índices
    __table_args__ = (
        Index('idx_user_tenant_email', 'tenant_id', 'email', unique=True),
        Index('idx_user_active', 'is_active'),
    )

    def set_password(self, password: str) -> None:
        """Hash y guardar password"""
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        """Verificar que un password coincide con el hash"""
        return pwd_context.verify(password, self.password_hash)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
