import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pdfplumber
import re
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP v21 - Full System", layout="wide")

# --- ESTILOS AMARILLO MAXTIVA ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #FFD700; color: #1e3d59; font-weight: bold; }
    .stMetric { background-color: white; border: 2px solid #FFD700; border-radius: 10px; padding: 15px; }
    .stButton>button { background-color: #FFD700; color: #1e3d59; font-weight: bold; border: 1px solid #1e3d59; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN DE SEGURIDAD REFORZADA ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            # LIMPIEZA EXTREMA: Borra cualquier residuo de formato
            key = info["private_key"].replace("\\n", "\n")
            lines = [l.strip() for l in key.split('\n') if l.strip()]
            info["private_key"] = "\n".join(lines)
            
            creds = Credentials.from_service_account_info(info, scopes=scope)
            return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error de validación de llave: {e}")
    return None

def load_data():
    client = get_gsheet_client()
    if client:
        try:
            # Archivos reales en tu Drive
            sh_o = client.open("ERP MAXTIVA").worksheet("Obras")
            sh_g = client.open("gastos MAXTIVA").get_worksheet(0)
            return pd.DataFrame(sh_o.get_all_records()), pd.DataFrame(sh_g.get_all_records()), True
        except Exception as e:
            st.error(f"Error al abrir archivos: {e}")
            st.info("💡 RECUERDA: Comparte tus Sheets con: maxtiva-erp@maxtiva-erp.iam.gserviceaccount.com")
    return pd.DataFrame(), pd.DataFrame(), False

# --- ESTADO DE SESIÓN ---
if "db_o" not in st.session_state:
    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()

# --- FUNCIONES DE ESCRITURA/BORRADO ---
def run_sync(file_name, sheet_name, data=None, mode="add", index=None):
    client = get_gsheet_client()
    sh = client.open(file_name).worksheet(sheet_name)
    if mode == "add":
        sh.append_row(data)
    elif mode == "delete":
        sh.delete_rows(index + 2)
    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()
    st.rerun()

# --- MÓDULOS DEL SISTEMA ---

def modulo_dashboard():
    st.title("📊 Panel de Control Real-Time")
    o, g = st.session_state.db_o, st.session_state.db_g
    if not o.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos", f"{o['PRESUPUESTO'].sum():,.2f} €")
        c2.metric("Gastos", f"{g['Importe'].sum() if not g.empty else 0:,.2f} €")
        c3.metric("Margen", f"{o['PRESUPUESTO'].sum() - (g['Importe'].sum() if not g.empty else 0):,.2f} €")
        st.write("### Obras en Curso")
        st.dataframe(o, use_container_width=True)

def modulo_gestion():
    st.title("🏗️ Gestión de Obras")
    t1, t2 = st.tabs(["➕ Añadir Obra", "🗑️ Eliminar"])
    with t1:
        with st.form("add_form"):
            c = st.columns(2)
            id_n = c[0].text_input("ID")
            cli = c[1].text_input("Cliente")
            nom = st.text_input("Nombre de la Obra")
            pre = st.number_input("Presupuesto", min_value=0.0)
            if st.form_submit_button("Guardar en Google Drive"):
                run_sync("ERP MAXTIVA", "Obras", [id_n, cli, pre, "Activa", nom, "Localización"], "add")
    with t2:
        if not st.session_state.db_o.empty:
            sel = st.selectbox("Selecciona obra", st.session_state.db_o.index, format_func=lambda x: st.session_state.db_o.loc[x, 'NOMBRE'])
            if st.button("Confirmar Borrado"):
                run_sync("ERP MAXTIVA", "Obras", mode="delete", index=sel)

def modulo_pedidos():
    st.title("📦 Extracción de Importes (IA)")
    pdf = st.file_uploader("Sube factura/presupuesto", type="pdf")
    if pdf:
        with pdfplumber.open(pdf) as p:
            texto = "\n".join([page.extract_text() for page in p.pages])
        # Buscamos el importe total
        match = re.findall(r"(\d+[\.,]\d{2})", texto)
        imp_detectado = float(match[-1].replace(",", ".")) if match else 0.0
        st.success(f"Importe detectado: {imp_detectado} €")
        if st.button("Registrar como Gasto"):
            run_sync("gastos MAXTIVA", "Hoja 1", ["Admin", str(time.strftime("%Y-%m-%d")), "Material", pdf.name, imp_detectado, "", "Extraído"], "add")

# --- NAVEGACIÓN PRINCIPAL ---
def main():
    with st.sidebar:
        st.header("🏢 MAXTIVA ERP")
        st.divider()
        if st.session_state.ready:
            st.success("Conectado a Drive")
        else:
            st.error("Error de Conexión")
            if st.button("Reintentar"):
                st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_data()
                st.rerun()
        
        menu = st.radio("MENÚ", ["Dashboard", "Gestión Obras", "Pedidos PDF"])
        
    if st.session_state.ready:
        if menu == "Dashboard": modulo_dashboard()
        elif menu == "Gestión Obras": modulo_gestion()
        elif menu == "Pedidos PDF": modulo_pedidos()
    else:
        st.warning("Por favor, soluciona el error de credenciales para ver los módulos.")

if __name__ == "__main__":
    main()
