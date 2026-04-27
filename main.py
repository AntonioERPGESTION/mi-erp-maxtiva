import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pdfplumber
import re
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="MAXTIVA ERP - SISTEMA CENTRAL", layout="wide")

# --- LÓGICA DE CONEXIÓN BLINDADA ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            # Limpieza forzada de la llave PEM
            key = info["private_key"].replace("\\n", "\n")
            lines = [l.strip() for l in key.split('\n') if l.strip()]
            info["private_key"] = "\n".join(lines)
            
            creds = Credentials.from_service_account_info(info, scopes=scope)
            return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error de validación: {e}")
    return None

def load_all_data():
    client = get_gsheet_client()
    if client:
        try:
            # Sincronización con archivos de Drive
            sh_o = client.open("ERP MAXTIVA").worksheet("Obras")
            sh_g = client.open("gastos MAXTIVA").get_worksheet(0)
            return pd.DataFrame(sh_o.get_all_records()), pd.DataFrame(sh_g.get_all_records()), True
        except Exception as e:
            st.error(f"Error de acceso: {e}. ¿Has compartido los archivos con el email maxtiva-erp@...?")
    return pd.DataFrame(), pd.DataFrame(), False

# --- INICIALIZACIÓN ---
if "db_o" not in st.session_state:
    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_all_data()

# --- MÓDULOS DEL SISTEMA ---

def modulo_dashboard():
    st.title("📊 Dashboard Ejecutivo")
    o, g = st.session_state.db_o, st.session_state.db_g
    
    col1, col2, col3 = st.columns(3)
    presupuestado = o['PRESUPUESTO'].sum() if not o.empty else 0
    gastado = g['Importe'].sum() if not g.empty else 0
    
    col1.metric("Ingresos Totales", f"{presupuestado:,.2f} €")
    col2.metric("Gastos Totales", f"{gastado:,.2f} €")
    col3.metric("Margen Real", f"{presupuestado - gastado:,.2f} €")
    
    st.divider()
    st.subheader("Obras Activas")
    st.dataframe(o, use_container_width=True)

def modulo_obras():
    st.title("🏗️ Gestión de Obras")
    t1, t2 = st.tabs(["➕ Registrar Obra", "🗑️ Eliminar"])
    
    with t1:
        with st.form("new_obra"):
            c = st.columns(2)
            id_obra = c[0].text_input("ID Obra")
            cliente = c[1].text_input("Cliente")
            nombre = st.text_input("Nombre del Proyecto")
            presu = st.number_input("Presupuesto (€)", min_value=0.0)
            if st.form_submit_button("Guardar en Cloud"):
                client = get_gsheet_client()
                sh = client.open("ERP MAXTIVA").worksheet("Obras")
                sh.append_row([id_obra, cliente, presu, "Activa", nombre, "España"])
                st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_all_data()
                st.rerun()
                
    with t2:
        if not st.session_state.db_o.empty:
            sel = st.selectbox("Seleccione obra a borrar", st.session_state.db_o.index, 
                               format_func=lambda x: f"{st.session_state.db_o.loc[x, 'NOMBRE']}")
            if st.button("Confirmar Borrado Definitivo"):
                client = get_gsheet_client()
                sh = client.open("ERP MAXTIVA").worksheet("Obras")
                sh.delete_rows(int(sel) + 2)
                st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_all_data()
                st.rerun()

def modulo_pedidos_pdf():
    st.title("📦 Extracción de Importes (PDF)")
    archivo = st.file_uploader("Subir Factura o Pedido", type="pdf")
    
    if archivo:
        with pdfplumber.open(archivo) as pdf:
            texto = "\n".join([pagina.extract_text() for pagina in pdf.pages])
        
        # IA de detección de importes
        importes = re.findall(r"(\d+[\.,]\d{2})", texto)
        valor = float(importes[-1].replace(",", ".")) if importes else 0.0
        
        st.info(f"Importe detectado automáticamente: **{valor} €**")
        
        if st.button("📥 Registrar como Gasto en Drive"):
            client = get_gsheet_client()
            sh = client.open("gastos MAXTIVA").get_worksheet(0)
            sh.append_row(["Admin", str(datetime.now().date()), "Pedido PDF", archivo.name, valor, "", "Pendiente"])
            st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_all_data()
            st.success("Gasto registrado y Drive actualizado.")

# --- NAVEGACIÓN ---
def main():
    st.sidebar.title("🏢 GRUPO MAXTIVA")
    
    if not st.session_state.ready:
        st.sidebar.error("❌ ERROR DE CONEXIÓN")
        st.warning("El sistema no puede ver tus hojas de cálculo. Revisa las Credenciales.")
        if st.sidebar.button("🔄 Reintentar Sincronización"):
            st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_all_data()
            st.rerun()
    else:
        st.sidebar.success("✅ CLOUD SYNC ACTIVO")
        menu = st.sidebar.radio("MENÚ PRINCIPAL", ["Dashboard", "Gestión de Obras", "Pedidos PDF"])
        
        if menu == "Dashboard": modulo_dashboard()
        elif menu == "Gestión de Obras": modulo_obras()
        elif menu == "Pedidos PDF": modulo_pedidos_pdf()

if __name__ == "__main__":
    main()
