"""
weather_client.py
Capa de Percepción: ingesta de telemetría desde la API REST de
Weather Underground (estación Sainlogic SA7).
"""

import requests
from config import WU_API_KEY, WU_STATION_ID, WU_BASE_URL


def get_current_observation() -> dict:
    """
    Consulta la observación actual de la estación y devuelve
    únicamente las 5 variables telemétricas que necesita el proyecto.
    Lanza una excepción si la petición HTTP falla.
    """
    params = {
        "stationId": WU_STATION_ID,
        "format": "json",
        "units": "m",       # m = métrico (°C, mm, km/h)
        "apiKey": WU_API_KEY,
    }

    response = requests.get(WU_BASE_URL, params=params, timeout=10)
    response.raise_for_status()  # lanza error si el status no es 2xx
    data = response.json()

    observations = data.get("observations")
    if not observations:
        raise ValueError(
            "La API respondió sin observaciones. Verifica que la "
            "estación esté transmitiendo (revisa la app o WU Dashboard)."
        )

    obs = observations[0]
    metric = obs.get("metric", {})

    return {
        "timestamp_utc": obs.get("obsTimeUtc"),
        "precipitacion_mm": metric.get("precipTotal"),
        "temperatura_c": metric.get("temp"),
        "radiacion_solar_wm2": obs.get("solarRadiation"),
        "rafaga_viento_kmh": metric.get("windGust"),
        "humedad_relativa_pct": obs.get("humidity"),
    }


if __name__ == "__main__":
    # Prueba rápida: python weather_client.py
    datos = get_current_observation()
    print("Lectura actual de la estación Sainlogic SA7:")
    for clave, valor in datos.items():
        print(f"  {clave}: {valor}")