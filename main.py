import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="MA XTIVA ERP", layout="wide")

# Estilos Maxtiva
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #FFD700; }
    .stMetric { background-color: white; border: 2px solid #FFD700; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN DE CARGA SEGURA ---
def cargar_datos():
    try:
        # Cargamos directamente desde la URL de exportación CSV definida en Secrets
        url_erp = st.secrets["gsheets"]["erp"]
        url_gastos = st.secrets["gsheets"]["gastos"]
        
        df_o = pd.read_csv(url_erp)
        df_g = pd.read_csv(url_gastos)
        
        return df_o, df_g, True
    except Exception as e:
        st.error(f"Error de lectura: {e}")
        return pd.DataFrame(), pd.DataFrame(), False

# --- INICIO DE APP ---
df_obras, df_gastos, conectado = cargar_datos()

st.sidebar.title("🏢 GRUPO MAXTIVA")

if conectado:
    st.sidebar.success("✅ Conexión Establecida")
    menu = st.sidebar.radio("MENÚ", ["📊 Dashboard", "🏗️ Gestión Obras", "📦 Pedidos PDF"])

    if menu == "📊 Dashboard":
        st.title("Resumen Ejecutivo Maxtiva")
        
        # Métricas
        c1, c2, c3 = st.columns(3)
        # Ajustamos los nombres de columnas según tu imagen de Excel
        ingresos = df_obras['PRESUPUESTO'].sum() if 'PRESUPUESTO' in df_obras.columns else 0
        gastos = df_gastos['Importe'].sum() if 'Importe' in df_gastos.columns else 0
        
        c1.metric("Ingresos (Obras)", f"{ingresos:,.2f} €")
        c2.metric("Gastos Totales", f"{gastos:,.2f} €")
        c3.metric("Diferencia", f"{ingresos - gastos:,.2f} €")
        
        st.divider()
        st.subheader("Listado de Obras (Desde ERP MAXTIVA)")
        st.dataframe(df_obras, use_container_width=True)

    elif menu == "🏗️ Gestión Obras":
        st.title("Gestión de Proyectos")
        st.dataframe(df_obras)
        st.info("Para actualizar datos, modifica tu Google Sheets y refresca esta página.")

    elif menu == "📦 Pedidos PDF":
        st.title("Extractor de Pedidos")
        archivo = st.file_uploader("Subir PDF", type="pdf")
        if archivo:
            with pdfplumber.open(archivo) as pdf:
                texto = "\n".join([p.extract_text() for p in pdf.pages])
            st.success("Análisis completado")
            st.text_area("Texto detectado:", texto[:800])

    if st.sidebar.button("🔄 Refrescar Todo"):
        st.rerun()
else:
    st.error("❌ Fallo crítico de conexión.")
    st.info("Asegúrate de que tus Google Sheets estén compartidas como: 'Cualquier persona con el enlace puede leer'.")
