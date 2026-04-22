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

# Estructura Maestra con campos de Facturación y Vinculación
ESTRUCTURA_BBDD = {
    "USUARIOS": ["USUARIO", "CONTRASEÑA", "ROL"],
    "Obras": ["NOMBRE", "PRESUPUESTO", "CLIENTE", "ESTADO"],
    "Empleados": ["NOMBRE", "DNI", "CARGO", "COSTE_H_NORMAL", "COSTE_H_EXTRA"],
    "Imputaciones": ["FECHA", "TRABAJADOR", "OBRA", "HORAS_TOTALES", "DIETAS", "GASOLINA", "PEAJES", "ORA", "OTROS", "FACTURABLE"],
    "Inventario": ["REFERENCIA", "ARTICULO", "STOCK", "UBICACION"],
    "Pedidos": ["FECHA", "PROVEEDOR", "MATERIAL", "CANTIDAD", "IMPORTE", "ESTADO"],
    "Incidencias": ["FECHA", "OBRA", "TRABAJADOR", "DESCRIPCION", "ESTADO"],
    "Agenda": ["FECHA_INICIO", "FECHA_FIN", "OBRA", "TRABAJADOR", "FACTURABLE", "NOTAS"]
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
        
        df = pd.DataFrame(data[1:], columns=[c.upper().strip() for c in data[0]])
        for c in columnas_nec:
            if c not in df.columns: df[c] = ""
        return df.fillna(""), ws
    except:
        return pd.DataFrame(columns=columnas_nec), None

def to_num(val):
    if val is None or str(val).strip() in ["", "None"]: return 0.0
    try:
        return float(str(val).replace('€', '').replace(' ', '').replace(',', '.'))
    except: return 0.0

# --- SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

sh = conectar_bbdd()

if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("Acceso ERP Maxtiva")
        with st.form("Login"):
            u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                df_u, _ = asegurar_y_obtener_datos(sh, "USUARIOS")
                if (u == "admin" and p == "admin") or (not df_u.empty and u in df_u['USUARIO'].values):
                    st.session_state.autenticado = True
                    st.rerun()
    st.stop()

# --- NAVEGACIÓN ---
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=100)
    seccion = st.selectbox("Módulos", ["📊 Dashboard"] + list(ESTRUCTURA_BBDD.keys()))
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- 📊 DASHBOARD MULTIDIMENSIONAL ---
if seccion == "📊 Dashboard":
    st.header("Dashboard Inteligente de Obras")
    df_i, _ = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    
    if df_o.empty:
        st.warning("No hay obras registradas.")
    else:
        # Procesamiento de datos para el Dashboard
        df_o['PRESUPUESTO'] = df_o['PRESUPUESTO'].apply(to_num)
        
        # Limpieza de Imputaciones
        for col in ['HORAS_TOTALES', 'DIETAS', 'GASOLINA', 'PEAJES', 'ORA', 'OTROS']:
            df_i[col] = df_i[col].apply(to_num)
        
        # Cálculos derivados
        df_i['SUMA_GASTOS'] = df_i[['DIETAS', 'GASOLINA', 'PEAJES', 'ORA', 'OTROS']].sum(axis=1)
        
        # Selector de Vista
        vista = st.radio("Seleccionar métrica de análisis:", 
                         ["Totales (Presupuesto vs Gastos)", "Solo Facturable", "Solo Gastos de Viaje", "Horas Imputadas"],
                         horizontal=True)
        
        if vista == "Totales (Presupuesto vs Gastos)":
            res = df_i.groupby('OBRA')['SUMA_GASTOS'].sum().reset_index().rename(columns={'OBRA':'NOMBRE', 'SUMA_GASTOS':'GASTO_TOTAL'})
            df_plot = pd.merge(df_o, res, on='NOMBRE', how='left').fillna(0)
            fig = px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_TOTAL'], barmode='group', title="Control Presupuestario")
            st.plotly_chart(fig, use_container_width=True)

        elif vista == "Solo Facturable":
            res = df_i[df_i['FACTURABLE'] == 'SÍ'].groupby('OBRA')['HORAS_TOTALES'].sum().reset_index()
            st.plotly_chart(px.bar(res, x='OBRA', y='HORAS_TOTALES', title="Horas Totales Facturables por Obra", color_discrete_sequence=['#2ECC71']))

        elif vista == "Solo Gastos de Viaje":
            res = df_i.groupby('OBRA')[['DIETAS', 'GASOLINA', 'PEAJES', 'ORA']].sum().reset_index()
            fig = px.bar(res, x='OBRA', y=['DIETAS', 'GASOLINA', 'PEAJES', 'ORA'], title="Desglose de Gastos por Obra")
            st.plotly_chart(fig, use_container_width=True)

        elif vista == "Horas Imputadas":
            res = df_i.groupby('OBRA')['HORAS_TOTALES'].sum().reset_index()
            st.plotly_chart(px.bar(res, x='OBRA', y='HORAS_TOTALES', title="Volumen de Horas Totales por Obra", color_discrete_sequence=['#3498DB']))

