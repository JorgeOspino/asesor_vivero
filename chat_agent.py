"""
chat_agent.py
Asistente conversacional del Vivero CECAR (Groq).
Consulta la estación en vivo (Weather Underground) en cada pregunta y usa
la base de datos solo como historial.
"""

import pandas as pd
import requests
from groq import Groq
from config import GROQ_API_KEY
from database import get_connection
from weather_client import get_current_observation
from rules_engine import (
    evaluar_regla,
    UMBRAL_VIENTO_PELIGRO_KMH,
    UMBRAL_LLUVIA_SUPRESION_MM,
    UMBRAL_TEMP_ESTRES_C,
    UMBRAL_HUMEDAD_ESTRES_PCT,
    UMBRAL_RADIACION_ESTRES_WM2,
)


# Lista de modelos activos en la API de Groq
# Lista de modelos de producción activos y vigentes en Groq
MODELOS_FALLBACK = [
    "llama-3.1-8b-instant",     # Estable, ultra rápido y con mayor cuota en el plan gratuito
    "openai/gpt-oss-120b",      # Modelo de alta capacidad para respuestas complejas
    "openai/gpt-oss-20b",       # Modelo rápido y balanceado
    "llama-3.3-70b-versatile",  # Modelo de alta precisión
]
MAX_MENSAJES_HISTORIAL = 10
ZONA = "America/Bogota"
HORAS_VIVO_VIEJO = 1       # Si la estación reporta algo más viejo, se advierte
HORAS_GUARDADO_VIEJO = 3   # Para la lectura guardada usada como respaldo


def _antiguedad(ts: pd.Timestamp, ahora: pd.Timestamp) -> tuple[float, str]:
    horas = (ahora - ts).total_seconds() / 3600
    if horas < 1:
        return horas, f"hace {max(int(horas * 60), 0)} minutos"
    return horas, f"hace {horas:.1f} horas"


def _bloque_lectura(titulo: str, ts: pd.Timestamp, ahora: pd.Timestamp, d: dict,
                    limite_horas: float) -> str:
    horas, texto = _antiguedad(ts, ahora)
    bloque = (
        f"{titulo}\n"
        f"- Fecha y hora: {ts.strftime('%d/%m/%Y %H:%M')} (Bogotá), {texto}\n"
        f"- Temperatura: {d['temperatura_c']} C\n"
        f"- Precipitación acumulada: {d['precipitacion_mm']} mm\n"
        f"- Humedad relativa: {d['humedad_relativa_pct']} %\n"
        f"- Ráfaga de viento: {d['rafaga_viento_kmh']} km/h\n"
        f"- Radiación solar: {d['radiacion_solar_wm2']} W/m2\n"
        f"- Regla aplicada: {d['regla']}\n"
        f"- Orden de riego: {d['orden_riego']}\n"
        f"- Mensaje: {d['mensaje']}"
    )
    if horas > limite_horas:
        bloque += (
            f"\nADVERTENCIA: esta lectura tiene {horas:.1f} horas de antigüedad y puede no "
            f"reflejar las condiciones actuales. Menciónalo al responder."
        )
    return bloque


def _lectura_en_vivo(ahora: pd.Timestamp) -> tuple[str | None, str | None]:
    """Consulta la estación ahora mismo. Devuelve (bloque_texto, error)."""
    try:
        obs = get_current_observation()
    except (ValueError, TimeoutError, requests.RequestException) as e:
        return None, str(e)

    evaluacion = evaluar_regla(pd.Series(obs))
    datos = {**obs, **evaluacion.to_dict()}

    ts_utc = obs.get("timestamp_utc")
    ts = pd.to_datetime(ts_utc, utc=True).tz_convert(ZONA) if ts_utc else ahora

    bloque = _bloque_lectura(
        "LECTURA EN VIVO (consultada a la estación en este momento; usa ESTA para "
        "preguntas sobre hoy, ahora o el estado actual):",
        ts, ahora, datos, HORAS_VIVO_VIEJO,
    )
    return bloque, None


def _cargar_guardadas() -> pd.DataFrame:
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT fecha_registro, temperatura_c, precipitacion_mm, humedad_relativa_pct, "
            "rafaga_viento_kmh, radiacion_solar_wm2, regla_aplicada AS regla, orden_riego, mensaje "
            "FROM telemetria_diaria WHERE temperatura_c IS NOT NULL "
            "ORDER BY fecha_registro DESC LIMIT 20",
            conn,
        )
    finally:
        conn.close()

    if not df.empty:
        df["fecha_registro"] = pd.to_datetime(df["fecha_registro"], utc=True).dt.tz_convert(ZONA)
        df = df.sort_values("fecha_registro", ascending=False).reset_index(drop=True)
    return df


