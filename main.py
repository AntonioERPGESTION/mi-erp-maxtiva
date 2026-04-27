import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
import pdfplumber
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MAXTIVA ERP - SISTEMA ONLINE", layout="wide")

# --- CONEXIÓN DE SEGURIDAD (MÉTODO BASE64) ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            # 1. Obtenemos el texto codificado
            encoded_json = st.secrets["gcp_service_account"]["json_base64"]
            # 2. Lo decodificamos
            decoded_json = base64.b64decode(encoded_json).decode("utf-8")
            # 3. Lo cargamos como JSON
            info = json.loads(decoded_json)
            
            creds = Credentials.from_service_account_info(info, scopes=scope)
            return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error de validación: {e}")
    return None

def load_data():
    client = get_gsheet_client()
    if client:
        try:
            # Nombres exactos de tus archivos en Drive
            sh_o = client.open("ERP MAXTIVA").worksheet("Obras")
            sh_g = client.open("gastos MAXTIVA").get_worksheet(0)
            return pd.DataFrame(sh_o.get_all_records()), pd.DataFrame(sh_g.get_all_records()), True
        except Exception as e:
            st.error(f"No se encuentran los archivos: {e}")
            st.info("Asegúrate de compartir los archivos con el email 'client_email' de tu JSON.")
    return pd.DataFrame(), pd.DataFrame(), False

# --- INICIALIZACIÓN ---
if "db_o" not in st.session_state:
    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()

# --- INTERFAZ ---
def main():
    st.sidebar.title("🏢 GRUPO MAXTIVA")
    
    if not st.session_state.ready:
        st.error("❌ ERROR DE CREDENCIALES")
        st.write("Sigue los pasos del método Base64 para conectar.")
        if st.button("🔄 Reintentar Conexión"):
            st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()
            st.rerun()
    else:
        st.sidebar.success("✅ CONECTADO")
        menu = st.sidebar.radio("MENÚ", ["Dashboard", "Gestión Obras", "Pedidos PDF"])

        if menu == "Dashboard":
            st.title("📊 Dashboard Ejecutivo")
            o, g = st.session_state.db_o, st.session_state.db_g
            c1, c2 = st.columns(2)
            c1.metric("Ingresos (Presupuestado)", f"{o['PRESUPUESTO'].sum():,.2f} €" if not o.empty else "0 €")
            c2.metric("Gastos Totales", f"{g['Importe'].sum():,.2f} €" if not g.empty else "0 €")
            st.dataframe(o, use_container_width=True)

        elif menu == "Gestión Obras":
            st.title("🏗️ Gestión de Proyectos")
            with st.form("add_obra"):
                c = st.columns(2)
                id_o = c[0].text_input("ID")
                cli = c[1].text_input("Cliente")
                nom = st.text_input("Nombre de la Obra")
                pre = st.number_input("Presupuesto (€)", min_value=0.0)
                if st.form_submit_button("Guardar en Google Drive"):
                    client = get_gsheet_client()
                    sh = client.open("ERP MAXTIVA").worksheet("Obras")
                    sh.append_row([id_o, cli, pre, "Activa", nom, ""])
                    st.success("¡Obra sincronizada!")
                    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()
                    st.rerun()

        elif menu == "Pedidos PDF":
            st.title("📦 Extracción de Facturas PDF")
            uploaded_file = st.file_uploader("Subir PDF", type="pdf")
            if uploaded_file:
                with pdfplumber.open(uploaded_file) as pdf:
                    text = "\n".join([page.extract_text() for page in pdf.pages])
                # Buscar importes (ej: 1.250,50 €)
                importes = re.findall(r"(\d+[\.,]\d{2})", text)
                if importes:
                    st.success(f"Importe detectado: {importes[-1]} €")
                else:
                    st.warning("No se detectó el importe automáticamente.")

if __name__ == "__main__":
    main()
