import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="ERP GRUPO MAXTIVA", layout="wide", page_icon="⚡")

SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"
# Nombres exactos de tus archivos en la raíz
LOGOS = ["logo_maxtiva.png", "logo_ceta.png", "logo_ipalux.png"]

# --- CONEXIÓN CON CACHE (Para evitar desconexiones) ---
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
        data = ws.get_all_values()
        if not data:
            return pd.DataFrame(), ws
        
        df = pd.DataFrame(data[1:], columns=data[0])
        # Normalizar cabeceras
        df.columns = [str(c).upper().strip() for c in df.columns]
        # Limpieza de espacios en celdas
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df, ws
    except Exception as e:
        st.sidebar.error(f"Error en hoja {nombre_hoja}: {e}")
        return pd.DataFrame(), None

# --- ESTADO DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        # Mostrar logos en el login
        l_cols = st.columns(3)
        for i, l_name in enumerate(LOGOS):
            if os.path.exists(l_name):
                l_cols[i].image(l_name, use_container_width=True)
        
        st.title("Acceso ERP Maxtiva")
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                sh = conectar_bbdd()
                if sh:
                    df_u, _ = obtener_datos(sh, "USUARIOS")
                    if not df_u.empty:
                        # Buscamos columna contraseña (con Ñ o sin ella)
                        col_p = 'CONTRASEÑA' if 'CONTRASEÑA' in df_u.columns else 'PASSWORD'
                        match = df_u[(df_u['USUARIO'] == u) & (df_u[col_p] == p)]
                        if not match.empty:
                            st.session_state.autenticado = True
                            st.session_state.usuario = u
                            st.session_state.rol = str(match.iloc[0].get('ROL', 'EMPLEADO')).upper()
                            st.rerun()
                    st.error("Usuario o contraseña incorrectos.")
    st.stop()

# --- APP PRINCIPAL (Si está autenticado) ---
sh = conectar_bbdd()

with st.sidebar:
    # Logos en el menú lateral
    for l_name in LOGOS:
        if os.path.exists(l_name):
            st.image(l_name, width=120)
    
    st.write("---")
    st.write(f"👤 **{st.session_state.usuario}**")
    st.write(f"🔑 Rol: `{st.session_state.rol}`")
    st.write("---")
    
    menu = st.radio("Módulos", [
        "📊 Dashboard", "🏗️ Obras", "💰 Gastos", 
        "👥 Personal", "📦 Inventario", "📅 Agenda", 
        "📝 Pedidos/Incidencias", "⚙️ Sistema"
    ])
    
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- MÓDULO DASHBOARD (REPARADO) ---
if menu == "📊 Dashboard":
    st.header("Dashboard de Gestión")
    df_g, _ = obtener_datos(sh, "Gastos_Detalle")
    df_o, _ = obtener_datos(sh, "Obras")
    
    if not df_g.empty and not df_o.empty:
        # Forzar conversión numérica de importes y presupuestos
        df_g['IMPORTE'] = pd.to_numeric(df_g['IMPORTE'], errors='coerce').fillna(0)
        df_o['PRESUPUESTO'] = pd.to_numeric(df_o['PRESUPUESTO'], errors='coerce').fillna(0)
        
        # Agrupar gastos por obra
        g_obra = df_g.groupby('OBRA')['IMPORTE'].sum().reset_index().rename(columns={'OBRA':'NOMBRE', 'IMPORTE':'GASTO_REAL'})
        
        # Cruzar con tabla de obras
        df_plot = pd.merge(df_o, g_obra, on='NOMBRE', how='left').fillna(0)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Gasto Total", f"{df_g['IMPORTE'].sum():,.2f} €")
        c2.metric("Nº Obras", len(df_o))
        c3.metric("Ppto. Total", f"{df_o['PRESUPUESTO'].sum():,.2f} €")
        
        if not df_plot.empty:
            fig = px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_REAL'], 
                         barmode='group', title="Presupuesto vs Gasto Real",
                         color_discrete_map={"PRESUPUESTO": "#1f77b4", "GASTO_REAL": "#ef553b"})
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos suficientes para mostrar gráficos. Revisa las hojas 'Obras' y 'Gastos_Detalle'.")

# --- MÓDULOS DE DATOS ---
elif menu in ["🏗️ Obras", "💰 Gastos", "👥 Personal", "📦 Inventario", "📅 Agenda", "📝 Pedidos/Incidencias"]:
    mapa = {
        "🏗️ Obras": "Obras", "💰 Gastos": "Gastos_Detalle", 
        "👥 Personal": "Empleados", "📦 Inventario": "Inventario",
        "📅 Agenda": "Planificacion", "📝 Pedidos/Incidencias": "Incidencias"
    }
    nombre_h = mapa[menu]
    df, ws = obtener_datos(sh, nombre_h)
    
    st.subheader(f"Gestión de {nombre_h}")
    
    if st.session_state.rol == "ADMIN":
        df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"ed_{nombre_h}")
        if st.button("💾 Guardar Cambios"):
            ws.clear()
            # Reinsertar cabeceras + datos
            ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
            st.success("¡Datos actualizados en Google Sheets!")
            st.rerun()
    else:
        st.dataframe(df, use_container_width=True)

# --- MÓDULO SISTEMA ---
elif menu == "⚙️ Sistema":
    st.header("Configuración")
    if st.session_state.rol == "ADMIN":
        st.write("Administración de Usuarios")
        df_u, ws_u = obtener_datos(sh, "USUARIOS")
        df_u_ed = st.data_editor(df_u, num_rows="dynamic", use_container_width=True)
        if st.button("Guardar Usuarios"):
            ws_u.clear()
            ws_u.update('A1', [df_u_ed.columns.tolist()] + df_u_ed.values.tolist())
            st.success("Usuarios actualizados.")
    else:
        st.error("No tienes permisos.")
