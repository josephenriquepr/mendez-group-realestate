# 🔧 PLAN TÉCNICO FASE 1: DB MIGRATION & MULTI-TENANT (Semanas 1-2)

**Objetivo**: Migrar de SQLite a PostgreSQL y preparar arquitectura para múltiples clientes.

---

## PASO 1: Estructura de Base de Datos Multi-Tenant

### Schema PostgreSQL Nuevo

```sql
-- ===== TENANTS (Clientes/Agentes) =====
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- ej: "kelitza-mendez"
    plan VARCHAR(50) DEFAULT 'starter',  -- starter, pro, premium, enterprise
    status VARCHAR(50) DEFAULT 'active',  -- active, trial, suspended, cancelled
    subscription_id VARCHAR(255),  -- Stripe subscription ID
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ===== USERS (Usuarios/Agentes + Admins) =====
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'agent',  -- owner, admin, agent, viewer
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, email)  -- Email único por tenant
);

-- ===== PROPERTIES (Propiedades) =====
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    address VARCHAR(500) NOT NULL,
    price DECIMAL(15, 2),
    bedrooms INT,
    bathrooms DECIMAL(3, 1),
    sqft INT,
    description TEXT,
    instagram_copy TEXT,
    main_photo_url VARCHAR(500),
    status VARCHAR(50) DEFAULT 'active',  -- active, sold, rented, archived
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ===== PROPERTY PHOTOS =====
CREATE TABLE property_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    photo_url VARCHAR(500),
    order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ===== CONTACTS/LEADS (CRM) =====
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    status VARCHAR(50) DEFAULT 'new',  -- new, interested, negotiating, won, lost
    property_id UUID REFERENCES properties(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ===== CAMPAIGNS =====
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',  -- draft, active, paused, completed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ===== TASKS =====
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, completed
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ===== USAGE TRACKING (para suscripciones) =====
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    feature VARCHAR(100) NOT NULL,  -- 'generate_description', 'generate_instagram', etc.
    count INT DEFAULT 1,
    date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, feature, date)
);

-- ===== INDEXES (Optimización) =====
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_properties_tenant ON properties(tenant_id);
CREATE INDEX idx_contacts_tenant ON contacts(tenant_id);
CREATE INDEX idx_campaigns_tenant ON campaigns(tenant_id);
CREATE INDEX idx_usage_tenant_date ON usage_logs(tenant_id, date);
```

---

## PASO 2: Modelos SQLAlchemy (Python)

### Instalación de dependencias

```bash
pip install sqlalchemy postgresql psycopg2-binary
```

### Archivo: `models/base.py`

```python
from sqlalchemy import Column, DateTime, UUID, func, create_engine
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.ext.hybrid import hybrid_property
import uuid
from datetime import datetime

Base = declarative_base()

class TimestampMixin:
    """Agregar created_at y updated_at automáticamente"""
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class UUIDMixin:
    """Usar UUID como PK"""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

class TenantMixin:
    """Agregar tenant_id para multi-tenant"""
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
```

### Archivo: `models/tenant.py`

```python
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base, UUIDMixin, TimestampMixin
import uuid

class Tenant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenants"
    
    company_name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)  # kelitza-mendez
    plan = Column(String(50), default="starter")  # starter, pro, premium, enterprise
    status = Column(String(50), default="active")  # active, trial, suspended, cancelled
    subscription_id = Column(String(255))  # Stripe ID
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="tenant", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="tenant", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="tenant", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="tenant", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="tenant", cascade="all, delete-orphan")
```

### Archivo: `models/user.py`

```python
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from models.base import Base, UUIDMixin, TimestampMixin
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="agent")  # owner, admin, agent, viewer
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    tasks = relationship("Task", back_populates="assigned_to")
    
    def set_password(self, password: str):
        self.password_hash = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)
```

### Archivo: `models/property.py`

```python
from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base, UUIDMixin, TimestampMixin

class Property(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "properties"
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    address = Column(String(500), nullable=False)
    price = Column(Float)
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    sqft = Column(Integer)
    description = Column(Text)
    instagram_copy = Column(Text)
    main_photo_url = Column(String(500))
    status = Column(String(50), default="active")  # active, sold, rented, archived
    
    # Relationships
    tenant = relationship("Tenant", back_populates="properties")
    photos = relationship("PropertyPhoto", back_populates="property", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="property")

class PropertyPhoto(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "property_photos"
    
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    photo_url = Column(String(500))
    order = Column(Integer, default=0)
    
    # Relationships
    property = relationship("Property", back_populates="photos")
```

### Archivo: `models/crm.py`

```python
from sqlalchemy import Column, String, Text, Date, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base, UUIDMixin, TimestampMixin

class Contact(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "contacts"
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(20))
    status = Column(String(50), default="new")  # new, interested, negotiating, won, lost
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"))
    
    tenant = relationship("Tenant", back_populates="contacts")
    property = relationship("Property", back_populates="contacts")

class Campaign(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "campaigns"
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="draft")  # draft, active, paused, completed
    
    tenant = relationship("Tenant", back_populates="campaigns")

class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="pending")  # pending, in_progress, completed
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    due_date = Column(Date)
    
    tenant = relationship("Tenant", back_populates="tasks")
    assigned_user = relationship("User", back_populates="tasks", foreign_keys=[assigned_to])

class UsageLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "usage_logs"
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    feature = Column(String(100), nullable=False)  # generate_description, generate_instagram
    count = Column(Integer, default=1)
    date = Column(Date, server_default=func.current_date())
    
    tenant = relationship("Tenant", back_populates="usage_logs")
```

