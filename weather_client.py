"""
weather_client.py
Módulo cliente para la lectura telemétrica de la estación meteorológica en Weather Underground.
La radiación solar y el UV se estiman con Open-Meteo (la estación no tiene esos sensores).
"""

import logging
import os
import threading
import time

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

WU_API_KEY = os.getenv("WU_API_KEY")
WU_STATION_ID = os.getenv("WU_STATION_ID")

# Coordenadas del vivero (ajústalas a las reales o defínelas en .env)
VIVERO_LAT = float(os.getenv("VIVERO_LAT", "9.30"))
VIVERO_LON = float(os.getenv("VIVERO_LON", "-75.40"))

# --- Caché de Open-Meteo (en memoria) ---
_cache_rad = {"valor": None, "ts": 0.0}
_lock = threading.Lock()
CACHE_TTL = 15 * 60          # Open-Meteo actualiza "current" cada ~15 min
CACHE_MAX_EDAD = 3 * 3600    # no usar un dato de más de 3 h como fallback


class LimiteOpenMeteo(RuntimeError):
    """Open-Meteo respondió 429: no tiene sentido reintentar de inmediato."""


def obtener_radiacion_open_meteo(
    lat: float = VIVERO_LAT, lon: float = VIVERO_LON, intentos: int = 2
) -> dict:
    """Estima radiación solar (W/m2) e índice UV con el modelo de Open-Meteo.

    - Usa caché de 15 min para no consultar la API en cada ejecución.
    - Ante un 429 no reintenta (empeoraría el bloqueo).
    - Si la API falla, devuelve el último valor bueno (máx. 3 h de antigüedad).
    - Lanza RuntimeError si no hay ningún dato válido.
    """
    with _lock:
        ahora = time.time()

        # 1) Caché fresca: no se llama a la API
        if _cache_rad["valor"] and ahora - _cache_rad["ts"] < CACHE_TTL:
            return dict(_cache_rad["valor"])

        ultimo_error = None
        for n in range(1, intentos + 1):
            try:
                r = requests.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "shortwave_radiation,uv_index",
                        "timezone": "America/Bogota",
                    },
                    timeout=10,
                )
                if r.status_code == 429:
                    raise LimiteOpenMeteo(f"429 de Open-Meteo: {r.text[:200]}")
                r.raise_for_status()
                c = r.json()["current"]

                radiacion = c.get("shortwave_radiation")
                if radiacion is None:
                    raise ValueError(f"Open-Meteo no devolvió shortwave_radiation: {c}")

                valor = {
                    "radiacion_solar_wm2": float(radiacion),
                    "uv_index": float(c.get("uv_index") or 0.0),
                }
                _cache_rad.update(valor=valor, ts=time.time())
                return dict(valor)
            except LimiteOpenMeteo as e:  # 429: no insistir
                ultimo_error = e
                break
            except Exception as e:
                ultimo_error = e
                if n < intentos:
                    time.sleep(2 * n)

        # 2) Fallback: último valor bueno si no es demasiado viejo
        if _cache_rad["valor"] and ahora - _cache_rad["ts"] < CACHE_MAX_EDAD:
            log.warning(
                "Open-Meteo falló (%s); uso el último valor en caché", ultimo_error
            )
            return dict(_cache_rad["valor"])

        raise RuntimeError(f"Open-Meteo falló: {ultimo_error}")


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

        datos = {
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

    # La SA7 no mide radiación: si la estación reporta 0, se usa Open-Meteo
    if datos["radiacion_solar_wm2"] == 0.0:
        try:
            datos.update(obtener_radiacion_open_meteo())
        except Exception as e:
            # Se conserva el 0.0 de la estación, pero queda registrado el motivo
            log.warning(
                "No se pudo estimar la radiación con Open-Meteo; se deja en 0: %s", e
            )

    return datos


def get_current_observation() -> dict:
    """Wrapper de compatibilidad para llamadas secundarias."""
    return obtener_datos_estacion()


if __name__ == "__main__":
    # Diagnóstico rápido: python weather_client.py
    logging.basicConfig(level=logging.INFO)
    print("Open-Meteo:", obtener_radiacion_open_meteo())
    print("Estación + radiación:", obtener_datos_estacion())