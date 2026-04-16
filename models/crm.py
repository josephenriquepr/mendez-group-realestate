from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id             = Column(Integer, primary_key=True, index=True)
    nombre         = Column(String(200), nullable=False)
    telefono       = Column(String(50),  default="")
    email          = Column(String(200), default="")
    tipo           = Column(String(50),  default="prospecto")   # comprador|vendedor|prospecto|ambos
    notas          = Column(Text,        default="")
    follow_up_date = Column(String(20),  nullable=True)
    fuente         = Column(String(50),  default="manual")       # manual|instagram|facebook|email
    meta_sender_id = Column(String(200), nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    properties = relationship("SavedProperty", back_populates="contact",
                              cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="contact",
                              cascade="all, delete-orphan")
    oportunidades = relationship("Oportunidad", back_populates="contacto")
    meta_conversations = relationship("MetaConversation", back_populates="contact")
    email_sends = relationship("EmailSend", back_populates="contact")
    contact_tags = relationship("ContactTag", back_populates="contact",
                                cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="contact",
                         cascade="all, delete-orphan", order_by="Task.fecha_vencimiento")


class SavedProperty(Base):
    __tablename__ = "saved_properties"

    id               = Column(Integer, primary_key=True, index=True)
    contact_id       = Column(Integer, ForeignKey("contacts.id"), nullable=True)

    # Core property data
    tipo_propiedad   = Column(String(100), default="")
    operacion        = Column(String(50),  default="")
    direccion        = Column(String(500), default="")
    pueblo           = Column(String(100), default="")
    precio           = Column(Float,       default=0)
    habitaciones     = Column(Integer,     nullable=True)
    banos            = Column(Float,       nullable=True)
    pies_cuadrados   = Column(Integer,     nullable=True)
    estacionamientos = Column(Integer,     nullable=True)
    metros_terreno   = Column(String(100), default="")
    amenidades       = Column(Text,        default="[]")   # JSON

    # AI outputs
    listing_description = Column(Text, default="")
    instagram_copy      = Column(Text, default="")

    # Asset URLs
    foto_portada_url    = Column(String(500), default="")
    fotos_extras_urls   = Column(Text,        default="[]")  # JSON
    pdf_url             = Column(String(500), default="")
    instagram_image_url = Column(String(500), default="")
    carousel_urls       = Column(Text,        default="[]")  # JSON

    # Agent snapshot
    nombre_agente   = Column(String(200), default="")
    telefono_agente = Column(String(50),  default="")

    # CRM fields
    stage      = Column(String(50), default="prospecto")   # prospecto|activo|oferta|contrato|cerrado
    notas_crm  = Column(Text,       default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contact    = relationship("Contact",  back_populates="properties")
    activities = relationship("Activity", back_populates="property",
                              cascade="all, delete-orphan")


class Activity(Base):
    __tablename__ = "activities"

    id             = Column(Integer, primary_key=True, index=True)
    contact_id     = Column(Integer, ForeignKey("contacts.id"),          nullable=True)
    property_id    = Column(Integer, ForeignKey("saved_properties.id"),  nullable=True)
    oportunidad_id = Column(Integer, ForeignKey("oportunidades.id"),     nullable=True)
    tipo           = Column(String(50), default="nota")  # llamada|visita|correo|nota|reunion|mensaje_meta
    descripcion    = Column(Text,       default="")
    fecha          = Column(String(20), default="")
    created_at     = Column(DateTime, default=datetime.utcnow)

    contact     = relationship("Contact",       back_populates="activities")
    property    = relationship("SavedProperty", back_populates="activities")
    oportunidad = relationship("Oportunidad",   back_populates="activities",
                               foreign_keys=[oportunidad_id])


# ─── New models ───────────────────────────────────────────────────────────────

class Oportunidad(Base):
    __tablename__ = "oportunidades"

    id                    = Column(Integer, primary_key=True, index=True)
    nombre                = Column(String(300), nullable=False)
    valor                 = Column(Float, default=0)
    etapa                 = Column(String(50), default="prospecto")
    # etapas: prospecto|contacto|propuesta|negociacion|cerrado_ganado|cerrado_perdido
    fecha_cierre_esperada = Column(String(20), nullable=True)
    probabilidad          = Column(Integer, default=20)   # 0-100
    contacto_id           = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    notas                 = Column(Text, default="")
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contacto   = relationship("Contact", back_populates="oportunidades")
    activities = relationship("Activity", back_populates="oportunidad",
                              foreign_keys="Activity.oportunidad_id",
                              cascade="all, delete-orphan")


class EmailCampaign(Base):
    __tablename__ = "email_campaigns"

    id               = Column(Integer, primary_key=True, index=True)
    nombre           = Column(String(300), nullable=False)
    asunto           = Column(String(500), nullable=False)
    html_body        = Column(Text, nullable=False)
    segmento         = Column(String(50), default="todos")
    # segmentos: todos|comprador|vendedor|prospecto|ambos
    status           = Column(String(30), default="borrador")
    # status: borrador|enviando|completado|error
    total_enviados   = Column(Integer, default=0)
    total_fallidos   = Column(Integer, default=0)
    programado_para  = Column(String(30), nullable=True)
    enviado_en       = Column(String(30), nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    sends = relationship("EmailSend", back_populates="campaign",
                         cascade="all, delete-orphan")


class EmailSend(Base):
    __tablename__ = "email_sends"

    id          = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("email_campaigns.id"), nullable=False)
    contact_id  = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    email       = Column(String(200), nullable=False)
    status      = Column(String(20), default="pendiente")  # pendiente|enviado|fallido
    error_msg   = Column(Text, nullable=True)
    sent_at     = Column(DateTime, nullable=True)

    campaign = relationship("EmailCampaign", back_populates="sends")
    contact  = relationship("Contact", back_populates="email_sends")


class MetaConversation(Base):
    __tablename__ = "meta_conversations"

    id         = Column(Integer, primary_key=True, index=True)
    platform   = Column(String(30), nullable=False)    # instagram|facebook
    sender_id  = Column(String(200), nullable=False, unique=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="meta_conversations")


# ─── Tags ─────────────────────────────────────────────────────────────────────

class Tag(Base):
    __tablename__ = "tags"

    id         = Column(Integer, primary_key=True, index=True)
    nombre     = Column(String(100), nullable=False, unique=True)
    color      = Column(String(20), default="#1a6b8a")
    created_at = Column(DateTime, default=datetime.utcnow)

    contact_tags = relationship("ContactTag", back_populates="tag",
                                cascade="all, delete-orphan")


class ContactTag(Base):
    __tablename__ = "contact_tags"

    contact_id = Column(Integer, ForeignKey("contacts.id"), primary_key=True)
    tag_id     = Column(Integer, ForeignKey("tags.id"), primary_key=True)

    contact = relationship("Contact", back_populates="contact_tags")
    tag     = relationship("Tag", back_populates="contact_tags")


# ─── Tasks ────────────────────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"

    id                = Column(Integer, primary_key=True, index=True)
    contact_id        = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    titulo            = Column(String(300), nullable=False)
    descripcion       = Column(Text, default="")
    fecha_vencimiento = Column(String(20), nullable=True)
    completada        = Column(Boolean, default=False)
    created_at        = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="tasks")
