"""
migrar_a_neon.py
Script de un solo uso para copiar el historial telemétrico de SQLite local a Neon.
"""

import sqlite3
import psycopg2
import pandas as pd
from config import DATABASE_URL, DB_PATH


def migrar():
    if not DATABASE_URL:
        print("Error: DATABASE_URL no está configurada en tu archivo .env.")
        return

    print("1. Leyendo datos de la base de datos local (SQLite)...")
    try:
        conn_local = sqlite3.connect(DB_PATH)
        df_telemetria = pd.read_sql_query("SELECT * FROM telemetria_diaria", conn_local)
        df_notificaciones = pd.read_sql_query("SELECT * FROM notificaciones", conn_local)
        conn_local.close()
    except Exception as e:
        print(f"Error al leer SQLite local: {e}")
        return

    print(f"   - Registros telemétricos encontrados: {len(df_telemetria)}")
    print(f"   - Notificaciones encontradas: {len(df_notificaciones)}")

    if df_telemetria.empty and df_notificaciones.empty:
        print("No hay datos locales para migrar.")
        return

    print("2. Conectando e insertando en Neon (PostgreSQL)...")
    try:
        conn_neon = psycopg2.connect(DATABASE_URL)
        cursor = conn_neon.cursor()

        # Insertar registros de telemetría
        if not df_telemetria.empty:
            for _, row in df_telemetria.iterrows():
                cursor.execute("""
                    INSERT INTO telemetria_diaria (
                        fecha_registro, temperatura_c, precipitacion_mm, radiacion_solar_wm2,
                        rafaga_viento_kmh, humedad_relativa_pct, regla_aplicada, orden_riego,
                        alerta, mensaje
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    row["fecha_registro"], row["temperatura_c"], row["precipitacion_mm"],
                    row["radiacion_solar_wm2"], row["rafaga_viento_kmh"], row["humedad_relativa_pct"],
                    row["regla_aplicada"], row["orden_riego"], bool(row["alerta"]), row["mensaje"]
                ))

        # Insertar registros de notificaciones
        if not df_notificaciones.empty:
            for _, row in df_notificaciones.iterrows():
                cursor.execute("""
                    INSERT INTO notificaciones (fecha_envio, canal, tipo, clave)
                    VALUES (%s, %s, %s, %s)
                """, (row["fecha_envio"], row["canal"], row["tipo"], row["clave"]))

        conn_neon.commit()
        print("¡Migración completada exitosamente en Neon!")

    except Exception as e:
        if 'conn_neon' in locals():
            conn_neon.rollback()
        print(f"Error durante la inserción en Neon: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn_neon' in locals():
            conn_neon.close()


if __name__ == "__main__":
    migrar()