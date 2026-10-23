"""
notifier.py
Capa de Acción:
- Telegram: instrucciones de riego y alertas para el jardinero.
- Correo (Gmail SMTP): reporte diario.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import requests

from config import (
    EMAIL_REMITENTE,
    EMAIL_APP_PASSWORD,
    EMAIL_DESTINATARIO,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_IDS,
)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
ZONA = "America/Bogota"

# Qué debe hacer el jardinero según la orden de riego.
# Ajusta estos textos a la práctica real del vivero (por ejemplo, minutos por zona).
INSTRUCCIONES_RIEGO = {
    "ESTANDAR": (
        "RIEGO ESTÁNDAR",
        "Aplicar el riego habitual del vivero.",
    ),
    "PROFUNDO": (
        "RIEGO PROFUNDO",
        "Aplicar un riego más abundante que el habitual (mayor tiempo o volumen), "
        "preferiblemente en las horas de menor sol.",
    ),
    "SUSPENDIDO": (
        "NO REGAR",
        "Suspender el riego hasta nuevo aviso.",
    ),
}


def _valor(v, unidad: str, decimales: int = 1) -> str:
    if v is None or pd.isna(v):
        return "--"
    return f"{v:.{decimales}f} {unidad}"


def construir_mensaje_jardinero(fila: dict) -> str:
    """Arma el mensaje de Telegram con la instrucción de riego y las condiciones actuales."""
    titulo_riego, indicacion = INSTRUCCIONES_RIEGO.get(
        fila["orden_riego"], (str(fila["orden_riego"]), "Consultar con el administrador.")
    )
    es_alerta = bool(fila.get("alerta"))
    encabezado = "ALERTA - VIVERO CECAR" if es_alerta else "INSTRUCCIÓN DE RIEGO - VIVERO CECAR"

    ts = fila.get("timestamp_utc")
    hora = pd.to_datetime(ts, utc=True).tz_convert(ZONA) if ts else pd.Timestamp.now(tz=ZONA)

    lineas = [
        encabezado,
        "",
        f"Riego a aplicar: {titulo_riego}",
        f"Qué hacer: {indicacion}",
    ]
    if es_alerta:
        lineas.append("Acción adicional: revisar y asegurar la polisombra y las estructuras del vivero.")
    lineas += [
        "",
        f"Motivo: {fila['mensaje']}",
        "",
        "Condiciones actuales:",
        f"- Temperatura: {_valor(fila.get('temperatura_c'), 'C')}",
        f"- Humedad: {_valor(fila.get('humedad_relativa_pct'), '%', 0)}",
        f"- Lluvia acumulada: {_valor(fila.get('precipitacion_mm'), 'mm')}",
        f"- Ráfaga de viento: {_valor(fila.get('rafaga_viento_kmh'), 'km/h')}",
        f"- Radiación solar: {_valor(fila.get('radiacion_solar_wm2'), 'W/m2', 0)}",
        "",
        f"Lectura: {hora.strftime('%d/%m/%Y %H:%M')}",
    ]
    return "\n".join(lineas)


def _chat_ids() -> list[str]:
    return [c.strip() for c in (TELEGRAM_CHAT_IDS or "").split(",") if c.strip()]


def enviar_telegram(mensaje: str) -> bool:
    """Envía el mensaje a todos los chats configurados. True si llegó al menos a uno."""
    chats = _chat_ids()
    if not TELEGRAM_BOT_TOKEN or not chats:
        print("  Credenciales de Telegram incompletas en .env — no se envió el mensaje.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    enviados = 0
    for chat_id in chats:
        try:
            r = requests.post(url, json={"chat_id": chat_id, "text": mensaje}, timeout=20)
            if r.ok:
                enviados += 1
            else:
                print(f"  Error de Telegram en el chat {chat_id}: {r.text}")
        except requests.RequestException as e:
            print(f"  No se pudo contactar a Telegram para el chat {chat_id}: {e}")

    if enviados:
        print(f"  Telegram enviado a {enviados} de {len(chats)} chats.")
    return enviados > 0


def enviar_correo(asunto: str, mensaje: str) -> bool:
    """Envía un correo por Gmail. True si se envió, False si faltan credenciales o falla."""
    if not all([EMAIL_REMITENTE, EMAIL_APP_PASSWORD, EMAIL_DESTINATARIO]):
        print("  Credenciales de correo incompletas en .env — no se envió el correo.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_REMITENTE
        msg["To"] = EMAIL_DESTINATARIO
        msg["Subject"] = asunto
        msg.attach(MIMEText(mensaje, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_REMITENTE, EMAIL_APP_PASSWORD)
            server.send_message(msg)

        print(f"  Correo enviado a {EMAIL_DESTINATARIO}")
        return True
    except Exception as e:
        print(f"  Error enviando correo: {e}")
        return False


if __name__ == "__main__":
    # Prueba rápida: python notifier.py
    print("Probando Telegram...")
    enviar_telegram("Prueba del Asesor Inteligente del Vivero CECAR. Si lees esto, Telegram funciona.")
    print("Probando correo...")
    enviar_correo(
        "Prueba del Asesor Inteligente del Vivero CECAR",
        "Si recibes este correo, el envío por Gmail funciona correctamente.",
    )