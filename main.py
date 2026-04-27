import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pdfplumber
import re
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="MAXTIVA ERP - DIAGNÓSTICO", layout="wide")

# --- CONEXIÓN CON DIAGNÓSTICO ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            # Limpieza profunda de la llave
            key = info["private_key"].replace("\\n", "\n").strip()
            info["private_key"] = key
            creds = Credentials.from_service_account_info(info, scopes=scope)
            return gspread.authorize(creds)
        else:
            st.error("No se encontraron 'gcp_service_account' en los Secrets de Streamlit.")
    except Exception as e:
        st.error(f"Error en la Llave Privada: {e}")
    return None

def load_data():
    client = get_gsheet_client()
    if client:
        try:
            # Intentar abrir Obras
            try:
                sh_o = client.open("ERP MAXTIVA").worksheet("Obras")
                df_o = pd.DataFrame(sh_o.get_all_records())
            except Exception as e:
                st.error(f"Error al leer 'ERP MAXTIVA' -> 'Obras': {e}")
                df_o = pd.DataFrame()

            # Intentar abrir Gastos
            try:
                sh_g = client.open("gastos MAXTIVA").get_worksheet(0)
                df_g = pd.DataFrame(sh_g.get_all_records())
            except Exception as e:
                st.error(f"Error al leer 'gastos MAXTIVA': {e}")
                df_g = pd.DataFrame()

            return df_o, df_g, True
        except Exception as e:
            st.error(f"Error general de acceso: {e}")
    return pd.DataFrame(), pd.DataFrame(), False

# --- INICIALIZACIÓN ---
if "db_o" not in st.session_state:
    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()

# --- INTERFAZ ---
def main():
    st.sidebar.title("🏢 GRUPO MAXTIVA")
    
    if st.sidebar.button("🔄 Forzar Reconexión"):
        st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()
        st.rerun()

    if not st.session_state.ready:
        st.title("❌ Estado: Sin Conexión")
        st.warning("Revisa los errores rojos arriba para saber qué falla exactamente.")
        st.info(f"Asegúrate de haber compartido tus archivos con: \n`maxtiva-erp@maxtiva-erp.iam.gserviceaccount.com`")
    else:
        st.sidebar.success("✅ Conectado")
        menu = st.sidebar.radio("MENÚ", ["Dashboard", "Gestión Obras", "Pedidos PDF"])

        if menu == "Dashboard":
            st.title("📊 Dashboard")
            st.write("### Datos de Obras")
            st.dataframe(st.session_state.db_o)
            
        elif menu == "Gestión Obras":
            st.title("🏗️ Gestión")
            # Formulario simple para probar escritura
            with st.form("test_add"):
                id_o = st.text_input("ID")
                cli = st.text_input("Cliente")
                nom = st.text_input("Obra")
                pre = st.number_input("Presupuesto", min_value=0.0)
                if st.form_submit_button("Guardar en Drive"):
                    client = get_gsheet_client()
                    sh = client.open("ERP MAXTIVA").worksheet("Obras")
                    sh.append_row([id_o, cli, pre, "Activa", nom, ""])
                    st.success("¡Guardado! Refresca para ver.")

        elif menu == "Pedidos PDF":
            st.title("📦 Pedidos")
            st.info("Módulo listo. Sube un PDF para probar.")

if __name__ == "__main__":
    main()
