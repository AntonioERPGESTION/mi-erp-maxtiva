import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import pdfplumber
import re

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="MA XTIVA ERP", layout="wide", page_icon="🏗️")

# Estilos Maxtiva
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #FFD700; }
    .stMetric { background-color: white; border: 2px solid #FFD700; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN DIRECTA A LAS 2 HOJAS ---
def cargar_datos():
    try:
        # Conexión 1: ERP (Obras)
        conn_erp = st.connection("gsheets_erp", type=GSheetsConnection)
        # Especificamos la pestaña 'Obras' que vemos en tu captura de pantalla
        df_o = conn_erp.read(worksheet="Obras", ttl=0)
        
        # Conexión 2: Gastos
        conn_g = st.connection("gsheets_gastos", type=GSheetsConnection)
        df_g = conn_g.read(ttl=0) 
        
        return df_o, df_g, True
    except Exception as e:
        st.error(f"Error al conectar con las hojas: {e}")
        return pd.DataFrame(), pd.DataFrame(), False

# --- LÓGICA PRINCIPAL ---
df_obras, df_gastos, conectado = cargar_datos()

st.sidebar.title("🏢 GRUPO MAXTIVA")

if conectado:
    st.sidebar.success("✅ Conectado a ERP y Gastos")
    menu = st.sidebar.radio("MENÚ PRINCIPAL", ["📊 Dashboard", "🏗️ Gestión de Obras", "📦 Pedidos PDF"])

    if menu == "📊 Dashboard":
        st.title("📊 Resumen Ejecutivo Maxtiva")
        
        # Métricas principales
        c1, c2, c3 = st.columns(3)
        ingresos = df_obras['PRESUPUESTO'].sum() if 'PRESUPUESTO' in df_obras.columns else 0
        gastos = df_gastos['Importe'].sum() if not df_gastos.empty and 'Importe' in df_gastos.columns else 0
        
        c1.metric("Presupuestado Total", f"{ingresos:,.2f} €")
        c2.metric("Gastos Registrados", f"{gastos:,.2f} €")
        c3.metric("Margen Estimado", f"{ingresos - gastos:,.2f} €")
        
        st.divider()
        st.subheader("Obras en Curso (Desde ERP MAXTIVA)")
        st.dataframe(df_obras, use_container_width=True)

    elif menu == "🏗️ Gestión de Obras":
        st.title("🏗️ Gestión de Obras")
        st.write("Datos extraídos de la pestaña 'Obras':")
        st.dataframe(df_obras, use_container_width=True)
        st.info("💡 Para actualizar: modifica el Excel en Google Drive y pulsa 'Refrescar Todo'.")

    elif menu == "📦 Pedidos PDF":
        st.title("📦 Extractor de Datos PDF")
        archivo = st.file_uploader("Sube el PDF de la factura", type="pdf")
        if archivo:
            with pdfplumber.open(archivo) as pdf:
                texto = "\n".join([pagina.extract_text() for pagina in pdf.pages])
            
            # Buscar importes con decimales
            importes = re.findall(r"(\d+[\.,]\d{2})", texto)
            if importes:
                st.success(f"Importe detectado: **{importes[-1]} €**")
            
            st.text_area("Texto extraído del documento:", texto[:800], height=300)

    # Botón de refresco manual
    if st.sidebar.button("🔄 Refrescar Todo"):
        st.cache_data.clear()
        st.rerun()

else:
    st.warning("⚠️ El sistema no detecta las URLs en los Secrets o las hojas no son públicas.")
    st.info("Asegúrate de que en Google Sheets pusiste: 'Cualquier persona con el enlace puede leer'.")
