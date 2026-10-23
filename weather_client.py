"""
weather_client.py
Capa de Percepción: ingesta de telemetría desde la API REST de
Weather Underground (estación Sainlogic SA7).
"""

import pandas as pd
import requests
from config import WU_API_KEY, WU_STATION_ID, WU_BASE_URL


def get_current_observation(
    timeout: tuple[float, float] | float = (3.0, 5.0),
    max_antiguedad_minutos: int = 45,
) -> dict:
    """
    Consulta la observación actual de la estación y devuelve las 5 variables
    telemétricas. Lanza ValueError o TimeoutError si la estación no entregó 
    datos válidos, la lectura está obsoleta o la API no responde a tiempo.

    :param timeout: Tupla (tiempo_conexion, tiempo_lectura) o float en segundos.
    :param max_antiguedad_minutos: Límite de minutos para considerar la lectura como actual.
    """
    params = {
        "stationId": WU_STATION_ID,
        "format": "json",
        "units": "m",       # m = métrico (°C, mm, km/h)
        "apiKey": WU_API_KEY,
    }

    try:
        response = requests.get(WU_BASE_URL, params=params, timeout=timeout)
    except requests.exceptions.Timeout as e:
        raise TimeoutError("Tiempo de espera agotado al consultar Weather Underground (Timeout).") from e
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error de red al conectar con Weather Underground: {e}") from e

    if response.status_code == 204:
        raise ValueError("La API no tiene datos recientes de la estación (HTTP 204).")

    response.raise_for_status()

    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError as e:
        raise ValueError("La respuesta de la API no tiene un formato JSON válido.") from e

    observations = payload.get("observations")
    if not observations:
        raise ValueError(
            "La API respondió sin observaciones. Verifica que la estación "
            "esté transmitiendo (revisa la app o WU Dashboard)."
        )

    obs = observations[0]
    metric = obs.get("metric") or {}

    datos = {
        "timestamp_utc": obs.get("obsTimeUtc"),
        "precipitacion_mm": metric.get("precipTotal"),
        "temperatura_c": metric.get("temp"),
        "radiacion_solar_wm2": obs.get("solarRadiation"),
        "rafaga_viento_kmh": metric.get("windGust"),
        "humedad_relativa_pct": obs.get("humidity"),
    }

    # Sin temperatura o humedad no hay lectura confiable
    if datos["temperatura_c"] is None or datos["humedad_relativa_pct"] is None:
        raise ValueError(f"La estación devolvió una lectura incompleta: {obs}")

    # Validación de frescura del dato (comprobar si la estación perdió Wi-Fi)
    if datos["timestamp_utc"]:
        try:
            ts_lectura = pd.to_datetime(datos["timestamp_utc"], utc=True)
            ahora_utc = pd.Timestamp.now(tz="UTC")
            minutos_antiguedad = (ahora_utc - ts_lectura).total_seconds() / 60

            if minutos_antiguedad > max_antiguedad_minutos:
                raise ValueError(
                    f"La estación está fuera de línea. La última lectura registrada en la nube "
                    f"tiene {int(minutos_antiguedad)} minutos de antigüedad."
                )
        except ValueError as e:
            raise e
        except Exception:
            pass  # Si ocurre un error inesperado al parsear la fecha, no bloquea el flujo principal

    return datos


if __name__ == "__main__":
    try:
        datos = get_current_observation()
        print("Lectura actual de la estación Sainlogic SA7:")
        for clave, valor in datos.items():
            print(f"  {clave}: {valor}")
    except Exception as e:
        print(f"Error al obtener lectura: {e}")