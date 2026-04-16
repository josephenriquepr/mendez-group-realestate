# 🚀 SETUP LOCAL - GUÍA PASO A PASO

**Tu arquitectura está 100% refactorizada.** Aquí te enseño cómo levantar TODO localmente en 30 minutos.

---

## ✅ CHECKLIST PRE-SETUP

Antes de empezar, asegúrate de tener:

- [ ] Python 3.10+ (`python --version`)
- [ ] Docker instalado (`docker --version`)
- [ ] Git configurado (`git config --list`)
- [ ] Tu API Key de OpenAI lista

---

## PASO 1: Crear Virtual Environment (2 min)

```bash
# Desde la carpeta del proyecto
python -m venv .venv

# Activar
source .venv/bin/activate  # macOS/Linux
# O en Windows:
# .venv\Scripts\activate
```

**Verificación:**
```bash
which python  # Debería mostrar .venv/bin/python
python -V    # Python 3.10+
```

---

## PASO 2: Instalar Dependencias (3 min)

```bash
# Asegúrate que .venv está activo
pip install --upgrade pip

# Instalar todos los paquetes
pip install -r requirements.txt

# Verificación
pip list | grep -E "fastapi|sqlalchemy|psycopg2"
# Debería mostrar: fastapi, sqlalchemy, psycopg2-binary, etc
```

---

## PASO 3: Configurar Variables de Entorno (2 min)

```bash
# Copiar template
cp .env.example .env

# Editar .env (abrir con tu editor favorito)
# IMPORTANTE: Agregar tu OPENAI_API_KEY
nano .env  # O usa VS Code, etc
```

**Valores mínimos necesarios:**
```env
# DATABASE (ya está configurada para Docker)
DATABASE_URL=postgresql://listapro_user:listapro_secure_dev_password@localhost:5432/listapro_db

# OPENAI - IMPORTANTE!
OPENAI_API_KEY=sk-your-actual-key-here

# Security (para desarrollo está bien, cambiar en producción)
SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars
```

---

## PASO 4: Levantar PostgreSQL con Docker (3 min)

```bash
# Asegúrate de que Docker Desktop está corriendo
# (En Mac/Windows abre la app; en Linux, verifica que el daemon corre)

# Levantar containers
docker-compose up -d

# Verificar que está UP
docker-compose logs

# Debería ver algo como:
# postgres_1  | LOG:  database system is ready to accept connections
```

**Verificaciones:**
```bash
# Ver containers corriendo
docker ps
# Debería mostrar: listapro_postgres y listapro_pgadmin

# Acceder a PgAdmin
# URL: http://localhost:5050
# Email: admin@listapro.local
# Password: admin123

# En PgAdmin: Conectar al servidor
# Host: postgres (no localhost!)
# User: listapro_user
# Password: listapro_secure_dev_password
# Database: listapro_db
```

---

## PASO 5: Iniciar FastAPI Server (2 min)

```bash
# Asegúrate que .venv está activo y estás en el folder correcto

python main.py

# Debería ver algo como:
# 🚀 Iniciando ListaPro SaaS...
# ✅ Conexión a PostgreSQL: OK
# ✅ Base de datos inicializada
# INFO:     Uvicorn running on http://0.0.0.0:8003
```

---

## PASO 6: Probar la API (5 min)

Abre una **nueva terminal** (sin cerrar la que corre el servidor):

### 1️⃣ Health Check

```bash
curl http://localhost:8003/health

# Response:
# {"status":"healthy","version":"2.0.0","database":"connected"}
```

### 2️⃣ Registrar Nueva Empresa

```bash
curl -X POST http://localhost:8003/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Real Estate",
    "company_slug": "test-real-estate",
    "email": "test@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
  }'

# Copiar el access_token de la respuesta
# Guardalo en una variable para los próximos pasos
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3️⃣ Obtener Info del Usuario

```bash
# Reemplaza TOKEN con el que obtuviste arriba
curl http://localhost:8003/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {
#   "user": {...},
#   "tenant": {...}
# }
```

### 4️⃣ Generar Contenido IA

```bash
curl -X POST http://localhost:8003/api/generate \
  -H "Authorization: Bearer $TOKEN" \
  -F "address=123 Ocean View, San Juan, PR" \
  -F "price=450000" \
  -F "bedrooms=3" \
  -F "bathrooms=2.5" \
  -F "sqft=2100"

