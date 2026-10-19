"""
dashboard.py
Capa de Usabilidad: Dashboard en Streamlit (versión visual mejorada).
KPIs, medidores, gráficas interactivas y boletines del Asesor Inteligente
del Vivero CECAR. Se auto-refresca cada 60 segundos.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fpdf import FPDF
from streamlit_autorefresh import st_autorefresh
from database import get_connection, init_db

# ---------------------------------------------------------------
# Configuración general
# ---------------------------------------------------------------
st.set_page_config(page_title="Asesor Vivero CECAR", page_icon="🌱", layout="wide")
init_db()
st_autorefresh(interval=60000, key="auto_refresh")

UMBRAL_VIENTO = 50.0  # debe coincidir con rules_engine.py

COLORES_RIEGO = {
    "ESTANDAR": ("#22C55E", "💧", "Riego estándar"),
    "PROFUNDO": ("#38BDF8", "🌊", "Riego profundo"),
    "SUSPENDIDO": ("#F97316", "⛔", "Riego suspendido"),
}

# ---------------------------------------------------------------
# Estilos CSS personalizados
# ---------------------------------------------------------------
st.markdown("""
<style>
.block-container { padding-top: 1.5rem; }
.hero {
    background: linear-gradient(135deg, #166534 0%, #15803D 45%, #0E7490 100%);
    padding: 28px 34px; border-radius: 20px; margin-bottom: 22px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.35);
}
.hero h1 { margin: 0; font-size: 2.2rem; color: #fff; }
.hero p  { margin: 6px 0 0 0; color: #D1FAE5; font-size: 1.05rem; }
.kpi {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-left: 6px solid var(--c);
    border-radius: 16px; padding: 18px 20px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.25);
}
.kpi .icon  { font-size: 1.7rem; }
.kpi .label { color: #A7C4B0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; }
.kpi .value { color: #fff; font-size: 2rem; font-weight: 700; line-height: 1.2; }
.kpi .unit  { color: var(--c); font-size: 1rem; font-weight: 600; margin-left: 4px; }
.banner {
    border-radius: 18px; padding: 22px 28px; margin: 18px 0 8px 0;
    background: linear-gradient(90deg, var(--c) 0%, rgba(0,0,0,0.15) 140%);
    box-shadow: 0 6px 22px rgba(0,0,0,0.35);
}
.banner .t { font-size: 1.7rem; font-weight: 800; color: #fff; }
.banner .m { font-size: 1.05rem; color: #fff; opacity: 0.95; margin-top: 4px; }
.banner .r { font-size: 0.85rem; color: #fff; opacity: 0.8; margin-top: 8px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Funciones auxiliares de UI
# ---------------------------------------------------------------
def kpi_card(icono, etiqueta, valor, unidad, color):
    st.markdown(f"""
    <div class="kpi" style="--c:{color}">
        <div class="icon">{icono}</div>
        <div class="label">{etiqueta}</div>
        <div class="value">{valor}<span class="unit">{unidad}</span></div>
    </div>
    """, unsafe_allow_html=True)


def gauge(valor, titulo, rango, color, sufijo="", umbral=None):
    gauge_cfg = {
        "axis": {"range": rango, "tickcolor": "#A7C4B0"},
        "bar": {"color": color},
        "bgcolor": "rgba(255,255,255,0.05)",
        "borderwidth": 0,
    }
    if umbral is not None:
        gauge_cfg["threshold"] = {
            "line": {"color": "#EF4444", "width": 4},
            "thickness": 0.8,
            "value": umbral,
        }
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor if valor is not None else 0,
        title={"text": titulo, "font": {"size": 16, "color": "#E8F5E9"}},
        number={"suffix": sufijo, "font": {"color": "#fff"}},
        gauge=gauge_cfg,
    ))
    fig.update_layout(
        height=230, margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font={"color": "#E8F5E9"},
    )
    return fig


def estilo_figura(fig, alto=380):
    fig.update_layout(
        template="plotly_dark", height=alto,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.03)",
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", y=1.12),
    )
    return fig


def boletin_a_pdf(titulo: str, contenido: str) -> bytes:
    """Convierte el texto del boletín en un PDF simple y legible."""
    reemplazos = {
        "–": "-", "—": "-", "−": "-",
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "•": "-", "·": "-", "…": "...",
        "→": "->", "←": "<-", "≥": ">=", "≤": "<=",
    }

    def limpiar(t: str) -> str:
        for original, nuevo in reemplazos.items():
            t = t.replace(original, nuevo)
        # Elimina lo que no exista en latin-1 (emojis, etc.) en vez de poner "?"
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

if not df.empty:
    df["fecha_registro"] = (
        pd.to_datetime(df["fecha_registro"], utc=True).dt.tz_convert("America/Bogota")
    )

# ---------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------
st.markdown("""
<div class="hero">
    <h1>🌱 Asesor Inteligente · Vivero CECAR</h1>
    <p>Monitoreo climático y recomendaciones de riego en tiempo real · Estación Sainlogic SA7</p>
</div>
""", unsafe_allow_html=True)

if st.button("🔄 Actualizar ahora"):
    st.rerun()

if df.empty:
    st.warning("Todavía no hay datos guardados. Corre `python main_diario.py` primero.")
    st.stop()

ultimo = df.iloc[0]
color_riego, icono_riego, texto_riego = COLORES_RIEGO.get(
    ultimo["orden_riego"], ("#22C55E", "💧", ultimo["orden_riego"])
)
if ultimo["alerta"]:
    color_riego, icono_riego = "#EF4444", "🚨"

# ---------------------------------------------------------------
# Banner de decisión de riego
# ---------------------------------------------------------------
st.markdown(f"""
<div class="banner" style="--c:{color_riego}">
    <div class="t">{icono_riego} {texto_riego.upper()}</div>
    <div class="m">{ultimo['mensaje']}</div>
    <div class="r">{ultimo['regla_aplicada']} · Actualizado: {ultimo['fecha_registro'].strftime('%d/%m/%Y %H:%M')}</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Estado Actual", "📈 Historial", "📰 Boletines"])

# ===== TAB 1: Estado actual =====
with tab1:
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("🌡️", "Temperatura", ultimo["temperatura_c"], "°C", "#F87171")
    with c2:
        kpi_card("🌧️", "Precipitación", ultimo["precipitacion_mm"], "mm", "#38BDF8")
    with c3:
        kpi_card("💦", "Humedad", ultimo["humedad_relativa_pct"], "%", "#2DD4BF")
    with c4:
        kpi_card("💨", "Ráfaga", ultimo["rafaga_viento_kmh"], "km/h", "#FBBF24")
    with c5:
        kpi_card("☀️", "Radiación", ultimo["radiacion_solar_wm2"], "W/m²", "#FB923C")

    st.markdown("<br>", unsafe_allow_html=True)

    g1, g2, g3 = st.columns(3)
    with g1:
        st.plotly_chart(
            gauge(ultimo["temperatura_c"], "Temperatura", [0, 50], "#F87171", " °C", 33),
            use_container_width=True,
        )
    with g2:
        st.plotly_chart(
            gauge(ultimo["humedad_relativa_pct"], "Humedad relativa", [0, 100], "#2DD4BF", " %"),
            use_container_width=True,
        )
    with g3:
        st.plotly_chart(
            gauge(ultimo["rafaga_viento_kmh"], "Ráfaga de viento", [0, 100], "#FBBF24", " km/h", UMBRAL_VIENTO),
            use_container_width=True,
        )
    st.caption("La línea roja en cada medidor marca el umbral que activa una regla del sistema.")

# ===== TAB 2: Historial =====
with tab2:
    d = df.sort_values("fecha_registro")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=d["fecha_registro"], y=d["temperatura_c"], name="Temperatura (°C)",
        mode="lines+markers", line=dict(color="#F87171", width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=d["fecha_registro"], y=d["humedad_relativa_pct"], name="Humedad (%)",
        mode="lines+markers", line=dict(color="#2DD4BF", width=3)), secondary_y=True)
    fig.update_yaxes(title_text="°C", secondary_y=False)
    fig.update_yaxes(title_text="%", secondary_y=True)
    fig.update_layout(title="Temperatura vs. Humedad")
    st.plotly_chart(estilo_figura(fig), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        fig2 = go.Figure(go.Bar(
            x=d["fecha_registro"], y=d["precipitacion_mm"], marker_color="#38BDF8"))
        fig2.update_layout(title="Precipitación (mm)")
        st.plotly_chart(estilo_figura(fig2, 320), use_container_width=True)
    with col_b:
        conteo = df["regla_aplicada"].value_counts()
        fig3 = go.Figure(go.Pie(
            labels=conteo.index, values=conteo.values, hole=0.55,
            marker=dict(colors=["#22C55E", "#38BDF8", "#F97316", "#EF4444"])))
        fig3.update_layout(title="Reglas activadas")
        st.plotly_chart(estilo_figura(fig3, 320), use_container_width=True)

    with st.expander("🗂️ Ver tabla completa de registros"):
        st.dataframe(df)

# ===== TAB 3: Boletines =====
with tab3:
    if boletines.empty:
        st.info("Aún no se ha generado ningún boletín. Corre `python ai_agent.py`.")
    else:
        for _, fila in boletines.iterrows():
            titulo = f"Boletín Climático - Vivero CECAR ({fila['fecha_inicio']} al {fila['fecha_fin']})"
            with st.expander(f"📰 Boletín del {fila['fecha_inicio']} al {fila['fecha_fin']}"):
                st.write(fila["contenido"])

                col_pdf, col_txt, _ = st.columns([1, 1, 4])
                with col_pdf:
                    st.download_button(
                        "⬇️ Descargar PDF",
                        data=boletin_a_pdf(titulo, fila["contenido"]),
                        file_name=f"boletin_{fila['fecha_inicio']}_{fila['fecha_fin']}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{fila['id']}",
                    )
                with col_txt:
                    st.download_button(
                        "⬇️ Descargar TXT",
                        data=f"{titulo}\n\n{fila['contenido']}",
                        file_name=f"boletin_{fila['fecha_inicio']}_{fila['fecha_fin']}.txt",
                        mime="text/plain",
                        key=f"txt_{fila['id']}",
                    )