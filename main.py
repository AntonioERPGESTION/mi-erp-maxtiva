import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="ERP MAXTIVA", layout="wide", page_icon="⚡")

# --- VARIABLES DE CONEXIÓN ---
# Sustituye esta URL por la de tu Google Sheet real
URL = "https://docs.google.com/spreadsheets/d/TU_ID_DE_HOJA_AQUI/edit"

def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # Extraemos los datos de Secrets (Streamlit Cloud)
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Limpieza de la clave privada (Arregla errores de formato y padding)
        pk = creds_dict["private_key"]
        if "\\n" in pk:
            pk = pk.replace("\\n", "\n")
        
        if "-----BEGIN PRIVATE KEY-----" in pk:
            cuerpo = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
            cuerpo = "".join(cuerpo.split())
            pk_final = f"-----BEGIN PRIVATE KEY-----\n{cuerpo}\n-----END PRIVATE KEY-----\n"
            creds_dict["private_key"] = pk_final

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
       # El ID es lo que hay entre /d/ y /edit en tu URL
ID_HOJA = https://docs.google.com/spreadsheets/d/1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM/edit?gid=2078741773#gid=2078741773 
return gspread.authorize(creds).open(ID_HOJA)

# --- LÓGICA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def login():
    st.title("⚡ ERP MAXTIVA")
    with st.form("Login"):
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        boton = st.form_submit_button("Entrar")
        
        if boton:
            gc = conectar()
            if gc:
                try:
                    # Buscamos en la pestaña 'Usuarios'
                    ws_user = gc.worksheet("Usuarios")
                    usuarios_df = pd.DataFrame(ws_user.get_all_records())
                    
                    user_data = usuarios_df[(usuarios_df['usuario'] == usuario) & (usuarios_df['clave'].astype(str) == clave)]
                    
                    if not user_data.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario = usuario
                        st.session_state.rol = user_data.iloc[0]['rol']
                        st.success("¡Bienvenido!")
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos")
                except Exception as e:
                    st.error(f"Error al leer usuarios: {e}")

# --- PANEL PRINCIPAL ---
if not st.session_state.autenticado:
    login()
else:
    st.sidebar.title(f"Hola, {st.session_state.usuario}")
    rol = st.session_state.rol
    menu = st.sidebar.radio("Menú", ["Empresas", "Gastos", "Inventario"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    # CONEXIÓN A LOS DATOS
    gc = conectar()
    if gc:
        try:
            # IMPORTANTE: Asegúrate de que los nombres coincidan con tus pestañas de Google Sheets
            nombre_pestaña = "Obras" if menu == "Empresas" else menu
            ws = gc.worksheet(nombre_pestaña)
            datos = ws.get_all_records()
            df = pd.DataFrame(datos)

            st.header(f"Gestión de {menu}")

            if rol == "Admin":
                # Editor interactivo para el Administrador
                st.info("Modifica los datos directamente en la tabla y pulsa Guardar.")
                df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"editor_{menu}")
                
                if st.button("💾 GUARDAR CAMBIOS"):
                    with st.spinner("Guardando..."):
                        # Reemplazar todo el contenido de la hoja
                        ws.clear()
                        # Preparar datos incluyendo encabezados
                        lista_final = [df_editado.columns.values.tolist()] + df_editado.values.tolist()
                        ws.update('A1', lista_final)
                        st.success("¡Datos actualizados en la nube!")
                        time.sleep(1)
                        st.rerun()
            else:
                # Vista de solo lectura para Empleados
                st.dataframe(df, use_container_width=True)
                st.warning("No tienes permisos para editar esta sección.")

        except Exception as e:
            st.error(f"Error al cargar la pestaña {menu}: {e}")
            st.info("Verifica que el nombre de la pestaña en Google Sheets sea exactamente igual al del menú.")
