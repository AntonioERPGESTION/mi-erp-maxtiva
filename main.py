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

# Estructura Maestra Integrada
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

# --- MENÚ LATERAL ---
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=100)
    seccion = st.selectbox("Gestión Central", ["📊 Dashboard de Producción", "📅 Agenda y Tareas Extras", "🕒 Imputación de Partes", "🏗️ Obras", "👥 Personal", "📦 Almacén/Inventario", "🛒 Pedidos", "⚠️ Incidencias", "⚙️ Usuarios"])
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False; st.rerun()

# --- 📊 DASHBOARD DE PRODUCCIÓN ---
if seccion == "📊 Dashboard de Producción":
    st.header("Análisis de Costes y Facturación Extras")
    df_i, _ = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    
    if not df_o.empty:
        # Cálculos de Facturación
        df_i['H_NUM'] = df_i['HORAS_TOTALES'].apply(to_num)
        df_i['MAT_NUM'] = df_i['COSTE_MATERIALES'].apply(to_num)
        df_i['VIAJE_NUM'] = df_i[['DIETAS', 'GASOLINA', 'PEAJES']].applymap(to_num).sum(axis=1)
        
        # Solo lo que hemos marcado como facturable
        df_fact = df_i[df_i['FACTURABLE'] == 'SÍ'].copy()
        resumen = df_fact.groupby('OBRA')[['H_NUM', 'MAT_NUM', 'VIAJE_NUM']].sum().reset_index()
        resumen['TOTAL_A_FACTURAR'] = resumen['H_NUM']*25 + resumen['MAT_NUM'] + resumen['VIAJE_NUM'] # Ejemplo: 25€/h

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Pendiente de Facturar por Obra (€)")
            st.plotly_chart(px.bar(resumen, x='OBRA', y='TOTAL_A_FACTURAR', color='OBRA'))
        with c2:
            st.subheader("Desglose de Costes Extras")
            st.plotly_chart(px.pie(resumen, values='TOTAL_A_FACTURAR', names='OBRA', hole=.3))

# --- 📅 AGENDA Y TAREAS EXTRAS ---
elif seccion == "📅 Agenda y Tareas Extras":
    st.header("Planificación de Trabajos y Tareas Extras")
    df_a, ws_a = asegurar_y_obtener_datos(sh, "Agenda_Tareas")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Personal")

    with st.expander("📝 Crear Nueva Tarea / Orden de Trabajo"):
        with st.form("f_tarea"):
            c1, c2 = st.columns(2)
            fecha = c1.date_input("Fecha Programada")
            obra = c1.selectbox("Obra", df_o['NOMBRE'].unique() if not df_o.empty else ["-"])
            tra = c2.selectbox("Trabajador", df_e['NOMBRE'].unique() if not df_e.empty else ["-"])
            horas_p = c2.number_input("Horas Previstas", 0.0)
            desc = st.text_area("Descripción del Trabajo Extra")
            fact = st.checkbox("¿Trabajo Facturable a Cliente?", value=True)
            
            if st.form_submit_button("Añadir a Agenda"):
                ws_a.append_row([str(fecha), tra, obra, desc, horas_p, "SÍ" if fact else "NO", "PENDIENTE"])
                st.rerun()

    st.subheader("Listado de Tareas Programadas")
    df_ed = st.data_editor(df_a, num_rows="dynamic", use_container_width=True, column_config={
        "ESTADO": st.column_config.SelectboxColumn(options=["PENDIENTE", "EN CURSO", "FINALIZADO"]),
        "FACTURABLE": st.column_config.SelectboxColumn(options=["SÍ", "NO"])
    })
    if st.button("Guardar Cambios Agenda"):
        ws_a.clear(); ws_a.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()

# --- 🕒 IMPUTACIÓN DE PARTES (CON MATERIALES) ---
elif seccion == "🕒 Imputación de Partes":
    st.header("Carga de Partes de Trabajo y Materiales")
    df_i, ws_i = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Personal")
    df_v, _ = asegurar_y_obtener_datos(sh, "Almacén/Inventario")

    with st.expander("➕ Subir Parte de Trabajo"):
        with st.form("f_parte"):
            c1, c2, c3 = st.columns(3)
            f = c1.date_input("Fecha")
            o = c1.selectbox("Obra", df_o['NOMBRE'].unique() if not df_o.empty else ["-"])
            t = c2.selectbox("Trabajador", df_e['NOMBRE'].unique() if not df_e.empty else ["-"])
            h = c2.number_input("Horas Reales", 0.0, 11.0)
            
            mat = c3.multiselect("Materiales Utilizados", df_v['ARTICULO'].unique() if not df_v.empty else [])
            c_mat = c3.number_input("Coste Total Materiales (€)", 0.0)
            
            ext = st.text_input("Referencia Tarea Extra (Si procede)")
            fac = st.radio("¿Es Facturable?", ["SÍ", "NO"], horizontal=True)
            
            if st.form_submit_button("Registrar Parte"):
                ws_i.append_row([str(f), t, o, ext, h, ", ".join(mat), c_mat, 0, 0, 0, fac])
                st.success("Parte registrado y vinculado."); st.rerun()

    st.subheader("Histórico de Imputaciones")
    df_ed = st.data_editor(df_i, num_rows="dynamic", use_container_width=True)
    if st.button("Actualizar Histórico"):
        ws_i.clear(); ws_i.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()

# --- RESTO DE MÓDULOS ---
else:
    mapa = {"🏗️ Obras":"Obras", "👥 Personal":"Empleados", "📦 Almacén/Inventario":"Inventario", "🛒 Pedidos":"Pedidos", "⚠️ Incidencias":"Incidencias", "⚙️ Usuarios":"USUARIOS"}
    nombre_h = mapa[seccion]
    st.header(f"Gestión de {seccion}")
    df, ws = asegurar_y_obtener_datos(sh, nombre_h)
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button(f"Sincronizar {seccion}"):
        ws.clear(); ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()); st.rerun()
