import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pdfplumber
import re
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Full Sync", layout="wide", page_icon="🏗️")

# --- ESTILOS AMARILLO CORPORATIVO ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8f9fa; }}
    [data-testid="stSidebar"] {{ background-color: #FFD700; color: #1e3d59; font-weight: bold; }}
    .stMetric {{ background-color: white; border: 2px solid #FFD700; padding: 15px; border-radius: 10px; }}
    .stButton>button {{ background-color: #FFD700; color: #1e3d59; font-weight: bold; width: 100%; border: 1px solid #1e3d59; }}
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN SEGURA A GOOGLE SHEETS ---
def get_gsheet_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Intenta cargar desde secrets (Streamlit Cloud) o archivo local
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Error de Credenciales: {e}")
        return None

def load_data_from_sheets():
    client = get_gsheet_client()
    if client:
        try:
            sh_obras = client.open("ERP MAXTIVA").worksheet("Obras")
            sh_gastos = client.open("gastos MAXTIVA").get_worksheet(0)
            return pd.DataFrame(sh_obras.get_all_records()), pd.DataFrame(sh_gastos.get_all_records())
        except Exception as e:
            st.error(f"❌ Error accediendo a las hojas: {e}")
    return pd.DataFrame(), pd.DataFrame()

# --- INICIALIZACIÓN CRÍTICA (Evita el AttributeError) ---
if "db_obras" not in st.session_state or "db_gastos" not in st.session_state:
    st.session_state.db_obras, st.session_state.db_gastos = load_data_from_sheets()

# --- FUNCIONES DE GESTIÓN EN DRIVE (Añadir/Borrar) ---
def sync_action(file_name, sheet_name, row=None, action="add", row_index=None):
    client = get_gsheet_client()
    sh = client.open(file_name).worksheet(sheet_name)
    if action == "add":
        sh.append_row(row)
    elif action == "delete" and row_index is not None:
        # +2 porque gspread empieza en 1 y la primera fila es el encabezado
        sh.delete_rows(row_index + 2)
    
    # Recargar datos tras la acción
    st.session_state.db_obras, st.session_state.db_gastos = load_data_from_sheets()
    st.toast(f"✅ Sincronizado: {action}")
    st.rerun()

# --- MÓDULO DASHBOARD ---
def modulo_dashboard():
    st.title("📊 Panel de Control Real-Time")
    obras = st.session_state.db_obras
    gastos = st.session_state.db_gastos
    
    if obras.empty:
        st.warning("⚠️ No hay datos de obras cargados.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos Totales", f"{obras['PRESUPUESTO'].sum():,.2f} €")
    c2.metric("Gastos Totales", f"{gastos['Importe'].sum():,.2f} €" if not gastos.empty else "0 €")
    c3.metric("Beneficio", f"{(obras['PRESUPUESTO'].sum() - (gastos['Importe'].sum() if not gastos.empty else 0)):,.2f} €")
    
    st.divider()
    st.subheader("Obras en curso")
    st.dataframe(obras, use_container_width=True)

# --- MÓDULO GESTIÓN (EDITAR / BORRAR) ---
def modulo_gestion_obras():
    st.title("🏗️ Gestión de Obras y Borrado")
    obras = st.session_state.db_obras
    
    t1, t2 = st.tabs(["➕ Nueva Obra", "🗑️ Eliminar Obra"])
    
    with t1:
        with st.form("add_o"):
            id_o = st.text_input("ID")
            cli = st.text_input("Cliente")
            pre = st.number_input("Presupuesto", min_value=0.0)
            est = st.selectbox("Estado", ["Activa", "Finalizada", "Presupuesto"])
            nom = st.text_input("Nombre Obra")
            ubi = st.text_input("Ubicación")
            if st.form_submit_button("Guardar en Drive"):
                nueva = [id_o, cli, pre, est, nom, ubi]
                sync_action("ERP MAXTIVA", "Obras", row=nueva, action="add")

    with t2:
        if not obras.empty:
            sel = st.selectbox("Seleccione obra para ELIMINAR del Drive", obras.index, format_func=lambda x: f"{obras.loc[x, 'NOMBRE']} ({obras.loc[x, 'CLIENTE']})")
            if st.button("⚠️ ELIMINAR PERMANENTEMENTE"):
                sync_action("ERP MAXTIVA", "Obras", action="delete", row_index=sel)
        else:
            st.info("No hay obras para eliminar.")

# --- NAVEGACIÓN ---
def main():
    with st.sidebar:
        st.write("### 🏢 MA XTIVA ERP v15")
        st.divider()
        menu = st.radio("MENÚ", ["Dashboard", "Gestión de Obras", "Gastos", "Pedidos PDF"])
        if st.button("🔄 Sincronizar Ahora"):
            st.session_state.db_obras, st.session_state.db_gastos = load_data_from_sheets()
            st.rerun()

    if menu == "Dashboard": modulo_dashboard()
    elif menu == "Gestión de Obras": modulo_gestion_obras()
    # Los otros módulos siguen la misma lógica de sync_action...

if __name__ == "__main__":
    main()
