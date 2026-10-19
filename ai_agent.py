"""
ai_agent.py
Capa de Cerebro (avanzada): Agente de IA semanal.
Lee los últimos 7 días de telemetria_diaria y genera un boletín
climático ejecutivo usando Groq (Llama 3.3).
"""

from datetime import datetime, timezone
from groq import Groq
from config import GROQ_API_KEY
from database import obtener_ultimos_dias, guardar_boletin

MODELO = "openai/gpt-oss-120b"

PROMPT_SISTEMA = """Eres un asesor agrónomo experto que redacta boletines climáticos
ejecutivos semanales para el administrador de un vivero. Tu tono es profesional,
claro y directo. Recibirás datos tabulares de 7 días de telemetría (clima y
decisiones de riego). Debes:
1. Resumir las condiciones climáticas de la semana (temperatura, lluvia, viento).
2. Señalar cuántos días hubo alertas y de qué tipo.
3. Dar 2-3 recomendaciones prácticas y accionables para la próxima semana.
Responde en español, en máximo 200 palabras, en formato de boletín (no uses JSON)."""


def generar_boletin_semanal() -> str:
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "Falta GROQ_API_KEY en tu .env. Consíguela en console.groq.com/keys"
        )

    df = obtener_ultimos_dias(7)
    if df.empty:
        return "No hay suficientes datos de telemetría todavía para generar un boletín."

    resumen_datos = df[[
        "fecha_registro", "temperatura_c", "precipitacion_mm",
        "rafaga_viento_kmh", "humedad_relativa_pct",
        "regla_aplicada", "orden_riego", "alerta"
    ]].to_string(index=False)

    client = Groq(api_key=GROQ_API_KEY)
    respuesta = client.chat.completions.create(
        model=MODELO,
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": f"Datos de la semana:\n{resumen_datos}"},
        ],
        max_tokens=500,
        temperature=0.4,
    )

    boletin = respuesta.choices[0].message.content

    fecha_fin = datetime.now(timezone.utc).date().isoformat()
    fecha_inicio = df["fecha_registro"].min()[:10]
    guardar_boletin(fecha_inicio, fecha_fin, boletin)

    return boletin


if __name__ == "__main__":
    print("Generando boletín semanal...\n")
    boletin = generar_boletin_semanal()
    print("=== Boletín Climático Ejecutivo ===\n")
    print(boletin)