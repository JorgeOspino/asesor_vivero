"""
dashboard.py
Capa de Usabilidad: Dashboard en Streamlit.
KPIs, medidores, gráficas interactivas, boletines y asistente conversacional
del Asesor Inteligente del Vivero CECAR. Se auto-refresca cada 60 segundos.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fpdf import FPDF
from streamlit_autorefresh import st_autorefresh
from database import get_connection, init_db
from chat_agent import responder

# ---------------------------------------------------------------
# Configuración general
# ---------------------------------------------------------------
st.set_page_config(page_title="Asesor Vivero CECAR", layout="wide")
init_db()
st_autorefresh(interval=60000, key="auto_refresh")

UMBRAL_VIENTO = 50.0  # debe coincidir con rules_engine.py
UMBRAL_TEMP = 33.0    # debe coincidir con rules_engine.py

ESTADOS_RIEGO = {
    "ESTANDAR":   ("#15803D", "Riego estándar"),
    "PROFUNDO":   ("#0369A1", "Riego profundo"),
    "SUSPENDIDO": ("#B45309", "Riego suspendido"),
}
COLOR_ALERTA = "#B91C1C"

# ---------------------------------------------------------------
# Estilos CSS
# ---------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, button, input {
    font-family: 'Inter', sans-serif !important;
}
header[data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
.block-container { padding-top: 1.6rem; max-width: 1280px; }

.hero {
    background: linear-gradient(120deg, #14532D 0%, #166534 55%, #0F766E 100%);
    padding: 30px 38px; border-radius: 16px; margin-bottom: 22px;
}
.hero .eyebrow {
    color: #86EFAC; font-size: 0.78rem; font-weight: 600;
    letter-spacing: 2px; text-transform: uppercase;
}
.hero h1 { margin: 4px 0 0 0; font-size: 2.1rem; font-weight: 800; color: #FFFFFF; }
.hero p  { margin: 6px 0 0 0; color: #D1FAE5; font-size: 1rem; }

.estado {
    background: #FFFFFF; border: 1px solid #DCE5DA;
    border-left: 8px solid var(--c); border-radius: 14px;
    padding: 22px 28px; margin-bottom: 18px;
    box-shadow: 0 2px 10px rgba(20,60,30,0.06);
}
.estado .pill {
    display: inline-block; background: var(--c); color: #fff;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; padding: 4px 12px; border-radius: 999px;
}
.estado .titulo { font-size: 1.8rem; font-weight: 800; color: #14231A; margin: 10px 0 2px 0; }
.estado .msg    { font-size: 1.02rem; color: #3A4D40; }
.estado .meta   { font-size: 0.82rem; color: #6B7F70; margin-top: 10px; }

.kpi {
    background: #FFFFFF; border: 1px solid #DCE5DA;
    border-top: 4px solid var(--c); border-radius: 14px;
    padding: 18px 20px; box-shadow: 0 2px 10px rgba(20,60,30,0.06);
}
.kpi .label { color: #5F7366; font-size: 0.76rem; font-weight: 600;
              text-transform: uppercase; letter-spacing: 1.2px; }
.kpi .value { color: #14231A; font-size: 2.1rem; font-weight: 800; line-height: 1.25; margin-top: 4px; }
.kpi .unit  { color: var(--c); font-size: 0.95rem; font-weight: 700; margin-left: 5px; }

.seccion { font-size: 1.05rem; font-weight: 700; color: #14231A; margin: 6px 0 2px 0; }

div[data-testid="stTabs"] button { font-weight: 600; font-size: 0.98rem; }
div[data-testid="stExpander"] { background: #FFFFFF; border-radius: 12px; border: 1px solid #DCE5DA; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Funciones auxiliares de UI
# ---------------------------------------------------------------
def fmt(valor, decimales=1):
    if valor is None or pd.isna(valor):
        return "--"
    return f"{valor:.{decimales}f}"


def kpi_card(etiqueta, valor, unidad, color):
    st.markdown(f"""
    <div class="kpi" style="--c:{color}">
        <div class="label">{etiqueta}</div>
        <div class="value">{valor}<span class="unit">{unidad}</span></div>
    </div>
    """, unsafe_allow_html=True)


def gauge(valor, titulo, rango, color, sufijo="", umbral=None):
    cfg = {
        "axis": {"range": rango, "tickcolor": "#6B7F70"},
        "bar": {"color": color, "thickness": 0.7},
        "bgcolor": "#E8EFE6",
        "borderwidth": 0,
    }
    if umbral is not None:
        cfg["threshold"] = {"line": {"color": COLOR_ALERTA, "width": 4},
                            "thickness": 0.85, "value": umbral}
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=0 if valor is None or pd.isna(valor) else valor,
        title={"text": titulo, "font": {"size": 15, "color": "#14231A"}},
        number={"suffix": sufijo, "font": {"color": "#14231A", "size": 34}},
        gauge=cfg,
    ))
    fig.update_layout(height=240, margin=dict(l=25, r=25, t=55, b=10),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


def estilo_figura(fig, alto=380):
    fig.update_layout(
        template="plotly_white", height=alto,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF",
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", y=1.15),
        font=dict(family="Inter, sans-serif", color="#14231A"),
    )
    return fig


def boletin_a_pdf(titulo: str, contenido: str) -> bytes:
    """Convierte el texto del boletín en un PDF simple y legible."""
    reemplazos = {
        "–": "-", "—": "-", "−": "-",
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "•": "-", "·": "-", "…": "...",
        "→": "->", "←": "<-", "≥": ">=", "≤": "<=",
        "°C": " C", "²": "2",
        "**": "", "#": "", "*": "-",
    }

    def limpiar(t: str) -> str:
        for original, nuevo in reemplazos.items():
            t = t.replace(original, nuevo)
        return t.encode("latin-1", "ignore").decode("latin-1")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, limpiar(titulo), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 7, limpiar(contenido))
    return bytes(pdf.output())

# ---------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------
conn = get_connection()
df = pd.read_sql_query("SELECT * FROM telemetria_diaria ORDER BY fecha_registro DESC", conn)
boletines = pd.read_sql_query("SELECT * FROM boletines_semanales ORDER BY fecha_generacion DESC", conn)
conn.close()

df = df.dropna(subset=["temperatura_c"])  # ignora registros sin datos

if not df.empty:
    df["fecha_registro"] = (
        pd.to_datetime(df["fecha_registro"], utc=True).dt.tz_convert("America/Bogota")
    )

# ---------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------
st.markdown("""
<div class="hero">
    <div class="eyebrow">Sistema de apoyo a la decisión</div>
    <h1>Asesor Inteligente &middot; Vivero CECAR</h1>
    <p>Monitoreo climático y recomendaciones de riego en tiempo real &middot; Estación Sainlogic SA7</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("Todavía no hay datos guardados. Corre `python main_diario.py` primero.")
    st.stop()

