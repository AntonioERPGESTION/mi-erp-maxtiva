import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="ERP MAXTIVA", layout="wide", page_icon="⚡")

# --- URL DE TU SHEET REAL ---
URL = "https://docs.google.com/spreadsheets/d/1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM/edit"

def conectar():
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
        return client.open_by_url(URL)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- LÓGICA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def login():
    st.title("⚡ ERP MAXTIVA - Acceso")
    with st.form("Login"):
        usuario_input = st.text_input("Usuario").strip()
        clave_input = st.text_input("Contraseña", type="password").strip()
        boton = st.form_submit_button("Entrar")
        
        if boton:
            sh = conectar()
            if sh:
                try:
                    lista_hojas = [h.title for h in sh.worksheets()]
                    hoja_user_real = next((h for h in lista_hojas if h.upper() == "USUARIOS"), "USUARIOS")
                    
                    ws_user = sh.worksheet(hoja_user_real)
                    usuarios_df = pd.DataFrame(ws_user.get_all_records())
                    
                    # Normalizamos columnas a mayúsculas
                    usuarios_df.columns = [str(c).upper().strip() for c in usuarios_df.columns]
                    
                    # CAMBIO CLAVE: Ahora buscamos 'PASSWORD' en lugar de 'CONTRASEÑA'
                    col_user = 'USUARIO'
                    col_pass = 'PASSWORD' if 'PASSWORD' in usuarios_df.columns else 'CONTRASEÑA'
                    col_rol = 'ROL'
                    
                    if col_user in usuarios_df.columns and col_pass in usuarios_df.columns:
                        user_match = usuarios_df[
                            (usuarios_df[col_user].astype(str).str.strip() == usuario_input) & 
                            (usuarios_df[col_pass].astype(str).str.strip() == clave_input)
                        ]
                        
                        if not user_match.empty:
                            st.session_state.autenticado = True
                            st.session_state.usuario = usuario_input
                            st.session_state.rol = user_match.iloc[0][col_rol]
                            st.success("¡Acceso concedido!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos")
                    else:
                        st.error(f"Faltan columnas. Detectadas: {list(usuarios_df.columns)}")
                except Exception as e:
                    st.error(f"Error en el sistema de usuarios: {e}")

# --- PANEL DE CONTROL ---
if not st.session_state.autenticado:
    login()
else:
    st.sidebar.title("⚡ ERP MAXTIVA")
    st.sidebar.write(f"Usuario: **{st.session_state.usuario}**")
    
    opcion = st.sidebar.radio("Navegación", ["Empresas", "Gastos", "Obras", "Inventario"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    sh = conectar()
    if sh:
        try:
            lista_hojas = [h.title for h in sh.worksheets()]
            mapa_nombres = {
                "Empresas": "CLIENTES",
                "Gastos": "GASTOS",
                "Obras": "OBRAS",
                "Inventario": "INVENTARIO"
            }
            objetivo = mapa_nombres[opcion]
            hoja_real = next((h for h in lista_hojas if h.upper().strip() == objetivo), objetivo)
            
            ws = sh.worksheet(hoja_real)
            datos = ws.get_all_records()
            df = pd.DataFrame(datos)

            st.header(f"Gestión de {opcion}")

            if str(st.session_state.rol).upper() == "ADMIN":
                st.info(f"💡 Editando hoja: {hoja_real}")
                df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"ed_{hoja_real}")
                
                if st.button(f"💾 Guardar Cambios"):
                    with st.spinner("Guardando..."):
                        ws.clear()
                        datos_a_subir = [df_editado.columns.tolist()] + df_editado.values.tolist()
                        ws.update('A1', datos_a_subir)
                        st.success("¡Sincronizado!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.dataframe(df, use_container_width=True)
                st.warning("Solo lectura (Empleado)")

        except Exception as e:
            st.error(f"Error al cargar '{opcion}': {e}")
