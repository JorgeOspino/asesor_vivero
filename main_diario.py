"""
main_diario.py
Orquestador del flujo diario: ingesta -> reglas -> persistencia -> notificación.
Este es el script que se ejecutaría una vez al día (ej. con un cron job).
"""

from rules_engine import procesar_observacion
from database import init_db, guardar_telemetria
from notifier import enviar_correo


def ejecutar_flujo_diario():
    init_db()  # asegura que las tablas existan
    df = procesar_observacion()
    fila = df.iloc[0].to_dict()

    guardar_telemetria(fila)

    print("=== Flujo Diario Ejecutado ===")
    print(f"  Regla aplicada : {fila['regla']}")
    print(f"  Orden de riego : {fila['orden_riego']}")
    print(f"  Guardado en DB : OK")

    if fila["alerta"]:
        print("  ⚠️  ALERTA ACTIVA — enviando notificación por correo...")
        mensaje = (
            f"Alerta del Asesor Inteligente - Vivero CECAR\n\n"
            f"{fila['mensaje']}\n\n"
            f"Regla aplicada: {fila['regla']}\n"
            f"Orden de riego: {fila['orden_riego']}"
        )
        enviar_correo("🚨 Alerta Vivero CECAR", mensaje)


if __name__ == "__main__":
    ejecutar_flujo_diario()