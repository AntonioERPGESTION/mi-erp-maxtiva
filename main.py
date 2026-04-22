import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="ERP GRUPO MAXTIVA", layout="wide", page_icon="⚡")

SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"
LOGOS = ["logo_maxtiva.png", "logo_ceta.png", "logo_ipalux.png"]

# --- 1. CONEXIÓN Y LECTURA ROBUSTA ---
@st.cache_resource
def conectar_bbdd():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds).open_by_key(SPREADSHEET_ID)
    except Exception as e:
        st.error(f"Error crítico de conexión con Google: {e}")
        return None

def obtener_datos(sh, nombre_hoja):
    """Obtiene datos y asegura que las cabeceras estén limpias y en mayúsculas."""
    try:
        ws = sh.worksheet(nombre_hoja)
        data = ws.get_all_values()
        if not data or len(data) == 1: # Si está vacía o solo tiene cabeceras
            cabeceras = [str(c).upper().strip() for c in (data[0] if data else [])]
            return pd.DataFrame(columns=cabeceras), ws
        
        df = pd.DataFrame(data[1:], columns=data[0])
        df.columns = [str(c).upper().strip() for c in df.columns]
        return df, ws
    except Exception as e:
        st.sidebar.error(f"⚠️ No se encontró la hoja: {nombre_hoja}")
        return pd.DataFrame(), None

def limpiar_dinero(val):
    """Convierte cualquier formato de moneda a float válido para operar."""
    if pd.isna(val) or val == "": return 0.0
    val = str(val).replace('€', '').replace(' ', '').strip()
    if ',' in val and '.' in val:
        val = val.replace('.', '').replace(',', '.')
    elif ',' in val:
        val = val.replace(',', '.')
    try:
        return float(val)
    except:
        return 0.0

# --- 2. GESTIÓN DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- 3. PANTALLA DE ACCESO (LOGIN) ---
if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.write("#")
        l_cols = st.columns(3)
        for i, l in enumerate(LOGOS):
            if os.path.exists(l): l_cols[i].image(l, use_container_width=True)
            
        st.title("Acceso ERP Maxtiva")
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                sh = conectar_bbdd()
                if sh:
                    df_u, _ = obtener_datos(sh, "USUARIOS")
                    if not df_u.empty:
                        col_p = 'CONTRASEÑA' if 'CONTRASEÑA' in df_u.columns else 'PASSWORD'
                        match = df_u[(df_u['USUARIO'].astype(str).str.strip() == u.strip()) & 
                                     (df_u[col_p].astype(str).str.strip() == p.strip())]
                        if not match.empty:
                            st.session_state.autenticado = True
                            st.session_state.usuario = u
                            st.session_state.rol = str(match.iloc[0].get('ROL', 'EMPLEADO')).upper().strip()
                            st.rerun()
                        else:
                            st.error("Credenciales incorrectas")
                else:
                    st.error("No se pudo conectar a la base de datos.")
    st.stop()

# --- 4. APP PRINCIPAL ---
sh = conectar_bbdd()

