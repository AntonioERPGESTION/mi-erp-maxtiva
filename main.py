import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
import pdfplumber
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="MA XTIVA ERP - EDICIÓN TOTAL", layout="wide")

# --- CONEXIÓN ---
def conectar_google():
    try:
        encoded = st.secrets["claves_gcp"]["json_base64"]
        info = json.loads(base64.b64decode(encoded).decode("utf-8"))
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")
        return None

def obtener_pestaña(nombre_ws):
    gc = conectar_google()
    if gc:
        try:
            sh = gc.open("ERP MAXTIVA")
            return sh.worksheet(nombre_ws)
        except:
            return None
    return None

# --- MENÚ ---
with st.sidebar:
    st.title("🏢 GRUPO MAXTIVA")
    menu = st.radio("SECCIONES", ["📊 Dashboard", "🏗️ Obras", "👥 Empleados", "⏱️ Horas", "💸 Gastos", "📦 Pedidos PDF"])

# --- LÓGICA DE EDICIÓN (CRUD) ---
if menu in ["🏗️ Obras", "👥 Empleados", "⏱️ Horas", "💸 Gastos"]:
    nombre_pestaña = menu.split()[-1] # Extrae 'Obras', 'Empleados', etc.
    st.title(f"📝 Edición de {nombre_pestaña}")
    
    ws = obtener_pestaña(nombre_pestaña)
    if ws:
        # 1. Leer datos
        df_actual = pd.DataFrame(ws.get_all_records())
        
        st.info("💡 Haz doble clic en una celda para editar. Para borrar, selecciona la fila y pulsa 'Suprimir'.")
        
        # 2. EL EDITOR MÁGICO (Aquí es donde se puede editar)
        # num_rows="dynamic" permite añadir filas nuevas al final de la tabla
        df_editado = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic", key=f"editor_{nombre_pestaña}")
        
        # 3. BOTÓN DE GUARDADO
        if st.button(f"💾 Guardar Cambios en {nombre_pestaña}", type="primary"):
            try:
                # Limpiar la hoja y subir el nuevo dataframe editado
                ws.clear()
                ws.update([df_editado.columns.values.tolist()] + df_editado.astype(str).values.tolist())
                st.success("✅ ¡Datos sincronizados con Google Sheets!")
                st.balloons()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

elif menu == "📊 Dashboard":
    st.title("📊 Resumen de Negocio")
    # Lectura rápida para métricas
    ws_o = obtener_pestaña("Obras")
    ws_g = obtener_pestaña("Gastos")
    if ws_o and ws_g:
        df_o = pd.DataFrame(ws_o.get_all_records())
        df_g = pd.DataFrame(ws_g.get_all_records())
        c1, c2 = st.columns(2)
        c1.metric("Total Obras", len(df_o))
        if 'IMPORTE' in df_g.columns:
            total_g = pd.to_numeric(df_g['IMPORTE'], errors='coerce').sum()
            c2.metric("Gastos Totales", f"{total_g:,.2f} €")

elif menu == "📦 Pedidos PDF":
    st.title("📦 Extractor de Pedidos")
    archivo = st.file_uploader("Subir factura/pedido", type="pdf")
    if archivo:
        with pdfplumber.open(archivo) as pdf:
            texto = "\n".join([p.extract_text() for p in pdf.pages])
        st.success("Análisis completado")
        st.text_area("Texto extraído:", texto, height=300)
