"""
api.py
Endpoint HTTP para invocar el flujo telemétrico del Vivero CECAR desde n8n.
"""

import os
from fastapi import FastAPI, Header, HTTPException
from main_diario import ejecutar_flujo_diario

app = FastAPI(title="Vivero CECAR Telemetry API")

# Clave de seguridad para evitar invocaciones no autorizadas
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "cecar_vivero_secret_key_2026")


@app.get("/")
def home():
    return {"status": "online", "system": "Vivero CECAR Smart Irrigation"}


@app.post("/ejecutar-flujo")
def trigger_flujo(authorization: str = Header(None)):
    """Endpoint que activa la ingesta de datos y evaluación de reglas."""
    token_esperado = f"Bearer {WEBHOOK_SECRET}"

    if authorization != token_esperado:
        raise HTTPException(status_code=401, detail="No autorizado.")

    try:
        ejecutar_flujo_diario()
        return {
            "status": "success",
            "message": "Flujo telemétrico ejecutado e ingresado a Neon correctamente.",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error durante la ejecución: {str(e)}"
        )