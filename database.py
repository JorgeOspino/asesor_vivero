"""
database.py
Capa de Persistencia para el Vivero CECAR.
Soporta PostgreSQL (Neon) como motor cloud principal y SQLite como respaldo local.
"""

import sqlite3
import pandas as pd
from config import DATABASE_URL, DB_PATH

# Importación condicional de psycopg2 para PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


def get_connection():
    """Devuelve una conexión a PostgreSQL (Neon) o a SQLite local."""
    if DATABASE_URL and HAS_PSYCOPG2:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_PATH)


def _es_postgres(conn) -> bool:
    """Detecta si la conexión activa pertenece a PostgreSQL."""
    return HAS_PSYCOPG2 and isinstance(conn, psycopg2.extensions.connection)


def init_db():
    """Crea la estructura de tablas e índices en la base de datos si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if _es_postgres(conn):
            # Tablas para PostgreSQL (Neon)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetria_diaria (
                    id SERIAL PRIMARY KEY,
                    fecha_registro TIMESTAMPTZ NOT NULL,
                    temperatura_c REAL,
                    precipitacion_mm REAL,
                    radiacion_solar_wm2 REAL,
                    rafaga_viento_kmh REAL,
                    humedad_relativa_pct REAL,
                    regla_aplicada VARCHAR(100),
                    orden_riego VARCHAR(100),
                    alerta BOOLEAN,
                    mensaje TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notificaciones (
                    id SERIAL PRIMARY KEY,
                    fecha_envio TIMESTAMPTZ NOT NULL,
                    canal VARCHAR(50),
                    tipo VARCHAR(50),
                    clave VARCHAR(100)
                );
            """)
        else:
            # Tablas para SQLite (Local)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetria_diaria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_registro TEXT NOT NULL,
                    temperatura_c REAL,
                    precipitacion_mm REAL,
                    radiacion_solar_wm2 REAL,
                    rafaga_viento_kmh REAL,
                    humedad_relativa_pct REAL,
                    regla_aplicada TEXT,
                    orden_riego TEXT,
                    alerta BOOLEAN,
                    mensaje TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notificaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_envio TEXT NOT NULL,
                    canal TEXT,
                    tipo TEXT,
                    clave TEXT
                );
            """)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def guardar_telemetria(datos: dict):
    """Persiste una lectura telemétrica en la base de datos activa."""
    conn = get_connection()
    cursor = conn.cursor()

    ahora = pd.Timestamp.now(tz="UTC").isoformat()
    postgres = _es_postgres(conn)
    placeholder = "%s" if postgres else "?"

    query = f"""
        INSERT INTO telemetria_diaria (
            fecha_registro, temperatura_c, precipitacion_mm, radiacion_solar_wm2,
            rafaga_viento_kmh, humedad_relativa_pct, regla_aplicada, orden_riego,
            alerta, mensaje
        ) VALUES ({', '.join([placeholder] * 10)});
    """
    valores = (
        ahora,
        datos.get("temperatura_c"),
        datos.get("precipitacion_mm"),
        datos.get("radiacion_solar_wm2"),
        datos.get("rafaga_viento_kmh"),
        datos.get("humedad_relativa_pct"),
        datos.get("regla"),
        datos.get("orden_riego"),
        bool(datos.get("alerta", False)),
        datos.get("mensaje"),
    )

    try:
        cursor.execute(query, valores)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def ultima_notificacion(canal: str, tipo: str) -> dict | None:
    """Recupera el último registro de notificación según canal y tipo."""
    conn = get_connection()
    postgres = _es_postgres(conn)
    placeholder = "%s" if postgres else "?"

    query = f"""
        SELECT fecha_envio, canal, tipo, clave
        FROM notificaciones
        WHERE canal = {placeholder} AND tipo = {placeholder}
        ORDER BY fecha_envio DESC
        LIMIT 1;
    """

    try:
        if postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, (canal, tipo))
            row = cursor.fetchone()
            return dict(row) if row else None
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (canal, tipo))
            row = cursor.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def registrar_notificacion(canal: str, tipo: str, clave: str):
    """Guarda un registro de envío de notificación en el historial."""
    conn = get_connection()
    cursor = conn.cursor()
    ahora = pd.Timestamp.now(tz="UTC").isoformat()
    postgres = _es_postgres(conn)
    placeholder = "%s" if postgres else "?"

    query = f"""
        INSERT INTO notificaciones (fecha_envio, canal, tipo, clave)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder});
    """

    try:
        cursor.execute(query, (ahora, canal, tipo, clave))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    init_db()
    print("Tablas verificadas e inicializadas en la base de datos.")