---

## PASO 3: Database Connection y Migrations

### Archivo: `database.py` (refactor)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import os

# Configuración
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost/listapro_db"
)

# Engine
if os.getenv("ENV") == "production":
    # En prod, usar NullPool para evitar conexiones abiertas
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
else:
    # En dev, usar pool normal
    engine = create_engine(
        DATABASE_URL,
        echo=True,  # Ver queries SQL
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency para FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Crear todas las tablas"""
    from models.base import Base
    Base.metadata.create_all(bind=engine)
```

### Archivo: `.env.example` (actualizado)

```env
# Database
DATABASE_URL=postgresql://usuario:password@localhost:5432/listapro_db

# OpenAI
OPENAI_API_KEY=sk-...

# JWT
SECRET_KEY=your-secret-key-min-32-chars-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email (opcional para Fase 2)
SENDGRID_API_KEY=SG...
SENDGRID_FROM_EMAIL=noreply@listapro.app

# Environment
ENV=development  # development, staging, production
DEBUG=True
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8003"]
```

---

## PASO 4: Setup Local con Docker

### Archivo: `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: listapro_postgres
    environment:
      POSTGRES_USER: listapro
      POSTGRES_PASSWORD: listapro_dev_password
      POSTGRES_DB: listapro_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U listapro"]
      interval: 10s
      timeout: 5s
      retries: 5

  pgadmin:
    image: dpage/pgadmin4
    container_name: listapro_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@listapro.local
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres

volumes:
  postgres_data:
```

### Comando para levantar:

```bash
docker-compose up -d
```

Luego acceder a PgAdmin en `http://localhost:5050`

---

## PASO 5: Refactor de Routers (Ejemplo: Generate)

### Archivo: `routers/generate.py` (nuevo)

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from database import get_db
from auth import get_current_user, get_current_tenant
from models.user import User
from models.tenant import Tenant
from models.property import Property
from services.openai_service import generate_description, generate_instagram_copy
from services.usage_service import check_usage_limit, log_usage

router = APIRouter()
security = HTTPBearer()

@router.post("/generate")
async def generate_property_content(
    address: str,
    price: float,
    bedrooms: int,
    bathrooms: float,
    sqft: int,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    main_photo: UploadFile = File(None)
):
    """
    Generar descripción y copy Instagram para una propiedad
    """
    
    # Verificar límite de generaciones según plan
    if not check_usage_limit(db, current_tenant.id, "generate"):
        raise HTTPException(
            status_code=429,
            detail="Has alcanzado el límite de generaciones para tu plan"
        )
    
    try:
        # Guardar propiedad
        property_obj = Property(
            tenant_id=current_tenant.id,
            address=address,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            sqft=sqft
        )
        
        # Procesar foto si existe
        if main_photo:
            filename = f"{uuid.uuid4()}_{main_photo.filename}"
            filepath = f"uploads/{filename}"
            with open(filepath, "wb") as f:
                f.write(await main_photo.read())
            property_obj.main_photo_url = f"/uploads/{filename}"
        
        # Generar con IA
        description = await generate_description(address, price, bedrooms, bathrooms, sqft)
        instagram_copy = await generate_instagram_copy(address, price, bedrooms)
        
        property_obj.description = description
        property_obj.instagram_copy = instagram_copy
        
        # Guardar en DB
        db.add(property_obj)
        db.commit()
        db.refresh(property_obj)
        
        # Registrar uso
        log_usage(db, current_tenant.id, "generate", 2)  # 2 porque generamos 2 textos
        
        return {
            "property_id": property_obj.id,
            "address": property_obj.address,
            "description": property_obj.description,
            "instagram_copy": property_obj.instagram_copy,
            "created_at": property_obj.created_at
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## PASO 6: Checklist de Implementación

- [ ] Crear DB PostgreSQL local
- [ ] Escribir SQL schema
- [ ] Crear modelos SQLAlchemy
- [ ] Escribir `database.py` nuevo
- [ ] Setup Docker Compose
- [ ] Crear `auth.py` con JWT
- [ ] Refactor router `generate.py` con multi-tenant
- [ ] Refactor router `crm.py` con tenant isolation
- [ ] Tests de DB (crear/leer/actualizar datos)
- [ ] Documentar en README

---

## PASO 7: Testing rápido

```bash
# 1. Levantar PostgreSQL
docker-compose up -d

# 2. Crear las tablas
python -c "from database import init_db; init_db()"

# 3. Verificar con PgAdmin
# Ir a http://localhost:5050
# Email: admin@listapro.local / Password: admin

# 4. Conectar servidor Postgres
# Host: postgres (desde el docker network)
# User: listapro
# Password: listapro_dev_password
# Database: listapro_db

# 5. Correr FastAPI
python main.py
# Debería estar en http://localhost:8003
```

---

## 🎯 RESULTADO FINAL (Fin de Semana 2)

✅ PostgreSQL corriendo localmente  
✅ Modelos SQLAlchemy multi-tenant  
✅ Tablas creadas con relaciones correctas  
✅ Routers refactorizados con tenant isolation  
✅ Base sólida para agregar Auth la Semana 3  

---

**Siguiente paso**: Una vez tengas esto, hablamos de JWT y Auth endpoints.

¿Empezamos? ¿Preguntas sobre la DB schema?
