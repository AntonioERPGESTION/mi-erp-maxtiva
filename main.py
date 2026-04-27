import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Fix Credentials", layout="wide")

# --- CONEXIÓN MEJORADA ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # OPCIÓN A: Streamlit Cloud (Secrets)
    if "gcp_service_account" in st.secrets:
        try:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"Error en Secrets: {e}")
            return None
            
    # OPCIÓN B: Local (Archivo credentials.json)
    import os
    if os.path.exists("credentials.json"):
        try:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"Error en archivo local: {e}")
            return None
    
    # Si nada funciona:
    st.warning("⚠️ No se han encontrado credenciales. Asegúrate de subir 'credentials.json' o configurar los 'Secrets' en Streamlit Cloud.")
    return None

def load_data():
    client = get_gsheet_client()
    if client:
        try:
            # Intentamos abrir las hojas por su nombre exacto
            sh_obras = client.open("ERP MAXTIVA").worksheet("Obras")
            sh_gastos = client.open("gastos MAXTIVA").get_worksheet(0)
            
            df_o = pd.DataFrame(sh_obras.get_all_records())
            df_g = pd.DataFrame(sh_gastos.get_all_records())
            return df_o, df_g, True
        except Exception as e:
            st.error(f"No se pudo acceder a las tablas: {e}. ¿Has compartido las hojas con el email del JSON?")
    return pd.DataFrame(), pd.DataFrame(), False

# --- LÓGICA DE INICIO ---
if "autenticado" not in st.session_state:
    st.session_state.db_obras, st.session_state.db_gastos, st.session_state.autenticado = load_data()

# --- INTERFAZ ---
st.sidebar.title("🏢 GRUPO MAXTIVA")
if not st.session_state.autenticado:
    if st.button("🔄 Reintentar Conexión"):
        st.session_state.db_obras, st.session_state.db_gastos, st.session_state.autenticado = load_data()
        st.rerun()
else:
    menu = st.sidebar.radio("Menú", ["Dashboard", "Gestión"])
    
    if menu == "Dashboard":
        st.title("📊 Panel de Control")
        if not st.session_state.db_obras.empty:
            st.metric("Total Presupuestos", f"{st.session_state.db_obras['PRESUPUESTO'].sum():,.2f} €")
            st.dataframe(st.session_state.db_obras)
        else:
            st.info("La hoja de Obras está vacía o no tiene el formato correcto.")
