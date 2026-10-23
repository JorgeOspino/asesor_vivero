"""
telegram_chat_id.py
Muestra el chat_id de las personas que le han escrito al bot.
Antes de correrlo, cada persona debe abrir el bot en Telegram y enviarle /start.
"""

import requests
from config import TELEGRAM_BOT_TOKEN

if not TELEGRAM_BOT_TOKEN:
    raise SystemExit("Falta TELEGRAM_BOT_TOKEN en el archivo .env")

resp = requests.get(
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates", timeout=20
)
resp.raise_for_status()

chats = {}
for update in resp.json().get("result", []):
    mensaje = update.get("message") or update.get("edited_message") or {}
    chat = mensaje.get("chat")
    if chat:
        nombre = chat.get("first_name") or chat.get("title") or chat.get("username") or "sin nombre"
        chats[chat["id"]] = nombre

if not chats:
    print("Todavía no hay mensajes. Escríbele algo al bot desde Telegram y vuelve a correr esto.")
else:
    print("Chats encontrados (copia los ids al .env):")
    for chat_id, nombre in chats.items():
        print(f"  {chat_id}  ->  {nombre}")