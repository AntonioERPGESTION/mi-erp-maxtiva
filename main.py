import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="ERP GRUPO MAXTIVA", layout="wide", page_icon="⚡")

SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"
LOGOS = ["logo_maxtiva.png", "logo_ceta.png", "logo_ipalux.png"]

# Estructura maestra: Si falta algo en el Excel, el código lo crea solo.
ESTRUCTURA_BBDD = {
    "USUARIOS": ["USUARIO", "CONTRASEÑA", "ROL"],
    "Obras": ["NOMBRE", "PRESUPUESTO", "CLIENTE", "ESTADO"],
    "Empleados": ["NOMBRE", "DNI", "CARGO", "COSTE_H_NORMAL", "COSTE_H_EXTRA"],
    "Imputaciones": ["FECHA", "TRABAJADOR", "OBRA", "HORAS_TOTALES", "DIETAS", "GASOLINA", "PEAJES", "ORA", "OTROS"],
    "Inventario": ["REFERENCIA", "ARTICULO", "STOCK", "UBICACION"],
    "Pedidos": ["FECHA", "PROVEEDOR", "MATERIAL", "CANTIDAD", "IMPORTE", "ESTADO"],
    "Incidencias": ["FECHA", "OBRA", "TRABAJADOR", "DESCRIPCION", "ESTADO"],
    "Agenda": ["FECHA_INICIO", "FECHA_FIN", "OBRA", "EQUIPO", "NOTAS"]
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
        if not data:
            return pd.DataFrame(columns=columnas_nec), ws
        
        df = pd.DataFrame(data[1:], columns=[c.upper().strip() for c in data[0]])
        # Asegurar que todas las columnas necesarias existan en el DataFrame
        for c in columnas_nec:
            if c not in df.columns:
                df[c] = "0"
        return df, ws
    except:
        return pd.DataFrame(columns=columnas_nec), None

def to_num(val):
    if val is None or str(val).strip() in ["", "None"]: return 0.0
    try:
        return float(str(val).replace('€', '').replace(' ', '').replace(',', '.'))
    except: return 0.0

# --- SEGURIDAD ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

sh = conectar_bbdd()

if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        cols = st.columns(3)
        for i, l in enumerate(LOGOS):
            if os.path.exists(l): cols[i].image(l, use_container_width=True)
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                df_u, _ = asegurar_y_obtener_datos(sh, "USUARIOS")
                if (u == "admin" and p == "admin") or (not df_u.empty and u in df_u['USUARIO'].values and p in df_u['CONTRASEÑA'].values):
                    st.session_state.autenticado, st.session_state.usuario = True, u
                    st.rerun()
                st.error("Credenciales incorrectas")
    st.stop()

# --- MENÚ ---
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=100)
    seccion = st.radio("Módulos", list(ESTRUCTURA_BBDD.keys()) + ["📊 Dashboard"])
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- DASHBOARD ---
if seccion == "📊 Dashboard":
    st.header("Dashboard de Gestión Maxtiva")
    df_i, _ = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    
    if not df_o.empty:
        # Cálculo de costes (reparado para evitar el error AttributeError)
        columnas_gasto = ['DIETAS', 'GASOLINA', 'PEAJES', 'ORA', 'OTROS']
        for col in columnas_gasto:
            df_i[col] = df_i[col].apply(to_num)
        
        df_i['GASTO_TOTAL'] = df_i[columnas_gasto].sum(axis=1)
        resumen = df_i.groupby('OBRA')['GASTO_TOTAL'].sum().reset_index().rename(columns={'OBRA':'NOMBRE', 'GASTO_TOTAL':'REAL'})
        
        df_o['PRESUPUESTO'] = df_o['PRESUPUESTO'].apply(to_num)
        df_plot = pd.merge(df_o, resumen, on='NOMBRE', how='left').fillna(0)
        
        st.plotly_chart(px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO', 'REAL'], barmode='group'))
    else:
        st.info("No hay datos suficientes.")

# --- MÓDULO DE IMPUTACIONES (CON LÓGICA DE 11H) ---
elif seccion == "Imputaciones":
    st.header("🕒 Registro de Horas y Gastos")
    df_i, ws_i = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Empleados")
    
    with st.expander("Añadir Nueva Imputación"):
        with st.form("f_imp"):
            c1, c2, c3 = st.columns(3)
            f = c1.date_input("Fecha")
            t = c2.selectbox("Trabajador", df_e['NOMBRE'].unique() if not df_e.empty else ["Crea empleados"])
            o = c3.selectbox("Obra", df_o['NOMBRE'].unique() if not df_o.empty else ["Crea obras"])
            
            h = st.slider("Horas (Máx 11h)", 0.0, 11.0, 8.0)
            c4, c5, c6, c7 = st.columns(4)
            d = c4.number_input("Dietas", 0.0)
            g = c5.number_input("Gasolina", 0.0)
            p = c6.number_input("Peajes", 0.0)
            ora = c7.number_input("ORA", 0.0)
            
            if st.form_submit_button("Guardar"):
                ws_i.append_row([str(f), t, o, h, d, g, p, ora, 0])
                st.success("Guardado"); st.rerun()
    
    df_ed = st.data_editor(df_i, num_rows="dynamic", use_container_width=True)
    if st.button("Actualizar"):
        ws_i.clear(); ws_i.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()

# --- RESTO DE MÓDULOS GENÉRICOS ---
else:
    st.header(f"Gestión de {seccion}")
    df, ws = asegurar_y_obtener_datos(sh, seccion)
    
    # Configuración especial para que Pedidos y Agenda tengan formato de fecha
    config = {}
    if "FECHA" in df.columns or "FECHA_INICIO" in df.columns:
        for col in df.columns:
            if "FECHA" in col: config[col] = st.column_config.DateColumn()

    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, column_config=config)
    
    if st.button(f"Guardar {seccion}"):
        ws.clear()
        ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
        st.success("Datos sincronizados"); st.rerun()
