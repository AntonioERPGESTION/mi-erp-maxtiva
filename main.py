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

# Identificación de logos locales según tus archivos subidos
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

def asegurar_columnas(df, columnas_requeridas):
    """Crea columnas vacías si no existen para evitar que el código falle"""
    for col in columnas_requeridas:
        if col not in df.columns:
            df[col] = 0 if col in ['Importe', 'Presupuesto', 'Gasto_Real'] else ""
    return df

# --- SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- PANTALLA DE LOGIN ---
def login():
    cols = st.columns([1, 2, 1])
    with cols[1]:
        # Mostrar los 3 logos en el login
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
                    df = pd.DataFrame(ws.get_all_records())
                    # Normalizar nombres de columnas a mayúsculas
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    
                    # Verificar si existe Usuario y CONTRASEÑA (con Ñ)
                    col_u = 'USUARIO'
                    col_p = 'CONTRASEÑA' if 'CONTRASEÑA' in df.columns else 'PASSWORD'
                    
                    match = df[(df[col_u].astype(str) == u) & (df[col_p].astype(str) == p)]
                    if not match.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario = u
                        st.session_state.rol = str(match.iloc[0].get('ROL', 'EMPLEADO')).upper()
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos")

if not st.session_state.autenticado:
    login()
else:
    # --- INTERFAZ PRINCIPAL ---
    with st.sidebar:
        # Logos en miniatura en el sidebar
        for logo in LOGOS:
            if os.path.exists(logo): st.image(logo, width=120)
        
        st.write(f"👤 **{st.session_state.usuario}**")
        menu = st.radio("Módulos", ["📊 Dashboard", "📁 Gestión de Datos", "👤 Informes Trabajador", "⚙️ Usuarios"])
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()

    sh = conectar()
    
    # --- MÓDULO DASHBOARD ---
    if menu == "📊 Dashboard":
        st.header("Dashboard de Control")
        try:
            # Vinculación de datos: Obras y Gastos
            df_obras = pd.DataFrame(sh.worksheet("Obras").get_all_records())
            df_gastos = pd.DataFrame(sh.worksheet("Gastos_Detalle").get_all_records())
            
            # Asegurar columnas críticas para que no dé error
            df_obras = asegurar_columnas(df_obras, ['Nombre', 'Presupuesto', 'Gasto_Real'])
            df_gastos = asegurar_columnas(df_gastos, ['Obra', 'Importe', 'Concepto'])

            c1, c2, c3 = st.columns(3)
            c1.metric("Gasto Total", f"{df_gastos['Importe'].sum():,.2f} €")
            c2.metric("Obras en Curso", len(df_obras))
            c3.metric("Registros Gastos", len(df_gastos))

            col_a, col_b = st.columns(2)
            with col_a:
                fig1 = px.bar(df_obras, x='Nombre', y=['Presupuesto', 'Gasto_Real'], barmode='group', title="Presupuesto vs Real")
                st.plotly_chart(fig1, use_container_width=True)
            with col_b:
                fig2 = px.pie(df_gastos, values='Importe', names='Obra', title="Distribución de Gastos")
                st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.info("Configura las pestañas 'Obras' y 'Gastos_Detalle' para activar estadísticas.")

    # --- MÓDULO GESTIÓN DE DATOS ---
    elif menu == "📁 Gestión de Datos":
        tablas = ["Obras", "Inventario", "Reportes", "Empleados", "Gastos_Detalle", "Pedidos", "Planificacion", "Incidencias", "Agenda"]
        sel = st.selectbox("Seleccionar Tabla", tablas)
        
        ws = sh.worksheet(sel)
        raw = ws.get_all_values()
        df = pd.DataFrame(raw[1:], columns=raw[0]) if len(raw) > 1 else pd.DataFrame(columns=raw[0] if raw else [])
        
        if st.session_state.rol == "ADMIN":
            df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Guardar Cambios"):
                ws.clear()
                ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
                st.success("Guardado en Google Sheets")
        else:
            st.dataframe(df, use_container_width=True)

    # --- MÓDULO INFORMES TRABAJADOR ---
    elif menu == "👤 Informes Trabajador":
        st.header("Generador de Informes")
        try:
            df_emp = pd.DataFrame(sh.worksheet("Empleados").get_all_records())
            df_gastos = pd.DataFrame(sh.worksheet("Gastos_Detalle").get_all_records())
            
            # Asegurar vinculación por nombre
            if 'Nombre' in df_emp.columns and 'Trabajador' in df_gastos.columns:
                emp = st.selectbox("Seleccionar Empleado", df_emp['Nombre'].unique())
                info = df_gastos[df_gastos['Trabajador'] == emp]
                
                st.subheader(f"Actividad de {emp}")
                st.metric("Total Gastado/Horas", f"{info['Importe'].sum() if 'Importe' in info.columns else 0} €")
                st.dataframe(info, use_container_width=True)
                
                csv = info.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar Informe CSV", csv, f"Informe_{emp}.csv", "text/csv")
            else:
                st.error("Faltan columnas 'Nombre' en Empleados o 'Trabajador' en Gastos_Detalle.")
        except:
            st.error("Error al vincular las hojas de Empleados y Gastos.")

    # --- MÓDULO USUARIOS ---
    elif menu == "⚙️ Usuarios":
        if st.session_state.rol == "ADMIN":
            ws = sh.worksheet("USUARIOS")
            raw = ws.get_all_values()
            df = pd.DataFrame(raw[1:], columns=raw[0])
            df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Actualizar Usuarios"):
                ws.clear()
                ws.update('A1', [df_ed.columns.tolist()] + df_ed.values.tolist())
                st.success("Usuarios actualizados")
        else:
            st.error("Acceso denegado")
