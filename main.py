import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import pdfplumber
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="MAXTIVA ERP - SISTEMA OK", layout="wide")

# --- LÓGICA DE CARGA ---
def load_data():
    try:
        # Conexión 1: ERP (ID: 1dJWM...HQ3BM)
        conn_erp = st.connection("gsheets_erp", type=GSheetsConnection)
        df_o = conn_erp.read(worksheet="Obras") # Asegúrate que la pestaña se llame Obras
        
        # Conexión 2: Gastos (ID: 1u85J...V5ybg)
        conn_g = st.connection("gsheets_gastos", type=GSheetsConnection)
        df_g = conn_g.read() # Lee la primera pestaña
        
        return df_o, df_g, True
    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")
        return pd.DataFrame(), pd.DataFrame(), False

# --- PROCESO ---
df_o, df_g, conectado = load_data()

# --- INTERFAZ ---
st.sidebar.title("🏢 GRUPO MAXTIVA")

if conectado:
    st.sidebar.success("✅ Conectado a Drive")
    menu = st.sidebar.radio("MENÚ", ["📊 Dashboard", "🏗️ Gestión Obras", "📦 Pedidos PDF"])

    if menu == "📊 Dashboard":
        st.title("Panel de Control")
        c1, c2 = st.columns(2)
        
        # Intentamos calcular totales si las columnas existen
        try:
            total_presu = df_o['PRESUPUESTO'].sum()
            total_gastos = df_g['Importe'].sum()
            c1.metric("Ingresos Totales", f"{total_presu:,.2f} €")
            c2.metric("Gastos Totales", f"{total_gastos:,.2f} €")
        except:
            st.warning("Verifica que las columnas se llamen 'PRESUPUESTO' e 'Importe'.")

        st.write("### Vista de Obras")
        st.dataframe(df_o, use_container_width=True)

    elif menu == "🏗️ Gestión Obras":
        st.title("Gestión de Obras")
        st.dataframe(df_o)
        st.info("💡 Edita directamente en Google Sheets y pulsa el botón de abajo.")

    elif menu == "📦 Pedidos PDF":
        st.title("Extractor de Datos")
        up = st.file_uploader("Subir PDF", type="pdf")
        if up:
            with pdfplumber.open(up) as pdf:
                texto = "\n".join([p.extract_text() for p in pdf.pages])
            st.text_area("Contenido:", texto[:500])

    if st.sidebar.button("🔄 Refrescar Datos"):
        st.cache_data.clear()
        st.rerun()
else:
    st.error("⚠️ No se pudo conectar. Revisa que el formato TOML en Secrets sea el correcto.")
