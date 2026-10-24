"""
api.py
Servicio API REST en FastAPI para el Vivero CECAR.
Recibe peticiones HTTP (webhooks) desde n8n, ejecuta la ingesta telemétrica
y persiste los datos en Neon ajustando la zona horaria a America/Bogota (UTC-5).
"""

import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
import psycopg2
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel
from rules_engine import evaluar_reglas_riego
from weather_client import obtener_datos_estacion

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WU_API_KEY = os.getenv("WU_API_KEY")
WU_STATION_ID = os.getenv("WU_STATION_ID")

app = FastAPI(
    title="API Telemétrica Vivero CECAR",
    description="Backend de automatización para monitoreo de riego agrícola",
    version="1.0.0",
)


def verificar_token(authorization: Optional[str] = Header(None)):
    """Verifica el token de autenticación Bearer en la cabecera HTTP."""
    if not API_TOKEN:
        return True
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabecera Authorization no proporcionada.",
        )
    token = authorization.replace("Bearer ", "").strip()
    if token != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token de autenticación inválido.",
        )
    return True


def guardar_en_neon(telemetria: dict, decision: dict):
    """Guarda la lectura e informe en Neon con la hora oficial de Colombia."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL no configurada.")

    # Generación explícita de hora en Colombia (UTC-5)
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


@app.get("/")
def estado_api():
    """Endpoint de comprobación de estado."""
    return {"status": "ok", "servicio": "API Telemétrica CECAR activa"}


@app.post("/ejecutar-flujo")
def ejecutar_flujo_webhook(autorizado: bool = Depends(verificar_token)):
    """Endpoint consumido por n8n para desencadenar la lectura e inserción telemétrica."""
    try:
        telemetria = obtener_datos_estacion(WU_STATION_ID, WU_API_KEY)
        decision = evaluar_reglas_riego(telemetria)
        guardar_en_neon(telemetria, decision)

        return {
            "status": "success",
            "message": "Flujo telemétrico ejecutado e ingresado a Neon correctamente.",
            "hora_colombia": datetime.now(
                ZoneInfo("America/Bogota")
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "datos_registrados": {
                "temperatura_c": telemetria["temperatura_c"],
                "orden_riego": decision["orden_riego"],
                "regla_aplicada": decision["regla_aplicada"],
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el procesamiento del flujo: {str(e)}",
        )