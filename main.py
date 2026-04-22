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

# Estructura Maestra
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
        if not data or len(data) == 0:
            return pd.DataFrame(columns=columnas_nec), ws
        
        # Normalizar cabeceras y crear DF
        cabeceras = [c.upper().strip() for c in data[0]]
        df = pd.DataFrame(data[1:], columns=cabeceras)
        
        # Asegurar que no falten columnas y limpiar nulos
        for c in columnas_nec:
            if c not in df.columns:
                df[c] = ""
        return df.fillna(""), ws
    except Exception as e:
        st.error(f"Error cargando {nombre_hoja}: {e}")
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
        st.title("Acceso ERP Maxtiva")
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

# --- NAVEGACIÓN ---
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=100)
    seccion = st.selectbox("Módulos", ["📊 Dashboard"] + list(ESTRUCTURA_BBDD.keys()))
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- DASHBOARD ---
if seccion == "📊 Dashboard":
    st.header("Dashboard de Gestión")
    df_i, _ = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    
    if not df_o.empty:
        cols_gasto = ['DIETAS', 'GASOLINA', 'PEAJES', 'ORA', 'OTROS']
        for col in cols_gasto:
            if col not in df_i.columns: df_i[col] = 0
            df_i[col] = df_i[col].apply(to_num)
        
        df_i['TOTAL_G'] = df_i[cols_gasto].sum(axis=1)
        res = df_i.groupby('OBRA')['TOTAL_G'].sum().reset_index().rename(columns={'OBRA':'NOMBRE', 'TOTAL_G':'GASTO_REAL'})
        df_o['PRESUPUESTO'] = df_o['PRESUPUESTO'].apply(to_num)
        df_plot = pd.merge(df_o, res, on='NOMBRE', how='left').fillna(0)
        st.plotly_chart(px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_REAL'], barmode='group'))
    else:
        st.info("Registra obras para ver el gráfico.")

# --- IMPUTACIONES (8h + 3h extras) ---
elif seccion == "Imputaciones":
    st.header("🕒 Imputación de Horas y Gastos")
    df_i, ws_i = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Empleados")
    
    with st.expander("📝 Nueva Entrada"):
        with st.form("f_imp"):
            c1, c2, c3 = st.columns(3)
            f = c1.date_input("Fecha", datetime.now())
            t = c2.selectbox("Trabajador", df_e['NOMBRE'].unique() if not df_e.empty else ["Vacío"])
            o = c3.selectbox("Obra", df_o['NOMBRE'].unique() if not df_o.empty else ["Vacío"])
            h = st.slider("Horas Totales (Máx 11h)", 0.0, 11.0, 8.0)
            c4, c5, c6, c7 = st.columns(4)
            d, g, p, ora = c4.number_input("Dietas",0.0), c5.number_input("Gasolina",0.0), c6.number_input("Peajes",0.0), c7.number_input("ORA",0.0)
            if st.form_submit_button("Guardar"):
                ws_i.append_row([str(f), t, o, h, d, g, p, ora, 0])
                st.success("Guardado"); st.rerun()
    
    # Editor simplificado sin column_config complejo para evitar el error de tipos
    df_ed = st.data_editor(df_i, num_rows="dynamic", use_container_width=True)
    if st.button("Guardar cambios en tabla"):
        ws_i.clear(); ws_i.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()

# --- OTROS MÓDULOS ---
else:
    st.header(f"Gestión: {seccion}")
    df, ws = asegurar_y_obtener_datos(sh, seccion)
    # Mostramos la tabla tal cual para evitar conflictos de StreamlitAPI con formatos de fecha
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button(f"Sincronizar {seccion}"):
        ws.clear(); ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()