# Response:
# {
#   "property_id": "uuid",
#   "address": "123 Ocean View, San Juan, PR",
#   "description": "Hermosa casa con vistas...",
#   "instagram_copy": "🏡 ¡Espectacular propiedad!...",
#   "usage_remaining": 49,
#   "message": "✅ Contenido generado exitosamente"
# }
```

---

## PASO 7: Explorar Interactive Docs (3 min)

Abre en tu navegador:

**http://localhost:8003/docs**

Aquí puedes:
- ✅ Ver todos los endpoints
- ✅ Probar requests sin curl
- ✅ Ver schemas de request/response
- ✅ Ver códigos de error

---

## 🔍 VERIFICACIÓN FINAL

Si llegaste aquí, TODO está funcionando correctamente:

```bash
# En la terminal del servidor, deberías ver logs como:
# INFO:     127.0.0.1:port GET /health
# INFO:     127.0.0.1:port POST /api/auth/register
# INFO:     127.0.0.1:port GET /api/auth/me
# INFO:     127.0.0.1:port POST /api/generate
```

✅ **Servidor**: Corriendo en http://localhost:8003  
✅ **Base de Datos**: PostgreSQL en puerto 5432  
✅ **Autenticación**: JWT funcionando  
✅ **OpenAI**: Integrando correctamente  

---

## 📱 DESDE VS CODE

Si quieres hacer debugging:

### 1. Instalar extensión Rest Client

```
Extensión: REST Client (Huachao Mao)
```

### 2. Crear archivo `requests.http`

```http
### Health Check
GET http://localhost:8003/health

### Register
POST http://localhost:8003/api/auth/register
Content-Type: application/json

{
  "company_name": "Kelitza Test",
  "company_slug": "kelitza-test-123",
  "email": "kelitza@test.com",
  "password": "SecurePass123!",
  "full_name": "Kelitza Test"
}

### Get User (reemplaza TOKEN)
GET http://localhost:8003/api/auth/me
Authorization: Bearer {{TOKEN}}

### Generate
POST http://localhost:8003/api/generate
Authorization: Bearer {{TOKEN}}
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="address"

123 Ocean View, San Juan, PR
------WebKitFormBoundary
Content-Disposition: form-data; name="price"

450000
------WebKitFormBoundary
Content-Disposition: form-data; name="bedrooms"

3
------WebKitFormBoundary
Content-Disposition: form-data; name="bathrooms"

2.5
------WebKitFormBoundary
Content-Disposition: form-data; name="sqft"

2100
------WebKitFormBoundary--
```

### 3. Usar Rest Client

- `Ctrl+Alt+R` en cada request
- Resultados en panel lateral

---

## 🐛 ERRORES COMUNES & SOLUCIONES

### ❌ "Cannot connect to PostgreSQL"

```bash
# 1. Verificar Docker
docker ps

# 2. Si no ve los containers, levantar:
docker-compose up -d

# 3. Si sigue sin funcionar, recrear:
docker-compose down
docker-compose up -d
```

### ❌ "Invalid OpenAI API Key"

```bash
# 1. Verificar que .env tiene la key correcta
cat .env | grep OPENAI_API_KEY

# 2. Si es incorrecta, actualizar
# Copiar key nueva desde https://platform.openai.com/api-keys

# 3. Reiniciar servidor:
# Presiona Ctrl+C en la terminal del servidor
# Vuelve a correr: python main.py
```

### ❌ "Port 8003 already in use"

```bash
# Encontrar qué está usando el puerto
lsof -i :8003  # macOS/Linux
netstat -ano | findstr :8003  # Windows

# Matar el proceso
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# O simplemente cambiar el puerto en main.py:
# uvicorn.run(..., port=8004)
```

### ❌ "ModuleNotFoundError: No module named 'sqlalchemy'"

```bash
# Asegúrate que .venv está activo
source .venv/bin/activate

# Reinstalar:
pip install -r requirements.txt --force-reinstall
```

---

## 📝 PRÓXIMOS PASOS (Después de verificar setup)

1. **Git Setup**
   ```bash
   git init
   git add .
   git commit -m "Refactor: Multi-tenant PostgreSQL architecture"
   git remote add origin https://github.com/tu-usuario/listapro-saas.git
   git push -u origin main
   ```

2. **Crear archivo `.gitignore`** (si no existe)
   ```
   .venv/
   __pycache__/
   *.pyc
   .env
   uploads/
   .DS_Store
   .idea/
   .vscode/
   *.db
   ```

3. **Pruebas (Opcional)**
   ```bash
   pip install pytest pytest-asyncio
   pytest
   ```

4. **Frontend (Próximo paso)**
   - Crear login/signup UI
   - Crear dashboard
   - Integrar con endpoints

---

## 💡 TIPS

- **Ver SQL queries**: Cambiar en `.env` `SQL_ECHO=true`
- **Logs más detallados**: `DEBUG=true` en `.env`
- **Recrear DB**: `python -c "from database import drop_all_tables; drop_all_tables()"`
- **Entrar a DB directamente**: `docker-compose exec postgres psql -U listapro_user -d listapro_db`

---

## ✨ ¡ESTÁS LISTO!

Si todo pasó sin errores, **FELICIDADES**.

Tu arquitectura multi-tenant está corriendo. Ahora puedes:

1. ✅ **Registrar múltiples tenants**
2. ✅ **Cada uno ve solo sus datos**
3. ✅ **Generar contenido con IA**
4. ✅ **Escalar a producción**

---

**¿Stuck en algo?** Revisa TROUBLESHOOTING arriba o contacta.

**Siguiente fase**: Crear endpoints de CRM (Contactos, Tareas, Campañas)

Referencia: `PLAN_TECNICO_FASE1.md`
