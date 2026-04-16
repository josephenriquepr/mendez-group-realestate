# ListaPro SaaS 🏠

**Plataforma multi-tenant para generación de contenido IA y CRM para agentes inmobiliarios**

Generate professional real estate descriptions and Instagram copies with AI. Multi-tenant architecture with JWT authentication and PostgreSQL.

---

## 📋 Requisitos

- **Python**: 3.10+
- **Docker** (para PostgreSQL local)
- **API Keys**:
  - OpenAI (para generación de contenido)
  - (Opcional) Stripe (para billing en Fase 2)

---

## 🚀 Quick Start (5 minutos)

### 1. Clonar y Setup

```bash
git clone https://github.com/tu-usuario/listapro-saas.git
cd listapro-saas

# Crear virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Edita .env y agrega tu OPENAI_API_KEY
```

### 2. Levantar PostgreSQL (Docker)

```bash
# Asegúrate de tener Docker corriendo
docker-compose up -d

# Verificar que PostgreSQL está arriba
docker-compose logs postgres
```

### 3. Iniciar Servidor

```bash
python main.py
```

**Accesos:**
- 🌐 API: http://localhost:8003
- 📚 Docs: http://localhost:8003/docs
- 🏥 Health: http://localhost:8003/health
- 🐘 PgAdmin: http://localhost:5050 (admin@listapro.local / admin123)

---

## 📚 Documentación API

### Endpoints Principales

#### **Autenticación**

```bash
# Registrar nueva empresa y usuario
POST /api/auth/register
Content-Type: application/json

{
  "company_name": "Kelitza Méndez Bienes Raíces",
  "company_slug": "kelitza-mendez",
  "email": "kelitza@mendezgroup.com",
  "password": "SecurePassword123!",
  "full_name": "Kelitza Méndez"
}

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": { ... }
}
```

```bash
# Login
POST /api/auth/login
Content-Type: application/json

{
  "email": "kelitza@mendezgroup.com",
  "password": "SecurePassword123!"
}
```

#### **Generar Contenido**

```bash
# Generar descripción e Instagram copy
POST /api/generate
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

address=123 Ocean View Avenue, San Juan, PR
price=450000
bedrooms=3
bathrooms=2.5
sqft=2100
photo=<binary photo file>

# Response
{
  "property_id": "uuid",
  "address": "123 Ocean View Avenue...",
  "description": "Hermosa casa con vistas al océano...",
  "instagram_copy": "🏡 ¡Espectacular propiedad! 3 hab...",
  "hashtags": "#puertorigoproperty #realestatepr...",
  "usage_remaining": 47
}
```

```bash
# Listar propiedades
GET /api/properties
Authorization: Bearer <access_token>

# Obtener propiedad específica
GET /api/properties/{property_id}
Authorization: Bearer <access_token>
```

---

## 📁 Estructura del Proyecto

```
listapro-saas/
├── main.py                      # FastAPI app
├── database.py                  # PostgreSQL setup
├── auth.py                      # JWT authentication
├── models/
│   ├── __init__.py
│   ├── base.py                  # Mixins (UUIDMixin, TimestampMixin)
│   ├── tenant.py                # Tenant model
│   ├── user.py                  # User model
│   ├── property_models.py       # Property, PropertyPhoto
│   └── crm_models.py            # Contact, Campaign, Task, UsageLog
├── routers/
│   ├── auth_router.py           # /api/auth/* endpoints
│   ├── generate_router.py       # /api/generate endpoints
│   └── ... (routers antiguos por compatibilidad)
├── services/
│   ├── openai_service.py        # OpenAI integration
│   └── ... (otros servicios)
├── static/                      # Frontend (HTML/CSS/JS)
├── uploads/                     # User photos
├── requirements.txt
├── docker-compose.yml           # PostgreSQL setup
├── .env.example                 # Environment variables template
└── README.md (este archivo)
```

---

## 🔐 Autenticación

ListaPro usa **JWT (JSON Web Tokens)** para autenticación.

### Flow de Autenticación

1. **Registro**: Usuario crea cuenta → Nuevo Tenant + User creado
2. **Login**: Email + password → Access token + Refresh token
3. **Requests**: Header `Authorization: Bearer <access_token>`
4. **Validación**: Middleware valida token y tenant

