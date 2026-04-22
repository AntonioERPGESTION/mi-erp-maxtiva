import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import plotly.express as px
import time
from datetime import datetime
import os # Para verificar que existen las imágenes locales

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="ERP GRUPO MAXTIVA", layout="wide", page_icon="⚡")

# ID de tu Google Sheet (verificado por tus capturas)
SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"

# --- DEFINICIÓN DE LOGOS LOCALES ---
# Asegúrate de que estos archivos estén en la raíz de tu repositorio en GitHub
LOGOS = {
    "MAXTIVA_INDUSTRIAL": "image_2.png",
    "CETA_INSTALACIONES": "image_3.png",
    "IPALUX": "image_4.png"
}

def conectar():
    """Conexión robusta con Google Sheets (Secrets)"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        # Limpieza de clave para Streamlit Cloud
        pk = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")
        return None

# --- FUNCION VISUAL: CUADRÍCULA DE LOGOS ---
def mostrar_logos_grupo(anchura=150):
    """Muestra los logos de las empresas del grupo en una cuadrícula"""
    st.write("### Empresas del Grupo")
    col_logos = st.columns(len(LOGOS))
    for i, (nombre, archivo) in enumerate(LOGOS.items()):
        with col_logos[i]:
            if os.path.exists(archivo):
                st.image(archivo, width=anchura)
            else:
                # Si no encuentra el archivo local, muestra el texto
                st.info(f"Logo {nombre} no encontrado en la raíz.")

# --- LÓGICA DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- PANTALLA DE LOGIN ---
def login():
    # Cabecera de Login con Logos
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        mostrar_logos_grupo(anchura=200)
        st.title("⚡ Acceso al ERP")
    
    with st.form("Login"):
        # Usando columnas exactas de tu foto: Usuario, CONTRASEÑA, Rol
        u_in = st.text_input("Usuario").strip()
        p_in = st.text_input("Contraseña", type="password").strip()
        
        if st.form_submit_button("Entrar"):
            sh = conectar()
            if sh:
                try:
                    # Búsqueda flexible de la pestaña de usuarios
                    hojas = [h.title for h in sh.worksheets()]
                    h_user_real = next((h for h in hojas if "USUARIO" in h.upper().strip()), "USUARIOS")
                    
                    ws_user = sh.worksheet(h_user_name if 'h_user_name' in locals() else h_user_real)
                    df_u = pd.DataFrame(ws_user.get_all_records())
                    
                    # Normalizamos columnas de tu foto (Usuario, CONTRASEÑA, Rol)
                    df_u.columns = [str(c).upper().strip() for c in df_u.columns]
                    
                    match = df_u[
                        (df_u['USUARIO'].astype(str).str.strip() == u_in) & 
                        (df_u['CONTRASEÑA'].astype(str).str.strip() == p_in)
                    ]
                    
                    if not match.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario = u_in
                        # Según tu foto, los roles son "Admin" o "Empleado"
                        st.session_state.rol = str(match.iloc[0]['ROL']).upper().strip()
                        st.success("Acceso correcto")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos")
                except Exception as e:
                    st.error(f"Error en login: {e}")

# --- APP PRINCIPAL ---
if not st.session_state.autenticado:
    login()
else:
    # --- INTERFAZ PRINCIPAL CON LOGOS EN SIDEBAR ---
    with st.sidebar:
        mostrar_logos_grupo(anchura=100) # Logos pequeños en el menú
        st.write("---")
        st.write(f"👤 **{st.session_state.usuario}**")
        st.write(f"Rol: `{st.session_state.rol}`")
        st.write("---")
        
        # Mapeo de TODAS las pestañas que hemos visto en tus fotos
        menu_map = {
            "📊 Dashboard": "Obras", # Usaremos Obras para el Dashboard
            "📁 Gestión de Datos": "Gastos_Detalle", # Sección genérica de edición
            "👤 Informe Trabajador": "Empleados", # Generador de informes
            "⚙️ Usuarios": "USUARIOS"
        }
        
        seleccion = st.radio("Módulos", list(menu_map.keys()))
        
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()

    sh = conectar()
    if not sh:
        st.error("Error de conexión.")
        st.stop()

    # --- MÓDULO 1: DASHBOARD (Resúmenes y Gráficos) ---
    if seleccion == "📊 Dashboard":
        st.header("Dashboard General del Grupo")
        
        # Integración de Logos en el Dashboard
        mostrar_logos_grupo(anchura=180)
        
        try:
            # Ejemplo: Gráfico de Obras (Asegúrate de tener columnas: Nombre, Presupuesto, Gasto_Real)
            df_obras = pd.DataFrame(sh.worksheet("Obras").get_all_records())
            
            if not df_obras.empty and 'PRESUPUESTO' in df_obras.columns.str.upper():
                st.subheader("Estado Financiero de Obras")
                df_obras.columns = [c.upper() for c in df_obras.columns]
                
                fig = px.bar(df_obras, x='NOMBRE', y=['PRESUPUESTO', 'GASTO_REAL'], 
                             title="Presupuesto vs Gasto Real por Obra", barmode='group')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Añade columnas 'Presupuesto' y 'Gasto_Real' a la pestaña 'Obras' para ver gráficos.")
        except Exception as e:
            st.warning(f"Error en Dashboard: {e}")

    # --- MÓDULO 2: GESTIÓN DE DATOS (Editor Flexible) ---
    elif seleccion == "📁 Gestión de Datos":
        st.header("Gestión de Bases de Datos")
        # Lista de todas tus pestañas originales de las fotos
        tablas = ["Obras", "Inventario", "Reportes", "Empleados", "Gastos_Detalle", "Pedidos", "Planificacion", "Incidencias", "Agenda"]
        tabla_sel = st.selectbox("Selecciona la tabla a editar", tablas)
        
        try:
            ws = sh.worksheet(tabla_sel)
            # Obtenemos valores crudos para el editor para evitar fallos por celdas vacías
            datos_raw = ws.get_all_values()
            
            if len(datos_raw) > 0:
                df = pd.DataFrame(datos_raw[1:], columns=datos_raw[0])
            else:
                df = pd.DataFrame()

            st.subheader(f"Edición en vivo: {tabla_sel}")

            # Permisos: Solo ADMIN (como tú en la foto) edita
            if "ADMIN" in st.session_state.rol:
                st.info("💡 Eres Administrador. Puedes editar y guardar cambios.")
                df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"ed_{tabla_sel}")
                
                if st.button("💾 GUARDAR CAMBIOS EN LA NUBE"):
                    with st.spinner("Sincronizando..."):
                        ws.clear()
                        # Preparamos lista: encabezados + datos (rellenando celdas vacías para que no falle)
                        final_data = [df_editado.columns.tolist()] + df_editado.fillna("").values.tolist()
                        ws.update('A1', final_data)
                        st.success("¡Datos guardados!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.warning("Vista de Solo Lectura.")
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error cargando pestaña: {e}")

    # --- MÓDULO 3: INFORMES POR TRABAJADOR ---
    elif seleccion == "👤 Informe Trabajador":
        st.header("Generador de Informes Personales")
        
        try:
            df_emp = pd.DataFrame(sh.worksheet("Empleados").get_all_records())
            trabajador = st.selectbox("Selecciona un trabajador", df_emp["Nombre"].unique())
            
            if trabajador:
                # Ejemplo: Buscamos gastos de ese trabajador (Asegúrate de tener columna 'Trabajador' en Gastos_Detalle)
                df_gastos_all = pd.DataFrame(sh.worksheet("Gastos_Detalle").get_all_records())
                informe = df_gastos_all[df_gastos_all["Trabajador"] == trabajador]
                
                st.subheader(f"Informe Detallado: {trabajador}")
                st.write(f"Total Gastos Registrados: {informe['Importe'].sum():,.2f} €")
                st.dataframe(informe, use_container_width=True)
                
                # Botón de Descarga (CSV formateado)
                csv = informe.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Informe (CSV)",
                    data=csv,
                    file_name=f"Informe_{trabajador}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )
        except Exception as e:
            st.error(f"Error al generar informe: {e}. Revisa las columnas de tus pestañas.")

    # --- MÓDULO 4: GESTIÓN DE USUARIOS ---
    elif seleccion == "⚙️ Usuarios":
        st.header("Administración de Usuarios")
        if "ADMIN" in st.session_state.rol:
            ws = sh.worksheet("USUARIOS")
            datos_raw = ws.get_all_values()
            df = pd.DataFrame(datos_raw[1:], columns=datos_raw[0])
            
            df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="ed_usuarios")
            if st.button("💾 Guardar Usuarios"):
                ws.clear()
                ws.update('A1', [df_editado.columns.tolist()] + df_editado.values.tolist())
                st.success("Lista de usuarios actualizada.")
        else:
            st.error("No tienes permisos para ver esta sección.")
