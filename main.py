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

# Estructura extendida para incluir Horas y Gastos detallados
ESTRUCTURA_BBDD = {
    "USUARIOS": ["USUARIO", "CONTRASEÑA", "ROL"],
    "Obras": ["NOMBRE", "PRESUPUESTO", "ESTADO"],
    "Empleados": ["NOMBRE", "CARGO", "COSTE_HORA_NORMAL", "COSTE_HORA_EXTRA"],
    "Imputaciones": ["FECHA", "TRABAJADOR", "OBRA", "HORAS_TOTALES", "DIETAS", "GASOLINA", "PEAJES", "ORA", "OTROS_GASTOS"],
    "Inventario": ["ARTICULO", "CANTIDAD", "OBRA_ASIGNADA"],
    "Incidencias": ["FECHA", "OBRA", "DESCRIPCION", "ESTADO"]
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
            ws = sh.add_worksheet(title=nombre_hoja, rows="500", cols="20")
            ws.append_row(columnas_nec)
        
        data = ws.get_all_values()
        if not data:
            ws.append_row(columnas_nec)
            return pd.DataFrame(columns=columnas_nec), ws
        
        df = pd.DataFrame(data[1:], columns=[c.upper().strip() for c in data[0]])
        for c in columnas_nec:
            if c not in df.columns: df[c] = ""
        return df, ws
    except:
        return pd.DataFrame(columns=columnas_nec), None

def to_num(val):
    if val is None or str(val).strip() == "" or str(val).strip() == "None": return 0.0
    try:
        return float(str(val).replace('€', '').replace(' ', '').replace(',', '.'))
    except:
        return 0.0

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
                if (df_u.empty and u=="admin" and p=="admin") or (u in df_u['USUARIO'].values and p in df_u['CONTRASEÑA'].values):
                    st.session_state.autenticado, st.session_state.usuario = True, u
                    st.session_state.rol = "ADMIN"
                    st.rerun()
                st.error("Error de acceso")
    st.stop()

# --- NAVEGACIÓN ---
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=100)
    menu = st.radio("Menú ERP", ["📊 Dashboard", "🕒 Imputar Horas/Gastos", "🏗️ Obras", "👥 Personal", "📦 Inventario", "⚙️ Sistema"])
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("Estado Global de Obras")
    df_i, _ = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Empleados")
    
    if not df_o.empty and not df_i.empty:
        # Procesar costes
        df_i['H_TOTAL'] = df_i['HORAS_TOTALES'].apply(to_num)
        df_i['H_NORM'] = df_i['H_TOTAL'].apply(lambda x: min(x, 8))
        df_i['H_EXT'] = df_i['H_TOTAL'].apply(lambda x: max(0, x-8))
        
        # Gastos adicionales
        gastos_cols = ['DIETAS', 'GASOLINA', 'PEAJES', 'ORA', 'OTROS_GASTOS']
        for col in gastos_cols: df_i[col] = df_i[col].apply(to_num)
        
        df_i['TOTAL_VIAJE'] = df_i[gastos_cols].sum(axis=1)
        
        # Unir con costes de empleado (opcional, aquí simplificamos a suma de gastos)
        resumen_gastos = df_i.groupby('OBRA')[['TOTAL_VIAJE']].sum().reset_index().rename(columns={'OBRA':'NOMBRE', 'TOTAL_VIAJE':'GASTO_VIAJES'})
        
        df_o['PRESUPUESTO'] = df_o['PRESUPUESTO'].apply(to_num)
        df_plot = pd.merge(df_o, resumen_gastos, on='NOMBRE', how='left').fillna(0)
        
        st.metric("Gasto Total en Viajes/Dietas", f"{df_plot['GASTO_VIAJES'].sum():,.2f} €")
        fig = px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_VIAJES'], barmode='group', title="Presupuesto vs Gastos Operativos")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Esperando datos para generar estadísticas...")

# --- IMPUTACIONES (EL MOTOR PRINCIPAL) ---
elif menu == "🕒 Imputar Horas/Gastos":
    st.header("Registro Diario de Actividad")
    df_i, ws_i = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Empleados")
    
    obras = df_o['NOMBRE'].unique().tolist()
    empleados = df_e['NOMBRE'].unique().tolist()
    
    st.markdown("### 📝 Nueva Entrada")
    with st.expander("Añadir nueva fila de trabajo"):
        with st.form("nueva_imputacion"):
            col1, col2, col3 = st.columns(3)
            fecha = col1.date_input("Fecha", datetime.now())
            emp = col2.selectbox("Trabajador", empleados)
            obr = col3.selectbox("Obra", obras)
            
            h_tot = st.slider("Horas Totales (Máximo 11h)", 0.0, 11.0, 8.0, step=0.5)
            
            c_d, c_g, c_p, c_o = st.columns(4)
            dietas = c_d.number_input("Dietas (€)", 0.0)
            gas = c_g.number_input("Gasolina (€)", 0.0)
            peaje = c_p.number_input("Peajes (€)", 0.0)
            ora = c_o.number_input("ORA (€)", 0.0)
            
            if st.form_submit_button("➕ Registrar en el Sistema"):
                nueva_fila = [str(fecha), emp, obr, h_tot, dietas, gas, peaje, ora, 0]
                ws_i.append_row(nueva_fila)
                st.success("Imputación guardada correctamente")
                st.rerun()

    st.markdown("### 📋 Histórico Reciente")
    df_ed = st.data_editor(df_i, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Guardar Cambios en Histórico"):
        ws_i.clear()
        ws_i.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
        st.rerun()

# --- GESTIÓN DE TABLAS ---
elif menu in ["🏗️ Obras", "👥 Personal", "📦 Inventario", "⚙️ Sistema"]:
    mapa = {"🏗️ Obras":"Obras", "👥 Personal":"Empleados", "📦 Inventario":"Inventario", "⚙️ Sistema":"USUARIOS"}
    nombre = mapa[menu]
    df, ws = asegurar_y_obtener_datos(sh, nombre)
    st.subheader(f"Gestión de {nombre}")
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button(f"Guardar {nombre}"):
        ws.clear()
        ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
        st.success("Sincronizado")
