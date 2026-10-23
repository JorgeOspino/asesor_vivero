"""
main_diario.py
Orquestador del flujo periódico: ingesta -> reglas -> persistencia -> Telegram.
Se ejecuta cada 30 minutos con el Programador de tareas. Solo notifica cuando
aporta información nueva, para no saturar al jardinero.
"""

import pandas as pd
import requests

from rules_engine import procesar_observacion
from database import init_db, guardar_telemetria, ultima_notificacion, registrar_notificacion
from notifier import enviar_telegram, construir_mensaje_jardinero

ZONA = "America/Bogota"
REPETIR_ALERTA_HORAS = 2  # cada cuánto se recuerda una alerta que sigue activa


def motivo_para_notificar(fila: dict) -> str | None:
    """Devuelve el motivo por el que hay que avisar, o None si no hace falta."""
    ahora = pd.Timestamp.now(tz="UTC")
    clave = f"{fila['regla']}|{fila['orden_riego']}"
    ultima = ultima_notificacion("telegram", "instruccion_riego")

    if ultima is None:
        return "primera notificación"

    enviada = pd.to_datetime(ultima["fecha_envio"], utc=True, format="ISO8601")

    if enviada.tz_convert(ZONA).date() != ahora.tz_convert(ZONA).date():
        return "primera lectura del día"
    if ultima["clave"] != clave:
        return "cambió la condición de riego"
    if fila["alerta"] and (ahora - enviada) >= pd.Timedelta(hours=REPETIR_ALERTA_HORAS):
        return "recordatorio de alerta activa"
    return None


def ejecutar_flujo_diario():
    init_db()

    ahora_local = pd.Timestamp.now(tz=ZONA).strftime("%d/%m/%Y %H:%M:%S")

    try:
        df = procesar_observacion()
    except (ValueError, TimeoutError, requests.RequestException) as e:
        print(f"[{ahora_local}] No se obtuvieron datos válidos de la estación. No se guardó registro.\n   Detalle: {e}")
        return
    except Exception as e:
        print(f"[{ahora_local}] Error inesperado durante el flujo diario:\n   Detalle: {e}")
        return

    fila = df.iloc[0].to_dict()
    guardar_telemetria(fila)

    print(f"=== Flujo Ejecutado [{ahora_local}] ===")
    print(f"  Regla aplicada : {fila['regla']}")
    print(f"  Orden de riego : {fila['orden_riego']}")
    print("  Guardado en DB : OK")

    motivo = motivo_para_notificar(fila)
    if motivo is None:
        print("  Sin cambios: no se envía Telegram.")
        return

    print(f"  Enviando Telegram ({motivo})...")
    if enviar_telegram(construir_mensaje_jardinero(fila)):
        registrar_notificacion("telegram", "instruccion_riego", f"{fila['regla']}|{fila['orden_riego']}")


if __name__ == "__main__":
    ejecutar_flujo_diario()