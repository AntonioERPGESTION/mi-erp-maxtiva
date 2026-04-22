import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="ERP MAXTIVA", layout="wide", page_icon="⚡")

# ID de tu Google Sheet (verificado por tu enlace)
SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"

def conectar():
    """Conexión con limpieza de llave para Streamlit Cloud"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        pk = creds_dict["private_key"]
        
        if "\\n" in pk: pk = pk.replace("\\n", "\n")
        if "-----BEGIN PRIVATE KEY-----" in pk:
            cuerpo = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
            cuerpo = "".join(cuerpo.split())
            pk_final = "-----BEGIN PRIVATE KEY-----\n"
            for i in range(0, len(cuerpo), 64):
                pk_final += cuerpo[i:i+64] + "\n"
            pk_final += "-----END PRIVATE KEY-----\n"
            creds_dict["private_key"] = pk_final

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- LÓGICA DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- PANTALLA DE LOGIN ---
def login():
    st.title("⚡ ERP MAXTIVA - Acceso")
    with st.form("Login"):
        u_input = st.text_input("Usuario").strip()
        p_input = st.text_input("Contraseña", type="password").strip()
        
        if st.form_submit_button("Entrar"):
            sh = conectar()
            if sh:
                try:
                    # Buscamos la pestaña USUARIOS (insensible a mayúsculas/espacios)
                    hojas = [h.title for h in sh.worksheets()]
                    h_user_name = next((h for h in hojas if "USUARIO" in h.upper().strip()), None)
                    
                    if not h_user_name:
                        st.error("No se encontró la pestaña 'USUARIOS'.")
                        return

                    ws_user = sh.worksheet(h_user_name)
                    df_user = pd.DataFrame(ws_user.get_all_records())
                    
                    # Normalizamos columnas según tu foto (Usuario, CONTRASEÑA, Rol)
                    df_user.columns = [str(c).upper().strip() for c in df_user.columns]
                    
                    # Verificamos credenciales
                    match = df_user[
                        (df_user['USUARIO'].astype(str).str.strip() == u_input) & 
                        (df_user['CONTRASEÑA'].astype(str).str.strip() == p_input)
                    ]
                    
                    if not match.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario = u_input
                        # Importante: según tu foto es "Admin" o "Empleado"
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
    st.sidebar.title("⚡ ERP MAXTIVA")
    st.sidebar.write(f"Usuario: **{st.session_state.usuario}**")
    
    # Mapeo de navegación con TODAS las pestañas de tus fotos
    menu_map = {
        "Obras": "Obras",
        "Inventario": "Inventario",
        "Reportes": "Reportes",
        "Empleados": "Empleados",
        "Gastos": "Gastos_Detalle",
        "Pedidos": "Pedidos",
        "Planificación": "Planificacion",
        "Incidencias": "Incidencias",
        "Agenda": "Agenda",
        "Gestión Usuarios": "USUARIOS"
    }
    
    seleccion = st.sidebar.radio("Ir a:", list(menu_map.keys()))
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    sh = conectar()
    if sh:
        try:
            hojas_reales = [h.title for h in sh.worksheets()]
            objetivo = menu_map[seleccion].upper()
            
            # Buscador flexible para encontrar la pestaña real
            hoja_actual = next((h for h in hojas_reales if objetivo in h.upper().strip()), None)

            if hoja_actual:
                ws = sh.worksheet(hoja_actual)
                datos_raw = ws.get_all_values()
                
                if len(datos_raw) > 0:
                    df = pd.DataFrame(datos_raw[1:], columns=datos_raw[0])
                else:
                    df = pd.DataFrame()

                st.header(f"Módulo: {seleccion}")

                # Permisos: Solo ADMIN (como tú en la foto) edita
                if "ADMIN" in st.session_state.rol:
                    st.info("💡 Eres Administrador. Puedes editar y guardar cambios.")
                    df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"ed_{seleccion}")
                    
                    if st.button("💾 GUARDAR CAMBIOS"):
                        with st.spinner("Guardando..."):
                            ws.clear()
                            final_data = [df_editado.columns.tolist()] + df_editado.fillna("").values.tolist()
                            ws.update('A1', final_data)
                            st.success("¡Datos guardados!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.warning("Vista de Solo Lectura.")
                    st.dataframe(df, use_container_width=True)
            else:
                st.error(f"Pestaña '{menu_map[seleccion]}' no encontrada en este archivo.")
        
        except Exception as e:
            st.error(f"Error: {e}")
