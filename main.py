import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
import pdfplumber
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MA XTIVA ERP - SISTEMA COMPLETO", layout="wide", page_icon="🏢")

# --- ESTILOS CORPORATIVOS ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #FFD700; }
    .stMetric { background-color: white; border: 2px solid #FFD700; padding: 15px; border-radius: 10px; }
    .stButton>button { background-color: #1e3d59; color: white; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN SEGURA ---
def conectar_google():
    try:
        encoded = st.secrets["claves_gcp"]["json_base64"]
        info = json.loads(base64.b64decode(encoded).decode("utf-8"))
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.sidebar.error(f"Error de llaves: {e}")
        return None

def obtener_pestaña(nombre_ws):
    gc = conectar_google()
    if gc:
        try:
            sh = gc.open("ERP MAXTIVA")
            return sh.worksheet(nombre_ws)
        except:
            return None
    return None

# --- NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.title("🏢 GRUPO MAXTIVA")
    st.divider()
    menu = st.radio("MENÚ PRINCIPAL", [
        "📊 Dashboard", 
        "🏗️ Gestión de Obras", 
        "👥 Empleados", 
        "⏱️ Control de Horas", 
        "💸 Gastos", 
        "📦 Pedidos PDF"
    ])
    st.divider()
    if st.button("🔄 Sincronizar Todo"):
        st.cache_data.clear()
        st.rerun()

# --- MÓDULOS DEL SISTEMA ---

# 1. DASHBOARD
if menu == "📊 Dashboard":
    st.title("📊 Resumen Ejecutivo")
    ws_obras = obtener_pestaña("Obras")
    ws_gastos = obtener_pestaña("Gastos")
    
    if ws_obras and ws_gastos:
        df_o = pd.DataFrame(ws_obras.get_all_records())
        df_g = pd.DataFrame(ws_gastos.get_all_records())
        
        c1, c2, c3 = st.columns(3)
        ingresos = pd.to_numeric(df_o['PRESUPUESTO'], errors='coerce').sum() if 'PRESUPUESTO' in df_o.columns else 0
        gastos_totales = pd.to_numeric(df_g['IMPORTE'], errors='coerce').sum() if 'IMPORTE' in df_g.columns else 0
        
        c1.metric("Presupuesto Total", f"{ingresos:,.2f} €")
        c2.metric("Gastos Acumulados", f"{gastos_totales:,.2f} €")
        c3.metric("Margen Neto", f"{ingresos - gastos_totales:,.2f} €")
        
        st.subheader("Estado de Proyectos")
        st.dataframe(df_o, use_container_width=True)

# 2. GESTIÓN DE OBRAS (CRUD)
elif menu == "🏗️ Gestión de Obras":
    st.title("🏗️ Control de Obras")
    ws = obtener_pestaña("Obras")
    if ws:
        df = pd.DataFrame(ws.get_all_records())
        t1, t2 = st.tabs(["📋 Ver/Borrar", "➕ Añadir Obra"])
        with t1:
            if not df.empty:
                idx = st.selectbox("Seleccionar para borrar", df.index)
                if st.button("🗑️ Eliminar Registro"):
                    ws.delete_rows(int(idx) + 2)
                    st.success("Borrado. Sincroniza para actualizar.")
                st.dataframe(df, use_container_width=True)
        with t2:
            with st.form("add_obra"):
                id_o = st.text_input("ID")
                cli = st.text_input("Cliente")
                nom = st.text_input("Nombre Obra")
                pre = st.text_input("Presupuesto")
                est = st.selectbox("Estado", ["Activa", "Finalizada", "Pendiente"])
                if st.form_submit_button("Guardar Obra"):
                    ws.append_row([id_o, cli, nom, pre, est])
                    st.success("Obra guardada.")

# 3. EMPLEADOS
elif menu == "👥 Empleados":
    st.title("👥 Plantilla de Empleados")
    ws = obtener_pestaña("Empleados")
    if ws:
        df = pd.DataFrame(ws.get_all_records())
        st.dataframe(df, use_container_width=True)
        with st.expander("➕ Añadir Empleado"):
            with st.form("add_emp"):
                nombre = st.text_input("Nombre Completo")
                dni = st.text_input("DNI")
                puesto = st.text_input("Puesto")
                if st.form_submit_button("Registrar"):
                    ws.append_row([nombre, dni, puesto])
                    st.rerun()

# 4. PEDIDOS PDF (EL QUE FALTABA)
elif menu == "📦 Pedidos PDF":
    st.title("📦 Extractor de Datos de Pedidos")
    st.info("Sube un PDF y el sistema extraerá el importe y el texto automáticamente.")
    archivo = st.file_uploader("Sube el PDF del proveedor", type="pdf")
    if archivo:
        with pdfplumber.open(archivo) as pdf:
            texto_completo = "\n".join([pagina.extract_text() for pagina in pdf.pages])
        
        # Lógica de extracción de importes
        importes = re.findall(r"(\d+[\.,]\d{2})", texto_completo)
        if importes:
            st.success(f"💰 Importe detectado: {importes[-1]} €")
        
        st.subheader("Texto Extraído")
        st.text_area("Previsualización:", texto_completo, height=400)

# 5. GASTOS / HORAS (ESTRUCTURA SIMILAR)
else:
    st.title(f"{menu}")
    st.warning(f"Módulo {menu} activo. Asegúrate de tener la pestaña correspondiente en el Excel.")
    ws = obtener_pestaña(menu.split()[-1]) # Busca 'Gastos' o 'Horas'
    if ws:
        df = pd.DataFrame(ws.get_all_records())
        st.dataframe(df, use_container_width=True)
