import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pdfplumber
import re
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MA XTIVA ERP", layout="wide", page_icon="🏗️")

# --- ESTILOS ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #FFD700; color: #1e3d59; }
    .stMetric { background-color: white; border: 2px solid #FFD700; border-radius: 10px; padding: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN ---
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            # Limpieza forzada de la llave PEM
            info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
            creds = Credentials.from_service_account_info(info, scopes=scope)
            return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error de credenciales: {e}")
    return None

def load_data():
    client = get_client()
    if client:
        try:
            # Sincronización con las pestañas reales que veo en tu imagen
            sh_o = client.open("ERP MAXTIVA").worksheet("Obras")
            # Para gastos, usa el nombre exacto de la primera pestaña
            sh_g = client.open("gastos MAXTIVA").get_worksheet(0)
            
            return pd.DataFrame(sh_o.get_all_records()), pd.DataFrame(sh_g.get_all_records()), True
        except Exception as e:
            st.error(f"No se pudo conectar con las hojas: {e}")
    return pd.DataFrame(), pd.DataFrame(), False

# --- ESTADO ---
if "db_o" not in st.session_state:
    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()

# --- MÓDULOS ---
def main():
    st.sidebar.title("🏗️ MA XTIVA ERP")
    
    if st.session_state.ready:
        st.sidebar.success("Conectado a Drive")
        menu = st.sidebar.radio("MENÚ", ["Dashboard", "Gestión de Obras", "Gastos", "Pedidos PDF"])
        
        if menu == "Dashboard":
            st.title("📊 Panel de Control")
            o, g = st.session_state.db_o, st.session_state.db_g
            c1, c2 = st.columns(2)
            c1.metric("Presupuesto Total", f"{o['PRESUPUESTO'].sum() if not o.empty else 0:,.2f} €")
            c2.metric("Gastos Totales", f"{g['Importe'].sum() if not g.empty else 0:,.2f} €")
            st.dataframe(o, use_container_width=True)

        elif menu == "Gestión de Obras":
            st.title("🏗️ Gestión de Obras")
            with st.form("nueva_obra"):
                c = st.columns(2)
                id_o = c[0].text_input("ID")
                cli = c[1].text_input("Cliente")
                nom = st.text_input("Nombre Obra")
                pre = st.number_input("Presupuesto", min_value=0.0)
                if st.form_submit_button("Guardar en Drive"):
                    client = get_client()
                    sh = client.open("ERP MAXTIVA").worksheet("Obras")
                    sh.append_row([id_o, cli, pre, "Activa", nom, ""])
                    st.success("Obra guardada.")
                    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()

        elif menu == "Pedidos PDF":
            st.title("📦 Extracción de Pedidos")
            file = st.file_uploader("Sube el PDF", type="pdf")
            if file:
                with pdfplumber.open(file) as pdf:
                    texto = "\n".join([p.extract_text() for p in pdf.pages])
                importes = re.findall(r"(\d+[\.,]\d{2})", texto)
                st.info(f"Importe detectado: {importes[-1] if importes else 'No encontrado'} €")

        if st.sidebar.button("🔄 Sincronizar Ahora"):
            st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()
            st.rerun()
    else:
        st.error("Error de conexión. Revisa los pasos 1 y 2.")
        if st.button("Reintentar Conexión"):
            st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()
            st.rerun()

if __name__ == "__main__":
    main()
