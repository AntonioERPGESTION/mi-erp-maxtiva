import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pdfplumber
import re
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Cloud Sync", layout="wide", page_icon="🏗️")

# --- ESTILOS AMARILLO CORPORATIVO ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8f9fa; }}
    [data-testid="stSidebar"] {{ background-color: #FFD700; color: #1e3d59; }}
    .stMetric {{ background-color: white; border: 2px solid #FFD700; border-radius: 10px; }}
    .stButton>button {{ background-color: #FFD700; color: #1e3d59; font-weight: bold; width: 100%; }}
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN A GOOGLE SHEETS ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Asegúrate de que el archivo credentials.json esté en la carpeta
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    return gspread.authorize(creds)

def load_data_from_sheets():
    client = get_gsheet_client()
    # Conectamos con tus archivos reales
    sh_obras = client.open("ERP MAXTIVA").worksheet("Obras")
    sh_gastos = client.open("gastos MAXTIVA").get_worksheet(0) # La primera pestaña
    
    df_obras = pd.DataFrame(sh_obras.get_all_records())
    df_gastos = pd.DataFrame(sh_gastos.get_all_records())
    return df_obras, df_gastos

# --- INICIALIZACIÓN ---
if "db_obras" not in st.session_state:
    try:
        st.session_state.db_obras, st.session_state.db_gastos = load_data_from_sheets()
    except Exception as e:
        st.error(f"Error de conexión: {e}. Asegúrate de tener el archivo credentials.json y haber compartido la Sheet.")

# --- FUNCIONES DE ESCRITURA ---
def add_row_to_sheet(file_name, sheet_name, row):
    client = get_gsheet_client()
    sh = client.open(file_name).worksheet(sheet_name)
    sh.append_row(row)
    st.toast("✅ Sincronizado con Google Drive")

# --- MÓDULO DASHBOARD ---
def modulo_dashboard():
    st.title("📊 Panel de Control en Tiempo Real")
    obras = st.session_state.db_obras
    gastos = st.session_state.db_gastos
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Presupuestado", f"{obras['PRESUPUESTO'].sum():,.2f} €")
    col2.metric("Gasto Acumulado", f"{gastos['Importe'].sum():,.2f} €")
    col3.metric("Margen Bruto", f"{obras['PRESUPUESTO'].sum() - gastos['Importe'].sum():,.2f} €")
    
    st.divider()
    st.subheader("Obras Activas (Drive)")
    st.dataframe(obras, use_container_width=True)

# --- MÓDULO GASTOS (CON ESCRITURA EN DRIVE) ---
def modulo_gastos():
    st.title("💸 Registro de Gastos Imputables")
    with st.form("nuevo_gasto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        usuario = col1.text_input("Usuario", value="Admin")
        fecha = col2.date_input("Fecha", value=None)
        cat = st.selectbox("Categoría", ["Gasolina", "Dietas", "Hotel", "Suministros"])
        con = st.text_input("Concepto")
        imp = st.number_input("Importe", min_value=0.0)
        
        if st.form_submit_button("Guardar en Google Sheets"):
            # Preparar fila para el Drive según tus columnas: Usuario, Fecha, Categoría, Concepto, Importe, URL, Estado
            nueva_fila = [usuario, str(fecha), cat, con, imp, "", "Pendiente"]
            add_row_to_sheet("gastos MAXTIVA", "Hoja 1", nueva_fila)
            # Recargar datos locales
            st.session_state.db_obras, st.session_state.db_gastos = load_data_from_sheets()
            st.rerun()

# --- NAVEGACIÓN ---
def main():
    with st.sidebar:
        st.write("### 🏗️ MA XTIVA ERP v14")
        st.divider()
        menu = st.radio("MENÚ", ["Dashboard", "Registrar Gasto", "Pedidos PDF"])
        if st.button("🔄 Forzar Sincronización"):
            st.session_state.db_obras, st.session_state.db_gastos = load_data_from_sheets()
            st.rerun()

    if menu == "Dashboard": modulo_dashboard()
    elif menu == "Registrar Gasto": modulo_gastos()

if __name__ == "__main__":
    main()
