"""
weather_client.py
Módulo cliente para la lectura telemétrica de la estación meteorológica en Weather Underground.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

WU_API_KEY = os.getenv("WU_API_KEY")
WU_STATION_ID = os.getenv("WU_STATION_ID")


def obtener_datos_estacion(
    station_id: str = None, api_key: str = None
) -> dict:
    """Consulta la API de Weather Underground y retorna las variables ambientales estructuradas."""
    s_id = station_id or WU_STATION_ID
    a_key = api_key or WU_API_KEY

    if not s_id or not a_key:
        raise ValueError(
            "Faltan credenciales WU_STATION_ID o WU_API_KEY en las variables de entorno."
        )

    url = "https://api.weather.com/v2/pws/observations/current"
    params = {
        "stationId": s_id,
        "format": "json",
        "units": "m",
        "apiKey": a_key,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        obs = data["observations"][0]
        metric = obs.get("metric", {})

        return {
            "temperatura_c": float(metric.get("temp") or 0.0),
            "precipitacion_mm": float(metric.get("precipTotal") or 0.0),
            "radiacion_solar_wm2": float(obs.get("solarRadiation") or 0.0),
            "rafaga_viento_kmh": float(metric.get("windGust") or 0.0),
            "direccion_viento_grados": int(obs.get("winddir") or 0),
            "humedad_relativa_pct": float(obs.get("humidity") or 0.0),
        }
    except Exception as e:
        raise RuntimeError(
            f"Error al obtener datos telemétricos de la estación: {e}"
        )


def get_current_observation() -> dict:
    """Wrapper de compatibilidad para llamadas secundarias."""
    return obtener_datos_estacion()