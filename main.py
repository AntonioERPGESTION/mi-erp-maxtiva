import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
import pdfplumber
import re
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MAXTIVA ERP - CÁLCULO 8H", layout="wide", page_icon="🏢")

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
    if st.button("🔄 Actualizar Datos"):
        st.cache_data.clear()
        st.rerun()

# --- 4. CARGA DE LISTAS (DESPLEGABLES) ---
lista_obras = []
lista_empleados = []

ws_o_list = obtener_pestaña("Obras")
if ws_o_list:
    data_o = ws_o_list.get_all_records()
    if data_o:
        df_temp_o = pd.DataFrame(data_o)
        if "NOMBRE" in df_temp_o.columns:
            lista_obras = [str(x) for x in df_temp_o["NOMBRE"].unique() if x]

ws_e_list = obtener_pestaña("Empleados")
if ws_e_list:
    data_e = ws_e_list.get_all_records()
    if data_e:
        df_temp_e = pd.DataFrame(data_e)
        if "NOMBRE" in df_temp_e.columns:
            lista_empleados = [str(x) for x in df_temp_e["NOMBRE"].unique() if x]

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
            raw = ws.get_all_records()
            df_actual = pd.DataFrame(raw)
        except:
            df_actual = pd.DataFrame()

        if df_actual.empty:
            cols = {
                "Obras": ["ID", "CLIENTE", "NOMBRE", "PRESUPUESTO", "ESTADO"],
                "Empleados": ["NOMBRE", "DNI", "PUESTO", "TELÉFONO"],
                "Horas": ["FECHA", "EMPLEADO", "OBRA", "HORAS REALIZADAS", "DÍAS TRABAJADOS", "HORAS ESTIMADAS"],
                "Gastos": ["FECHA", "CONCEPTO", "IMPORTE", "OBRA"]
            }
            df_actual = pd.DataFrame(columns=cols.get(target, ["Dato"]))

        config_columnas = {}
        
        # --- LÓGICA ESPECÍFICA DE HORAS (8h/día) ---
        if target == "Horas":
            # Si el usuario pone los días, calculamos Horas Estimadas (Días * 8h)
            if "DÍAS TRABAJADOS" in df_actual.columns:
                df_actual["DÍAS TRABAJADOS"] = pd.to_numeric(df_actual["DÍAS TRABAJADOS"], errors='coerce').fillna(0)
                df_actual["HORAS ESTIMADAS"] = df_actual["DÍAS TRABAJADOS"] * 8
            
            config_columnas = {
                "FECHA": st.column_config.TextColumn("FECHA (Vacío = Hoy)"),
                "EMPLEADO": st.column_config.SelectboxColumn("EMPLEADO", options=lista_empleados),
                "OBRA": st.column_config.SelectboxColumn("OBRA", options=lista_obras),
                "HORAS ESTIMADAS": st.column_config.NumberColumn("HORAS ESTIMADAS", disabled=True, help="Cálculo automático: Días * 8h")
            }
        
        elif target == "Gastos":
            config_columnas = {
                "FECHA": st.column_config.TextColumn("FECHA (Vacío = Hoy)"),
                "OBRA": st.column_config.SelectboxColumn("OBRA", options=lista_obras)
            }

        # --- EDITOR ---
        df_editado = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic", column_config=config_columnas, key=f"ed_{target}")
        
        # --- GUARDADO ---
        if st.button(f"💾 GUARDAR {target.upper()}", type="primary"):
            try:
                # Fecha automática
                hoy = datetime.now().strftime("%d/%m/%Y")
                if "FECHA" in df_editado.columns:
                    df_editado["FECHA"] = df_editado["FECHA"].apply(lambda x: hoy if str(x).strip() == "" else x)

                # Recalcular 8h antes de subir
                if target == "Horas" and "DÍAS TRABAJADOS" in df_editado.columns:
                    df_editado["HORAS ESTIMADAS"] = pd.to_numeric(df_editado["DÍAS TRABAJADOS"], errors='coerce').fillna(0) * 8
                
                df_final = df_editado.fillna("").astype(str)
                datos = [df_final.columns.values.tolist()] + df_final.values.tolist()
                ws.clear()
                ws.update('A1', datos)
                st.success("✅ ¡Datos guardados y horas calculadas (Base 8h)! ")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# Módulos Dashboard y PDF simplificados para el ejemplo
elif menu == "📊 Dashboard":
    st.title("📊 Resumen")
    st.info("Cálculo actual: 1 día = 8 horas laborables.")
elif menu == "📦 Extractor PDF":
    st.title("📦 Extractor")
    st.write("Sube tu PDF.")
