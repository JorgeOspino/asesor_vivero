"""
main_diario.py
Script principal de ingesta de telemetría y evaluación de reglas de riego.
Garantiza el registro de fechas en horario oficial de Colombia (UTC-5).
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo
import psycopg2
from dotenv import load_dotenv
from rules_engine import evaluar_reglas_riego
from weather_client import obtener_datos_estacion

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
WU_API_KEY = os.getenv("WU_API_KEY")
WU_STATION_ID = os.getenv("WU_STATION_ID")


def guardar_en_neon(telemetria: dict, decision: dict):
    """Inserta la lectura telemétrica y el resultado del motor de reglas en Neon."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL no configurada en las variables de entorno.")

    # Fecha y hora exacta fijada en la zona horaria de Colombia
    fecha_colombia = datetime.now(ZoneInfo("America/Bogota"))

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    query = """
        INSERT INTO telemetria_diaria (
            fecha_registro,
            temperatura_c,
            precipitacion_mm,
            radiacion_solar_wm2,
            rafaga_viento_kmh,
            humedad_relativa_pct,
            orden_riego,
            regla_aplicada,
            mensaje
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    valores = (
        fecha_colombia,
        telemetria["temperatura_c"],
        telemetria["precipitacion_mm"],
        telemetria["radiacion_solar_wm2"],
        telemetria["rafaga_viento_kmh"],
        telemetria["humedad_relativa_pct"],
        decision["orden_riego"],
        decision["regla_aplicada"],
        decision["mensaje"],
    )

    cursor.execute(query, valores)
    conn.commit()
    cursor.close()
    conn.close()


def ejecutar_flujo_diario():
    """Ejecuta el ciclo telemétrico completo."""
    datos_clima = obtener_datos_estacion(WU_STATION_ID, WU_API_KEY)
    decision = evaluar_reglas_riego(datos_clima)
    guardar_en_neon(datos_clima, decision)
    return decision


if __name__ == "__main__":
    resultado = ejecutar_flujo_diario()
    print(f"Flujo ejecutado correctamente: {resultado}")