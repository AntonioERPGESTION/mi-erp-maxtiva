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

ESTRUCTURA_BBDD = {
    "USUARIOS": ["USUARIO", "CONTRASEÑA", "ROL"],
    "Obras": ["NOMBRE", "PRESUPUESTO", "ESTADO"],
    "Gastos_Detalle": ["FECHA", "OBRA", "TRABAJADOR", "CONCEPTO", "IMPORTE"],
    "Empleados": ["NOMBRE", "CARGO", "CATEGORIA"]
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
            ws = sh.add_worksheet(title=nombre_hoja, rows="100", cols="20")
            ws.append_row(columnas_nec)
        
        data = ws.get_all_values()
        if not data or len(data) == 0:
            ws.append_row(columnas_nec)
            return pd.DataFrame(columns=columnas_nec), ws
        
        # Crear DataFrame y limpiar cabeceras
        df = pd.DataFrame(data[1:], columns=[c.upper().strip() for c in data[0]])
        
        # Verificar que no falten columnas críticas
        faltantes = [c for c in columnas_nec if c not in df.columns]
        if faltantes:
            for c in faltantes: df[c] = ""
            ws.update('A1', [list(df.columns)])
            
        return df, ws
    except Exception as e:
        st.error(f"Error en {nombre_hoja}: {e}")
        return pd.DataFrame(), None

def to_num(val):
    """Convierte a número de forma segura para evitar el error de Plotly."""
    if val is None or str(val).strip() == "": return 0.0
    try:
        # Limpiar símbolos, espacios y manejar comas decimales
        s = str(val).replace('€', '').replace(' ', '').replace(',', '.')
        return float(s)
    except:
        return 0.0

# --- LÓGICA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

sh = conectar_bbdd()

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
                df_u, _ = asegurar_y_obtener_datos(sh, "USUARIOS")
                # Rescate admin/admin si la tabla está vacía
                if (df_u.empty and u == "admin" and p == "admin") or \
                   (not df_u.empty and u in df_u['USUARIO'].astype(str).values and p in df_u['CONTRASEÑA'].astype(str).values):
                    st.session_state.autenticado, st.session_state.usuario, st.session_state.rol = True, u, "ADMIN"
                    st.rerun()
                st.error("Credenciales incorrectas")
    st.stop()

# --- BARRA LATERAL ---
with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=120)
    st.write(f"👤 **{st.session_state.usuario}**")
    menu = st.radio("Módulos", ["📊 Dashboard", "💰 Gastos", "🏗️ Obras", "👥 Empleados", "⚙️ Sistema"])
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("Control Presupuestario")
    df_g, _ = asegurar_y_obtener_datos(sh, "Gastos_Detalle")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    
    if not df_o.empty:
        # LIMPIEZA CRÍTICA PARA EVITAR EL ERROR DE PLOTLY
        df_g['IMPORTE'] = df_g['IMPORTE'].apply(to_num)
        df_o['PRESUPUESTO'] = df_o['PRESUPUESTO'].apply(to_num)
        
        # Agrupar gastos por obra
        g_obra = df_g.groupby('OBRA')['IMPORTE'].sum().reset_index().rename(columns={'OBRA':'NOMBRE', 'IMPORTE':'GASTO_REAL'})
        
        # Unir y asegurar que ambas columnas sean float64
        df_plot = pd.merge(df_o[['NOMBRE', 'PRESUPUESTO']], g_obra, on='NOMBRE', how='left').fillna(0)
        df_plot['PRESUPUESTO'] = df_plot['PRESUPUESTO'].astype(float)
        df_plot['GASTO_REAL'] = df_plot['GASTO_REAL'].astype(float)
        
        c1, c2 = st.columns(2)
        c1.metric("Total Gastado", f"{df_plot['GASTO_REAL'].sum():,.2f} €")
        c2.metric("Total Presupuestado", f"{df_plot['PRESUPUESTO'].sum():,.2f} €")
        
        fig = px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_REAL'], 
                     barmode='group', title="Presupuesto vs Gasto Real")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Añade obras para ver las gráficas.")

# --- CARGA DE GASTOS (CORREGIDO DESPLEGABLES) ---
elif menu == "💰 Gastos":
    st.header("Carga de Gastos")
    df_g, ws_g = asegurar_y_obtener_datos(sh, "Gastos_Detalle")
    df_o, _ = asegurar_y_obtener_datos(sh, "Obras")
    df_e, _ = asegurar_y_obtener_datos(sh, "Empleados")
    
    # Obtener opciones de las otras hojas
    opciones_obras = df_o['NOMBRE'].unique().tolist() if not df_o.empty else []
    opciones_empleados = df_e['NOMBRE'].unique().tolist() if not df_e.empty else []

    st.write("Selecciona la obra y el trabajador en las columnas correspondientes:")
    
    df_ed = st.data_editor(df_g, num_rows="dynamic", use_container_width=True,
        column_config={
            "OBRA": st.column_config.SelectboxColumn("Obra", options=opciones_obras, required=True),
            "TRABAJADOR": st.column_config.SelectboxColumn("Trabajador", options=opciones_empleados, required=True),
            "IMPORTE": st.column_config.NumberColumn("Importe (€)", format="%.2f")
        })
    
    if st.button("💾 Guardar y Sincronizar"):
        ws_g.clear()
        ws_g.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
        st.success("Gastos actualizados.")
        st.rerun()

# --- OTROS MÓDULOS ---
elif menu in ["🏗️ Obras", "👥 Empleados", "⚙️ Sistema"]:
    mapas = {"🏗️ Obras": "Obras", "👥 Empleados": "Empleados", "⚙️ Sistema": "USUARIOS"}
    nombre_h = mapas[menu]
    df, ws = asegurar_y_obtener_datos(sh, nombre_h)
    
    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button(f"Guardar {nombre_h}"):
        ws.clear()
        ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
        st.success("Guardado correctamente.")
        st.rerun()
