"""
database.py
Capa de Memoria: persistencia en SQLite.
Crea y gestiona las tablas telemetria_diaria y boletines_semanales.
"""

import sqlite3
from datetime import datetime, timezone
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Crea las tablas si no existen. Seguro de llamar varias veces."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS telemetria_diaria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_registro TEXT NOT NULL,
            timestamp_utc TEXT,
            precipitacion_mm REAL,
            temperatura_c REAL,
            radiacion_solar_wm2 REAL,
            rafaga_viento_kmh REAL,
            humedad_relativa_pct REAL,
            regla_aplicada TEXT,
            orden_riego TEXT,
            alerta INTEGER,
            mensaje TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS boletines_semanales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_generacion TEXT NOT NULL,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            contenido TEXT
        )
    """)

    conn.commit()
    conn.close()


def guardar_telemetria(fila: dict) -> None:
    """Inserta una fila ya evaluada (salida de rules_engine) en telemetria_diaria."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO telemetria_diaria (
            fecha_registro, timestamp_utc, precipitacion_mm, temperatura_c,
            radiacion_solar_wm2, rafaga_viento_kmh, humedad_relativa_pct,
            regla_aplicada, orden_riego, alerta, mensaje
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        fila.get("timestamp_utc"),
        fila.get("precipitacion_mm"),
        fila.get("temperatura_c"),
        fila.get("radiacion_solar_wm2"),
        fila.get("rafaga_viento_kmh"),
        fila.get("humedad_relativa_pct"),
        fila.get("regla"),
        fila.get("orden_riego"),
        int(fila.get("alerta", False)),
        fila.get("mensaje"),
    ))
    conn.commit()
    conn.close()


def guardar_boletin(fecha_inicio: str, fecha_fin: str, contenido: str) -> None:
    """Inserta un boletín ejecutivo generado por el agente de IA semanal."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO boletines_semanales (fecha_generacion, fecha_inicio, fecha_fin, contenido)
        VALUES (?, ?, ?, ?)
    """, (datetime.now(timezone.utc).isoformat(), fecha_inicio, fecha_fin, contenido))
    conn.commit()
    conn.close()


def obtener_ultimos_dias(n: int = 7):
    """Trae los últimos n registros de telemetria_diaria (para el boletín semanal)."""
    import pandas as pd
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM telemetria_diaria ORDER BY fecha_registro DESC LIMIT ?",
        conn, params=(n,)
    )
    conn.close()
    return df


if __name__ == "__main__":
    init_db()
    print(f"Base de datos inicializada en: {DB_PATH}")