import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MA XTIVA ERP - PANEL TOTAL", layout="wide", page_icon="🏗️")

# --- CONEXIÓN PROFESIONAL (LECTURA Y ESCRITURA) ---
def conectar_google():
    try:
        # Usamos la etiqueta personalizada 'claves_gcp'
        encoded = st.secrets["claves_gcp"]["json_base64"]
        info = json.loads(base64.b64decode(encoded).decode("utf-8"))
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_datos(nombre_pestaña):
    gc = conectar_google()
    if gc:
        try:
            # Abre el archivo principal
            sh = gc.open("ERP MAXTIVA")
            return sh.worksheet(nombre_pestaña)
        except Exception as e:
            st.error(f"Pestaña '{nombre_pestaña}' no encontrada: {e}")
    return None

# --- INTERFAZ ---
st.sidebar.title("🏢 MA XTIVA ERP")
menu = st.sidebar.radio("IR A:", ["Obras", "Empleados", "Horas", "Gastos"])

# --- FUNCIÓN CRUD (Añadir, Editar, Borrar) ---
def modulo_interactivo(titulo, pestaña, campos):
    st.title(f"Gestión de {titulo}")
    ws = obtener_datos(pestaña)
    
    if ws:
        # Cargar datos actuales
        df = pd.DataFrame(ws.get_all_records())
        
        tab_ver, tab_add, tab_edit = st.tabs(["📋 Listado / Borrar", "➕ Añadir", "✏️ Modificar"])
        
        with tab_ver:
            if not df.empty:
                st.write("Datos actuales en Google Sheets:")
                # Selección para borrar
                fila_idx = st.selectbox("Selecciona fila para eliminar", df.index, format_func=lambda x: f"Fila {x} - {df.iloc[x].iloc[0]}")
                if st.button(f"🗑️ Eliminar fila {fila_idx}", type="primary"):
                    ws.delete_rows(int(fila_idx) + 2)
                    st.success("Registro eliminado correctamente.")
                    st.rerun()
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No hay registros en esta pestaña.")

        with tab_add:
            with st.form("nuevo_registro"):
                st.subheader(f"Nuevo {titulo}")
                datos_nuevos = []
                for campo in campos:
                    datos_nuevos.append(st.text_input(campo))
                
                if st.form_submit_button("💾 Guardar en Drive"):
                    ws.append_row(datos_nuevos)
                    st.success("Guardado con éxito.")
                    st.rerun()

        with tab_edit:
            if not df.empty:
                st.subheader("Editar registro")
                idx_e = st.selectbox("Fila a editar", df.index, key="edit_sel")
                nuevos_valores = []
                for i, campo in enumerate(campos):
                    valor_actual = str(df.iloc[idx_e][campo])
                    nuevos_valores.append(st.text_input(f"Editar {campo}", value=valor_actual, key=f"e_{i}"))
                
                if st.button("🆙 Actualizar Fila"):
                    ws.update(f"A{idx_e+2}", [nuevos_valores])
                    st.success("Fila actualizada.")
                    st.rerun()

# --- CARGA DE MÓDULOS ---
if menu == "Obras":
    modulo_interactivo("Obras", "Obras", ["ID", "CLIENTE", "NOMBRE", "PRESUPUESTO", "ESTADO"])

elif menu == "Empleados":
    modulo_interactivo("Empleados", "Empleados", ["NOMBRE", "DNI", "PUESTO", "TELÉFONO"])

elif menu == "Horas":
    modulo_interactivo("Horas", "Horas", ["FECHA", "EMPLEADO", "OBRA", "HORAS"])

elif menu == "Gastos":
    modulo_interactivo("Gastos", "Gastos", ["FECHA", "CONCEPTO", "IMPORTE", "OBRA"])

if st.sidebar.button("🔄 Sincronizar Ahora"):
    st.rerun()
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
import time

def conectar_google():
    try:
        # Usamos tu clave en Base64 que ya tenemos configurada
        encoded = st.secrets["claves_gcp"]["json_base64"]
        info = json.loads(base64.b64decode(encoded).decode("utf-8"))
        
        # IMPORTANTE: Necesitamos ambos scopes para que funcione el CRUD
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error de configuración de claves: {e}")
        return None

def obtener_datos(nombre_pestaña):
    gc = conectar_google()
    if gc:
        try:
            # Abrimos el archivo por su nombre exacto
            sh = gc.open("ERP MAXTIVA")
            return sh.worksheet(nombre_pestaña)
        except Exception as e:
            if "403" in str(e):
                st.warning("⚠️ Google está activando los permisos. Espera 1 minuto y pulsa Sincronizar.")
            else:
                st.error(f"Error al acceder a '{nombre_pestaña}': {e}")
    return None
