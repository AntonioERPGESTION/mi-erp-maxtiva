import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import time
from datetime import datetime
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="ERP GRUPO MAXTIVA", layout="wide", page_icon="⚡")

SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"
LOGOS = ["logo_maxtiva.png", "logo_ceta.png", "logo_ipalux.png"]

def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        pk = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def limpiar_df(df):
    """Limpia nombres de columnas: Mayúsculas, sin espacios y quita filas vacías"""
    df.columns = [str(c).upper().strip() for c in df.columns]
    return df.dropna(how='all')

# --- SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- LOGIN ---
def login():
    cols = st.columns([1, 2, 1])
    with cols[1]:
        l_cols = st.columns(3)
        for i, logo in enumerate(LOGOS):
            if os.path.exists(logo): l_cols[i].image(logo, use_container_width=True)
        st.title("⚡ Acceso ERP Grupo Maxtiva")
        with st.form("Login"):
            u = st.text_input("Usuario").strip()
            p = st.text_input("Contraseña", type="password").strip()
            if st.form_submit_button("Entrar"):
                sh = conectar()
                if sh:
                    ws = sh.worksheet("USUARIOS")
                    df = limpiar_df(pd.DataFrame(ws.get_all_records()))
                    col_p = 'CONTRASEÑA' if 'CONTRASEÑA' in df.columns else 'PASSWORD'
                    match = df[(df['USUARIO'].astype(str) == u) & (df[col_p].astype(str) == p)]
                    if not match.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario = u
                        st.session_state.rol = str(match.iloc[0].get('ROL', 'EMPLEADO')).upper()
                        st.rerun()
                    else: st.error("Credenciales incorrectas")

if not st.session_state.autenticado:
    login()
else:
    # --- INTERFAZ ---
    with st.sidebar:
        for logo in LOGOS:
            if os.path.exists(logo): st.image(logo, width=120)
        st.write(f"👤 **{st.session_state.usuario}** | `{st.session_state.rol}`")
        
        # TODOS LOS MÓDULOS SEGÚN TUS PESTAÑAS
        menu = st.radio("Módulos", [
            "📊 Dashboard", 
            "🏗️ Obras", 
            "💰 Gastos Detalle", 
            "👥 Empleados", 
            "📦 Inventario", 
            "📅 Agenda/Planificación", 
            "📝 Pedidos e Incidencias",
            "📋 Informes",
            "⚙️ Usuarios"
        ])
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()

    sh = conectar()
    
    # --- 1. DASHBOARD (CÁLCULOS CRUZADOS) ---
    if menu == "📊 Dashboard":
        st.header("Dashboard de Control de Obras")
        try:
            df_gastos = limpiar_df(pd.DataFrame(sh.worksheet("Gastos_Detalle").get_all_records()))
            df_obras = limpiar_df(pd.DataFrame(sh.worksheet("Obras").get_all_records()))
            
            # Cálculo de Gasto Real por Obra desde la pestaña Gastos_Detalle
            gastos_por_obra = df_gastos.groupby('OBRA')['IMPORTE'].sum().reset_index()
            gastos_por_obra.columns = ['NOMBRE', 'GASTO_CALCULADO']
            
            # Unir con la tabla de Obras para comparar Presupuesto vs Realidad
            resumen_obras = pd.merge(df_obras, gastos_por_obra, on='NOMBRE', how='left').fillna(0)

            c1, c2, c3 = st.columns(3)
            c1.metric("Gasto Total Grupo", f"{df_gastos['IMPORTE'].sum():,.2f} €")
            c2.metric("Obra con más Gasto", gastos_por_obra.loc[gastos_por_obra['GASTO_CALCULADO'].idxmax(), 'NOMBRE'] if not gastos_por_obra.empty else "N/A")
            c3.metric("Total Obras", len(df_obras))

            fig = px.bar(resumen_obras, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_CALCULADO'], 
                         barmode='group', title="Presupuesto vs Gasto Acumulado (Real)")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.info("Asegúrate de que las columnas 'OBRA' e 'IMPORTE' existan en Gastos_Detalle.")

    # --- 2. GESTIÓN DE DATOS (TODOS LOS MÓDULOS) ---
    elif menu in ["🏗️ Obras", "💰 Gastos Detalle", "👥 Empleados", "📦 Inventario", "📅 Agenda/Planificación", "📝 Pedidos e Incidencias"]:
        mapa = {
            "🏗️ Obras": "Obras", "💰 Gastos Detalle": "Gastos_Detalle", 
            "👥 Empleados": "Empleados", "📦 Inventario": "Inventario",
            "📅 Agenda/Planificación": "Planificacion", "📝 Pedidos e Incidencias": "Incidencias"
        }
        tabla = mapa[menu]
        ws = sh.worksheet(tabla)
        raw = ws.get_all_values()
        df = pd.DataFrame(raw[1:], columns=raw[0]) if len(raw) > 1 else pd.DataFrame()
        
        st.subheader(f"Módulo: {tabla}")
        if st.session_state.rol == "ADMIN":
            df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"editor_{tabla}")
            if st.button("💾 Guardar"):
                ws.clear()
                ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
                st.success("Guardado")
        else: st.dataframe(df, use_container_width=True)

    # --- 3. INFORMES (FILTRADO TRABAJADOR / OBRA) ---
    elif menu == "📋 Informes":
        st.header("Generador de Informes Inteligente")
        df_gastos = limpiar_df(pd.DataFrame(sh.worksheet("Gastos_Detalle").get_all_records()))
        
        tab1, tab2 = st.tabs(["Por Trabajador", "Por Obra"])
        
        with tab1:
            worker = st.selectbox("Seleccionar Trabajador", df_gastos['TRABAJADOR'].unique() if 'TRABAJADOR' in df_gastos.columns else [])
            if worker:
                inf = df_gastos[df_gastos['TRABAJADOR'] == worker]
                st.metric(f"Total Gasto/Horas de {worker}", f"{inf['IMPORTE'].sum():,.2f} €")
                st.dataframe(inf, use_container_width=True)
        
        with tab2:
            obra = st.selectbox("Seleccionar Obra", df_gastos['OBRA'].unique() if 'OBRA' in df_gastos.columns else [])
            if obra:
                inf_o = df_gastos[df_gastos['OBRA'] == obra]
                st.write(f"Resumen de gastos imputados a: **{obra}**")
                # Gráfico de quién ha gastado más en esta obra
                fig_o = px.pie(inf_o, values='IMPORTE', names='TRABAJADOR', title="Gastos por Trabajador en esta Obra")
                st.plotly_chart(fig_o)
                st.dataframe(inf_o, use_container_width=True)

    # --- 4. USUARIOS ---
    elif menu == "⚙️ Usuarios":
        if st.session_state.rol == "ADMIN":
            ws = sh.worksheet("USUARIOS")
            raw = ws.get_all_values()
            df_ed = st.data_editor(pd.DataFrame(raw[1:], columns=raw[0]), num_rows="dynamic", use_container_width=True)
            if st.button("💾 Actualizar Usuarios"):
                ws.clear()
                ws.update('A1', [df_ed.columns.tolist()] + df_ed.values.tolist())
                st.success("Usuarios actualizados")
