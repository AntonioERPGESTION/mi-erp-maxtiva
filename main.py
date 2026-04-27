import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        if "gcp_service_account" in st.secrets:
            # Creamos una copia de los secretos para no alterar el original
            info = dict(st.secrets["gcp_service_account"])
            
            # --- LIMPIEZA EXTREMA DE LA LLAVE ---
            # 1. Quitamos los literales "\n" que a veces se pegan como texto
            # 2. Aseguramos que los saltos de línea sean los correctos para Python
            raw_key = info["private_key"]
            clean_key = raw_key.replace("\\n", "\n").strip()
            
            # 3. Si por algún motivo la llave se pegó en una sola línea, esto la restaura
            if "-----BEGIN PRIVATE KEY-----" in clean_key and "\n" not in clean_key[26:-24]:
                st.error("La llave parece estar en una sola línea. Revisa el formato en Secrets.")
            
            info["private_key"] = clean_key
            
            creds = Credentials.from_service_account_info(info, scopes=scope)
            return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error crítico de seguridad: {e}")
    return None

# --- CARGA DE DATOS SIN BLOQUEOS ---
def load_maxtiva_data():
    client = get_gsheet_client()
    if client:
        try:
            # Sincronización con tus archivos reales
            sh_o = client.open("ERP MAXTIVA").worksheet("Obras")
            sh_g = client.open("gastos MAXTIVA").get_worksheet(0)
            
            return pd.DataFrame(sh_o.get_all_records()), pd.DataFrame(sh_g.get_all_records()), True
        except Exception as e:
            st.error(f"Acceso denegado a las hojas. ¿Invitaste a {info['client_email']} como Editor?")
    return pd.DataFrame(), pd.DataFrame(), False

# Inicialización en el estado de la sesión
if "ready" not in st.session_state:
    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_maxtiva_data()