def _contexto_datos() -> str:
    ahora = pd.Timestamp.now(tz=ZONA)
    partes = [f"FECHA Y HORA ACTUAL (Bogotá): {ahora.strftime('%d/%m/%Y %H:%M')}"]

    guardadas = _cargar_guardadas()
    vivo, error = _lectura_en_vivo(ahora)

    if vivo:
        partes.append(vivo)
        historial = guardadas
    elif not guardadas.empty:
        partes.append(
            f"AVISO: no se pudo consultar la estación en vivo ({error}). "
            f"Se usa la última lectura guardada; indícalo claramente al responder."
        )
        u = guardadas.iloc[0]
        partes.append(_bloque_lectura(
            "ÚLTIMA LECTURA GUARDADA (no es en vivo):",
            u["fecha_registro"], ahora, u.to_dict(), HORAS_GUARDADO_VIEJO,
        ))
        historial = guardadas.iloc[1:]
    else:
        partes.append(f"No se pudo consultar la estación ({error}) y no hay lecturas guardadas.")
        return "\n\n".join(partes)

    if not historial.empty:
        h = historial.copy()
        h["fecha_registro"] = h["fecha_registro"].dt.strftime("%d/%m/%Y %H:%M")
        partes.append(
            "HISTORIAL DE LECTURAS GUARDADAS (solo para tendencias; de la más reciente a la "
            "más antigua, hora de Bogotá):\n" + h.drop(columns=["mensaje"]).to_string(index=False)
        )
    return "\n\n".join(partes)


def _prompt_sistema() -> str:
    return f"""Eres el asistente del Asesor Inteligente del Vivero CECAR. Ayudas al
administrador y al jardinero a entender las condiciones climáticas y las
decisiones de riego. Responde siempre en español, de forma clara, breve y práctica.

REGLAS DEL SISTEMA (en orden de prioridad):
1. Regla 4 - Seguridad: ráfaga de viento >= {UMBRAL_VIENTO_PELIGRO_KMH} km/h -> riego suspendido y revisar la polisombra.
2. Regla 1 - Supresión: precipitación acumulada >= {UMBRAL_LLUVIA_SUPRESION_MM} mm -> riego suspendido.
3. Regla 2 - Estrés térmico: temperatura >= {UMBRAL_TEMP_ESTRES_C} C, humedad <= {UMBRAL_HUMEDAD_ESTRES_PCT}% y radiación >= {UMBRAL_RADIACION_ESTRES_WM2} W/m2 -> riego profundo.
4. Regla 3 - Nominal: cualquier otro caso -> riego estándar.

DATOS DE LA ESTACIÓN:
{_contexto_datos()}

Instrucciones:
- Para preguntas sobre hoy, ahora o el estado actual, usa la LECTURA EN VIVO y cita su fecha y hora.
- Usa el historial solo para hablar de tendencias o de días anteriores.
- No inventes cifras ni lecturas que no estén arriba.
- Si no tienes información suficiente para responder, dilo con claridad.
- Para recomendaciones agronómicas generales puedes usar tu conocimiento, pero aclara que son orientativas.
- No uses emojis."""


def responder(historial: list[dict]) -> str:
    """
    Recibe el historial [{'role': 'user'|'assistant', 'content': str}] 
    e intenta generar la respuesta iterando sobre una lista de modelos 
    hasta encontrar uno disponible.
    """
    if not GROQ_API_KEY:
        return "Falta GROQ_API_KEY en el archivo config.py o .env."

    mensajes = [{"role": "system", "content": _prompt_sistema()}]
    mensajes += historial[-MAX_MENSAJES_HISTORIAL:]

    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        return f"Error de inicialización en el cliente de Groq: {e}"

    errores = []

    # Recorre la lista de modelos en orden de prioridad
    for modelo in MODELOS_FALLBACK:
        try:
            respuesta = client.chat.completions.create(
                model=modelo,
                messages=mensajes,
                max_tokens=1500,
                temperature=0.2,
            )
            # Retorna la respuesta inmediatamente al tener éxito
            return respuesta.choices[0].message.content
        except Exception as e:
            # Si falla por cuota (429), modelo inexistente (404) u otro motivo,
            # guarda el detalle e intenta con el siguiente modelo de la lista
            errores.append(f"- {modelo}: {e}")

    # Si todos los modelos fallan, reporta el fallo acumulado
    return (
        "No fue posible conectar con ningún modelo de IA disponible. "
        "Detalle de intentos:\n" + "\n".join(errores)
    )