import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pdfplumber
import re
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Pro Sync", layout="wide", page_icon="🏗️")

# --- ESTILOS CORPORATIVOS ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #FFD700; color: #1e3d59; font-weight: bold; }
    .stMetric { background-color: white; border: 2px solid #FFD700; padding: 15px; border-radius: 10px; }
    .stButton>button { background-color: #FFD700; color: #1e3d59; font-weight: bold; width: 100%; border: 1px solid #1e3d59; }
    h1, h2, h3 { color: #1e3d59; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN BLINDADA A GOOGLE SHEETS ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # 1. Intentar cargar desde Secrets (Streamlit Cloud)
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            # Limpieza crítica de la llave privada
            info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
            creds = Credentials.from_service_account_info(info, scopes=scope)
            return gspread.authorize(creds)
        
        # 2. Intentar cargar desde archivo local (Desarrollo)
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Fallo en credenciales: {e}")
        return None

def load_all_data():
    client = get_gsheet_client()
    if client:
        try:
            # Sincronización con nombres de archivos exactos
            sh_o = client.open("ERP MAXTIVA").worksheet("Obras")
            sh_g = client.open("gastos MAXTIVA").get_worksheet(0)
            
            df_o = pd.DataFrame(sh_o.get_all_records())
            df_g = pd.DataFrame(sh_g.get_all_records())
            return df_o, df_g, True
        except Exception as e:
            st.error(f"Error de acceso: {e}")
            st.info("Asegúrate de compartir las Sheets con el email de servicio.")
    return pd.DataFrame(), pd.DataFrame(), False

# --- INICIALIZACIÓN DE ESTADO ---
if "db_o" not in st.session_state:
    st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_all_data()

# --- FUNCIONES DE ACCIÓN (CRUD) ---
def sync_action(file_name, sheet_name, row=None, action="add", row_idx=None):
    client = get_gsheet_client()
    if client:
        sh = client.open(file_name).worksheet(sheet_name)
        if action == "add":
            sh.append_row(row)
        elif action == "delete" and row_idx is not None:
            sh.delete_rows(row_idx + 2) # +2 por encabezado y base 1
        
        # Recargar y refrescar
        st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_all_data()
        st.toast(f"Acción {action} completada en Drive")
        time.sleep(1)
        st.rerun()

# --- MÓDULO DASHBOARD ---
def modulo_dashboard():
    st.title("📊 Resumen Ejecutivo Maxtiva")
    o, g = st.session_state.db_o, st.session_state.db_g
    
    if not o.empty:
        c1, c2, c3 = st.columns(3)
        ingresos = o['PRESUPUESTO'].sum()
        gastos_tot = g['Importe'].sum() if not g.empty else 0
        c1.metric("Ingresos Totales", f"{ingresos:,.2f} €")
        c2.metric("Gastos Totales", f"{gastos_tot:,.2f} €")
        c3.metric("Margen Neto", f"{ingresos - gastos_tot:,.2f} €")
        
        st.divider()
        st.subheader("Obras Registradas")
        st.dataframe(o, use_container_width=True)
    else:
        st.warning("No hay datos disponibles en 'ERP MAXTIVA'.")

# --- MÓDULO PEDIDOS PDF ---
def modulo_pedidos():
    st.title("📦 Extracción de Pedidos e Importes")
    archivo = st.file_uploader("Subir PDF de proveedor", type="pdf")
    
    if archivo:
        with pdfplumber.open(archivo) as pdf:
            texto = "\n".join([p.extract_text() for p in pdf.pages])
            
        # IA de detección de importe
        importes = re.findall(r"(\d+[\.,]\d{2})\s*€", texto)
        valor_sugerido = float(importes[-1].replace(",", ".")) if importes else 0.0
        
        with st.form("confirmar_p"):
            st.info("Datos detectados en el documento")
            col1, col2 = st.columns(2)
            nom = col1.text_input("Concepto/Material", value=archivo.name)
            imp = col2.number_input("Importe Extraído (€)", value=valor_sugerido)
            det = st.text_area("Partidas detectadas", value=texto[:500] + "...")
            
            if st.form_submit_button("Guardar en Drive"):
                # Asumimos que los pedidos van a la hoja de gastos
                nueva_fila = ["Admin", str(time.strftime("%Y-%m-%d")), "Suministros", nom, imp, "", "Pedido PDF"]
                sync_action("gastos MAXTIVA", "Hoja 1", row=nueva_fila)

# --- NAVEGACIÓN ---
def main():
    with st.sidebar:
        st.header("🏢 GRUPO MAXTIVA")
        st.divider()
        if not st.session_state.ready:
            st.error("🔴 Sin conexión a Drive")
            if st.button("🔌 Reintentar Conexión"):
                st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_all_data()
                st.rerun()
        else:
            st.success("🟢 Cloud Sync Activo")
        
        menu = st.radio("MENÚ", ["Dashboard", "Gestión de Obras", "Pedidos PDF"])
        st.divider()
        if st.button("🔄 Refrescar Todo"):
            st.session_state.db_o, st.session_state.db_g, st.session_state.ready = load_all_data()
            st.rerun()

    if menu == "Dashboard": modulo_dashboard()
    elif menu == "Pedidos PDF": modulo_pedidos()
    elif menu == "Gestión de Obras":
        st.title("🏗️ Gestión de Obras")
        tab1, tab2 = st.tabs(["Añadir", "Borrar"])
        with tab1:
            with st.form("new_o"):
                c1, c2 = st.columns(2)
                id_o = c1.text_input("ID")
                cli = c2.text_input("Cliente")
                pre = st.number_input("Presupuesto", min_value=0.0)
                nom = st.text_input("Nombre Obra")
                if st.form_submit_button("Sincronizar Nueva Obra"):
                    sync_action("ERP MAXTIVA", "Obras", row=[id_o, cli, pre, "Activa", nom, "Ubicación"])
        with tab2:
            if not st.session_state.db_o.empty:
                sel = st.selectbox("Obra a eliminar", st.session_state.db_o.index, 
                                 format_func=lambda x: f"{st.session_state.db_o.loc[x, 'NOMBRE']}")
                if st.button("🗑️ Eliminar de Google Drive"):
                    sync_action("ERP MAXTIVA", "Obras", action="delete", row_idx=sel)

if __name__ == "__main__":
    main()
