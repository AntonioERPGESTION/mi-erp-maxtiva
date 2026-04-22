import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="ERP GRUPO MAXTIVA", layout="wide", page_icon="⚡")

SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"
LOGOS = ["logo_maxtiva.png", "logo_ceta.png", "logo_ipalux.png"]

# --- ESTRUCTURA COMPLETA DE LA BASE DE DATOS ---
ESTRUCTURA_BBDD = {
    "USUARIOS": ["USUARIO", "CONTRASEÑA", "ROL"],
    "Obras": ["NOMBRE", "PRESUPUESTO", "CLIENTE", "ESTADO"],
    "Empleados": ["NOMBRE", "DNI", "CARGO", "COSTE_H_NORMAL", "COSTE_H_EXTRA"],
    "Imputaciones": ["FECHA", "TRABAJADOR", "OBRA", "HORAS_TOTALES", "DIETAS", "GASOLINA", "PEAJES", "ORA", "OTROS"],
    "Inventario": ["REFERENCIA", "ARTICULO", "STOCK", "UBICACION", "ESTADO"],
    "Pedidos_Proveedores": ["FECHA", "PROVEEDOR", "MATERIAL", "CANTIDAD", "IMPORTE", "ESTADO"],
    "Incidencias": ["FECHA", "OBRA", "TRABAJADOR", "DESCRIPCION", "URGENCIA", "ESTADO"],
    "Agenda_Planificacion": ["FECHA_INICIO", "FECHA_FIN", "OBRA", "EQUIPO_ASIGNADO", "NOTAS"]
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
            ws.append_row(columnas_nec)
            return pd.DataFrame(columns=columnas_nec), ws
        
        df = pd.DataFrame(data[1:], columns=[c.upper().strip() for c in data[0]])
        for c in columnas_nec:
            if c not in df.columns: df[c] = ""
        return df, ws
    except:
        return pd.DataFrame(columns=columnas_nec), None

def to_num(val):
    if val is None or str(val).strip() in ["", "None"]: return 0.0
    try:
        return float(str(val).replace('€', '').replace(' ', '').replace(',', '.'))
    except: return 0.0

# --- AUTENTICACIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

sh = conectar_bbdd()

if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.write("#")
        l_cols = st.columns(3)
        for i, l in enumerate(LOGOS):
            if os.path.exists(l): l_cols[i].image(l, use_container_width=True)
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                df_u, _ = asegurar_y_obtener_datos(sh, "USUARIOS")
                if (df_u.empty and u=="admin" and p=="admin") or (u in df_u['USUARIO'].values and p in df_u['CONTRASEÑA'].values):
                    st.session_state.autenticado, st.session_state.usuario = True, u
                    st.session_state.rol = "ADMIN"
                    st.rerun()
                st.error("Acceso denegado")
    st.stop()

# --- NAVEGACIÓN LATERAL ---
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=110)
    st.title("Panel de Control")
    menu = st.option_menu if hasattr(st, 'option_menu') else st.radio
    seccion = menu("Menú Principal", [
        "📊 Dashboard General", 
        "🕒 Horas y Gastos", 
        "🏗️ Obras", 
        "👥 Personal", 
        "📦 Inventario", 
        "🛒 Pedidos", 
        "⚠️ Incidencias", 
        "📅 Agenda", 
        "⚙️ Sistema"
    ])
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- 1. DASHBOARD GENERAL ---
if seccion == "📊 Dashboard General":
    st.header("Estado Financiero y Operativo")
    df_i, _ = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_p, _ = asegurar_y_obtener_datos(sh, "Pedidos_Proveedores")
    
    if not df_o.empty:
        # Cálculo de costes totales por obra
        df_i['COSTO_TOTAL'] = df_i[['DIETAS', 'GASOLINA', 'PEAJES', 'ORA', 'OTROS']].applymap(to_num).sum(axis=1)
        resumen_gastos = df_i.groupby('OBRA')['COSTO_TOTAL'].sum().reset_index().rename(columns={'OBRA':'NOMBRE', 'COSTO_TOTAL':'GASTO_IMPUTADO'})
        
        df_o['PRESUPUESTO'] = df_o['PRESUPUESTO'].apply(to_num)
        df_plot = pd.merge(df_o, resumen_gastos, on='NOMBRE', how='left').fillna(0)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Presupuesto Vivo", f"{df_plot['PRESUPUESTO'].sum():,.2f} €")
        c2.metric("Gasto Operativo", f"{df_plot['GASTO_IMPUTADO'].sum():,.2f} €")
        c3.metric("Pedidos Pendientes", len(df_p[df_p['ESTADO'] != 'RECIBIDO']))
        
        fig = px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_IMPUTADO'], barmode='group', title="Rendimiento por Obra")
        st.plotly_chart(fig, use_container_width=True)

