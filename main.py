import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="ERP MAXTIVA", layout="wide", page_icon="⚡")

# ID de tu archivo basado en el enlace que enviaste
SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"

def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        pk = creds_dict["private_key"]
        if "\\n" in pk: pk = pk.replace("\\n", "\n")
        
        # Limpieza de llave
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

# --- SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- LOGIN ---
def login():
    st.title("⚡ ERP MAXTIVA")
    with st.form("Acceso"):
        u_in = st.text_input("Usuario").strip()
        p_in = st.text_input("Contraseña", type="password").strip()
        if st.form_submit_button("Entrar"):
            sh = conectar()
            if sh:
                try:
                    # BUSQUEDA FLEXIBLE DE PESTAÑA USUARIOS
                    hojas = [h.title for h in sh.worksheets()]
                    # Busca cualquier hoja que diga "USUARIO" ignorando espacios y mayúsculas
                    h_user = next((h for h in hojas if "USUARIO" in h.upper().strip()), None)
                    
                    if not h_user:
                        st.error(f"No se encontró la pestaña USUARIOS. Hojas disponibles: {hojas}")
                        return

                    ws_user = sh.worksheet(h_user)
                    df_u = pd.DataFrame(ws_user.get_all_records())
                    
                    # Normalizar nombres de columnas de la foto: Usuario, CONTRASEÑA, Rol
                    df_u.columns = [str(c).upper().strip() for c in df_u.columns]
                    
                    # Columnas esperadas tras normalizar: USUARIO, CONTRASEÑA, ROL
                    if 'USUARIO' in df_u.columns and 'CONTRASEÑA' in df_u.columns:
                        match = df_u[
                            (df_u['USUARIO'].astype(str).str.strip() == u_in) & 
                            (df_u['CONTRASEÑA'].astype(str).str.strip() == p_in)
                        ]
                        
                        if not match.empty:
                            st.session_state.autenticado = True
                            st.session_state.usuario = u_in
                            st.session_state.rol = str(match.iloc[0]['ROL']).upper()
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos")
                    else:
                        st.error(f"Columnas no coinciden. Detectadas: {list(df_u.columns)}")
                except Exception as e:
                    st.error(f"Error en login: {e}")

# --- APP PRINCIPAL ---
if not st.session_state.autenticado:
    login()
else:
    st.sidebar.title("ERP MAXTIVA")
    st.sidebar.success(f"Bienvenido: {st.session_state.usuario}")
    
    # Módulos según tus pestañas de la foto
    menu = {
        "Obras": "Obras",
        "Inventario": "Inventario",
        "Reportes": "Reportes",
        "Empleados": "Empleados",
        "Usuarios": "USUARIOS"
    }
    
    opcion = st.sidebar.radio("Menú Principal", list(menu.keys()))
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    sh = conectar()
    if sh:
        try:
            hojas_reales = [h.title for h in sh.worksheets()]
            objetivo = menu[opcion].upper()
            
            # Buscar la hoja real que coincida con la opción
            hoja_a_abrir = next((h for h in hojas_reales if objetivo in h.upper().strip()), None)

            if hoja_a_abrir:
                ws = sh.worksheet(hoja_a_abrir)
                datos = ws.get_all_values()
                if len(datos) > 0:
                    df = pd.DataFrame(datos[1:], columns=datos[0])
                else:
                    df = pd.DataFrame()

                st.header(f"Sección: {opcion}")
                
                # Si es Admin puede editar, si no, solo ver
                if "ADMIN" in st.session_state.rol:
                    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"ed_{opcion}")
                    if st.button("💾 GUARDAR CAMBIOS"):
                        ws.clear()
                        ws.update('A1', [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist())
                        st.success("¡Datos actualizados!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.dataframe(df, use_container_width=True)
            else:
                st.error(f"Pestaña '{objetivo}' no encontrada en el Excel.")
        except Exception as e:
            st.error(f"Error al cargar datos: {e}")
