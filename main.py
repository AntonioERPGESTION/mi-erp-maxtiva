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
st.set_page_config(page_title="MAXTIVA ERP - CONTROL DE HORAS", layout="wide", page_icon="🏢")

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

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.title("GRUPO MAXTIVA")
    menu = st.selectbox("MÓDULO", ["📊 Dashboard", "🏗️ Gestión de Obras", "👥 Empleados", "⏱️ Control de Horas"])

# --- 4. LÓGICA DE CONTROL DE HORAS ---
if menu == "⏱️ Control de Horas":
    st.title("⏱️ Registro de Horas Diarias y Estimadas")
    ws = obtener_pestaña("Horas") # Asegúrate que la pestaña se llame 'Horas'
    
    if ws:
        try:
            df = pd.DataFrame(ws.get_all_records())
        except:
            # Si está vacía, creamos la estructura basada en tu imagen
            columnas = ["NOMBRE", "CARGO", "COSTE_HORA", "OBRA_ASIGNADA", "DNI", "CATEGORÍA", "HORAS REALIZADAS", "COSTE_H_NOR", "COSTE_H_EXT", "HORAS ESTIMADAS", "DÍAS DURACIÓN OBRA"]
            df = pd.DataFrame(columns=columnas)

        st.info("Instrucciones: Introduce los 'DÍAS DURACIÓN OBRA' para calcular las horas estimadas automáticamente (10h/día).")

        # --- CÁLCULO AUTOMÁTICO ANTES DE EDITAR ---
        # Si el usuario mete días de duración, calculamos: días * 10 (8 normales + 2 extras)
        if "DÍAS DURACIÓN OBRA" in df.columns:
            df["DÍAS DURACIÓN OBRA"] = pd.to_numeric(df["DÍAS DURACIÓN OBRA"], errors='coerce').fillna(0)
            df["HORAS ESTIMADAS"] = df["DÍAS DURACIÓN OBRA"] * 10

        # --- EDITOR DE DATOS ---
        df_editado = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "HORAS ESTIMADAS": st.column_config.NumberColumn("HORAS ESTIMADAS (Auto)", help="Calculado: Días * 10h", disabled=True),
                "HORAS REALIZADAS": st.column_config.NumberColumn("HORAS REALIZADAS", help="Introduce las horas hechas hoy"),
                "DÍAS DURACIÓN OBRA": st.column_config.NumberColumn("DÍAS DURACIÓN", help="Días previstos de la obra")
            },
            key="editor_horas"
        )

        if st.button("💾 GUARDAR REGISTRO DE HORAS", type="primary"):
            # Recalcular por si acaso antes de guardar
            df_editado["HORAS ESTIMADAS"] = pd.to_numeric(df_editado["DÍAS DURACIÓN OBRA"], errors='coerce').fillna(0) * 10
            
            df_final = df_editado.fillna("").astype(str)
            datos_subir = [df_final.columns.values.tolist()] + df_final.values.tolist()
            ws.clear()
            ws.update('A1', datos_subir)
            st.success("✅ Horas actualizadas y cálculos guardados.")
            time.sleep(1)
            st.rerun()

# --- OTROS MÓDULOS (Dashboard / Obras / etc) ---
else:
    st.write(f"Has seleccionado {menu}. El código para esta sección sigue la misma lógica de los pasos anteriores.")
