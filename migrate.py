"""
Script de migración para agregar columnas nuevas a tablas existentes.
Ejecutar UNA sola vez antes de arrancar la aplicación:
    python migrate.py
"""
import sqlite3

conn = sqlite3.connect("listapro_crm.db")
cur = conn.cursor()

migrations = [
    "ALTER TABLE contacts ADD COLUMN fuente TEXT DEFAULT 'manual'",
    "ALTER TABLE contacts ADD COLUMN meta_sender_id TEXT",
    "ALTER TABLE activities ADD COLUMN oportunidad_id INTEGER REFERENCES oportunidades(id)",
]

for sql in migrations:
    try:
        cur.execute(sql)
        print(f"OK: {sql}")
    except Exception as e:
        print(f"Omitido (ya existe): {e}")

conn.commit()
conn.close()
print("\nMigración completada.")
