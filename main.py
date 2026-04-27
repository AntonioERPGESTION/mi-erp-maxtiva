import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
import pdfplumber
import re
import time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MAXTIVA ERP - SISTEMA INTEGRAL", layout="wide", page_icon="🏢")

# Estilos personalizados
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #FFD700; }
    .stButton>button { width: 100%; background-color: #1e3d59; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNCIONES DE CONEXIÓN ---
def conectar_google():
    try:
        # Verificamos si existe el secreto
        if "claves_gcp" not in st.secrets:
            st.error("❌ ERROR: No se encuentra la sección [claves_gcp] en los Secrets de Streamlit.")
            return None
        
        encoded = st.secrets["claves_gcp"]["json_base64"]
        info = json.loads(base64.b64decode(encoded).decode("utf-8"))
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ ERROR DE CONEXIÓN: {e}")
        return None

def obtener_pestaña(nombre_target):
    gc = conectar_google()
    if gc:
        try:
            # Intenta abrir el archivo. ASEGÚRATE DE QUE SE LLAMA ASÍ EN TU DRIVE
            sh = gc.open("ERP MAXTIVA")
            
            # Listar todas las pestañas disponibles para diagnóstico
            nombres_reales = [s.title for s in sh.worksheets()]
            
            for sheet in sh.worksheets():
                if sheet.title.lower() == nombre_target.lower():
                    return sheet
            
            st.warning(f"⚠️ No se encontró '{nombre_target}'. Disponibles: {nombres_reales}")
            return None
        except Exception as e:
            st.error(f"❌ ERROR AL ABRIR EXCEL: {e}")
            return None
    return None

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.title("GRUPO MAXTIVA")
    menu = st.selectbox("SELECCIONE MÓDULO", [
        "📊 Dashboard",
        "🏗️ Gestión de Obras",
        "👥 Empleados",
        "⏱️ Control de Horas",
        "📦 Extractor PDF"
    ])
    st.divider()
    if st.button("🔄 Refrescar Datos"):
        st.rerun()

# --- 4. LÓGICA DE MÓDULOS ---

# --- MÓDULO DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Panel de Control")
    st.write("Bienvenido. Selecciona un módulo para ver o editar datos.")

# --- MÓDULOS EDITABLES ---
elif menu in ["🏗️ Gestión de Obras", "👥 Empleados", "⏱️ Control de Horas"]:
    mapeo = {
        "🏗️ Gestión de Obras": "Obras",
        "👥 Empleados": "Empleados",
        "⏱️ Control de Horas": "Horas"
    }
    target = mapeo[menu]
    st.title(f"📝 {menu}")
    
    ws = obtener_pestaña(target)
    
    if ws:
        # Cargar datos
        try:
            raw = ws.get_all_records()
            df_actual = pd.DataFrame(raw)
        except:
            df_actual = pd.DataFrame()

        # Definición de columnas si está vacío
        if df_actual.empty:
            columnas_fijas = {
                "Obras": ["ID", "CLIENTE", "NOMBRE", "PRESUPUESTO", "ESTADO"],
                "Empleados": ["NOMBRE", "DNI", "PUESTO", "TELÉFONO"],
                "Horas": ["NOMBRE", "OBRA_ASIGNADA", "HORAS REALIZADAS", "HORAS ESTIMADAS", "DÍAS DURACIÓN OBRA"]
            }
            df_actual = pd.DataFrame(columns=columnas_fijas.get(target, ["Dato"]))
            st.info(f"Hoja '{target}' lista para nuevos datos.")

        # Lógica especial para Horas (Cálculo automático de estimadas)
        if target == "Horas" and "DÍAS DURACIÓN OBRA" in df_actual.columns:
            df_actual["DÍAS DURACIÓN OBRA"] = pd.to_numeric(df_actual["DÍAS DURACIÓN OBRA"], errors='coerce').fillna(0)
            df_actual["HORAS ESTIMADAS"] = df_actual["DÍAS DURACIÓN OBRA"] * 10

        # EDITOR
        df_editado = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic", key=f"ed_{target}")
        
        # BOTÓN GUARDAR
        if st.button(f"💾 GUARDAR EN {target.upper()}"):
            try:
                with st.spinner("Sincronizando..."):
                    # Recalcular horas antes de guardar si es el módulo de Horas
                    if target == "Horas":
                         df_editado["HORAS ESTIMADAS"] = pd.to_numeric(df_editado["DÍAS DURACIÓN OBRA"], errors='coerce').fillna(0) * 10
                    
                    df_final = df_editado.fillna("").astype(str)
                    datos = [df_final.columns.values.tolist()] + df_final.values.tolist()
                    ws.clear()
                    ws.update('A1', datos)
                    st.success("✅ Guardado correctamente.")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# --- MÓDULO PDF ---
elif menu == "📦 Extractor PDF":
    st.title("📦 Extractor de Pedidos")
    file = st.file_uploader("Subir PDF", type="pdf")
    if file:
        with pdfplumber.open(file) as pdf:
            texto = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        st.text_area("Contenido:", texto, height=400)
