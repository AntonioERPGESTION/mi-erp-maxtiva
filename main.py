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
st.set_page_config(page_title="MAXTIVA ERP", layout="wide", page_icon="🏢")

# --- 2. FUNCIONES DE CONEXIÓN ---
def conectar_google():
    try:
        encoded = st.secrets["claves_gcp"]["json_base64"]
        info = json.loads(base64.b64decode(encoded).decode("utf-8"))
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_pestaña(nombre_target):
    gc = conectar_google()
    if gc:
        try:
            sh = gc.open("ERP MAXTIVA")
            for sheet in sh.worksheets():
                if sheet.title.lower() == nombre_target.lower():
                    return sheet
            return None
        except:
            return None
    return None

def guardar_datos_seguro(ws, df_editado, target):
    try:
        df_limpio = df_editado.fillna("").astype(str)
        datos_a_subir = [df_limpio.columns.values.tolist()] + df_limpio.values.tolist()
        ws.clear()
        ws.update('A1', datos_a_subir)
        st.success(f"✅ ¡{target} actualizado!")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# --- 3. DEFINICIÓN DEL MENÚ (Aquí se soluciona el NameError) ---
with st.sidebar:
    st.title("🏢 GRUPO MAXTIVA")
    # Definimos 'menu' AQUÍ para que siempre exista antes de los 'if'
    menu = st.selectbox("SELECCIONE MÓDULO", [
        "📊 Dashboard General",
        "🏗️ Gestión de Obras",
        "👥 Gestión de Empleados",
        "⏱️ Imputación de Horas",
        "💸 Adjudicación de Gastos",
        "📦 Pedidos y Facturas PDF"
    ])
    st.divider()
    if st.button("🔄 Sincronizar"):
        st.rerun()

# --- 4. LÓGICA DE LOS MÓDULOS ---

if menu == "📊 Dashboard General":
    st.title("📊 Resumen General")
    st.info("Bienvenido al ERP Maxtiva. Selecciona una sección en el menú lateral.")

elif menu in ["🏗️ Gestión de Obras", "👥 Gestión de Empleados", "⏱️ Imputación de Horas", "💸 Adjudicación de Gastos"]:
    mapeo = {
        "🏗️ Gestión de Obras": "Obras",
        "👥 Gestión de Empleados": "Empleados",
        "⏱️ Imputación de Horas": "Horas",
        "💸 Adjudicación de Gastos": "Gastos"
    }
    target = mapeo[menu]
    ws = obtener_pestaña(target)
    
    if ws:
        st.title(f"📝 {menu}")
        raw = ws.get_all_records()
        df_actual = pd.DataFrame(raw) if raw else pd.DataFrame()
        
        df_editado = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic", key=f"ed_{target}")
        
        if st.button(f"💾 Guardar en {target}"):
            guardar_datos_seguro(ws, df_editado, target)
    else:
        st.error(f"No se encontró la pestaña '{target}' en Drive.")

elif menu == "📦 Pedidos y Facturas PDF":
    st.title("📦 Extractor PDF")
    archivo = st.file_uploader("Subir PDF", type="pdf")
    if archivo:
        with pdfplumber.open(archivo) as pdf:
            texto = "\n".join([p.extract_text() for p in pdf.pages])
        st.text_area("Texto extraído:", texto, height=300)
