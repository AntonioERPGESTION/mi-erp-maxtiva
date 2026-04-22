import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="ERP GRUPO MAXTIVA", layout="wide", page_icon="⚡")

SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"
LOGOS = ["logo_maxtiva.png", "logo_ceta.png", "logo_ipalux.png"]

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

def obtener_datos(sh, nombre_hoja):
    try:
        ws = sh.worksheet(nombre_hoja)
        data = ws.get_all_values()
        if not data: return pd.DataFrame(), ws
        df = pd.DataFrame(data[1:], columns=data[0])
        df.columns = [str(c).upper().strip() for c in df.columns]
        return df, ws
    except:
        return pd.DataFrame(), None

# --- SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- LOGIN (Simplificado para persistencia) ---
if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        l_cols = st.columns(3)
        for i, l in enumerate(LOGOS):
            if os.path.exists(l): l_cols[i].image(l, use_container_width=True)
        st.title("Acceso ERP Maxtiva")
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                sh = conectar_bbdd()
                df_u, _ = obtener_datos(sh, "USUARIOS")
                if not df_u.empty:
                    col_p = 'CONTRASEÑA' if 'CONTRASEÑA' in df_u.columns else 'PASSWORD'
                    match = df_u[(df_u['USUARIO'].astype(str) == u) & (df_u[col_p].astype(str) == p)]
                    if not match.empty:
                        st.session_state.autenticado, st.session_state.usuario = True, u
                        st.session_state.rol = str(match.iloc[0].get('ROL', 'EMPLEADO')).upper()
                        st.rerun()
                st.error("Error de acceso")
    st.stop()

sh = conectar_bbdd()

# --- SIDEBAR ---
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=120)
    st.write(f"👤 **{st.session_state.usuario}** ({st.session_state.rol})")
    menu = st.radio("Menú", ["📊 Dashboard", "💰 Carga de Gastos", "🏗️ Obras", "👥 Personal", "⚙️ Sistema"])
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- MÓDULO 1: DASHBOARD REPARADO ---
if menu == "📊 Dashboard":
    st.header("Análisis de Gastos por Obra")
    df_g, _ = obtener_datos(sh, "Gastos_Detalle")
    df_o, _ = obtener_datos(sh, "Obras")
    
    if not df_g.empty and not df_o.empty:
        # Limpieza de datos numéricos
        df_g['IMPORTE'] = pd.to_numeric(df_g['IMPORTE'].astype(str).str.replace(',','.'), errors='coerce').fillna(0)
        df_o['PRESUPUESTO'] = pd.to_numeric(df_o['PRESUPUESTO'].astype(str).str.replace(',','.'), errors='coerce').fillna(0)
        
        # Agrupar y cruzar
        g_obra = df_g.groupby('OBRA')['IMPORTE'].sum().reset_index().rename(columns={'OBRA':'NOMBRE', 'IMPORTE':'GASTO_REAL'})
        df_plot = pd.merge(df_o, g_obra, on='NOMBRE', how='left').fillna(0)
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Total Gastado", f"{df_g['IMPORTE'].sum():,.2f} €")
            st.dataframe(df_plot[['NOMBRE', 'PRESUPUESTO', 'GASTO_REAL']], hide_index=True)
        with c2:
            fig = px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_REAL'], barmode='group', title="Presupuesto vs Gasto Real")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Faltan datos en Obras o Gastos_Detalle")

# --- MÓDULO 2: CARGA DE GASTOS CON DESPLEGABLES ---
elif menu == "💰 Carga de Gastos":
    st.header("Registro de Gastos")
    df_g, ws_g = obtener_datos(sh, "Gastos_Detalle")
    df_o, _ = obtener_datos(sh, "Obras")
    df_e, _ = obtener_datos(sh, "Empleados")
    
    # Preparamos las listas para los desplegables
    lista_obras = df_o['NOMBRE'].unique().tolist() if not df_o.empty else []
    lista_trabajadores = df_e['NOMBRE'].unique().tolist() if not df_e.empty else []

    st.info("Utiliza los desplegables en las columnas 'OBRA' y 'TRABAJADOR' para evitar errores.")
    
    # Editor con validación de columnas
    df_ed = st.data_editor(
        df_g,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "OBRA": st.column_config.SelectboxColumn("Seleccionar Obra", options=lista_obras, required=True),
            "TRABAJADOR": st.column_config.SelectboxColumn("Seleccionar Trabajador", options=lista_trabajadores, required=True),
            "IMPORTE": st.column_config.NumberColumn("Importe (€)", format="%.2f"),
            "FECHA": st.column_config.DateColumn("Fecha")
        }
    )
    
    if st.button("💾 Guardar Gastos"):
        ws_g.clear()
        ws_g.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
        st.success("Gastos guardados y Dashboard actualizado.")
        st.rerun()

# --- RESTO DE MÓDULOS ---
elif menu in ["🏗️ Obras", "👥 Personal", "⚙️ Sistema"]:
    tablas = {"🏗️ Obras": "Obras", "👥 Personal": "Empleados", "⚙️ Sistema": "USUARIOS"}
    nombre = tablas[menu]
    df, ws = obtener_datos(sh, nombre)
    
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button(f"💾 Guardar {nombre}"):
        ws.clear()
        ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
        st.success("Actualizado")