# --- 2. HORAS Y GASTOS (MÓDULO SOLICITADO) ---
elif seccion == "🕒 Horas y Gastos":
    st.header("Imputación de Jornada y Gastos de Viaje")
    df_i, ws_i = asegurar_y_obtener_datos(sh, "Imputaciones")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Empleados")
    
    with st.expander("➕ Registrar Nueva Jornada", expanded=True):
        with st.form("form_horas"):
            c1, c2, c3 = st.columns(3)
            f = c1.date_input("Fecha")
            t = c2.selectbox("Trabajador", df_e['NOMBRE'].unique()) if not df_e.empty else st.warning("Crea empleados primero")
            o = c3.selectbox("Obra", df_o['NOMBRE'].unique()) if not df_o.empty else st.warning("Crea obras primero")
            
            st.write("---")
            h_tot = st.slider("Horas Totales (Máx. 11h)", 0.0, 11.0, 8.0, help="8h normales + 3h extras máx.")
            
            c4, c5, c6, c7 = st.columns(4)
            d = c4.number_input("Dietas (€)", 0.0)
            g = c5.number_input("Gasolina (€)", 0.0)
            p = c6.number_input("Peajes (€)", 0.0)
            ora = c7.number_input("ORA/Parking (€)", 0.0)
            
            if st.form_submit_button("Guardar Imputación"):
                ws_i.append_row([str(f), t, o, h_tot, d, g, p, ora, 0])
                st.success("Registrado.")
                st.rerun()
    
    st.subheader("Historial de Imputaciones")
    df_ed = st.data_editor(df_i, num_rows="dynamic", use_container_width=True)
    if st.button("Sincronizar Historial"):
        ws_i.clear(); ws_i.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())

# --- 3. INVENTARIO Y PEDIDOS ---
elif seccion == "📦 Inventario":
    st.header("Control de Almacén y Stock")
    df, ws = asegurar_y_obtener_datos(sh, "Inventario")
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button("Guardar Inventario"):
        ws.clear(); ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())

elif seccion == "🛒 Pedidos":
    st.header("Pedidos a Proveedores")
    df, ws = asegurar_y_obtener_datos(sh, "Pedidos_Proveedores")
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, 
                          column_config={"ESTADO": st.column_config.SelectboxColumn(options=["PENDIENTE", "SOLICITADO", "RECIBIDO"])})
    if st.button("Actualizar Pedidos"):
        ws.clear(); ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())

# --- 4. INCIDENCIAS Y AGENDA ---
elif seccion == "⚠️ Incidencias":
    st.header("Registro de Incidencias en Obra")
    df, ws = asegurar_y_obtener_datos(sh, "Incidencias")
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button("Guardar Incidencias"):
        ws.clear(); ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())

elif seccion == "📅 Agenda":
    st.header("Planificación de Equipos")
    df, ws = asegurar_y_obtener_datos(sh, "Agenda_Planificacion")
    st.info("Planifica las fechas de inicio y fin para cada equipo y obra.")
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True,
                          column_config={"FECHA_INICIO": st.column_config.DateColumn(), "FECHA_FIN": st.column_config.DateColumn()})
    if st.button("Guardar Agenda"):
        ws.clear(); ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())

# --- 5. MÓDULOS DE CONFIGURACIÓN ---
elif seccion in ["🏗️ Obras", "👥 Personal", "⚙️ Sistema"]:
    mapa = {"🏗️ Obras": "Obras", "👥 Personal": "Empleados", "⚙️ Sistema": "USUARIOS"}
    nombre = mapa[seccion]
    df, ws = asegurar_y_obtener_datos(sh, nombre)
    st.subheader(f"Gestión de {nombre}")
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button(f"Sincronizar {nombre}"):
        ws.clear(); ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
