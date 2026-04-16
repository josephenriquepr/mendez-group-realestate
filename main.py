"""
ListaPro - Plataforma SaaS para agentes inmobiliarios
Versión multi-tenant con PostgreSQL y autenticación JWT
"""
import os
import uvicorn
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import init_db, check_db_connection
from routers import auth_router, generate_router

# Importar routers antiguos (mantenidos por compatibilidad temporal)
try:
    from routers import generate, publish, video, crm as crm_router
    from routers import campaigns, oportunidades, analytics, meta_webhook, tags, tasks
    LEGACY_ROUTERS_AVAILABLE = True
except ImportError:
    LEGACY_ROUTERS_AVAILABLE = False

# ============= INICIALIZACIÓN =============

app = FastAPI(
    title="ListaPro SaaS",
    version="2.0.0",
    description="Plataforma para generación de contenido IA y CRM para agentes inmobiliarios"
)

# Crear directorios necesarios
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

# ============= STARTUP & SHUTDOWN =============

@app.on_event("startup")
async def startup_event():
    """Inicializar BD y verificar conexiones"""
    print("🚀 Iniciando ListaPro SaaS...")

    # Verificar conexión a PostgreSQL
    if check_db_connection():
        print("✅ Conexión a PostgreSQL: OK")
    else:
        print("⚠️  ADVERTENCIA: No se puede conectar a PostgreSQL")
        print("   Asegúrate de que Docker está corriendo: docker-compose up -d")

    # Crear tablas
    try:
        init_db()
        print("✅ Base de datos inicializada")
    except Exception as e:
        print(f"❌ Error inicializando BD: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup al apagar"""
    print("👋 Apagando ListaPro SaaS...")


# ============= MIDDLEWARE =============

# CORS configuration
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8003,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= HEALTH CHECK =============

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "database": "connected" if check_db_connection() else "disconnected"
    }


# ============= NUEVOS ROUTERS (MULTI-TENANT) =============

# Auth (registro, login, etc)
app.include_router(auth_router.router)

# Generate (generar contenido con IA)
app.include_router(generate_router.router)


# ============= ROUTERS ANTIGUOS (COMPATIBILIDAD TEMPORAL) =============

if LEGACY_ROUTERS_AVAILABLE:
    print("⚠️  Cargando routers antiguos (para compatibilidad temporal)...")
    try:
        app.include_router(generate.router, prefix="/api")
        app.include_router(publish.router, prefix="/api/publish")
        app.include_router(video.router, prefix="/api/video")
        app.include_router(crm_router.router, prefix="/api/crm")
        app.include_router(campaigns.router, prefix="/api/crm/campaigns")
        app.include_router(oportunidades.router, prefix="/api/crm/oportunidades")
        app.include_router(analytics.router, prefix="/api/crm/analytics")
        app.include_router(meta_webhook.router, prefix="/api/webhooks")
        app.include_router(tags.router, prefix="/api/crm/tags")
        app.include_router(tasks.router, prefix="/api/crm/tasks")
    except Exception as e:
        print(f"  Error cargando routers antiguos: {e}")


# ============= STATIC FILES & PAGES =============

# HTML page routes (debe estar ANTES de los static mounts)
@app.get("/", tags=["pages"])
async def root():
    """Landing page"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "ListaPro API v2.0.0"}


@app.get("/crm", tags=["pages"])
async def crm_page():
    """CRM page"""
    if os.path.exists("static/crm.html"):
        return FileResponse("static/crm.html")
    return {"message": "CRM Page"}


@app.get("/website", tags=["pages"])
async def website():
    """Website page"""
    if os.path.exists("static/mendez.html"):
        return FileResponse("static/mendez.html")
    return {"message": "Website"}


@app.get("/kelitza", tags=["pages"])
async def kelitza_page():
    """Kelitza page (cliente específico)"""
    if os.path.exists("static/kelitza.html"):
        return FileResponse("static/kelitza.html")
    return {"message": "Kelitza Page"}


# Static files mount (DESPUÉS de las rutas específicas)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============= MAIN =============

if __name__ == "__main__":
    ENV = os.getenv("ENV", "development")
    RELOAD = ENV == "development"

    print(f"\n{'='*50}")
    print(f"  ListaPro SaaS - Ambiente: {ENV.upper()}")
    print(f"  Puerto: 8003")
    print(f"  Docs: http://localhost:8003/docs")
    print(f"{'='*50}\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=RELOAD,
        log_level="info"
    )
