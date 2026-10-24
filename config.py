"""
config.py
Carga centralizada de variables de entorno para el proyecto Vivero CECAR.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _get_env(name: str, required: bool = True, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise EnvironmentError(
            f"Falta la variable de entorno '{name}'. Revisa tu archivo .env."
        )
    return value


# --- Weather Underground ---
WU_API_KEY = _get_env("WU_API_KEY")
WU_STATION_ID = _get_env("WU_STATION_ID")
WU_BASE_URL = "https://api.weather.com/v2/pws/observations/current"

# --- Groq (Agente IA y asistente) ---
GROQ_API_KEY = _get_env("GROQ_API_KEY", required=False)

# --- Email (reporte diario) ---
EMAIL_REMITENTE = _get_env("EMAIL_REMITENTE", required=False)
EMAIL_APP_PASSWORD = _get_env("EMAIL_APP_PASSWORD", required=False)
EMAIL_DESTINATARIO = _get_env("EMAIL_DESTINATARIO", required=False)

# --- Telegram (alertas e instrucciones de riego) ---
TELEGRAM_BOT_TOKEN = _get_env("TELEGRAM_BOT_TOKEN", required=False)
TELEGRAM_CHAT_IDS = _get_env("TELEGRAM_CHAT_IDS", required=False)  # ids separados por coma

# --- Base de datos ---
DATABASE_URL = _get_env("DATABASE_URL", required=False)  # Neon PostgreSQL
DB_PATH = _get_env("DB_PATH", required=False, default="vivero_cecar.db")  # Respaldo local SQLite


if __name__ == "__main__":
    print("Configuración cargada correctamente:")
    print(f"  WU_STATION_ID = {WU_STATION_ID}")
    print(f"  WU_API_KEY    = {'*' * (len(WU_API_KEY) - 4) + WU_API_KEY[-4:]}")
    if DATABASE_URL:
        print("  Motor de DB   = PostgreSQL (Neon)")
    else:
        print(f"  Motor de DB   = SQLite local ({DB_PATH})")