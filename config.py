"""
config.py
Carga centralizada de variables de entorno para el proyecto Vivero CECAR.
Todos los demás módulos (ingesta, reglas, IA, email, dashboard) deben
importar sus credenciales desde aquí en lugar de leer os.environ directamente.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # busca un archivo .env en el directorio de ejecución


def _get_env(name: str, required: bool = True, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise EnvironmentError(
            f"Falta la variable de entorno '{name}'. Revisa tu archivo .env "
            f"(usa .env.example como referencia)."
        )
    return value


# --- Weather Underground ---
WU_API_KEY = _get_env("WU_API_KEY")
WU_STATION_ID = _get_env("WU_STATION_ID")
WU_BASE_URL = "https://api.weather.com/v2/pws/observations/current"

# --- Groq (Agente IA semanal) ---
GROQ_API_KEY = _get_env("GROQ_API_KEY", required=False)

# --- Email (notificaciones al jardinero) ---
EMAIL_REMITENTE = _get_env("EMAIL_REMITENTE", required=False)
EMAIL_APP_PASSWORD = _get_env("EMAIL_APP_PASSWORD", required=False)
EMAIL_DESTINATARIO = _get_env("EMAIL_DESTINATARIO", required=False)

# --- Base de datos ---
DB_PATH = _get_env("DB_PATH", required=False, default="vivero_cecar.db")


if __name__ == "__main__":
    # Ejecuta este archivo directamente para verificar que las variables
    # obligatorias cargan correctamente: python config.py
    print("Configuración cargada correctamente:")
    print(f"  WU_STATION_ID = {WU_STATION_ID}")
    print(f"  WU_API_KEY    = {'*' * (len(WU_API_KEY) - 4) + WU_API_KEY[-4:]}")