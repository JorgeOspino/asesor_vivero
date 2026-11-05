"""
dashboard.py

Panel telemétrico interactivo y Asistente IA para el Vivero CECAR.
Diseño ejecutivo profesional con indicadores visuales avanzados y
sincronización de zona horaria para Colombia (America/Bogota).
"""

import os
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

# Configuración inicial de la página
st.set_page_config(
    page_title="SAVA-IoT | Vivero CECAR",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS Personalizados Avanzados
CSS_PROFESIONAL = """
<style>
    /* Fondo general */
    .stApp {
        background-color: #f8fafc;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Encabezado principal */
    .main-header {
        background: linear-gradient(135deg, #064e3b 0%, #047857 50%, #0f766e 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        color: #ffffff;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(6, 78, 59, 0.25);
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
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.2rem 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.06);
    }
    .metric-label {
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
    }
    .metric-value {
        font-size: 1.8rem;
        color: #0f172a;
        font-weight: 800;
        line-height: 1.1;
    }
    .metric-unit {
        font-size: 1rem;
        font-weight: 600;
        color: #64748b;
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
        background: linear-gradient(90deg, #fef2f2 0%, #ffffff 100%);
        border: 1px solid #fecaca;
        border-left: 6px solid #dc2626;
        padding: 1.3rem 1.6rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.05);
    }
    .status-card-inactive {
        background: linear-gradient(90deg, #f0fdf4 0%, #ffffff 100%);
        border: 1px solid #bbf7d0;
        border-left: 6px solid #16a34a;
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
        color: #991b1b;
        letter-spacing: 0.03em;
    }
    .status-title-inactive {
        font-size: 1rem;
        font-weight: 800;
        color: #166534;
        letter-spacing: 0.03em;
    }
    .status-desc {
        font-size: 0.95rem;
        color: #334155;
        margin: 0;
        line-height: 1.5;
    }

    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 46px;
        padding: 0 20px;
        color: #64748b;
        font-weight: 600;
        font-size: 0.95rem;
        border-radius: 8px 8px 0 0;
    }
    .stTabs [aria-selected="true"] {
        color: #047857 !important;
        background-color: #ecfdf5 !important;
        border-bottom: 3px solid #047857 !important;
    }

    /* Ocultar elementos innecesarios */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

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
st.markdown(
    """
    <div class="main-header">
        <div class="header-title-container">
            <h1>Sistema de Riego Inteligente</h1>
            <p>Estación Telemétrica y Motor de Reglas Agrícolas — Vivero Universidad CECAR</p>
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
    ["📊 Monitoreo Telemétrico", "🤖 Asistente IA Agrónomo"]
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
            f"<div style='color: #64748b; font-size: 0.88rem; margin-bottom: 1.2rem;'>"
            f"Última lectura telemétrica sincronizada: <b>{fecha_str} (Hora Colombia)</b></div>",
            unsafe_allow_html=True,
        )

        # Tarjetas Métricas Personalizadas con HTML/CSS
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.markdown(
                f"""
                <div class="metric-card metric-temp">
                    <div class="metric-label">Temperatura</div>
                    <div class="metric-value">{ultima['temperatura_c']}<span class="metric-unit">°C</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""
                <div class="metric-card metric-precip">
                    <div class="metric-label">Precipitación</div>
                    <div class="metric-value">{ultima['precipitacion_mm']}<span class="metric-unit">mm</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""
                <div class="metric-card metric-humidity">
                    <div class="metric-label">Humedad Rel.</div>
                    <div class="metric-value">{ultima['humedad_relativa_pct']}<span class="metric-unit">%</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col4:
            st.markdown(
                f"""
                <div class="metric-card metric-solar">
                    <div class="metric-label">Rad. Solar</div>
                    <div class="metric-value">{ultima['radiacion_solar_wm2']}<span class="metric-unit">W/m²</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col5:
            st.markdown(
                f"""
                <div class="metric-card metric-wind">
                    <div class="metric-label">Vel. Viento</div>
                    <div class="metric-value">{ultima['rafaga_viento_kmh']}<span class="metric-unit">km/h</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

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

        st.markdown("<h3 style='color: #0f172a; font-weight: 700; margin-top: 2rem;'>Histórico de Telemetría</h3>", unsafe_allow_html=True)

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
                    line=dict(color="#047857", width=3, shape="spline"),
                    fill="tozeroy",
                    fillcolor="rgba(4, 120, 87, 0.08)",
                )
            )
            fig_temp.update_layout(
                title=dict(text="<b>Evolución Térmica (°C)</b>", font=dict(size=15, color="#0f172a")),
                template="plotly_white",
                margin=dict(l=20, r=20, t=50, b=20),
                height=340,
                hovermode="x unified",
                xaxis=dict(showgrid=True, gridcolor="#f1f5f9", title=""),
                yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="°C"),
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
                        color="#3b82f6",
                        line=dict(color="#2563eb", width=1)
                    ),
                )
            )
            fig_precip.update_layout(
                title=dict(text="<b>Precipitación Acumulada (mm)</b>", font=dict(size=15, color="#0f172a")),
                template="plotly_white",
                margin=dict(l=20, r=20, t=50, b=20),
                height=340,
                hovermode="x unified",
                xaxis=dict(showgrid=True, gridcolor="#f1f5f9", title=""),
                yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="mm"),
            )
            st.plotly_chart(fig_precip, use_container_width=True)

        with st.expander("🔍 Consultar registros históricos detallados"):
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