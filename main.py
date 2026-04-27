import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Conectado", layout="wide")

# --- DATOS DE CREDENCIALES (Inyectados directamente) ---
GOOGLE_CREDS = {
  "type": "service_account",
  "project_id": "maxtiva-erp",
  "private_key_id": "8c1538ab401958fc0e4ae5c079f114c89444e180",
  "private_key": st.secrets["private_key"] if "private_key" in st.secrets else "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDZZUr8nEKlfVYj\n84nVA4aaoCtiMv75XBVgMg9DnzzcHsita+Q7IdwpxzIQa2eLeCXyvZzL9QtVSfC4\nArueD4bNxXg0TqxD0Q2Klr6T8SAtmxG5O3YDdr2iM1VDRmhBiwrgReomAXLuy+vT\nhpNHw/pzjl2VZNQI91LPKn/dhP9DyQ2y7ql/i7CRW2lQ+sMnhSoJTuQtrC+NrNCe\ncrs0FkWJNaScnJGX6GcrI+AaVQM0lNZDkEJu+ka9MumYoCbdGF+WAiQR+YC7LHap\nryCHDN73TizQSyhbKBKvXOKhwypy0CADIP0Xme3o8m0Iirty4hVvQfva4if4FoDT\ndl1ulnJAgMBAAECggEAENtLgDY27hFqOilqeOuSvASgDeI5u74fI4azgPZ6R/B/\nIQCqVsdzry2fPSoG17Ko8UnbPEQI7UO+zZXbVGXhzwIj0EfVZatyawTwoWoN/ltK\nztvEdSpM3qSE/6LC92oU8s+ZA09oyQljhNL83Ttd/Sh/KylWo5ysfXHPLlm0rV28\nmZ/YL+KvWkjvuMk5ENdGqU9PoMY3iP14R2Fi6MKCZNyBTeDUFN4gvnXB/D+QNXyC\nRP9izFSAfoP3/yN8H9aayiJaBURmHgEidAvrk5xOgJ7cFOUgvL6X99ZvG0S+S8Z3\nzfOYBdO75jTJzOcoH/deUEShi0NaUwIyF77lW9jzMQKBgQD8C2AFbZst4zXi5D+Y\ndlVXsAIAQmyyMt3/Iy8enE4v71Y7MiMhbfLrbk0HXaOlgXbHMCDpEdfNfi2w9vEF\nGfcoW+/GKxpJrD+61UdjyEjZwEQ566ieiRSL0OzQhLjlb42FedKlvazwS1BBH0QT\hoCW9Vs1jsz3YnPriOKQMgEmtQKBgQDczrYhGmAvRiMBgpj8I/IRSnDDEZfEuo7P\nFnWfI1JyKKnaPdEUZFowqa/7v7iuZsKE4fLG0GqFlnOsLLNq4HaBmMHFtv4TsKO7\nHYRrvtsFL2FNEFW/nPH9d/eWkew3YoBwB8zBcPGOIlNugjTayARqoQwdEZ3q3HBv\nnN0eGq8fRQKBgQDMK+bH3uci//ip6N3/gnRVyTWFwklM/VnKEVVdRZ8sw4OmBlJh\nBTEQOFTbz6X+L2bpqnouc47OXxViUlgiGsuVfQw6CraL0aX6kkT3dspU4qQiC12X\nt1HWhRMhQzKIYZpR8sKKEqGiMlA7wLkj3AQUxYLyWtB84dsnhMaLqoY2NQKBgQCZ\nLycXTA8SfNvoPkwYEG/tIvGbwubBapOMg45SOtUFscQ0TdJxDTWssOwQAPAEvfGQ\n8pfU6d4ck0XoWpKWQOa1/d3gZpVZ35+XPmERxrR3omkkZ4K1jhIrwECZyt5PhhyI\nnECmqs5JxvKOpfI5Ha5CszuOJxyhRRETvYWBTw3S6QKBgANpSIDL5m47XLrYUoGD\nBypq7ysuzojCxnNZinhRKtuHYWhJnCtqY6XzhnyhAUIavBRPGXG2ye94VZypqdzM\nYQWLoUMZH76eFqvSe6QeBgxvyKu6YQZwmeSYCexrbVSN/S7jrUIJtrqPle/bdk95\naTfZsv27/ncx46HplS6/7Ol8\n-----END PRIVATE KEY-----\n",
  "client_email": "maxtiva-erp@maxtiva-erp.iam.gserviceaccount.com",
  "client_id": "116215463228378612374",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/maxtiva-erp%40maxtiva-erp.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# --- CONEXIÓN ---
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Limpiamos posibles errores de saltos de línea
    GOOGLE_CREDS["private_key"] = GOOGLE_CREDS["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(GOOGLE_CREDS, scopes=scope)
    return gspread.authorize(creds)

def load_data():
    try:
        client = get_client()
        sh_obras = client.open("ERP MAXTIVA").worksheet("Obras")
        sh_gastos = client.open("gastos MAXTIVA").get_worksheet(0)
        return pd.DataFrame(sh_obras.get_all_records()), pd.DataFrame(sh_gastos.get_all_records()), True
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame(), pd.DataFrame(), False

# --- APP ---
if "init" not in st.session_state:
    st.session_state.db_o, st.session_state.db_g, st.session_state.ok = load_data()
    st.session_state.init = True

# --- INTERFAZ AMARILLA ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #FFD700; color: #1e3d59; }
    .stMetric { background-color: white; border: 2px solid #FFD700; border-radius: 10px; padding: 10px; }
    </style>
""", unsafe_allow_html=True)

st.sidebar.title("🏢 MA XTIVA ERP")

if st.session_state.ok:
    menu = st.sidebar.radio("Navegación", ["Dashboard", "Ver Obras", "Ver Gastos"])
    
    if menu == "Dashboard":
        st.title("📊 Resumen General")
        c1, c2 = st.columns(2)
        c1.metric("Total Presupuestos", f"{st.session_state.db_o['PRESUPUESTO'].sum():,.2f} €")
        c2.metric("Total Gastos", f"{st.session_state.db_g['Importe'].sum():,.2f} €")
        st.divider()
        st.write("### Últimas Obras Actualizadas")
        st.dataframe(st.session_state.db_o, use_container_width=True)
    
    elif menu == "Ver Obras":
        st.title("🏗️ Listado de Obras (Drive)")
        st.dataframe(st.session_state.db_o, use_container_width=True)

    if st.sidebar.button("🔄 Refrescar Datos"):
        st.session_state.db_o, st.session_state.db_g, st.session_state.ok = load_data()
        st.rerun()
else:
    st.error("No se pudo conectar con Google Drive. Revisa si compartiste las hojas con el email de servicio.")
