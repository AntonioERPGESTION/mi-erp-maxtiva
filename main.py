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
        # Extraemos los datos de Secrets (Streamlit Cloud)
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Limpieza profunda de la clave privada para evitar errores de firma/padding
        pk = creds_dict["private_key"]
        if "\\n" in pk:
            pk = pk.replace("\\n", "\n")
        
        if "-----BEGIN PRIVATE KEY-----" in pk:
            # Normalizamos el cuerpo de la llave
            cuerpo = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").strip()
            cuerpo = "".join(cuerpo.split())
            # Reconstruimos con el formato exacto de 64 caracteres por línea
            pk_final = "-----BEGIN PRIVATE KEY-----\n"
            for i in range(0, len(cuerpo), 64):
                pk_final += cuerpo[i:i+64] + "\n"
            pk_final += "-----END PRIVATE KEY-----\n"
            creds_dict["private_key"] = pk_final

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds).open_by_url(URL)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- LÓGICA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def login():
    st.title("⚡ ERP MAXTIVA - Acceso")
    with st.form("Login"):
        usuario_input = st.text_input("Usuario")
        clave_input = st.text_input("Contraseña", type="password")
        boton = st.form_submit_button("Entrar")
        
        if boton:
            gc = conectar()
            if gc:
                try:
                    # Cargamos la pestaña USUARIOS
                    ws_user = gc.worksheet("USUARIOS")
                    usuarios_df = pd.DataFrame(ws_user.get_all_records())
                    
                    # Verificamos credenciales (ajustado a tus nombres de columna en el Sheet)
                    # Nota: He usado .astype(str) por si las claves son números en el Excel
                    user_match = usuarios_df[
                        (usuarios_df['USUARIO'].astype(str) == usuario_input) & 
                        (usuarios_df['CONTRASEÑA'].astype(str) == clave_input)
                    ]
                    
                    if not user_match.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario = usuario_input
                        st.session_state.rol = user_match.iloc[0]['ROL']
                        st.success("¡Acceso concedido!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos")
                except Exception as e:
                    st.error(f"Error al validar usuarios: {e}. Revisa que la pestaña se llame 'USUARIOS'.")

# --- PANEL DE CONTROL ---
if not st.session_state.autenticado:
    login()
else:
    # Sidebar personalizada
    st.sidebar.title("⚡ ERP MAXTIVA")
    st.sidebar.write(f"Usuario: **{st.session_state.usuario}**")
    st.sidebar.write(f"Rol: `{st.session_state.rol}`")
    
    # Menú de navegación
    opcion = st.sidebar.radio("Navegación", ["Empresas", "Gastos", "Obras", "Inventario"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    # MAPEO DE PESTAÑAS (Aquí corregimos los nombres según tu Excel)
    mapa_pestanas = {
        "Empresas": "CLIENTES",
        "Gastos": "GASTOS",
        "Obras": "OBRAS",
        "Inventario": "INVENTARIO"
    }
    
    nombre_hoja = mapa_pestanas[opcion]
    
    gc = conectar()
    if gc:
        try:
            ws = gc.worksheet(nombre_hoja)
            datos = ws.get_all_records()
            df = pd.DataFrame(datos)

            st.header(f"Gestión de {opcion}")

            if st.session_state.rol == "Admin":
                st.info("💡 Modo Administrador: Puedes editar las celdas y añadir filas al final.")
                # Editor de datos
                df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"ed_{nombre_hoja}")
                
                if st.button(f"💾 Guardar Cambios en {nombre_hoja}"):
                    with st.spinner("Sincronizando con Google Sheets..."):
                        ws.clear()
                        # Escribir encabezados + datos
                        datos_a_subir = [df_editado.columns.tolist()] + df_editado.values.tolist()
                        ws.update('A1', datos_a_subir)
                        st.success("¡Cambios guardados correctamente!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.write("Vista de consulta (Solo lectura)")
                st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"No se pudo cargar la hoja '{nombre_hoja}': {e}")
            st.info("Comprueba que el nombre de la pestaña en el Excel esté en MAYÚSCULAS.")
