"""
Database setup para PostgreSQL con SQLAlchemy
Arquitectura multi-tenant
"""
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import os
from typing import Generator

from models.base import Base

# Configuración de BD desde variables de entorno o defaults
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://listapro_user:listapro_secure_dev_password@localhost:5432/listapro_db"
)

# Railway usa "postgres://" — SQLAlchemy requiere "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Ambiente
ENV = os.getenv("ENV", "development")

# Crear engine con configuración según ambiente
if ENV == "production":
    # En producción: NullPool para evitar conexiones abiertas
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        echo=False,
        connect_args={"connect_timeout": 10}
    )
else:
    # En desarrollo: pool normal para mejor performance
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        connect_args={"connect_timeout": 10},
        pool_size=5,
        max_overflow=10,
    )

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency para FastAPI que proporciona una sesión de BD.
    Uso:
        @app.get("/items")
        async def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Crear todas las tablas en la BD.
    Llamar después de importar todos los modelos.
    """
    print("Creando tablas en PostgreSQL...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas exitosamente")
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        raise


def drop_all_tables() -> None:
    """
    PELIGRO: Eliminar todas las tablas (solo para desarrollo).
    Nunca usar en producción.
    """
    if ENV != "development":
        raise RuntimeError("Solo puedes hacer DROP en desarrollo")

    print("⚠️  Eliminando TODAS las tablas...")
    Base.metadata.drop_all(bind=engine)
    print("✅ Tablas eliminadas")


# Health check para verificar conexión
def check_db_connection() -> bool:
    """Verificar que la BD está accesible"""
    try:
        with SessionLocal() as db:
            db.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"❌ DB connection error: {e}")
        return False

