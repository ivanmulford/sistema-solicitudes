import sqlite3

# Abre tu base de datos existente
conn = sqlite3.connect("solicitudes (4).db")
cursor = conn.cursor()

# Crear la tabla de ítems si no existe
cursor.execute("""
CREATE TABLE IF NOT EXISTS items_solicitud (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    solicitud_id INTEGER,
    cantidad INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    FOREIGN KEY (solicitud_id) REFERENCES solicitudes (id)
)
""")

conn.commit()
conn.close()

print("✅ Tabla 'items_solicitud' creada o ya existía")