with st.sidebar:
    for l in LOGOS:
        if os.path.exists(l): st.image(l, width=130)
    st.divider()
    st.write(f"👤 **{st.session_state.usuario}**")
    st.write(f"🔑 Rol: `{st.session_state.rol}`")
    
    menu = st.radio("Módulos", [
        "📊 Dashboard", 
        "💰 Carga de Gastos", 
        "🏗️ Obras", 
        "👥 Personal", 
        "📦 Inventario", 
        "📝 Planificación e Incidencias", 
        "⚙️ Sistema"
    ])
    
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- MÓDULO 1: DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("Análisis de Costos y Rendimiento")
    df_g, _ = obtener_datos(sh, "Gastos_Detalle")
    df_o, _ = obtener_datos(sh, "Obras")
    
    # Validar que existan las columnas necesarias
    if not df_g.empty and not df_o.empty and 'IMPORTE' in df_g.columns and 'PRESUPUESTO' in df_o.columns:
        
        # Limpiar datos numéricos con la función robusta
        df_g['IMPORTE_NUM'] = df_g['IMPORTE'].apply(limpiar_dinero)
        df_o['PRESUPUESTO_NUM'] = df_o['PRESUPUESTO'].apply(limpiar_dinero)
        
        # Normalizar nombres para que coincidan al 100%
        df_g['OBRA'] = df_g['OBRA'].astype(str).str.upper().str.strip()
        df_o['NOMBRE'] = df_o['NOMBRE'].astype(str).str.upper().str.strip()
        
        # Agrupar gastos por obra
        gasto_real = df_g.groupby('OBRA')['IMPORTE_NUM'].sum().reset_index()
        gasto_real.rename(columns={'OBRA': 'NOMBRE', 'IMPORTE_NUM': 'GASTO_REAL'}, inplace=True)
        
        # Cruzar tabla Obras con el Gasto Real
        df_plot = pd.merge(df_o[['NOMBRE', 'PRESUPUESTO_NUM']], gasto_real, on='NOMBRE', how='left').fillna(0)
        
        # Mostrar Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Gasto Total Imputado", f"{df_plot['GASTO_REAL'].sum():,.2f} €")
        c2.metric("Nº Obras Activas", len(df_o))
        c3.metric("Presupuesto Total", f"{df_plot['PRESUPUESTO_NUM'].sum():,.2f} €")
        
        # Mostrar Gráfico
        if df_plot['PRESUPUESTO_NUM'].sum() > 0 or df_plot['GASTO_REAL'].sum() > 0:
            fig = px.bar(df_plot, x='NOMBRE', y=['PRESUPUESTO_NUM', 'GASTO_REAL'], 
                         barmode='group', title="Comparativa: Presupuesto vs Realidad",
                         labels={'value': 'Euros (€)', 'variable': 'Concepto', 'NOMBRE': 'Obra'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Hay datos, pero los importes o presupuestos están a 0.")
            
    else:
        st.warning("⚠️ El Dashboard requiere datos en las hojas 'Obras' y 'Gastos_Detalle'. Verifica que las columnas OBRA, IMPORTE y PRESUPUESTO existan.")

# --- MÓDULO 2: CARGA DE GASTOS (CON DESPLEGABLES SEGUROS) ---
elif menu == "💰 Carga de Gastos":
    st.header("Registro de Gastos Imputados")
    df_g, ws_g = obtener_datos(sh, "Gastos_Detalle")
    df_o, _ = obtener_datos(sh, "Obras")
    df_e, _ = obtener_datos(sh, "Empleados")
    
    # Extraer listas seguras para los desplegables (evitar listas vacías que rompen la UI)
    lista_obras = df_o['NOMBRE'].dropna().unique().tolist() if not df_o.empty and 'NOMBRE' in df_o.columns else ["(Añade obras primero)"]
    lista_trabajadores = df_e['NOMBRE'].dropna().unique().tolist() if not df_e.empty and 'NOMBRE' in df_e.columns else ["(Añade empleados primero)"]

    st.info("Asegúrate de seleccionar una Obra y un Trabajador del menú desplegable.")
    
    # Si la hoja está totalmente vacía, forzar columnas base para el editor
    if df_g.empty:
        df_g = pd.DataFrame(columns=["FECHA", "OBRA", "TRABAJADOR", "CONCEPTO", "IMPORTE"])

    # Editor con restricciones
    df_ed = st.data_editor(
        df_g,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "OBRA": st.column_config.SelectboxColumn("Obra Asignada", options=lista_obras, required=True),
            "TRABAJADOR": st.column_config.SelectboxColumn("Trabajador", options=lista_trabajadores, required=True),
            "IMPORTE": st.column_config.NumberColumn("Importe (€)", format="%.2f", required=True),
            "FECHA": st.column_config.DateColumn("Fecha", required=True)
        }
    )
    
    if st.button("💾 Guardar Gastos"):
        ws_g.clear()
        ws_g.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
        st.success("✅ Gastos guardados correctamente. El Dashboard ha sido actualizado.")

# --- MÓDULO 3: GESTIÓN DE TABLAS SIMPLES ---
elif menu in ["🏗️ Obras", "👥 Personal", "📦 Inventario", "📝 Planificación e Incidencias"]:
    mapa = {
        "🏗️ Obras": "Obras", 
        "👥 Personal": "Empleados", 
        "📦 Inventario": "Inventario", 
        "📝 Planificación e Incidencias": "Incidencias"
    }
    nombre_h = mapa[menu]
    df, ws = obtener_datos(sh, nombre_h)
    
    st.subheader(f"Base de Datos: {nombre_h}")
    
    if st.session_state.rol == "ADMIN":
        df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button(f"💾 Guardar Cambios en {nombre_h}"):
            ws.clear()
            ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
            st.success("✅ Base de datos sincronizada.")
    else:
        st.dataframe(df, use_container_width=True)

# --- MÓDULO 4: CONFIGURACIÓN DEL SISTEMA ---
elif menu == "⚙️ Sistema":
    st.header("Herramientas de Administrador")
    if st.session_state.rol == "ADMIN":
        st.write("### 👥 Gestión de Usuarios")
        df_u, ws_u = obtener_datos(sh, "USUARIOS")
        if not df_u.empty:
            df_u_ed = st.data_editor(df_u, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Guardar Usuarios"):
                ws_u.clear()
                ws_u.update('A1', [df_u_ed.columns.tolist()] + df_u_ed.fillna("").values.tolist())
                st.success("Usuarios actualizados correctamente.")
    else:
        st.error("No tienes permisos de Administrador para ver esta sección.")
