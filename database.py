"""
Database setup — PostgreSQL en producción, SQLite en desarrollo sin Docker.
"""
from sqlalchemy import create_engine, text, pool
from sqlalchemy.orm import sessionmaker, Session
import os
from typing import Generator

from models.base import Base

# ──────────────────────────────────────────────
# Detectar si se usa PostgreSQL o SQLite
# ──────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Railway usa "postgres://" — SQLAlchemy requiere "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Si no hay DATABASE_URL, usar SQLite local (desarrollo)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./listapro_dev.db"
    print("ℹ️  Sin DATABASE_URL → usando SQLite (listapro_dev.db)")

ENV = os.getenv("ENV", "development")

# ──────────────────────────────────────────────
# Crear engine
# ──────────────────────────────────────────────
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
elif ENV == "production":
    engine = create_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
        echo=False,
        connect_args={"connect_timeout": 10},
    )
else:
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
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Crear todas las tablas."""
    # Importar modelos legacy para que SQLAlchemy los registre
    from models import crm as _crm_legacy  # noqa: F401
    print("Creando tablas...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas")
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        raise


def drop_all_tables() -> None:
    if ENV != "development":
        raise RuntimeError("Solo en desarrollo")
    Base.metadata.drop_all(bind=engine)


def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ DB error: {e}")
        return False
