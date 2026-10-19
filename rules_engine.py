"""
rules_engine.py
Capa de Cerebro: Lógica Determinista Diaria.
Evalúa la observación de la estación contra la Matriz de 4 Reglas
usando pandas, y determina la orden de riego del día.
"""

import pandas as pd
from weather_client import get_current_observation

# --- Umbrales (ajusta aquí si tu proyecto define otros valores) ---
UMBRAL_VIENTO_PELIGRO_KMH = 50.0
UMBRAL_LLUVIA_SUPRESION_MM = 5.0
UMBRAL_TEMP_ESTRES_C = 33.0
UMBRAL_HUMEDAD_ESTRES_PCT = 40.0
UMBRAL_RADIACION_ESTRES_WM2 = 600.0


def evaluar_regla(row: pd.Series) -> pd.Series:
    """Aplica la matriz de 4 reglas a una fila de datos ambientales."""

    viento = row["rafaga_viento_kmh"] or 0
    lluvia = row["precipitacion_mm"] or 0
    temp = row["temperatura_c"] or 0
    humedad = row["humedad_relativa_pct"] or 100
    radiacion = row["radiacion_solar_wm2"] or 0

    if viento >= UMBRAL_VIENTO_PELIGRO_KMH:
        return pd.Series({
            "regla": "Regla 4 - Seguridad",
            "orden_riego": "SUSPENDIDO",
            "alerta": True,
            "mensaje": f"Ráfaga de {viento} km/h supera el umbral de seguridad. Riego suspendido, revisar mallas de polisombra."
        })

    if lluvia >= UMBRAL_LLUVIA_SUPRESION_MM:
        return pd.Series({
            "regla": "Regla 1 - Supresión",
            "orden_riego": "SUSPENDIDO",
            "alerta": False,
            "mensaje": f"Precipitación de {lluvia} mm cubre el requerimiento hídrico del día. Riego suspendido."
        })

    if (temp >= UMBRAL_TEMP_ESTRES_C
            and humedad <= UMBRAL_HUMEDAD_ESTRES_PCT
            and radiacion >= UMBRAL_RADIACION_ESTRES_WM2):
        return pd.Series({
            "regla": "Regla 2 - Estrés Térmico",
            "orden_riego": "PROFUNDO",
            "alerta": False,
            "mensaje": f"Alta evapotranspiración ({temp}°C, {humedad}% HR, {radiacion} W/m²). Riego profundo requerido."
        })

    return pd.Series({
        "regla": "Regla 3 - Nominal",
        "orden_riego": "ESTANDAR",
        "alerta": False,
        "mensaje": "Condiciones normales. Riego estándar."
    })


def procesar_observacion() -> pd.DataFrame:
    """Trae la observación actual y le aplica la matriz de reglas."""
    obs = get_current_observation()
    df = pd.DataFrame([obs])
    resultado = df.apply(evaluar_regla, axis=1)
    return pd.concat([df, resultado], axis=1)


if __name__ == "__main__":
    df = procesar_observacion()
    fila = df.iloc[0]
    print("=== Decisión de Riego del Día ===")
    print(f"  Regla aplicada : {fila['regla']}")
    print(f"  Orden de riego : {fila['orden_riego']}")
    print(f"  Alerta         : {fila['alerta']}")
    print(f"  Mensaje        : {fila['mensaje']}")