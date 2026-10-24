"""
notifier.py
Módulo de notificaciones para el Vivero CECAR.
Construye y envía reportes telemétricos formateados a través de Telegram API.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def construir_mensaje_telemetria(telemetria: dict, decision: dict, hora: str) -> str:
    """
    Construye el texto plano del informe telemétrico sin emojis.
    """
    estado_riego = "ACTIVAR RIEGO" if decision.get("orden_riego") else "NO REGAR"

    temperatura = telemetria.get("temperatura_c", 0.0)
    humedad = telemetria.get("humedad_relativa_pct", 0.0)
    precipitacion = telemetria.get("precipitacion_mm", 0.0)
    viento = telemetria.get("rafaga_viento_kmh", 0.0)
    radiacion = telemetria.get("radiacion_solar_wm2", 0.0)
    regla = decision.get("regla_aplicada", "N/A")

    mensaje = (
        f"Informe Telemétrico - Vivero CECAR\n"
        f"Fecha: {hora}\n\n"
        f"Mediciones Telemétricas:\n"
        f"- Temperatura: {temperatura} °C\n"
        f"- Humedad: {humedad} %\n"
        f"- Precipitación: {precipitacion} mm\n"
        f"- Ráfaga de Viento: {viento} km/h\n"
        f"- Radiación Solar: {radiacion} W/m²\n\n"
        f"Decisión de Riego:\n"
        f"- Estado: {estado_riego}\n"
        f"- Regla Aplicada: {regla}\n"
    )

    return mensaje


def enviar_notificacion_telegram(mensaje: str) -> bool:
    """
    Envía un mensaje de texto al chat de Telegram configurado en las variables de entorno.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están configurados.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error al enviar la notificación a Telegram: {e}")
        return False


def notificar_evento(telemetria: dict, decision: dict, hora: str) -> bool:
    """
    Función orquestadora para construir y enviar la notificación.
    """
    mensaje = construir_mensaje_telemetria(telemetria, decision, hora)
    return enviar_notificacion_telegram(mensaje)


if __name__ == "__main__":
    # Prueba local simulada
    datos_prueba_telemetria = {
        "temperatura_c": 29.5,
        "humedad_relativa_pct": 75.0,
        "precipitacion_mm": 0.0,
        "rafaga_viento_kmh": 14.2,
        "radiacion_solar_wm2": 650.0,
    }

    datos_prueba_decision = {
        "orden_riego": True,
        "regla_aplicada": "Regla 3 - Nominal",
    }

    hora_prueba = "2026-10-24 10:15:00"

    print("--- Generando mensaje de prueba ---")
    texto = construir_mensaje_telemetria(datos_prueba_telemetria, datos_prueba_decision, hora_prueba)
    print(texto)