ultimo = df.iloc[0]
color_riego, texto_riego = ESTADOS_RIEGO.get(
    ultimo["orden_riego"], ("#15803D", str(ultimo["orden_riego"]))
)
etiqueta_estado = "Estado normal"
if ultimo["alerta"]:
    color_riego, etiqueta_estado = COLOR_ALERTA, "Alerta activa"

# ---------------------------------------------------------------
# Estado de riego
# ---------------------------------------------------------------
st.markdown(f"""
<div class="estado" style="--c:{color_riego}">
    <span class="pill">{etiqueta_estado}</span>
    <div class="titulo">{texto_riego}</div>
    <div class="msg">{ultimo['mensaje']}</div>
    <div class="meta">{ultimo['regla_aplicada']} &nbsp;|&nbsp; Última lectura: {ultimo['fecha_registro'].strftime('%d/%m/%Y %H:%M')}</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Estado actual", "Historial", "Boletines", "Asistente"])

# ===== TAB 1: Estado actual =====
with tab1:
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Temperatura", fmt(ultimo["temperatura_c"]), "°C", "#DC2626")
    with c2:
        kpi_card("Precipitación", fmt(ultimo["precipitacion_mm"]), "mm", "#0369A1")
    with c3:
        kpi_card("Humedad", fmt(ultimo["humedad_relativa_pct"], 0), "%", "#0F766E")
    with c4:
        kpi_card("Ráfaga de viento", fmt(ultimo["rafaga_viento_kmh"]), "km/h", "#B45309")
    with c5:
        kpi_card("Radiación solar", fmt(ultimo["radiacion_solar_wm2"], 0), "W/m²", "#C2410C")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="seccion">Medidores</div>', unsafe_allow_html=True)

    g1, g2, g3 = st.columns(3)
    with g1:
        st.plotly_chart(gauge(ultimo["temperatura_c"], "Temperatura", [0, 50],
                              "#DC2626", " °C", UMBRAL_TEMP), use_container_width=True)
    with g2:
        st.plotly_chart(gauge(ultimo["humedad_relativa_pct"], "Humedad relativa", [0, 100],
                              "#0F766E", " %"), use_container_width=True)
    with g3:
        st.plotly_chart(gauge(ultimo["rafaga_viento_kmh"], "Ráfaga de viento", [0, 100],
                              "#B45309", " km/h", UMBRAL_VIENTO), use_container_width=True)
    st.caption("La línea roja de cada medidor marca el umbral que activa una regla del sistema.")

# ===== TAB 2: Historial =====
with tab2:
    d = df.sort_values("fecha_registro")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=d["fecha_registro"], y=d["temperatura_c"], name="Temperatura (°C)",
        mode="lines+markers", line=dict(color="#DC2626", width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=d["fecha_registro"], y=d["humedad_relativa_pct"], name="Humedad (%)",
        mode="lines+markers", line=dict(color="#0F766E", width=3)), secondary_y=True)
    fig.update_yaxes(title_text="°C", secondary_y=False)
    fig.update_yaxes(title_text="%", secondary_y=True)
    fig.update_layout(title="Temperatura y humedad")
    st.plotly_chart(estilo_figura(fig), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        fig2 = go.Figure(go.Bar(
            x=d["fecha_registro"], y=d["precipitacion_mm"], marker_color="#0369A1"))
        fig2.update_layout(title="Precipitación (mm)")
        st.plotly_chart(estilo_figura(fig2, 320), use_container_width=True)
    with col_b:
        conteo = df["regla_aplicada"].value_counts()
        fig3 = go.Figure(go.Pie(
            labels=conteo.index, values=conteo.values, hole=0.55,
            marker=dict(colors=["#15803D", "#0369A1", "#B45309", "#B91C1C"])))
        fig3.update_layout(title="Reglas activadas")
        st.plotly_chart(estilo_figura(fig3, 320), use_container_width=True)

    with st.expander("Ver tabla completa de registros"):
        st.dataframe(df)

# ===== TAB 3: Boletines =====
with tab3:
    if boletines.empty:
        st.info("Aún no se ha generado ningún boletín. Corre `python ai_agent.py`.")
    else:
        for _, fila in boletines.iterrows():
            titulo = f"Boletín Climático - Vivero CECAR ({fila['fecha_inicio']} al {fila['fecha_fin']})"
            with st.expander(f"Boletín del {fila['fecha_inicio']} al {fila['fecha_fin']}"):
                st.write(fila["contenido"])

                col_pdf, col_txt, _ = st.columns([1, 1, 4])
                with col_pdf:
                    st.download_button(
                        "Descargar PDF",
                        data=boletin_a_pdf(titulo, fila["contenido"]),
                        file_name=f"boletin_{fila['fecha_inicio']}_{fila['fecha_fin']}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{fila['id']}",
                    )
                with col_txt:
                    st.download_button(
                        "Descargar TXT",
                        data=f"{titulo}\n\n{fila['contenido']}",
                        file_name=f"boletin_{fila['fecha_inicio']}_{fila['fecha_fin']}.txt",
                        mime="text/plain",
                        key=f"txt_{fila['id']}",
                    )

# ===== TAB 4: Asistente =====
with tab4:
    st.markdown('<div class="seccion">Pregúntale al asistente</div>', unsafe_allow_html=True)
    st.caption("Responde con base en las lecturas reales de la estación y las reglas del sistema.")

    if "chat" not in st.session_state:
        st.session_state.chat = []

    sugeridas = [
        "¿Por qué hoy se recomienda este tipo de riego?",
        "¿Cómo ha estado el clima en las últimas lecturas?",
        "¿Qué debo hacer si sube mucho el viento?",
    ]
    cols = st.columns(len(sugeridas))
    pregunta = None
    for i, (col, texto) in enumerate(zip(cols, sugeridas)):
        if col.button(texto, key=f"sug_{i}", use_container_width=True):
            pregunta = texto

    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    entrada = st.chat_input("Escribe tu pregunta sobre el clima o el riego")
    pregunta = pregunta or entrada

    if pregunta:
        st.session_state.chat.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.write(pregunta)
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                respuesta = responder(st.session_state.chat)
            st.write(respuesta)
        st.session_state.chat.append({"role": "assistant", "content": respuesta})

    if st.session_state.chat:
        if st.button("Borrar conversación"):
            st.session_state.chat = []
            st.rerun()