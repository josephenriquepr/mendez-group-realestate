"""
Modelos Property, PropertyPhoto - Propiedades inmobiliarias
"""
from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Index, DateTime, func, Boolean, UUID
from sqlalchemy.orm import relationship
from models.base import Base, UUIDMixin, TimestampMixin, TenantMixin

class Property(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """
    Una Property es una propiedad inmobiliaria.
    Cada propiedad pertenece a un tenant específico.
    """
    __tablename__ = "properties"

    # Foreign key al tenant
    tenant_id = Column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Información básica
    address = Column(String(500), nullable=False)
    price = Column(Float, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Float, nullable=True)
    sqft = Column(Integer, nullable=True)
    lot_size = Column(Float, nullable=True)

    # Descripción y contenido IA
    description = Column(Text, nullable=True)  # Generada con IA
    instagram_copy = Column(Text, nullable=True)  # Copy de Instagram generado
    hashtags = Column(String(500), nullable=True)  # Hashtags sugeridos

    # Fotos
    main_photo_url = Column(String(500), nullable=True)
    photo_count = Column(Integer, default=0)

    # Estado
    status = Column(String(50), default="active", index=True)  # active, sold, rented, archived
    listing_type = Column(String(50), nullable=True)  # for_sale, for_rent, sold

    # Metadata
    mls_number = Column(String(100), nullable=True, unique=True)
    property_type = Column(String(100), nullable=True)  # house, condo, land, commercial, etc

    # Relationships
    tenant = relationship("Tenant", back_populates="properties")
    photos = relationship("PropertyPhoto", back_populates="property", cascade="all, delete-orphan")

    # Índices
    __table_args__ = (
        Index('idx_property_tenant_status', 'tenant_id', 'status'),
        Index('idx_property_address', 'address'),
        Index('idx_property_mls', 'mls_number'),
    )

    def __repr__(self):
        return f"<Property {self.address} (${self.price})>"


class PropertyPhoto(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """
    Fotos asociadas a una Property
    """
    __tablename__ = "property_photos"

    property_id = Column(UUID(), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # URL de la foto (local o en cloud)
    photo_url = Column(String(500), nullable=False)

    # Metadata
    order = Column(Integer, default=0)  # Orden de visualización
    photo_type = Column(String(50), nullable=True)  # interior, exterior, kitchen, bathroom, etc
    is_main = Column(Boolean, default=False)

    # Relationships
    property = relationship("Property", back_populates="photos")
    tenant = relationship("Tenant")

    __table_args__ = (
        Index('idx_photo_property', 'property_id'),
    )

    def __repr__(self):
        return f"<PropertyPhoto {self.photo_url}>"
