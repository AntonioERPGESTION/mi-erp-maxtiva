import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MA XTIVA ERP - SISTEMA INTEGRAL", layout="wide", page_icon="🏢")

# Estilos visuales
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #FFD700; }
    .stMetric { background-color: white; border: 2px solid #FFD700; padding: 15px; border-radius: 10px; }
    .stButton>button { width: 100%; background-color: #1e3d59; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
def cargar_datos():
    try:
        url_erp = st.secrets["gsheets"]["erp"]
        url_gastos = st.secrets["gsheets"]["gastos"]
        df_o = pd.read_csv(url_erp)
        df_g = pd.read_csv(url_gastos)
        return df_o, df_g, True
    except:
        return pd.DataFrame(), pd.DataFrame(), False

df_o, df_g, conectado = cargar_datos()

# --- BARRA LATERAL (MENÚ COMPLETO) ---
with st.sidebar:
    st.title("🏢 GRUPO MAXTIVA")
    st.divider()
    if conectado:
        st.success("Sincronizado con Drive")
        menu = st.radio("SECCIONES", [
            "📊 Dashboard General",
            "🏗️ Gestión de Obras",
            "👥 Empleados",
            "⏱️ Control de Horas",
            "💸 Gastos y Facturas",
            "📦 Extractor PDF (IA)"
        ])
    else:
        st.error("Error de Conexión")
        menu = None

# --- MÓDULOS DEL SISTEMA ---
if conectado:
    
    if menu == "📊 Dashboard General":
        st.title("📊 Resumen Ejecutivo")
        c1, c2, c3 = st.columns(3)
        # Cálculos automáticos
        ingresos = df_o['PRESUPUESTO'].sum() if 'PRESUPUESTO' in df_o.columns else 0
        gastos = df_g['Importe'].sum() if 'Importe' in df_g.columns else 0
        
        c1.metric("Presupuesto en Curso", f"{ingresos:,.2f} €")
        c2.metric("Gastos Acumulados", f"{gastos:,.2f} €")
        c3.metric("Margen Neto", f"{ingresos - gastos:,.2f} €")
        
        st.subheader("Obras por Estado")
        if 'ESTADO' in df_o.columns:
            st.bar_chart(df_o['ESTADO'].value_value_counts())

    elif menu == "🏗️ Gestión de Obras":
        st.title("🏗️ Listado de Obras y Proyectos")
        st.dataframe(df_o, use_container_width=True)
        st.info("Para añadir o borrar obras, usa el Excel 'ERP MAXTIVA'.")

    elif menu == "👥 Empleados":
        st.title("👥 Gestión de Personal")
        # Aquí puedes crear una pestaña en tu Excel llamada "Empleados"
        st.info("Este módulo muestra los empleados activos registrados en la base de datos.")
        st.write("### Plantilla Actual")
        st.warning("Crea una pestaña llamada 'Empleados' en tu Excel para ver los nombres aquí.")

    elif menu == "⏱️ Control de Horas":
        st.title("⏱️ Registro de Jornadas")
        st.write("Control de horas por trabajador y obra.")
        # Ejemplo de tabla manual hasta que tengas la pestaña en Drive
        df_horas = pd.DataFrame({"Empleado": ["Juan", "Pedro"], "Horas": [8, 7], "Obra": ["Primor", "Sinergym"]})
        st.table(df_horas)

    elif menu == "💸 Gastos y Facturas":
        st.title("💸 Control de Gastos")
        st.write("Datos extraídos de 'gastos MAXTIVA':")
        st.dataframe(df_g, use_container_width=True)

    elif menu == "📦 Extractor PDF (IA)":
        st.title("📦 Extractor de Datos PDF")
        archivo = st.file_uploader("Subir PDF de proveedor", type="pdf")
        if archivo:
            with pdfplumber.open(archivo) as pdf:
                texto = "\n".join([p.extract_text() for p in pdf.pages])
            st.success("Análisis completado")
            importes = re.findall(r"(\d+[\.,]\d{2})", texto)
            if importes:
                st.info(f"Importe detectado: {importes[-1]} €")
            st.text_area("Contenido extraído:", texto[:800])

    if st.sidebar.button("🔄 Refrescar Todo"):
        st.rerun()

else:
    st.error("Por favor, verifica los Secrets y que las hojas sean públicas.")
