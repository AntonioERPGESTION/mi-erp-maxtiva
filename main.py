import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            
            # --- LIMPIEZA QUIRÚRGICA DE LA LLAVE ---
            key = info["private_key"]
            
            # 1. Normalizar saltos de línea (quita el texto "\n" y pone saltos reales)
            key = key.replace("\\n", "\n")
            
            # 2. Limpiar espacios accidentales al inicio/final de cada línea
            lines = [line.strip() for line in key.split('\n') if line.strip()]
            
            # 3. Reconstruir el bloque PEM asegurando las etiquetas correctas
            clean_key = "\n".join(lines)
            if not clean_key.startswith("-----BEGIN PRIVATE KEY-----"):
                clean_key = "-----BEGIN PRIVATE KEY-----\n" + clean_key
            if not clean_key.endswith("-----END PRIVATE KEY-----"):
                clean_key = clean_key + "\n-----END PRIVATE KEY-----"
            
            info["private_key"] = clean_key
            
            creds = Credentials.from_service_account_info(info, scopes=scope)
            return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Fallo en la validación de la llave: {e}")
    return None

# --- CARGA CON FILTRO DE SEGURIDAD ---
def cargar_datos_seguros():
    client = get_gsheet_client()
    if client:
        try:
            sh_o = client.open("ERP MAXTIVA").worksheet("Obras")
            sh_g = client.open("gastos MAXTIVA").get_worksheet(0)
            return pd.DataFrame(sh_o.get_all_records()), pd.DataFrame(sh_g.get_all_records()), True
        except Exception as e:
            st.error(f"Conexión OK, pero error de acceso: {e}")
            st.info("💡 Asegúrate de que compartiste las Sheets con: maxtiva-erp@maxtiva-erp.iam.gserviceaccount.com")
    return pd.DataFrame(), pd.DataFrame(), False

# Inicialización
if "ready" not in st.session_state:
    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = cargar_datos_seguros()
