"""
dashboard.py

Panel telemétrico interactivo y Asistente IA para el Vivero CECAR.
Diseño ejecutivo profesional con indicadores visuales avanzados y
sincronización de zona horaria para Colombia (America/Bogota).
"""

import base64
import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

@st.cache_data
def cargar_robot_base64():
    """Lee robot_savaiot.png (junto a este archivo) y lo devuelve en base64."""
    ruta = Path(__file__).parent / "robot_savaiot.png"
    return base64.b64encode(ruta.read_bytes()).decode() if ruta.exists() else ""


ROBOT_B64 = cargar_robot_base64()

# Configuración inicial de la página
st.set_page_config(
    page_title="SAVA-IoT ",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS Personalizados Avanzados
CSS_PROFESIONAL = """
<style>
    /* Fondo general */
    .stApp {
        background-color: #0b1220;
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Encabezado principal */
    .main-header {
        background: linear-gradient(135deg, #064e3b 0%, #047857 50%, #0f766e 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        color: #ffffff;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.6);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-title-container h1 {
        color: #ffffff !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        margin: 0 !important;
        letter-spacing: -0.02em;
    }
    .header-title-container p {
        color: #a7f3d0 !important;
        font-size: 0.95rem !important;
        margin-top: 0.4rem !important;
        font-weight: 400;
    }
    .header-badge {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.25);
        padding: 0.5rem 1rem;
        border-radius: 30px;
        color: #ecfdf5;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }

    /* Robot de la marca en el encabezado */
    .header-left {
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }
    .header-robot {
        height: 110px;
        width: auto;
        filter: drop-shadow(0 6px 10px rgba(0, 0, 0, 0.35));
        animation: flotar 3.5s ease-in-out infinite;
    }
    @keyframes flotar {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-6px); }
    }
    @media (max-width: 640px) {
        .main-header { flex-direction: column; align-items: flex-start; gap: 1rem; }
        .header-robot { height: 80px; }
    }

    /* Indicador de pulso en vivo */
    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        animation: pulse 1.8s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    /* Tarjetas métricas personalizadas */
    .metric-card {
        background-color: #111a2e;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1.2rem 1rem;
        box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.5);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 20px -3px rgba(0, 0, 0, 0.7);
    }
    .metric-label {
        font-size: 0.75rem;
        color: #94a3b8;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
    }
    .metric-value {
        font-size: 1.8rem;
        color: #f1f5f9;
        font-weight: 800;
        line-height: 1.1;
    }
    .metric-unit {
        font-size: 1rem;
        font-weight: 600;
        color: #94a3b8;
        margin-left: 2px;
    }

    /* Borde superior temático por variable */
    .metric-temp { border-top: 4px solid #f97316; }
    .metric-precip { border-top: 4px solid #3b82f6; }
    .metric-humidity { border-top: 4px solid #14b8a6; }
    .metric-solar { border-top: 4px solid #eab308; }
    .metric-wind { border-top: 4px solid #6366f1; }

    /* Tarjeta de estado de riego */
    .status-card-active {
        background: linear-gradient(90deg, rgba(220, 38, 38, 0.22) 0%, #111a2e 100%);
        border: 1px solid #7f1d1d;
        border-left: 6px solid #ef4444;
        padding: 1.3rem 1.6rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.05);
    }
    .status-card-inactive {
        background: linear-gradient(90deg, rgba(22, 163, 74, 0.22) 0%, #111a2e 100%);
        border: 1px solid #14532d;
        border-left: 6px solid #22c55e;
        padding: 1.3rem 1.6rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        box-shadow: 0 4px 12px rgba(22, 163, 74, 0.05);
    }
    .status-header-flex {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 0.4rem;
    }
    .status-title-active {
        font-size: 1rem;
        font-weight: 800;
        color: #fca5a5;
        letter-spacing: 0.03em;
    }
    .status-title-inactive {
        font-size: 1rem;
        font-weight: 800;
        color: #86efac;
        letter-spacing: 0.03em;
    }
    .status-desc {
        font-size: 0.95rem;
        color: #cbd5e1;
        margin: 0;
        line-height: 1.5;
    }

    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        border-bottom: 2px solid #1e293b;
        padding-bottom: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 46px;
        padding: 0 20px;
        color: #94a3b8;
        font-weight: 600;
        font-size: 0.95rem;
        border-radius: 8px 8px 0 0;
    }
    .stTabs [aria-selected="true"] {
        color: #34d399 !important;
        background-color: rgba(16, 185, 129, 0.12) !important;
        border-bottom: 3px solid #34d399 !important;
    }

    /* Tarjetas animadas (lluvia, humedad y sol) */
    .anim-card {
        position: relative;
        overflow: hidden;
        min-height: 210px;
        display: flex;
        align-items: center;
    }
    .anim-content { position: relative; z-index: 2; }
    .cloud-icon { position: absolute; top: 12px; right: 16px; z-index: 2; }
    .raindrop {
        position: absolute;
        top: -24px;
        width: 2px;
        border-radius: 2px;
        background: linear-gradient(to bottom, rgba(96, 165, 250, 0), #60a5fa);
        animation-name: caer;
        animation-timing-function: linear;
        animation-iteration-count: infinite;
        z-index: 1;
    }
    @keyframes caer {
        0% { transform: translateY(0); opacity: 0; }
        10% { opacity: 1; }
        100% { transform: translateY(260px); opacity: 0.2; }
    }
    @keyframes girar { to { transform: rotate(360deg); } }
    @keyframes latido {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.08); }
    }
    .sun-rays {
        transform-origin: 100px 100px;
        animation-name: girar;
        animation-timing-function: linear;
        animation-iteration-count: infinite;
    }
    .sun-core {
        transform-origin: 100px 100px;
        animation: latido 2.5s ease-in-out infinite;
    }

    /* Tarjetas contenedoras (termómetro y tacómetro) */
    .st-key-card_termo, .st-key-card_viento {
        background-color: #111a2e;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.5);
    }

    /* Barra superior y expander oscuros */
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stExpander"] {
        background-color: #111a2e;
        border: 1px solid #1e293b;
        border-radius: 12px;
    }

    /* Ocultar elementos innecesarios */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""

st.markdown(CSS_PROFESIONAL, unsafe_allow_html=True)


@st.cache_data(ttl=1)
def cargar_datos():
    """Consulta Neon y ajusta la hora de UTC a Colombia (America/Bogota)."""
    if not DATABASE_URL:
        st.error("DATABASE_URL no está configurada en los Secrets o .env.")
        return pd.DataFrame()

    try:
        conn = psycopg2.connect(DATABASE_URL)
        query = "SELECT * FROM telemetria_diaria ORDER BY fecha_registro DESC LIMIT 100;"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if not df.empty and "fecha_registro" in df.columns:
            df["fecha_registro"] = pd.to_datetime(df["fecha_registro"])

            if df["fecha_registro"].dt.tz is None:
                df["fecha_registro"] = (
                    df["fecha_registro"]
                    .dt.tz_localize("UTC")
                    .dt.tz_convert("America/Bogota")
                )
            else:
                df["fecha_registro"] = df["fecha_registro"].dt.tz_convert(
                    "America/Bogota"
                )

            df["fecha_registro"] = df["fecha_registro"].dt.tz_localize(None)

        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos Neon: {e}")
        return pd.DataFrame()


def color_temperatura(t):
    """Devuelve (color, estado) según el rango de temperatura."""
    if t < 15:
        return "#3b82f6", "FRÍO"
    if t < 22:
        return "#06b6d4", "FRESCO"
    if t < 27:
        return "#22c55e", "ÓPTIMA"
    if t < 32:
        return "#eab308", "CÁLIDO"
    if t < 36:
        return "#f97316", "CALUROSO"
    return "#dc2626", "CALOR EXTREMO"


def html_termometro(temp):
    """Termómetro SVG cuyo mercurio cambia de altura y color con la temperatura."""
    t = float(temp)
    color, estado = color_temperatura(t)
    frac = max(0.0, min(1.0, t / 45))
    y_top = 235 - frac * 205

    marcas = ""
    for val in range(0, 50, 10):
        y = 235 - val / 45 * 205
        marcas += (
            f'<line x1="80" y1="{y:.1f}" x2="92" y2="{y:.1f}" stroke="#64748b" stroke-width="2"/>'
            f'<text x="97" y="{y + 4:.1f}" font-size="11" fill="#94a3b8">{val}°</text>'
        )

    svg = (
        '<svg viewBox="0 0 130 300" width="130" height="300" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="45" y="20" width="30" height="220" rx="15" fill="#1e293b" stroke="#334155" stroke-width="2"/>'
        f'<circle cx="60" cy="255" r="30" fill="{color}" stroke="#334155" stroke-width="2"/>'
        f'<rect x="52" y="{y_top:.1f}" width="16" height="{255 - y_top:.1f}" rx="8" fill="{color}"/>'
        '<ellipse cx="50" cy="247" rx="6" ry="9" fill="#ffffff" opacity="0.35"/>'
        f"{marcas}"
        "</svg>"
    )

    return (
        '<div style="display:flex;align-items:center;justify-content:center;gap:1rem;">'
        f"{svg}"
        '<div><div class="metric-label">Temperatura</div>'
        f'<div class="metric-value" style="color:{color};font-size:2.6rem;">{t:.1f}<span class="metric-unit">°C</span></div>'
        f'<div style="display:inline-block;margin-top:0.5rem;padding:0.25rem 0.8rem;border-radius:20px;'
        f'background:{color}22;color:{color};font-weight:700;font-size:0.8rem;">{estado}</div></div>'
        "</div>"
    )


def estado_lluvia(p):
    """Devuelve (cantidad de gotas, estado, color) según la precipitación."""
    if p <= 0:
        return 0, "SIN LLUVIA", "#64748b"
    if p < 2.5:
        return 8, "LLOVIZNA", "#7dd3fc"
    if p < 7.5:
        return 16, "LLUVIA MODERADA", "#60a5fa"
    if p < 15:
        return 28, "LLUVIA FUERTE", "#3b82f6"
    return 40, "AGUACERO", "#818cf8"


def html_lluvia(precip):
    """Tarjeta con gotas cayendo; más gotas y más rápidas con más lluvia."""
    p = max(0.0, float(precip))
    n, estado, color = estado_lluvia(p)
    dur = max(0.5, 1.8 - p * 0.08)
    gotas = "".join(
        f'<span class="raindrop" style="left:{(i * 37 + 11) % 100}%;height:{12 + (i % 3) * 4}px;'
        f'animation-duration:{dur + (i % 3) * 0.25:.2f}s;animation-delay:-{(i * 0.29) % 2:.2f}s;"></span>'
        for i in range(n)
    )
    nube = "#94a3b8" if n else "#475569"
    return (
        f'<div class="metric-card metric-precip anim-card">{gotas}'
        '<svg class="cloud-icon" viewBox="0 0 64 40" width="64" height="40" xmlns="http://www.w3.org/2000/svg">'
        f'<g fill="{nube}"><circle cx="20" cy="24" r="12"/><circle cx="34" cy="16" r="14"/>'
        '<circle cx="48" cy="24" r="11"/><rect x="20" y="24" width="28" height="11"/></g></svg>'
        '<div class="anim-content">'
        '<div class="metric-label">Precipitación</div>'
        f'<div class="metric-value" style="font-size:2.4rem;">{p:.1f}<span class="metric-unit">mm</span></div>'
        '<div style="display:inline-block;margin-top:0.6rem;padding:0.25rem 0.8rem;border-radius:20px;'
        f'background:{color}22;color:{color};font-weight:700;font-size:0.8rem;">{estado}</div>'
        "</div></div>"
    )


def html_humedad(hum):
    """Tarjeta de humedad con barra de nivel."""
    h = float(hum)
    pct = max(0.0, min(100.0, h))
    return (
        '<div class="metric-card metric-humidity anim-card"><div class="anim-content" style="width:100%;">'
        '<div class="metric-label">Humedad Rel.</div>'
        f'<div class="metric-value" style="font-size:2.4rem;">{h:.1f}<span class="metric-unit">%</span></div>'
        '<div style="height:10px;background:#1e293b;border-radius:6px;margin-top:1rem;overflow:hidden;">'
        f'<div style="width:{pct:.0f}%;height:100%;background:linear-gradient(90deg,#14b8a6,#5eead4);'
        'border-radius:6px;"></div></div>'
        "</div></div>"
    )


def color_radiacion(r):
    """Devuelve (color, estado) según la radiación solar en W/m²."""
    if r < 50:
        return "#64748b", "SIN SOL"
    if r < 300:
        return "#fde047", "BAJA"
    if r < 600:
        return "#facc15", "MODERADA"
    if r < 800:
        return "#fb923c", "ALTA"
    if r < 1000:
        return "#f97316", "MUY ALTA"
    return "#ef4444", "EXTREMA"


def html_sol(rad):
    """Sol que se carga: el anillo se llena, los rayos giran más rápido y el brillo crece."""
    r = max(0.0, float(rad))
    color, estado = color_radiacion(r)
    frac = min(1.0, r / 1200)
    circ = 2 * 3.14159265 * 88
    prog = circ * frac

    rayos = "".join(
        f'<line x1="100" y1="48" x2="100" y2="34" stroke="{color}" stroke-width="5" '
        f'stroke-linecap="round" transform="rotate({a} 100 100)"/>'
        for a in range(0, 360, 30)
    )
    estilo_rayos = (
        f"animation-duration:{40 - 34 * frac:.1f}s;opacity:{0.45 + 0.55 * frac:.2f};"
        if r >= 50
        else "animation:none;opacity:0.4;"
    )
    anillo = (
        f'<circle cx="100" cy="100" r="88" fill="none" stroke="{color}" stroke-width="10" '
        f'stroke-linecap="round" stroke-dasharray="{prog:.1f} {circ:.1f}" transform="rotate(-90 100 100)"/>'
        if frac > 0
        else ""
    )

    svg = (
        '<svg viewBox="0 0 200 200" width="170" height="170" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><filter id="brillo" x="-50%" y="-50%" width="200%" height="200%">'
        f'<feGaussianBlur stdDeviation="{4 + 8 * frac:.1f}"/></filter></defs>'
        '<circle cx="100" cy="100" r="88" fill="none" stroke="#1e293b" stroke-width="10"/>'
        f"{anillo}"
        f'<g class="sun-rays" style="{estilo_rayos}">{rayos}</g>'
        f'<circle cx="100" cy="100" r="40" fill="{color}" opacity="{0.35 + 0.5 * frac:.2f}" filter="url(#brillo)"/>'
        f'<g class="sun-core"><circle cx="100" cy="100" r="30" fill="{color}"/>'
        '<circle cx="92" cy="92" r="10" fill="#ffffff" opacity="0.25"/></g>'
        "</svg>"
    )

    return (
        '<div class="metric-card metric-solar anim-card">'
        '<div style="display:flex;align-items:center;justify-content:center;gap:1rem;width:100%;">'
        f"{svg}"
        '<div><div class="metric-label">Rad. Solar</div>'
        f'<div class="metric-value" style="color:{color};font-size:2.2rem;">{r:.1f}<span class="metric-unit">W/m²</span></div>'
        '<div style="display:inline-block;margin-top:0.5rem;padding:0.25rem 0.8rem;border-radius:20px;'
        f'background:{color}22;color:{color};font-weight:700;font-size:0.8rem;">{estado}</div>'
        f'<div style="color:#94a3b8;font-size:0.8rem;margin-top:0.5rem;">Carga solar: <b>{frac * 100:.0f}%</b></div>'
        "</div></div></div>"
    )


def crear_tacometro(velocidad):
    """Tacómetro (gauge) para la velocidad del viento."""
    v = float(velocidad)
    maximo = 80
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=v,
            number={"suffix": " km/h", "font": {"size": 34, "color": "#f1f5f9"}},
            title={"text": "<b>VELOCIDAD DEL VIENTO</b>", "font": {"size": 14, "color": "#94a3b8"}},
            gauge={
                "axis": {"range": [0, maximo], "dtick": 10, "tickwidth": 2, "tickcolor": "#94a3b8", "tickfont": {"color": "#94a3b8"}},
                "bar": {"color": "rgba(0,0,0,0)"},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 15], "color": "#22c55e"},
                    {"range": [15, 30], "color": "#eab308"},
                    {"range": [30, 50], "color": "#f97316"},
                    {"range": [50, maximo], "color": "#dc2626"},
                ],
                "threshold": {
                    "line": {"color": "#f8fafc", "width": 6},
                    "thickness": 0.85,
                    "value": min(v, maximo),
                },
            },
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=30, r=30, t=60, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
    )
    return fig


# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("## **SAVA-IoT**")
    st.caption("Sistema de Telemetría Agrícola v2.4")
    st.divider()

    st.markdown("### Configuración de Inteligencia IA")
    OPCIONES_MODELOS = {
        "Llama 3.3 70B Versatile": "llama-3.3-70b-versatile",
        "Llama 3.1 8B Instant": "llama-3.1-8b-instant",
        "GPT-OSS 120B (OpenAI)": "openai/gpt-oss-120b",
        "GPT-OSS 20B (OpenAI)": "openai/gpt-oss-20b",
    }

    modelo_label = st.selectbox(
        "Modelo de Lenguaje Activo:",
        list(OPCIONES_MODELOS.keys()),
        index=0,
    )
    modelo_groq_id = OPCIONES_MODELOS[modelo_label]

    st.divider()
    st.markdown("### Estado del Sistema")
    st.markdown("🟢 **Neon PostgreSQL:** Conectado")
    st.markdown("🟢 **Motor de Reglas:** Activo")
    st.markdown("🟢 **Zona Horaria:** UTC-5 (Colombia)")


# --- ENCABEZADO PRINCIPAL ---
robot_html = (
    f'<img class="header-robot" src="data:image/png;base64,{ROBOT_B64}" alt="SAVA-IoT"/>'
    if ROBOT_B64
    else ""
)

st.markdown(
    f"""
    <div class="main-header">
        <div class="header-left">{robot_html}
            <div class="header-title-container">
                <h1>SAVA-IOT</h1>
                <p>Sistema autónomo de vigilancia agroclimática </p>
            </div>
        </div>
        <div class="header-badge">
            <span class="pulse-dot"></span> EN LÍNEA
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

df = cargar_datos()

# Pestañas principales
tab_monitoreo, tab_asistente = st.tabs(
    [" Monitoreo Telemétrico", " Asistente IA Agrónomo"]
)

# ---------------------------------------------------------
# TAB 1: MONITOREO TELEMÉTRICO
# ---------------------------------------------------------
with tab_monitoreo:
    if df.empty:
        st.info("Esperando recepción de datos telemétricos desde Neon...")
    else:
        ultima = df.iloc[0]
        fecha_str = ultima["fecha_registro"].strftime("%Y-%m-%d %H:%M:%S")

        st.markdown(
            f"<div style='color: #94a3b8; font-size: 0.88rem; margin-bottom: 1.2rem;'>"
            f"Última lectura telemétrica sincronizada: <b style='color:#e2e8f0;'>{fecha_str} (Hora Colombia)</b></div>",
            unsafe_allow_html=True,
        )

        # Fila 1: Termómetro + Tacómetro
        col_termo, col_viento = st.columns(2)

        with col_termo:
            with st.container(key="card_termo"):
                st.markdown(html_termometro(ultima["temperatura_c"]), unsafe_allow_html=True)

        with col_viento:
            with st.container(key="card_viento"):
                st.plotly_chart(
                    crear_tacometro(ultima["rafaga_viento_kmh"]),
                    use_container_width=True,
                )

        st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)

        # Fila 2: Lluvia + Humedad + Sol
        col_lluvia, col_hum, col_sol = st.columns(3)

        with col_lluvia:
            st.markdown(html_lluvia(ultima["precipitacion_mm"]), unsafe_allow_html=True)

        with col_hum:
            st.markdown(html_humedad(ultima["humedad_relativa_pct"]), unsafe_allow_html=True)

        with col_sol:
            st.markdown(html_sol(ultima["radiacion_solar_wm2"]), unsafe_allow_html=True)

        # Validación robusta de booleano vs string
        orden_val = ultima.get("orden_riego")
        if isinstance(orden_val, bool):
            riego_activo = orden_val
        else:
            riego_activo = str(orden_val).strip().lower() not in [
                "false",
                "0",
                "none",
                "off",
                "no",
                "",
            ]

        # Banner de Estado
        if riego_activo:
            st.markdown(
                f"""
                <div class="status-card-active">
                    <div class="status-header-flex">
                        <span class="status-title-active">ORDEN DE RIEGO ACTIVA</span>
                    </div>
                    <div class="status-desc">
                        Regla Aplicada: <b>{ultima.get('regla_aplicada', 'N/A')}</b> — {ultima.get('mensaje', '')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="status-card-inactive">
                    <div class="status-header-flex">
                        <span class="status-title-inactive">SISTEMA EN REPOSO — RIEGO DESACTIVADO</span>
                    </div>
                    <div class="status-desc">
                        Regla Aplicada: <b>{ultima.get('regla_aplicada', 'N/A')}</b> — {ultima.get('mensaje', '')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            "<h3 style='color: #f1f5f9; font-weight: 700; margin-top: 2rem;'>Histórico de Telemetría</h3>",
            unsafe_allow_html=True,
        )

        col_chart1, col_chart2 = st.columns(2)

        # Gráfico de Temperatura (Area suavizada)
        with col_chart1:
            fig_temp = go.Figure()
            fig_temp.add_trace(
                go.Scatter(
                    x=df["fecha_registro"],
                    y=df["temperatura_c"],
                    mode="lines",
                    name="Temperatura (°C)",
                    line=dict(color="#34d399", width=3, shape="spline"),
                    fill="tozeroy",
                    fillcolor="rgba(52, 211, 153, 0.12)",
                )
            )
            fig_temp.update_layout(
                title=dict(
                    text="<b>Evolución Térmica (°C)</b>",
                    font=dict(size=15, color="#e2e8f0"),
                ),
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=50, b=20),
                height=340,
                hovermode="x unified",
                xaxis=dict(showgrid=True, gridcolor="#1e293b", title=""),
                yaxis=dict(showgrid=True, gridcolor="#1e293b", title="°C"),
            )
            st.plotly_chart(fig_temp, use_container_width=True)

        # Gráfico de Precipitación (Barras pulidas)
        with col_chart2:
            fig_precip = go.Figure()
            fig_precip.add_trace(
                go.Bar(
                    x=df["fecha_registro"],
                    y=df["precipitacion_mm"],
                    name="Precipitación (mm)",
                    marker=dict(
                        color="#60a5fa",
                        line=dict(color="#3b82f6", width=1),
                    ),
                )
            )
            fig_precip.update_layout(
                title=dict(
                    text="<b>Precipitación Acumulada (mm)</b>",
                    font=dict(size=15, color="#e2e8f0"),
                ),
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=50, b=20),
                height=340,
                hovermode="x unified",
                xaxis=dict(showgrid=True, gridcolor="#1e293b", title=""),
                yaxis=dict(showgrid=True, gridcolor="#1e293b", title="mm"),
            )
            st.plotly_chart(fig_precip, use_container_width=True)

        with st.expander(" Consultar registros históricos detallados"):
            st.dataframe(df, use_container_width=True)

# ---------------------------------------------------------
# TAB 2: ASISTENTE IA AGRÓNOMO (MULTI-MODELO)
# ---------------------------------------------------------
with tab_asistente:
    st.subheader("Asistente Virtual Agrónomo")
    st.caption(f"Modelo de IA activo en Groq: **{modelo_groq_id}**")

    if not GROQ_API_KEY:
        st.warning(
            "La variable GROQ_API_KEY no se encuentra configurada en el entorno."
        )
    else:
        client = Groq(api_key=GROQ_API_KEY)

        if "messages" not in st.session_state:
            st.session_state.messages = []

        zona_chat = st.container()
        prompt = st.chat_input("Escriba su consulta agrónoma...")

        with zona_chat:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if prompt:
                st.session_state.messages.append(
                    {"role": "user", "content": prompt}
                )
                with st.chat_message("user"):
                    st.markdown(prompt)

                contexto_clima = "Sin datos disponibles."
                if not df.empty:
                    u = df.iloc[0]
                    contexto_clima = (
                        f"Lectura ({u['fecha_registro']}): "
                        f"Temperatura: {u['temperatura_c']}°C, Precipitación: {u['precipitacion_mm']}mm, "
                        f"Humedad Relativa: {u['humedad_relativa_pct']}%, Radiación Solar: {u['radiacion_solar_wm2']}W/m², "
                        f"Estado Riego: {u.get('orden_riego', 'N/A')}, Regla: {u.get('regla_aplicada', 'N/A')}, Diagnóstico: {u.get('mensaje', '')}."
                    )

                system_prompt = (
                    "Eres un ingeniero agrónomo consultor experto del Vivero CECAR. "
                    f"Información telemétrica actual del vivero en hora local de Colombia: {contexto_clima}. "
                    "Responde en un lenguaje claro, técnico, profesional y estrictamente sin utilizar ningún emoji en tu texto."
                )

                messages_for_api = [{"role": "system", "content": system_prompt}] + [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]

                with st.chat_message("assistant"):
                    try:
                        completion = client.chat.completions.create(
                            model=modelo_groq_id,
                            messages=messages_for_api,
                            temperature=0.6,
                            max_tokens=800,
                        )
                        respuesta = completion.choices[0].message.content
                        st.markdown(respuesta)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": respuesta}
                        )
                    except Exception as e:
                        st.error(
                            f"Error al procesar la solicitud con el modelo: {e}"
                        )