import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import os
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="ERP GRUPO MAXTIVA", layout="wide", page_icon="⚡")

SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"
LOGOS = ["logo_maxtiva.png", "logo_ceta.png", "logo_ipalux.png"]

# --- 1. CONEXIÓN OPTIMIZADA CON CACHE ---
@st.cache_resource
def conectar_bbdd():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        pk = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds).open_by_key(SPREADSHEET_ID)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_datos(sh, nombre_hoja):
    try:
        ws = sh.worksheet(nombre_hoja)
        df = pd.DataFrame(ws.get_all_records())
        # Limpieza profunda de columnas y datos
        df.columns = [str(c).upper().strip() for c in df.columns]
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        return df, ws
    except:
        return pd.DataFrame(), None

# --- 2. MANEJO DE SESIÓN PERSISTENTE ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- LOGIN ---
if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        cols_l = st.columns(3)
        for i, l in enumerate(LOGOS):
            if os.path.exists(l): cols_l[i].image(l, use_container_width=True)
        
        st.title("Acceso ERP Maxtiva")
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                sh = conectar_bbdd()
                df_u, _ = obtener_datos(sh, "USUARIOS")
                if not df_u.empty:
                    col_p = 'CONTRASEÑA' if 'CONTRASEÑA' in df_u.columns else 'PASSWORD'
                    match = df_u[(df_u['USUARIO'] == u) & (df_u[col_p] == p)]
                    if not match.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario = u
                        st.session_state.rol = str(match.iloc[0].get('ROL', 'EMPLEADO')).upper()
                        st.rerun()
                st.error("Credenciales inválidas")
    st.stop()

# --- APP PRINCIPAL ---
sh = conectar_bbdd()

with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=150)
    st.write(f"👤 **{st.session_state.usuario}** ({st.session_state.rol})")
    menu = st.radio("Menú", ["📊 Dashboard", "🏗️ Obras", "💰 Gastos", "👥 Personal", "📦 Inventario", "📅 Agenda", "📝 Pedidos/Incidencias", "⚙️ Configuración"])
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- 3. DASHBOARD REPARADO (Cruce de datos inteligente) ---
if menu == "📊 Dashboard":
    st.header("Análisis de Costos y Rendimiento")
    df_g, _ = obtener_datos(sh, "Gastos_Detalle")
    df_o, _ = obtener_datos(sh, "Obras")
    
    if not df_g.empty and not df_o.empty:
        # Aseguramos que los nombres de las obras coincidan (Mayúsculas y sin espacios)
        df_g['OBRA'] = df_g['OBRA'].str.upper().str.strip()
        df_o['NOMBRE'] = df_o['NOMBRE'].str.upper().str.strip()
        
        # Agrupar gastos
        g_por_obra = df_g.groupby('OBRA')['IMPORTE'].sum().reset_index().rename(columns={'OBRA':'NOMBRE', 'IMPORTE':'GASTO_REAL'})
        
        # Unir datos
        df_plot = pd.merge(df_o, g_por_obra, on='NOMBRE', how='left').fillna(0)
        
        if df_plot['GASTO_REAL'].sum() > 0 or df_plot['PRESUPUESTO'].sum() > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("Gasto Total Grupo", f"{df_plot['GASTO_REAL'].sum():,.2f} €")
            c2.metric("Obras Registradas", len(df_o))
            c3.metric("Presupuesto Total", f"{df_plot['PRESUPUESTO'].sum():,.2f} €")
            
            fig = px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_REAL'], 
                         barmode='group', title="Comparativa Presupuesto vs Gasto Real por Obra",
                         color_discrete_sequence=["#00CC96", "#EF553B"])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Hay datos en las hojas, pero los nombres de las Obras no coinciden entre 'Obras' y 'Gastos_Detalle'.")
    else:
        st.info("Introduce datos en 'Obras' y 'Gastos_Detalle' para activar el Dashboard.")

# --- RESTO DE MÓDULOS (Omitidos para brevedad, mantener igual que el anterior) ---
# ... (🏗️ Obras, 💰 Gastos, 👥 Personal, etc.)