# --- 📅 AGENDA CONECTADA ---
elif seccion == "Agenda":
    st.header("Planificación y Agenda")
    df_a, ws_a = asegurar_y_obtener_datos(sh, "Agenda")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Empleados")

    lista_e = df_e['NOMBRE'].unique().tolist() if not df_e.empty else ["SIN EMPLEADOS"]
    lista_o = df_o['NOMBRE'].unique().tolist() if not df_o.empty else ["SIN OBRAS"]

    with st.expander("Añadir a la Agenda"):
        with st.form("f_age"):
            c1, c2 = st.columns(2)
            f_i = c1.date_input("Inicio")
            f_f = c1.date_input("Fin")
            tra = c2.selectbox("Trabajador", lista_e)
            obr = c2.selectbox("Obra", lista_o)
            fac = st.selectbox("¿Facturable?", ["SÍ", "NO"])
            if st.form_submit_button("Agendar"):
                ws_a.append_row([str(f_i), str(f_f), obr, tra, fac, ""])
                st.rerun()

    df_ed = st.data_editor(df_a, num_rows="dynamic", use_container_width=True, column_config={
        "TRABAJADOR": st.column_config.SelectboxColumn("Trabajador", options=lista_e),
        "OBRA": st.column_config.SelectboxColumn("Obra", options=lista_o),
        "FACTURABLE": st.column_config.SelectboxColumn("Facturable", options=["SÍ", "NO"])
    })
    if st.button("Guardar Agenda"):
        ws_a.clear(); ws_a.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()

# --- 🕒 IMPUTACIONES ---
elif seccion == "Imputaciones":
    st.header("Imputación de Jornada")
    df_i, ws_i = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Empleados")
    
    lista_e = df_e['NOMBRE'].unique().tolist() if not df_e.empty else ["SIN EMPLEADOS"]
    lista_o = df_o['NOMBRE'].unique().tolist() if not df_o.empty else ["SIN OBRAS"]

    df_ed = st.data_editor(df_i, num_rows="dynamic", use_container_width=True, column_config={
        "TRABAJADOR": st.column_config.SelectboxColumn("Trabajador", options=lista_e),
        "OBRA": st.column_config.SelectboxColumn("Obra", options=lista_o),
        "FACTURABLE": st.column_config.SelectboxColumn("Facturable", options=["SÍ", "NO"]),
        "HORAS_TOTALES": st.column_config.NumberColumn(min_value=0, max_value=11)
    })
    if st.button("Sincronizar"):
        ws_i.clear(); ws_i.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()

# --- OTROS MÓDULOS ---
else:
    st.header(f"Módulo: {seccion}")
    df, ws = asegurar_y_obtener_datos(sh, seccion)
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button(f"Guardar {seccion}"):
        ws.clear(); ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()
