import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import os
import time
from datetime import datetime

# --- CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="ERP GRUPO MAXTIVA", layout="wide", page_icon="⚡")

SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"
LOGOS = ["logo_maxtiva.png", "logo_ceta.png", "logo_ipalux.png"]

# --- ESTRUCTURA DE DATOS REQUERIDA ---
ESTRUCTURA_IDEAL = {
    "USUARIOS": ["USUARIO", "CONTRASEÑA", "ROL"],
    "Obras": ["NOMBRE", "PRESUPUESTO", "UBICACIÓN", "ESTADO"],
    "Gastos_Detalle": ["FECHA", "OBRA", "TRABAJADOR", "CONCEPTO", "IMPORTE"],
    "Empleados": ["NOMBRE", "DNI", "CARGO", "CATEGORÍA"],
    "Inventario": ["ARTÍCULO", "CANTIDAD", "OBRA_ASIGNADA"],
    "Planificacion": ["FECHA", "OBRA", "TRABAJADOR_ASIGNADO"],
    "Incidencias": ["FECHA", "OBRA", "DESCRIPCIÓN", "ESTADO"],
    "Pedidos": ["FECHA", "PROVEEDOR", "MATERIAL", "IMPORTE"],
    "Agenda": ["FECHA", "EVENTO", "DETALLES"]
}

def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        pk = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds).open_by_key(SPREADSHEET_ID)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_df(sh, nombre):
    try:
        ws = sh.worksheet(nombre)
        df = pd.DataFrame(ws.get_all_records())
        df.columns = [str(c).upper().strip() for c in df.columns]
        return df, ws
    except:
        return pd.DataFrame(), None

# --- FUNCIÓN DE AUTO-REPARACIÓN ---
def reparar_bbdd(sh):
    with st.spinner("Sincronizando estructura..."):
        hojas_reales = {h.title: h for h in sh.worksheets()}
        for nombre, columnas in ESTRUCTURA_IDEAL.items():
            if nombre not in hojas_reales:
                ws = sh.add_worksheet(title=nombre, rows="100", cols="20")
                ws.append_row(columnas)
            else:
                ws = hojas_reales[nombre]
                actuales = [c.upper().strip() for c in ws.row_values(1)]
                faltantes = [c for c in columnas if c not in actuales]
                if faltantes:
                    nueva_fila = actuales + faltantes
                    ws.update('A1', [nueva_fila])
    st.toast("¡Estructura de Sheets actualizada!")

# --- SESIÓN Y LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.write("#")
        lc = st.columns(3)
        for i, l in enumerate(LOGOS):
            if os.path.exists(l): lc[i].image(l, use_container_width=True)
        st.title("Acceso ERP Maxtiva")
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                sh = conectar()
                df_u, _ = obtener_df(sh, "USUARIOS")
                col_p = 'CONTRASEÑA' if 'CONTRASEÑA' in df_u.columns else 'PASSWORD'
                if not df_u.empty and u in df_u['USUARIO'].astype(str).values:
                    match = df_u[(df_u['USUARIO'].astype(str) == u) & (df_u[col_p].astype(str) == p)]
                    if not match.empty:
                        st.session_state.autenticado, st.session_state.usuario = True, u
                        st.session_state.rol = str(match.iloc[0].get('ROL', 'EMPLEADO')).upper()
                        st.rerun()
                st.error("Credenciales incorrectas")
    st.stop()

# --- INTERFAZ PRINCIPAL ---
sh = conectar()
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=150)
    st.write(f"👤 **{st.session_state.usuario}** ({st.session_state.rol})")
    menu = st.radio("Módulos", ["📊 Dashboard", "🏗️ Obras", "💰 Gastos", "👥 Personal", "📦 Inventario", "📅 Agenda", "📝 Pedidos/Incidencias", "⚙️ Sistema"])
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- MÓDULO 1: DASHBOARD INTELIGENTE ---
if menu == "📊 Dashboard":
    st.header("Análisis de Costos y Rendimiento")
    df_g, _ = obtener_df(sh, "Gastos_Detalle")
    df_o, _ = obtener_df(sh, "Obras")
    
    if not df_g.empty and 'IMPORTE' in df_g.columns:
        g_obra = df_g.groupby('OBRA')['IMPORTE'].sum().reset_index().rename(columns={'OBRA':'NOMBRE', 'IMPORTE':'GASTO_REAL'})
        df_comp = pd.merge(df_o, g_obra, on='NOMBRE', how='left').fillna(0)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Gasto Total", f"{df_g['IMPORTE'].sum():,.2f} €")
        c2.metric("Obras Activas", len(df_o))
        c3.metric("Mayor Gasto", f"{df_comp['GASTO_REAL'].max():,.2f} €")
        
        st.plotly_chart(px.bar(df_comp, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_REAL'], barmode='group', title="Presupuesto vs Realidad"), use_container_width=True)

# --- MÓDULO 2: GESTIÓN DE DATOS ---
elif menu in ["🏗️ Obras", "💰 Gastos", "👥 Personal", "📦 Inventario", "📅 Agenda", "📝 Pedidos/Incidencias"]:
    tablas = {"🏗️ Obras":"Obras", "💰 Gastos":"Gastos_Detalle", "👥 Personal":"Empleados", "📦 Inventario":"Inventario", "📅 Agenda":"Planificacion", "📝 Pedidos/Incidencias":"Incidencias"}
    df, ws = obtener_df(sh, tablas[menu])
    
    # Informe rápido para personal
    if tablas[menu] == "Empleados" and not df.empty:
        emp = st.selectbox("Buscar Informe Trabajador", df['NOMBRE'].unique())
        if st.button("Generar Informe"):
            df_g, _ = obtener_df(sh, "Gastos_Detalle")
            st.dataframe(df_g[df_g['TRABAJADOR'] == emp])

    if st.session_state.rol == "ADMIN":
        df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Guardar"):
            ws.clear()
            ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
            st.success("Sincronizado")
    else: st.dataframe(df, use_container_width=True)

# --- MÓDULO 3: SISTEMA (CONFIGURACIÓN Y REPARACIÓN) ---
elif menu == "⚙️ Sistema":
    st.header("Configuración del Sistema")
    if st.session_state.rol == "ADMIN":
        if st.button("🛠️ Sincronizar Estructura de BBDD (Arreglar Sheets)"):
            reparar_bbdd(sh)
            
        st.write("### Gestión de Usuarios")
        df_u, ws_u = obtener_df(sh, "USUARIOS")
        df_u_ed = st.data_editor(df_u, num_rows="dynamic", use_container_width=True)
        if st.button("Guardar Usuarios"):
            ws_u.clear()
            ws_u.update('A1', [df_u_ed.columns.tolist()] + df_u_ed.values.tolist())
    else: st.error("Acceso restringido")
