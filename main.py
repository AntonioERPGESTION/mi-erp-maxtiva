import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="ERP GRUPO MAXTIVA", layout="wide", page_icon="🏗️")

SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"
# Lista de logos proporcionados
LOGOS = ["logo_maxtiva.png", "logo_ceta.png", "logo_ipalux.png"]

# --- ESTRUCTURA DE DATOS ---
ESTRUCTURA_BBDD = {
    "USUARIOS": ["USUARIO", "CONTRASEÑA", "ROL"],
    "Obras": ["NOMBRE", "PRESUPUESTO", "CLIENTE", "ESTADO"],
    "Empleados": ["NOMBRE", "CARGO", "COSTE_H_NORMAL", "COSTE_H_EXTRA"],
    "Imputaciones": ["FECHA", "TRABAJADOR", "OBRA", "TAREA_EXTRA", "HORAS_TOTALES", "MATERIALES", "COSTE_MAT", "DIETAS", "GASOLINA", "PEAJES", "FACTURABLE"],
    "Inventario": ["REFERENCIA", "ARTICULO", "STOCK", "PRECIO_VALOR"],
    "Pedidos": ["FECHA", "PROVEEDOR", "MATERIAL", "CANTIDAD", "IMPORTE", "ESTADO"],
    "Incidencias": ["FECHA", "OBRA", "TRABAJADOR", "DESCRIPCION", "ESTADO"],
    "Agenda_Tareas": ["FECHA_INICIO", "FECHA_FIN", "OBRA", "TRABAJADOR", "TAREA", "HORAS_PREVISTAS", "FACTURABLE", "ESTADO"]
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
            col_upper = c.upper()
            if col_upper not in df.columns:
                df[col_upper] = "0"
        return df.fillna("0"), ws
    except:
        return pd.DataFrame(columns=columnas_nec), None

def to_num(val):
    if val is None or str(val).strip() in ["", "None", "NaN"]: return 0.0
    try:
        return float(str(val).replace('€', '').replace(' ', '').replace(',', '.'))
    except: return 0.0

# --- AUTENTICACIÓN ---
sh = conectar_bbdd()
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.write("#")
        # Mostrar logos en el login
        l_cols = st.columns(3)
        for i, l in enumerate(LOGOS):
            if os.path.exists(l): l_cols[i].image(l, use_container_width=True)
        with st.form("Login"):
            u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
            if st.form_submit_button("Acceder"):
                st.session_state.autenticado = True; st.rerun()
    st.stop()

# --- BARRA LATERAL Y LOGOS ---
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=120)
    st.markdown("---")
    seccion = st.radio("MENÚ PRINCIPAL", [
        "📊 DASHBOARD ANALÍTICO", 
        "📅 AGENDA Y TAREAS", 
        "🕒 PARTES DE TRABAJO", 
        "🏗️ GESTIÓN DE OBRAS", 
        "👥 PERSONAL", 
        "📦 INVENTARIO", 
        "🛒 PEDIDOS", 
        "⚠️ INCIDENCIAS"
    ])
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False; st.rerun()

