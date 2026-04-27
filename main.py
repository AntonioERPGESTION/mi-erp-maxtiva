import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
import pdfplumber
import re
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MA XTIVA ERP", layout="wide", page_icon="🏢")

# --- CONEXIÓN ULTRA-SEGURA (MÉTODO BASE64) ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            # Decodificamos la caja sellada
            encoded_json = st.secrets["gcp_service_account"]["json_base64"]
            decoded_json = base64.b64decode(encoded_json).decode("utf-8")
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
            # Archivos en Drive
            sh_o = client.open("ERP MAXTIVA").worksheet("Obras")
            sh_g = client.open("gastos MAXTIVA").get_worksheet(0)
            return pd.DataFrame(sh_o.get_all_records()), pd.DataFrame(sh_g.get_all_records()), True
        except Exception as e:
            st.error(f"Archivos no encontrados o sin permiso: {e}")
            st.info("💡 Asegúrate de compartir los Excel con el email de tu JSON como 'Editor'.")
    return pd.DataFrame(), pd.DataFrame(), False

# --- SESIÓN ---
if "db_o" not in st.session_state:
    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()

# --- MÓDULOS DEL SISTEMA ---

def modulo_dashboard():
    st.title("📊 Dashboard Ejecutivo")
    o, g = st.session_state.db_o, st.session_state.db_g
    col1, col2, col3 = st.columns(3)
    
    ingresos = o['PRESUPUESTO'].sum() if not o.empty else 0
    gastos = g['Importe'].sum() if not g.empty else 0
    
    col1.metric("Ingresos Totales", f"{ingresos:,.2f} €")
    col2.metric("Gastos Totales", f"{gastos:,.2f} €")
    col3.metric("Beneficio", f"{ingresos - gastos:,.2f} €")
    
    st.divider()
    st.subheader("Listado de Obras")
    st.dataframe(o, use_container_width=True)

def modulo_obras():
    st.title("🏗️ Gestión de Obras")
    with st.form("nueva_obra"):
        c = st.columns(2)
        id_o = c[0].text_input("ID Proyecto")
        cli = c[1].text_input("Cliente")
        nom = st.text_input("Nombre de Obra")
        pre = st.number_input("Presupuesto (€)", min_value=0.0)
        if st.form_submit_button("Sincronizar con Drive"):
            client = get_gsheet_client()
            sh = client.open("ERP MAXTIVA").worksheet("Obras")
            sh.append_row([id_o, cli, pre, "Activa", nom, ""])
            st.success("Obra guardada correctamente.")
            st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()

def modulo_pdf():
    st.title("📦 Extractor de Pedidos (IA)")
    pdf_file = st.file_uploader("Sube el PDF del proveedor", type="pdf")
    if pdf_file:
        with pdfplumber.open(pdf_file) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages])
        importes = re.findall(r"(\d+[\.,]\d{2})", text)
        if importes:
            st.success(f"Importe detectado: {importes[-1]} €")
        else:
            st.warning("No se encontró el importe. Revisa el documento.")

# --- NAVEGACIÓN ---
def main():
    st.sidebar.title("🏢 GRUPO MAXTIVA")
    
    if not st.session_state.ready:
        st.sidebar.error("❌ ERROR DE CONEXIÓN")
        st.error("El sistema no puede validar la llave. Realiza el Paso 1 (Base64).")
        if st.button("🔄 Reintentar"):
            st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()
            st.rerun()
    else:
        st.sidebar.success("✅ SISTEMA ONLINE")
        menu = st.sidebar.radio("MENÚ", ["Dashboard", "Gestión Obras", "Pedidos PDF"])
        
        if menu == "Dashboard": modulo_dashboard()
        elif menu == "Gestión Obras": modulo_obras()
        elif menu == "Pedidos PDF": modulo_pdf()

if __name__ == "__main__":
    main()
