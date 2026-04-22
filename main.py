import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="ERP MAXTIVA", layout="wide", page_icon="⚡")

# URL de tu archivo (ID extraído para mayor estabilidad)
SPREADSHEET_ID = "1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM"

def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        pk = creds_dict["private_key"]
        if "\\n" in pk: pk = pk.replace("\\n", "\n")
        
        # Formateo estricto de la llave privada
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
        st.error(f"Error de conexión con Google: {e}")
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
                    # Buscamos la hoja de usuarios (flexible)
                    hojas = [h.title for h in sh.worksheets()]
                    h_user = next((h for h in hojas if "USER" in h.upper()), None)
                    if not h_user:
                        st.error("No existe pestaña de USUARIOS")
                        return

                    df_u = pd.DataFrame(sh.worksheet(h_user).get_all_records())
                    df_u.columns = [str(c).upper().strip() for c in df_u.columns]
                    
                    # Buscamos columnas de credenciales
                    c_u = 'USUARIO' if 'USUARIO' in df_u.columns else df_u.columns[0]
                    c_p = 'PASSWORD' if 'PASSWORD' in df_u.columns else ('CONTRASEÑA' if 'CONTRASEÑA' in df_u.columns else df_u.columns[1])
                    
                    match = df_u[(df_u[c_u].astype(str).str.strip() == u_in) & (df_u[c_p].astype(str).str.strip() == p_in)]
                    
                    if not match.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario = u_in
                        st.session_state.rol = str(match.iloc[0].get('ROL', 'Empleado')).upper()
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas")
                except Exception as e:
                    st.error(f"Fallo en login: {e}")

# --- APP PRINCIPAL ---
if not st.session_state.autenticado:
    login()
else:
    st.sidebar.title("ERP MAXTIVA")
    st.sidebar.info(f"Usuario: {st.session_state.usuario}\nRol: {st.session_state.rol}")
    
    # Módulos funcionando
    modulos = {
        "Empresas": "CLIENTES",
        "Gastos": "GASTOS",
        "Obras": "OBRAS",
        "Inventario": "INVENTARIO"
    }
    seleccion = st.sidebar.radio("Menú", list(modulos.keys()))
    
    if st.sidebar.button("Salir"):
        st.session_state.autenticado = False
        st.rerun()

    sh = conectar()
    if sh:
        try:
            # Lógica de búsqueda "tolerante" para las pestañas
            hojas_reales = [h.title for h in sh.worksheets()]
            objetivo = modulos[seleccion]
            
            # Intenta coincidencia exacta, si no, busca por contenido
            hoja_a_abrir = next((h for h in hojas_reales if h.upper().strip() == objetivo), None)
            if not hoja_a_abrir:
                hoja_a_abrir = next((h for h in hojas_reales if objetivo in h.upper()), None)

            if hoja_a_abrir:
                ws = sh.worksheet(hoja_a_abrir)
                raw_data = ws.get_all_values()
                
                if len(raw_data) > 0:
                    df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
                else:
                    df = pd.DataFrame()

                st.header(f"Módulo: {seleccion}")
                
                if st.session_state.rol == "ADMIN":
                    st.success("Modo Edición Activado")
                    df_ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"ed_{seleccion}")
                    if st.button("Guardar Cambios"):
                        with st.spinner("Sincronizando..."):
                            ws.clear()
                            final_data = [df_ed.columns.tolist()] + df_ed.fillna("").values.tolist()
                            ws.update('A1', final_data)
                            st.toast("¡Guardado!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.info("Vista de Consulta")
                    st.dataframe(df, use_container_width=True)
            else:
                st.error(f"Error: La pestaña '{objetivo}' no existe en el Excel. Pestañas encontradas: {hojas_reales}")
        except Exception as e:
            st.error(f"Error al cargar módulo: {e}")
