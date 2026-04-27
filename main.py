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
st.set_page_config(page_title="MAXTIVA ERP - INTELIGENTE", layout="wide", page_icon="🏢")

# --- 2. FUNCIONES DE CONEXIÓN ---
def conectar_google():
    try:
        if "claves_gcp" not in st.secrets:
            st.error("❌ Configura los 'Secrets' en Streamlit Cloud.")
            return None
        encoded = st.secrets["claves_gcp"]["json_base64"]
        info = json.loads(base64.b64decode(encoded).decode("utf-8"))
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error conexión: {e}")
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

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.title("GRUPO MAXTIVA")
    menu = st.selectbox("MÓDULO", [
        "📊 Dashboard",
        "🏗️ Gestión de Obras",
        "👥 Empleados",
        "⏱️ Control de Horas",
        "💸 Gastos Imputables",
        "📦 Extractor PDF"
    ])
    st.divider()
    if st.button("🔄 Refrescar Listas"):
        st.cache_data.clear()
        st.rerun()

# --- 4. CARGA DE LISTAS PARA DESPLEGABLES ---
# Obtenemos los nombres de obras y empleados para los menús
lista_obras = []
lista_empleados = []

ws_o_list = obtener_pestaña("Obras")
if ws_o_list:
    df_o_list = pd.DataFrame(ws_o_list.get_all_records())
    if not df_o_list.empty and "NOMBRE" in df_o_list.columns:
        lista_obras = df_o_list["NOMBRE"].unique().tolist()

ws_e_list = obtener_pestaña("Empleados")
if ws_e_list:
    df_e_list = pd.DataFrame(ws_e_list.get_all_records())
    if not df_e_list.empty and "NOMBRE" in df_e_list.columns:
        lista_empleados = df_e_list["NOMBRE"].unique().tolist()

# --- 5. LÓGICA DE MÓDULOS ---

if menu in ["🏗️ Gestión de Obras", "👥 Empleados", "⏱️ Control de Horas", "💸 Gastos Imputables"]:
    mapeo = {
        "🏗️ Gestión de Obras": "Obras",
        "👥 Empleados": "Empleados",
        "⏱️ Control de Horas": "Horas",
        "💸 Gastos Imputables": "Gastos"
    }
    target = mapeo[menu]
    st.title(f"📝 {menu}")
    
    ws = obtener_pestaña(target)
    if ws:
        try:
            df_actual = pd.DataFrame(ws.get_all_records())
        except:
            df_actual = pd.DataFrame()

        # Si está vacío, crear columnas base
        if df_actual.empty:
            cols = {
                "Obras": ["ID", "CLIENTE", "NOMBRE", "PRESUPUESTO", "ESTADO"],
                "Empleados": ["NOMBRE", "DNI", "PUESTO", "TELÉFONO"],
                "Horas": ["FECHA", "EMPLEADO", "OBRA", "HORAS REALIZADAS", "DÍAS DURACIÓN OBRA", "HORAS ESTIMADAS"],
                "Gastos": ["FECHA", "CONCEPTO", "IMPORTE", "OBRA"]
            }
            df_actual = pd.DataFrame(columns=cols.get(target, ["Dato"]))

        # --- CONFIGURACIÓN DE COLUMNAS (DESPLEGABLES) ---
        config_columnas = {}
        
        if target == "Horas":
            # Cálculo automático de estimadas
            df_actual["DÍAS DURACIÓN OBRA"] = pd.to_numeric(df_actual["DÍAS DURACIÓN OBRA"], errors='coerce').fillna(0)
            df_actual["HORAS ESTIMADAS"] = df_actual["DÍAS DURACIÓN OBRA"] * 10
            
            config_columnas = {
                "EMPLEADO": st.column_config.SelectboxColumn("EMPLEADO", options=lista_empleados),
                "OBRA": st.column_config.SelectboxColumn("OBRA", options=lista_obras),
                "HORAS ESTIMADAS": st.column_config.NumberColumn("HORAS ESTIMADAS", disabled=True)
            }
        
        elif target == "Gastos":
            config_columnas = {
                "OBRA": st.column_config.SelectboxColumn("OBRA", options=lista_obras),
                "FECHA": st.column_config.DateColumn("FECHA")
            }

        elif target == "Obras":
            config_columnas = {
                "ESTADO": st.column_config.SelectboxColumn("ESTADO", options=["Activa", "Finalizada", "Pendiente"])
            }

        # --- EDITOR ---
        df_editado = st.data_editor(
            df_actual, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config=config_columnas,
            key=f"ed_{target}"
        )
        
        if st.button(f"💾 GUARDAR CAMBIOS EN {target.upper()}"):
            try:
                # Recalcular horas estimadas antes de guardar
                if target == "Horas":
                    df_editado["HORAS ESTIMADAS"] = pd.to_numeric(df_editado["DÍAS DURACIÓN OBRA"], errors='coerce').fillna(0) * 10
                
                df_final = df_editado.fillna("").astype(str)
                datos = [df_final.columns.values.tolist()] + df_final.values.tolist()
                ws.clear()
                ws.update('A1', datos)
                st.success("✅ Sincronizado.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# (Resto de módulos: Dashboard y PDF se mantienen igual)
