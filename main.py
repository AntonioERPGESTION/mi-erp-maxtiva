import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="ERP MAXTIVA - GESTIÓN TOTAL", layout="wide", page_icon="🏗️")

SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"
LOGOS = ["logo_maxtiva.png", "logo_ceta.png", "logo_ipalux.png"]

# Estructura Maestra
ESTRUCTURA_BBDD = {
    "USUARIOS": ["USUARIO", "CONTRASEÑA", "ROL"],
    "Obras": ["NOMBRE", "PRESUPUESTO", "CLIENTE", "ESTADO"],
    "Empleados": ["NOMBRE", "CARGO", "COSTE_H_NORMAL", "COSTE_H_EXTRA"],
    "Imputaciones": ["FECHA", "TRABAJADOR", "OBRA", "TAREA_EXTRA", "HORAS_TOTALES", "MATERIALES_UTILIZADOS", "COSTE_MATERIALES", "DIETAS", "GASOLINA", "PEAJES", "FACTURABLE"],
    "Inventario": ["REFERENCIA", "ARTICULO", "STOCK", "PRECIO_UNIDAD"],
    "Pedidos": ["FECHA", "PROVEEDOR", "MATERIAL", "CANTIDAD", "IMPORTE", "ESTADO"],
    "Incidencias": ["FECHA", "OBRA", "TRABAJADOR", "DESCRIPCION", "ESTADO"],
    "Agenda_Tareas": ["FECHA", "TRABAJADOR", "OBRA", "DESCRIPCION_TAREA", "HORAS_PREVISTAS", "FACTURABLE", "ESTADO"]
}

@st.cache_resource
def conectar_bbdd():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds).open_by_key(SPREADSHEET_ID)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def asegurar_y_obtener_datos(sh, nombre_hoja):
    columnas_nec = ESTRUCTURA_BBDD.get(nombre_hoja, [])
    try:
        try:
            ws = sh.worksheet(nombre_hoja)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=nombre_hoja, rows="1000", cols="20")
            ws.append_row(columnas_nec)
        
        data = ws.get_all_values()
        if not data or len(data) <= 1:
            return pd.DataFrame(columns=columnas_nec), ws
        
        # NORMALIZACIÓN CRÍTICA: Mayúsculas y sin espacios
        df = pd.DataFrame(data[1:], columns=[c.upper().strip() for c in data[0]])
        
        # Crear columnas faltantes con ceros
        for c in columnas_nec:
            if c.upper() not in df.columns:
                df[c.upper()] = "0"
        return df.fillna("0"), ws
    except:
        return pd.DataFrame(columns=columnas_nec), None

def to_num(val):
    if val is None or str(val).strip() in ["", "None", "NaN"]: return 0.0
    try:
        # Limpiar moneda y formatos europeos
        s = str(val).replace('€', '').replace(' ', '').replace(',', '.')
        return float(s)
    except: return 0.0

# --- SESIÓN ---
sh = conectar_bbdd()
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("ERP Maxtiva")
        with st.form("Login"):
            u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                st.session_state.autenticado = True; st.rerun()
    st.stop()

# --- MENÚ ---
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=100)
    seccion = st.selectbox("Módulos", ["📊 Dashboard", "📅 Agenda/Tareas", "🕒 Imputaciones", "🏗️ Obras", "👥 Personal", "📦 Inventario"])
    if st.button("Salir"):
        st.session_state.autenticado = False; st.rerun()

# --- DASHBOARD (CORREGIDO) ---
if seccion == "📊 Dashboard":
    st.header("Análisis de Costes")
    df_i, _ = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    
    if not df_i.empty:
        # Convertir a número de forma segura uno a uno para evitar el AttributeError
        cols_a_sumar = ['DIETAS', 'GASOLINA', 'PEAJES']
        for c in cols_a_sumar:
            if c not in df_i.columns: df_i[c] = 0
            df_i[c] = df_i[c].apply(to_num)
        
        df_i['VIAJE_TOTAL'] = df_i[cols_a_sumar].sum(axis=1)
        df_i['H_TOTAL'] = df_i['HORAS_TOTALES'].apply(to_num)
        
        res = df_i.groupby('OBRA')[['VIAJE_TOTAL', 'H_TOTAL']].sum().reset_index()
        st.plotly_chart(px.bar(res, x='OBRA', y=['VIAJE_TOTAL', 'H_TOTAL'], barmode='group'))
    else:
        st.info("No hay datos de imputación todavía.")

# --- MÓDULOS DE DATOS ---
else:
    # Mapeo de nombres para evitar errores de carga
    mapa = {"📅 Agenda/Tareas":"Agenda_Tareas", "🕒 Imputaciones":"Imputaciones", "🏗️ Obras":"Obras", "👥 Personal":"Empleados", "📦 Inventario":"Inventario"}
    target = mapa[seccion]
    
    st.header(f"Gestión de {seccion}")
    df, ws = asegurar_y_obtener_datos(sh, target)
    
    # Configuración de selectores si es Imputación o Agenda
    config = {}
    if target in ["Imputaciones", "Agenda_Tareas"]:
        df_e, _ = asegurar_y_obtener_datos(sh, "Empleados")
        df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
        config = {
            "TRABAJADOR": st.column_config.SelectboxColumn(options=df_e['NOMBRE'].unique().tolist() if not df_e.empty else ["-"]),
            "OBRA": st.column_config.SelectboxColumn(options=df_o['NOMBRE'].unique().tolist() if not df_o.empty else ["-"]),
            "FACTURABLE": st.column_config.SelectboxColumn(options=["SÍ", "NO"])
        }

    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, column_config=config)
    
    if st.button(f"💾 Guardar {seccion}"):
        ws.clear()
        ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
        st.success("Guardado correctamente"); st.rerun()