### Headers Requeridos

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json (para JSON) o multipart/form-data (para uploads)
```

---

## 🏢 Multi-Tenant Architecture

### Conceptos Clave

- **Tenant**: Una empresa/agencia inmobiliaria (ej: "Kelitza Méndez Bienes Raíces")
- **User**: Un usuario dentro de un Tenant (ej: Kelitza, su asistente, etc)
- **Isolation**: Cada Tenant solo ve sus datos (propiedades, contactos, etc)

### Ejemplo de Aislamiento

```
┌─────────────────────────────────────────┐
│         DATABASE (PostgreSQL)           │
├─────────────────────────────────────────┤
│ Tenant 1: Kelitza Méndez               │
│  - User: Kelitza (owner)               │
│  - Properties: [Prop1, Prop2, ...]     │
│  - Contacts: [Contact1, Contact2, ...] │
├─────────────────────────────────────────┤
│ Tenant 2: Juan Flores Real Estate      │
│  - User: Juan (owner)                  │
│  - Properties: [PropA, PropB, ...]     │
│  - Contacts: [ContactA, ContactB, ...] │
└─────────────────────────────────────────┘

✅ Kelitza NO PUEDE VER propiedades de Juan
✅ Juan NO PUEDE VER contactos de Kelitza
✅ Cada uno ve solo SUS DATOS
```

---

## 💰 Planes y Límites

| Plan | Precio | Generaciones/mes | CRM | Social | Tours 3D |
|------|--------|-----|-----|--------|---------|
| **Starter** | $29 | 50 | ✅ | ❌ | ❌ |
| **Pro** | $79 | 250 | ✅ | ✅ | ❌ |
| **Premium** | $149 | ∞ | ✅ | ✅ | ✅ |

(Billing integrado en Fase 2)

---

## 🛠️ Desarrollo

### Ejecutar en modo debug

```bash
ENV=development DEBUG=true python main.py
```

### Ver SQL queries

```bash
# En .env, cambiar:
SQL_ECHO=true
```

### Ejecutar tests

```bash
pytest
pytest -v  # Verbose
pytest --cov  # Con coverage
```

---

## 📦 Deployment (Fase 5-6)

Opciones recomendadas:

### **Railway.app** (Recomendado - Más fácil)
```bash
# 1. Push a GitHub
git push origin main

# 2. Railway auto-deploy
# (Conectar repo en railway.app)
```

### **Heroku**
```bash
heroku create listapro-app
git push heroku main
```

### **DigitalOcean App Platform**
Configurar en el dashboard: https://cloud.digitalocean.com/apps

---

## 🤖 OpenAI Integration

### Configurar API Key

1. Ir a https://platform.openai.com/api-keys
2. Crear nueva key
3. Copiar en `.env`:
   ```
   OPENAI_API_KEY=sk-your-key-here
   OPENAI_MODEL=gpt-4o-mini  # Recomendado (barato y rápido)
   ```

### Costo Aproximado

- Descripción inmobiliaria: ~$0.001
- Instagram copy: ~$0.0005
- **Total por generación**: ~$0.0015

Con 100 generaciones/mes @ $0.0015 = $0.15/mes en OpenAI (muy barato)

---

## 🐛 Troubleshooting

### Error: "Cannot connect to PostgreSQL"

```bash
# 1. Verificar que Docker está corriendo
docker ps

# 2. Verificar que PostgreSQL está UP
docker-compose logs postgres

# 3. Reiniciar si es necesario
docker-compose down
docker-compose up -d
```

### Error: "Invalid authentication credentials"

- Verificar que `OPENAI_API_KEY` está en `.env`
- Asegúrate que la key es válida (no expirada)

### Error: "Database migration failed"

```bash
# Recrear DB desde cero (PELIGRO: borra todo)
python -c "from database import drop_all_tables; drop_all_tables()"

# Crear tablas de nuevo
python -c "from database import init_db; init_db()"
```

---

## 📞 Soporte & Roadmap

### Fase 1 (Semana 1-2): ✅ Completado
- [x] Multi-tenant architecture
- [x] PostgreSQL migration
- [x] JWT authentication
- [x] Generate endpoint

### Fase 2 (Semana 3-4): 📅 Próximo
- [ ] Stripe billing integration
- [ ] Team management (invitar usuarios)
- [ ] Email confirmación

### Fase 3 (Semana 5-6): 🚀 En Desarrollo
- [ ] Deploy a producción
- [ ] UI refactor (login, dashboard)
- [ ] Social media auto-posting

### Fase 4+ (Futuro)
- [ ] 3D tours integration
- [ ] MLS sync
- [ ] Mobile app

---

## 📝 License

MIT License - Libre para usar y modificar

---

**¿Preguntas?** Abre un issue en GitHub o contacta a joseph@listapro.app
