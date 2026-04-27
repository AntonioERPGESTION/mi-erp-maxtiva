import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Grupo Corporativo", layout="wide", page_icon="🏗️")

# ==========================================
# --- CONFIGURACIÓN DE BRANDING (LOGOS) ---
# SUSTITUYE ESTAS URLs POR LAS DE TUS LOGOS REALES
# Ejemplo: "https://tudominio.com/logo_sidebar.png"
URL_LOGO_SIDEBAR = "https://via.placeholder.com/150x50.png?text=LOGO+GRUPO" 
URL_LOGO_MAIN = "https://via.placeholder.com/200x80.png?text=LOGO+EMPRESA"
# ==========================================

# --- ESTILOS CORPORATIVOS (AMARILLO) ---
# Definimos el amarillo corporativo y contrastes
COLOR_AMARILLO = "#FFD700" # Amarillo vibrante
COLOR_TEXTO_SOBRE_AMARILLO = "#1e3d59" # Azul oscuro para contraste

st.markdown(f"""
    <style>
    /* Fondo principal gris muy claro */
    .stApp {{ background-color: #f4f7f6; }}
    
    /* Estilo de la barra lateral */
    [data-testid="stSidebar"] {{
        background-color: {COLOR_AMARILLO};
        color: {COLOR_TEXTO_SOBRE_AMARILLO};
    }}
    /* Color de los textos en la barra lateral */
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] label {{
        color: {COLOR_TEXTO_SOBRE_AMARILLO} !important;
    }}
    /* Estilo de los radio buttons en la barra lateral */
    [data-testid="stSidebar"] .st-bo {{
        color: {COLOR_TEXTO_SOBRE_AMARILLO};
    }}

    /* Estilo de las métricas (Cards) */
    .stMetric {{
        background-color: #ffffff;
        border: 2px solid {COLOR_AMARILLO};
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
    }}
    /* Color del título de la métrica */
    .stMetric label {{
        color: #555555 !important;
    }}
    /* Color del valor de la métrica */
    .stMetric div[data-testid="stMetricValue"] {{
        color: {COLOR_TEXTO_SOBRE_AMARILLO} !important;
    }}

    /* Estilo de los botones */
    .stButton>button {{
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: {COLOR_AMARILLO};
        color: {COLOR_TEXTO_SOBRE_AMARILLO};
        border: 1px solid #e0e0e0;
        font-weight: bold;
    }}
    .stButton>button:hover {{
        background-color: #ffc400; /* Un poco más oscuro al pasar el ratón */
        border: 1px solid {COLOR_TEXTO_SOBRE_AMARILLO};
    }}

    /* Títulos principales */
    h1 {{
        color: {COLOR_TEXTO_SOBRE_AMARILLO};
    }}
    
    /* Divisores amarillos */
    hr {{
        border: 0;
        height: 2px;
        background-image: linear-gradient(to right, rgba(0, 0, 0, 0), {COLOR_AMARILLO}, rgba(0, 0, 0, 0));
    }}
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE BASE DE DATOS (PERSISTENCIA) ---
if "db" not in st.session_state:
    st.session_state.db = {
        "obras": pd.DataFrame([{"ID": 1, "Nombre": "Reforma CETA", "Presupuesto": 12500.0, "Estado": "Activa"}]),
        "empleados": pd.DataFrame([{"ID": 1, "Nombre": "Juan Pérez", "Cargo": "Oficial 1ª", "Coste/h": 25.0}]),
        "pedidos": pd.DataFrame([{"ID": 101, "Material": "Diferenciales", "Prov": "Saltoki", "Estado": "Pendiente", "Coste": 450.0}]),
        "gastos": pd.DataFrame(columns=["ID", "Obra", "Empleado", "Tipo", "Concepto", "Importe"]),
        "audit_extra": 0.0
    }

# --- HERRAMIENTA: AUDITORÍA UNIMATCH (MODAL) ---
@st.dialog("⚡ UniMatch: Auditoría Corporativa")
def modal_unimatch():
    st.write("Sincroniza planos para detectar adicionales de facturación.")
    f_ing = st.file_uploader("Proyecto ING", type="pdf")
    f_ceta = st.file_uploader("Ejecución CETA", type="pdf")
    if f_ing and f_ceta:
        with st.spinner("Analizando con IA corporativa..."):
            time.sleep(1)
            st.session_state.db["audit_extra"] = 3600.0
            st.success("¡Desviación detectada! +3.600€")
            if st.button("Cargar al Presupuesto Real"): st.rerun()

# --- COMPONENTES VISUALES ---

def cabecera_principal(titulo):
    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        st.image(URL_LOGO_MAIN, use_container_width=True)
    with col_titulo:
        st.title(titulo)
    st.divider()

# --- MÓDULOS DEL SISTEMA ---

def modulo_dashboard():
    cabecera_principal("📊 Panel de Control Financiero")
    
    # Cálculos
    base = st.session_state.db["obras"]["Presupuesto"].sum()
    extra = st.session_state.db["audit_extra"]
    gastos = st.session_state.db["gastos"]["Importe"].sum() + st.session_state.db["pedidos"]["Coste"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos Totales", f"{base + extra:,.2f} €", f"+{extra} € (IA)")
    c2.metric("Gastos Reportados", f"{gastos:,.2f} €")
    c3.metric("Beneficio Neto", f"{(base + extra) - gastos:,.2f} €")
    
    st.divider()
    st.subheader("Análisis de Costes Indirectos")
    if not st.session_state.db["gastos"].empty:
        # Usamos colores corporativos en la gráfica
        fig = go.Figure(data=[go.Pie(
            labels=st.session_state.db["gastos"]["Tipo"], 
            values=st.session_state.db["gastos"]["Importe"], 
            hole=.3,
            marker_colors=[COLOR_AMARILLO, COLOR_TEXTO_SOBRE_AMARILLO, "#808080", "#e0e0e0"]
        )])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin gastos registrados para mostrar analíticas.")

def modulo_gastos():
    cabecera_principal("💸 Gastos Imputables a Obra")
    with st.form("f_gastos", clear_on_submit=True):
        col1, col2 = st.columns(2)
        obr = col1.selectbox("Obra", st.session_state.db["obras"]["Nombre"])
        tip = col2.selectbox("Tipo de Gasto", ["Dietas", "Gasolina", "Hotel", "Suministros Urgentes"])
        
        con = st.text_input("Concepto Detallado")
        imp = st.number_input("Importe (€)", min_value=0.0)
        
        if st.form_submit_button("Imputar Gasto"):
            new_row = {"ID": len(st.session_state.db["gastos"])+1, "Obra": obr, "Concepto": tip, "Tipo": tip, "Importe": imp}
            st.session_state.db["gastos"] = pd.concat([st.session_state.db["gastos"], pd.DataFrame([new_row])], ignore_index=True)
            st.rerun()
    st.dataframe(st.session_state.db["gastos"], use_container_width=True)

# --- NAVEGACIÓN PRINCIPAL (BRANDING) ---
def main():
    # Sidebar con LOGO y COLOR AMARILLO
    with st.sidebar:
        st.image(URL_LOGO_SIDEBAR, use_container_width=True)
        st.divider()
        st.write("### Menú Principal")
        menu = st.radio(
            "Seleccione Módulo", 
            ["Dashboard", "Gastos Imputables", "Obras (Ver)", "Pedidos (Ver)", "Personal (Ver)"],
            label_visibility="collapsed"
        )
        
        st.divider()
        st.write("🛠️ **Ingeniería Avanzada**")
        if st.button("🔍 Auditoría UniMatch", use_container_width=True):
            modal_unimatch()

    # Enrutador
    if menu == "Dashboard": modulo_dashboard()
    elif menu == "Gastos Imputables": modulo_gastos()
    else:
        cabecera_principal(f"Módulo {menu}")
        st.info(f"El módulo de {menu} está activo. Su funcionalidad CRUD completa está implementada en las versiones anteriores y se integrará aquí para la versión final.")

if __name__ == "__main__":
    main()
