"""
rules_engine.py
Capa de Cerebro: Lógica Determinista Diaria.
Evalúa las variables telemétricas de la estación contra la Matriz de 4 Reglas
y determina la orden de riego para el Vivero CECAR.
"""

import pandas as pd

# Umbrales configurables
UMBRAL_VIENTO_PELIGRO_KMH = 50.0
UMBRAL_LLUVIA_SUPRESION_MM = 5.0
UMBRAL_TEMP_ESTRES_C = 33.0
UMBRAL_HUMEDAD_ESTRES_PCT = 40.0
UMBRAL_RADIACION_ESTRES_WM2 = 600.0


def evaluar_reglas_riego(telemetria: dict) -> dict:
    """
    Función principal consumida por api.py.
    Recibe un diccionario con la lectura actual y retorna la decisión.
    """
    viento = telemetria.get("rafaga_viento_kmh") or 0.0
    lluvia = telemetria.get("precipitacion_mm") or 0.0
    temp = telemetria.get("temperatura_c") or 0.0
    humedad = (
        telemetria.get("humedad_relativa_pct")
        if telemetria.get("humedad_relativa_pct") is not None
        else 100.0
    )
    radiacion = telemetria.get("radiacion_solar_wm2") or 0.0

    # Regla 4 - Seguridad
    if viento >= UMBRAL_VIENTO_PELIGRO_KMH:
        return {
            "orden_riego": False,
            "regla_aplicada": "Regla 4 - Seguridad",
            "alerta": True,
            "tipo_riego": "SUSPENDIDO",
            "mensaje": f"Ráfaga de {viento} km/h supera el umbral de seguridad. Riego suspendido, revisar mallas de polisombra.",
        }

    # Regla 1 - Supresión
    if lluvia >= UMBRAL_LLUVIA_SUPRESION_MM:
        return {
            "orden_riego": False,
            "regla_aplicada": "Regla 1 - Supresión",
            "alerta": False,
            "tipo_riego": "SUSPENDIDO",
            "mensaje": f"Precipitación de {lluvia} mm cubre el requerimiento hídrico del día. Riego suspendido.",
        }

    # Regla 2 - Estrés Térmico
    if (
        temp >= UMBRAL_TEMP_ESTRES_C
        and humedad <= UMBRAL_HUMEDAD_ESTRES_PCT
        and radiacion >= UMBRAL_RADIACION_ESTRES_WM2
    ):
        return {
            "orden_riego": True,
            "regla_aplicada": "Regla 2 - Estrés Térmico",
            "alerta": False,
            "tipo_riego": "PROFUNDO",
            "mensaje": f"Alta evapotranspiración ({temp}°C, {humedad}% HR, {radiacion} W/m²). Riego profundo requerido.",
        }

    # Regla 3 - Nominal
    return {
        "orden_riego": True,
        "regla_aplicada": "Regla 3 - Nominal",
        "alerta": False,
        "tipo_riego": "ESTANDAR",
        "mensaje": "Condiciones normales. Riego estándar.",
    }


def evaluar_regla(row: pd.Series) -> pd.Series:
    """Wrapper de compatibilidad para evaluación con estructuras Pandas."""
    res = evaluar_reglas_riego(row.to_dict())
    return pd.Series(
        {
            "regla": res["regla_aplicada"],
            "regla_aplicada": res["regla_aplicada"],
            "orden_riego": res["tipo_riego"],
            "riego_activo": res["orden_riego"],
            "alerta": res["alerta"],
            "mensaje": res["mensaje"],
        }
    )