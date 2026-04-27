import streamlit as st
from streamlit_gsheets import GSheetsConnection
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

# --- CONEXIÓN DIRECTA ---
def cargar_datos():
    try:
        # Conexión 1: ERP MAXTIVA
        conn_erp = st.connection("gsheets_erp", type=GSheetsConnection)
        df_o = conn_erp.read(worksheet="Obras", ttl=0)
        
        # Conexión 2: gastos MAXTIVA
        conn_g = st.connection("gsheets_gastos", type=GSheetsConnection)
        df_g = conn_g.read(ttl=0) 
        
        return df_o, df_g, True
    except Exception as e:
        st.error(f"Fallo de conexión: {e}")
        return pd.DataFrame(), pd.DataFrame(), False

df_obras, df_gastos, conectado = cargar_datos()

# --- INTERFAZ ---
with st.sidebar:
    st.title("🏢 GRUPO MAXTIVA")
    if conectado:
        st.success("✅ Datos Sincronizados")
        menu = st.radio("MENÚ", ["📊 Dashboard", "🏗️ Gestión Obras", "📦 Pedidos PDF"])
    else:
        st.error("❌ Sin conexión a Drive")
        menu = None

if conectado and menu:
    if menu == "📊 Dashboard":
        st.title("Resumen Ejecutivo Maxtiva")
        
        # Métricas (Usando nombres exactos de tu imagen)
        c1, c2 = st.columns(2)
        total_presu = df_obras['PRESUPUESTO'].sum() if 'PRESUPUESTO' in df_obras.columns else 0
        c1.metric("Presupuesto en Curso", f"{total_presu:,.2f} €")
        
        st.divider()
        st.subheader("Obras Actuales")
        st.dataframe(df_obras[['ID', 'CLIENTE', 'PRESUPUESTO', 'ESTADO', 'NOMBRE']], use_container_width=True)

    elif menu == "🏗️ Gestión Obras":
        st.title("Gestión de Proyectos")
        st.dataframe(df_obras)
        st.info("💡 Edita el Excel original para ver cambios aquí.")

    elif menu == "📦 Pedidos PDF":
        st.title("Extractor de Datos")
        archivo = st.file_uploader("Subir factura PDF", type="pdf")
        if archivo:
            with pdfplumber.open(archivo) as pdf:
                texto = "\n".join([p.extract_text() for p in pdf.pages])
            st.success("PDF procesado.")
            st.text_area("Contenido:", texto[:500])

    if st.sidebar.button("🔄 Refrescar Todo"):
        st.cache_data.clear()
        st.rerun()