# --- 1. DASHBOARD ANALÍTICO (SELECCIONABLE) ---
if seccion == "📊 DASHBOARD ANALÍTICO":
    st.title("Panel de Control Maxtiva")
    df_i, _ = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    
    if df_i.empty or df_o.empty:
        st.info("Faltan datos en Obras o Imputaciones para generar métricas.")
    else:
        # Preparación de datos numérica
        cols_calc = ['HORAS_TOTALES', 'COSTE_MAT', 'DIETAS', 'GASOLINA', 'PEAJES']
        for col in cols_calc: df_i[col] = df_i[col].apply(to_num)
        df_o['PRESUPUESTO'] = df_o['PRESUPUESTO'].apply(to_num)
        
        # Filtro de tipo de informe
        tipo_info = st.selectbox("Seleccione el tipo de visualización:", [
            "Resumen General (Presupuesto vs Gastos)",
            "Análisis de Horas Facturables por Obra",
            "Desglose de Gastos de Viaje",
            "Coste de Materiales por Proyecto"
        ])
        
        if tipo_info == "Resumen General (Presupuesto vs Gastos)":
            df_i['GASTO_TOTAL'] = df_i[['COSTE_MAT', 'DIETAS', 'GASOLINA', 'PEAJES']].sum(axis=1)
            res = df_i.groupby('OBRA')['GASTO_TOTAL'].sum().reset_index().rename(columns={'OBRA':'NOMBRE'})
            df_plot = pd.merge(df_o, res, on='NOMBRE', how='left').fillna(0)
            st.plotly_chart(px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_TOTAL'], barmode='group', title="Estado Financiero por Obra"))

        elif tipo_info == "Análisis de Horas Facturables por Obra":
            res_h = df_i[df_i['FACTURABLE'] == 'SÍ'].groupby('OBRA')['HORAS_TOTALES'].sum().reset_index()
            st.plotly_chart(px.bar(res_h, x='OBRA', y='HORAS_TOTALES', title="Total Horas a Facturar", color_discrete_sequence=['#2ECC71']))

        elif tipo_info == "Desglose de Gastos de Viaje":
            res_v = df_i.groupby('OBRA')[['DIETAS', 'GASOLINA', 'PEAJES']].sum().reset_index()
            st.plotly_chart(px.bar(res_v, x='OBRA', y=['DIETAS', 'GASOLINA', 'PEAJES'], title="Gastos de Desplazamiento"))

        elif tipo_info == "Coste de Materiales por Proyecto":
            res_m = df_i.groupby('OBRA')['COSTE_MAT'].sum().reset_index()
            st.plotly_chart(px.pie(res_m, values='COSTE_MAT', names='OBRA', title="Distribución de Gasto en Materiales"))

# --- 2. AGENDA Y TAREAS (SISTEMA INTEGRADO) ---
elif seccion == "📅 AGENDA Y TAREAS":
    st.header("Planificación de Tareas y Trabajos Extras")
    df_a, ws_a = asegurar_y_obtener_datos(sh, "Agenda_Tareas")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Empleados")
    
    lista_e = df_e['NOMBRE'].unique().tolist() if not df_e.empty else ["-"]
    lista_o = df_o['NOMBRE'].unique().tolist() if not df_o.empty else ["-"]

    with st.expander("📝 Programar Nueva Tarea"):
        with st.form("f_age"):
            c1, c2 = st.columns(2)
            f_i = c1.date_input("Inicio")
            f_f = c1.date_input("Fin")
            obr = c2.selectbox("Obra", lista_o)
            tra = c2.selectbox("Trabajador", lista_e)
            tar = st.text_input("Descripción de la Tarea")
            h_p = st.number_input("Horas Estimadas", 0.0)
            fac = st.selectbox("¿Facturable?", ["SÍ", "NO"])
            if st.form_submit_button("Guardar en Agenda"):
                ws_a.append_row([str(f_i), str(f_f), obr, tra, tar, h_p, fac, "PENDIENTE"])
                st.rerun()

    df_ed = st.data_editor(df_a, num_rows="dynamic", use_container_width=True, column_config={
        "TRABAJADOR": st.column_config.SelectboxColumn(options=lista_e),
        "OBRA": st.column_config.SelectboxColumn(options=lista_o),
        "FACTURABLE": st.column_config.SelectboxColumn(options=["SÍ", "NO"]),
        "ESTADO": st.column_config.SelectboxColumn(options=["PENDIENTE", "EN CURSO", "FINALIZADO"])
    })
    if st.button("Actualizar Agenda"):
        ws_a.clear(); ws_a.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()

# --- 3. PARTES DE TRABAJO (IMPUTACIÓN) ---
elif seccion == "🕒 PARTES DE TRABAJO":
    st.header("Registro de Jornada, Gastos y Materiales")
    df_i, ws_i = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Empleados")
    
    lista_e = df_e['NOMBRE'].unique().tolist() if not df_e.empty else ["-"]
    lista_o = df_o['NOMBRE'].unique().tolist() if not df_o.empty else ["-"]

    df_ed = st.data_editor(df_i, num_rows="dynamic", use_container_width=True, column_config={
        "TRABAJADOR": st.column_config.SelectboxColumn(options=lista_e),
        "OBRA": st.column_config.SelectboxColumn(options=lista_o),
        "FACTURABLE": st.column_config.SelectboxColumn(options=["SÍ", "NO"])
    })
    if st.button("Guardar Partes"):
        ws_i.clear(); ws_i.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()

# --- OTROS MÓDULOS (GENÉRICOS) ---
else:
    mapa = {"🏗️ GESTIÓN DE OBRAS":"Obras", "👥 PERSONAL":"Empleados", "📦 INVENTARIO":"Inventario", "🛒 PEDIDOS":"Pedidos", "⚠️ INCIDENCIAS":"Incidencias"}
    target = mapa[seccion]
    st.header(f"Gestión de {seccion}")
    df, ws = asegurar_y_obtener_datos(sh, target)
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button(f"Sincronizar {seccion}"):
        ws.clear(); ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()
