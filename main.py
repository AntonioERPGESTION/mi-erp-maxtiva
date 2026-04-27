import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MA XTIVA ERP", layout="wide", page_icon="🏗️")

# Estilos visuales
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #FFD700; }
    .stMetric { background-color: white; border: 2px solid #FFD700; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN DE CARGA POR CSV (MÉTODO ROBUSTO) ---
def cargar_datos_maxtiva():
    try:
        # Leemos las URLs desde el diccionario 'gsheets' en Secrets
        url_erp = st.secrets["gsheets"]["erp"]
        url_gastos = st.secrets["gsheets"]["gastos"]
        
        # Lectura directa
        df_o = pd.read_csv(url_erp)
        df_g = pd.read_csv(url_gastos)
        
        return df_o, df_g, True
    except Exception as e:
        st.error(f"Error de lectura: {e}")
        return pd.DataFrame(), pd.DataFrame(), False

# --- EJECUCIÓN ---
df_obras, df_gastos, conectado = cargar_datos_maxtiva()

# --- INTERFAZ ---
st.sidebar.title("🏢 GRUPO MAXTIVA")

if conectado:
    st.sidebar.success("✅ Conectado a Google Drive")
    menu = st.sidebar.radio("MENÚ", ["📊 Dashboard", "🏗️ Gestión Obras", "📦 Pedidos PDF"])

    if menu == "📊 Dashboard":
        st.title("📊 Panel de Control Maxtiva")
        
        col1, col2, col3 = st.columns(3)
        
        # Nombres de columnas basados en tu imagen de Excel
        # Asegúrate de que en el Excel la columna se llame exactamente PRESUPUESTO e Importe
        ingresos = df_obras['PRESUPUESTO'].sum() if 'PRESUPUESTO' in df_obras.columns else 0
        gastos = df_gastos['Importe'].sum() if 'Importe' in df_gastos.columns else 0
        
        col1.metric("Presupuesto Total", f"{ingresos:,.2f} €")
        col2.metric("Gastos Acumulados", f"{gastos:,.2f} €")
        col3.metric("Margen Neto", f"{ingresos - gastos:,.2f} €")
        
        st.divider()
        st.subheader("Obras en Sistema")
        st.dataframe(df_obras, use_container_width=True)

    elif menu == "🏗️ Gestión Obras":
        st.title("🏗️ Gestión de Proyectos")
        st.write("Datos sincronizados con ERP MAXTIVA:")
        st.dataframe(df_obras, use_container_width=True)
        st.info("💡 Para actualizar: edita tu Excel y pulsa el botón 'Actualizar Datos'.")

    elif menu == "📦 Pedidos PDF":
        st.title("📦 Extractor de Datos PDF")
        pdf_file = st.file_uploader("Sube el pedido/factura", type="pdf")
        if pdf_file:
            with pdfplumber.open(pdf_file) as pdf:
                full_text = "\n".join([page.extract_text() for page in pdf.pages])
            
            # Buscar importes
            matches = re.findall(r"(\d+[\.,]\d{2})", full_text)
            if matches:
                st.success(f"Importe sugerido: {matches[-1]} €")
            
            st.text_area("Texto extraído:", full_text[:1000], height=300)

    if st.sidebar.button("🔄 Actualizar Datos"):
        st.rerun()

else:
    st.error("❌ Fallo de conexión: No se pudieron leer las hojas.")
    st.info("REVISA ESTO: \n1. En Google Sheets, ve a 'Compartir' y pon 'Cualquier persona con el enlace'. \n2. Verifica que las URLs en Secrets sean correctas.")
