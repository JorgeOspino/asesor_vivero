"""
notifier.py
Capa de Acción: envío de alertas y recomendaciones por correo electrónico
al jardinero, vía Gmail SMTP.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import EMAIL_REMITENTE, EMAIL_APP_PASSWORD, EMAIL_DESTINATARIO

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def enviar_correo(asunto: str, mensaje: str) -> bool:
    """
    Envía un correo al jardinero. Devuelve True si se envió,
    False si faltan credenciales (para no tumbar el flujo diario).
    """
    if not all([EMAIL_REMITENTE, EMAIL_APP_PASSWORD, EMAIL_DESTINATARIO]):
        print("  ⚠️  Credenciales de correo incompletas en .env — no se envió el correo.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_REMITENTE
        msg["To"] = EMAIL_DESTINATARIO
        msg["Subject"] = asunto
        msg.attach(MIMEText(mensaje, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_REMITENTE, EMAIL_APP_PASSWORD)
            server.send_message(msg)

        print(f"  ✅ Correo enviado a {EMAIL_DESTINATARIO}")
        return True
    except Exception as e:
        print(f"  ❌ Error enviando correo: {e}")
        return False


if __name__ == "__main__":
    # Prueba rápida: python notifier.py
    enviar_correo(
        "🌱 Prueba del Asesor Inteligente del Vivero CECAR",
        "Si recibes este correo, la notificación por email está funcionando correctamente."
    )