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

# Esta es la "Biblia" de tu ERP. Si no está en el Excel, el código lo crea.
ESTRUCTURA_BBDD = {
    "USUARIOS": ["USUARIO", "CONTRASEÑA", "ROL"],
    "Obras": ["NOMBRE", "PRESUPUESTO", "ESTADO"],
    "Gastos_Detalle": ["FECHA", "OBRA", "TRABAJADOR", "CONCEPTO", "IMPORTE"],
    "Empleados": ["NOMBRE", "CARGO", "CATEGORIA"],
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

def asegurar_estructura_fisica(sh, nombre_hoja):
    """Verifica el Excel y crea las columnas faltantes físicamente."""
    columnas_necesarias = ESTRUCTURA_BBDD.get(nombre_hoja, [])
    try:
        try:
            ws = sh.worksheet(nombre_hoja)
        except gspread.exceptions.WorksheetNotFound:
            # Si la hoja no existe, la crea con sus cabeceras
            ws = sh.add_worksheet(title=nombre_hoja, rows="100", cols="20")
            ws.append_row(columnas_necesarias)
            return ws

        # Si la hoja existe, comprobamos las columnas
        filas = ws.get_all_values()
        if not filas:
            ws.append_row(columnas_necesarias)
        else:
            cabeceras_actuales = [str(c).upper().strip() for c in filas[0]]
            faltantes = [c for c in columnas_necesarias if c not in cabeceras_actuales]
            if faltantes:
                nueva_cabecera = cabeceras_actuales + faltantes
                ws.update('A1', [nueva_cabecera])
        return ws
    except:
        return None

def obtener_datos(sh, nombre_hoja):
    """Obtiene datos y asegura que la estructura sea correcta."""
    ws = asegurar_estructura_fisica(sh, nombre_hoja)
    if ws:
        data = ws.get_all_values()
        if len(data) <= 1:
            return pd.DataFrame(columns=ESTRUCTURA_BBDD.get(nombre_hoja, [])), ws
        df = pd.DataFrame(data[1:], columns=[c.upper().strip() for c in data[0]])
        return df, ws
    return pd.DataFrame(), None

def limpiar_dinero(val):
    if pd.isna(val) or val == "": return 0.0
    val = str(val).replace('€', '').replace(' ', '').replace(',', '.')
    try:
        return float(val)
    except:
        return 0.0

# --- LÓGICA DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

sh = conectar_bbdd()

# --- LOGIN ---
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
                # Si no hay usuarios, admin/admin es el rescate
                df_u, _ = obtener_datos(sh, "USUARIOS")
                if (df_u.empty and u == "admin" and p == "admin") or \
                   (not df_u.empty and u in df_u['USUARIO'].values and p in df_u['CONTRASEÑA'].values):
                    st.session_state.autenticado, st.session_state.usuario = True, u
                    st.session_state.rol = "ADMIN" if u == "admin" else "EMPLEADO"
                    st.rerun()
                st.error("Credenciales incorrectas")
    st.stop()

# --- INTERFAZ ---
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=120)
    menu = st.radio("Menú", ["📊 Dashboard", "💰 Gastos", "🏗️ Obras", "👥 Empleados", "⚙️ Sistema"])
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("Dashboard de Control")
    df_g, _ = obtener_datos(sh, "Gastos_Detalle")
    df_o, _ = obtener_datos(sh, "Obras")
    
    if df_o.empty:
        st.warning("No hay obras creadas. Ve al módulo de Obras.")
    else:
        df_g['IMPORTE'] = df_g['IMPORTE'].apply(limpiar_dinero)
        df_o['PRESUPUESTO'] = df_o['PRESUPUESTO'].apply(limpiar_dinero)
        
        g_obra = df_g.groupby('OBRA')['IMPORTE'].sum().reset_index().rename(columns={'OBRA':'NOMBRE', 'IMPORTE':'GASTO_REAL'})
        df_plot = pd.merge(df_o, g_obra, on='NOMBRE', how='left').fillna(0)
        
        c1, c2 = st.columns(2)
        c1.metric("Gasto Total", f"{df_plot['GASTO_REAL'].sum():,.2f} €")
        c2.metric("Presupuesto Total", f"{df_plot['PRESUPUESTO'].sum():,.2f} €")
        
        fig = px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_REAL'], barmode='group')
        st.plotly_chart(fig, use_container_width=True)

# --- CARGA DE GASTOS CON DESPLEGABLES ---
elif menu == "💰 Gastos":
    st.header("Registro de Gastos")
    df_g, ws_g = obtener_datos(sh, "Gastos_Detalle")
    df_o, _ = obtener_datos(sh, "Obras")
    df_e, _ = obtener_datos(sh, "Empleados")
    
    # Estos selectores ahora siempre tendrán contenido o avisarán
    obras = df_o['NOMBRE'].unique().tolist() if not df_o.empty else ["CREA UNA OBRA PRIMERO"]
    empleados = df_e['NOMBRE'].unique().tolist() if not df_e.empty else ["CREA UN EMPLEADO PRIMERO"]

    df_ed = st.data_editor(df_g, num_rows="dynamic", use_container_width=True,
        column_config={
            "OBRA": st.column_config.SelectboxColumn("Obra", options=obras),
            "TRABAJADOR": st.column_config.SelectboxColumn("Trabajador", options=empleados),
            "IMPORTE": st.column_config.NumberColumn("Importe (€)")
        })
    
    if st.button("💾 Guardar y Reparar Sheets"):
        ws_g.clear()
        ws_g.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
        st.success("¡Datos guardados y estructura de Excel verificada!")

# --- OTROS MÓDULOS (Obras, Empleados, Sistema) ---
elif menu in ["🏗️ Obras", "👥 Empleados", "⚙️ Sistema"]:
    mapa = {"🏗️ Obras": "Obras", "👥 Empleados": "Empleados", "⚙️ Sistema": "USUARIOS"}
    nombre = mapa[menu]
    df, ws = obtener_datos(sh, nombre)
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button(f"Guardar {nombre}"):
        ws.clear()
        ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
        st.success("Guardado.")
