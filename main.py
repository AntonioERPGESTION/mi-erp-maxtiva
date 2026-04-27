import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
import pdfplumber
import re
import time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MAXTIVA ERP - CONTROL TOTAL", layout="wide", page_icon="🏢")

# Estilos Maxtiva
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #FFD700; }
    .stMetric { background-color: white; border: 2px solid #FFD700; padding: 15px; border-radius: 10px; }
    .stButton>button { width: 100%; background-color: #1e3d59; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNCIONES DE CONEXIÓN ---
def conectar_google():
    try:
        # Usamos la etiqueta 'claves_gcp' que configuramos en Secrets
        encoded = st.secrets["claves_gcp"]["json_base64"]
        info = json.loads(base64.b64decode(encoded).decode("utf-8"))
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")
        return None

def obtener_pestaña(nombre_target):
    gc = conectar_google()
    if gc:
        try:
            sh = gc.open("ERP MAXTIVA")
            # Buscador insensible a mayúsculas
            for sheet in sh.worksheets():
                if sheet.title.lower() == nombre_target.lower():
                    return sheet
            return None
        except:
            return None
    return None

# --- 3. BARRA LATERAL (DEFINICIÓN DEL MENÚ) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4091/4091450.png", width=100)
    st.title("GRUPO MAXTIVA")
    st.markdown("---")
    menu = st.selectbox("MENÚ PRINCIPAL", [
        "📊 Dashboard",
        "🏗️ Gestión de Obras",
        "👥 Empleados",
        "⏱️ Control de Horas",
        "💸 Gastos",
        "📦 Extractor PDF"
    ])
    st.markdown("---")
    if st.button("🔄 Forzar Sincronización"):
        st.cache_data.clear()
        st.rerun()

# --- 4. LÓGICA DE MÓDULOS ---

# Módulo Dashboard
if menu == "📊 Dashboard":
    st.title("📊 Resumen de Negocio")
    ws_o = obtener_pestaña("Obras")
    ws_g = obtener_pestaña("Gastos")
    
    col1, col2, col3 = st.columns(3)
    
    if ws_o:
        df_o = pd.DataFrame(ws_o.get_all_records())
        if not df_o.empty and 'PRESUPUESTO' in df_o.columns:
            total_pre = pd.to_numeric(df_o['PRESUPUESTO'], errors='coerce').sum()
            col1.metric("Cartera Obras", f"{total_pre:,.2f} €")
            
    if ws_g:
        df_g = pd.DataFrame(ws_g.get_all_records())
        if not df_g.empty:
            # Buscamos columna de importe sin importar mayúsculas
            col_imp = [c for c in df_g.columns if c.lower() == 'importe']
            if col_imp:
                total_gas = pd.to_numeric(df_g[col_imp[0]], errors='coerce').sum()
                col2.metric("Gastos Totales", f"{total_gas:,.2f} €")
    
    st.info("Utilice los módulos laterales para editar los datos.")

# Módulos Editables (Obras, Empleados, Horas, Gastos)
elif menu in ["🏗️ Gestión de Obras", "👥 Empleados", "⏱️ Control de Horas", "💸 Gastos"]:
    mapeo = {
        "🏗️ Gestión de Obras": "Obras",
        "👥 Empleados": "Empleados",
        "⏱️ Control de Horas": "Horas",
        "💸 Gastos": "Gastos"
    }
    target = mapeo[menu]
    st.title(f"📝 {menu}")
    
    ws = obtener_pestaña(target)
    
    if ws:
        # Intentar leer datos
        try:
            raw = ws.get_all_records()
            df_actual = pd.DataFrame(raw)
        except:
            df_actual = pd.DataFrame()

        # AUTO-REPARACIÓN DE ENCABEZADOS SI LA HOJA ESTÁ VACÍA
        if df_actual.empty:
            columnas_fijas = {
                "Obras": ["ID", "CLIENTE", "NOMBRE", "PRESUPUESTO", "ESTADO"],
                "Empleados": ["NOMBRE", "DNI", "PUESTO", "TELÉFONO"],
                "Horas": ["FECHA", "EMPLEADO", "OBRA", "HORAS"],
                "Gastos": ["FECHA", "CONCEPTO", "IMPORTE", "OBRA"]
            }
            df_actual = pd.DataFrame(columns=columnas_fijas.get(target, ["Dato 1"]))
            st.warning(f"La hoja '{target}' estaba vacía. Se han restaurado los encabezados.")

        st.write(f"Editando hoja: **{target}**")
        
        # EL EDITOR DE DATOS
        df_editado = st.data_editor(
            df_actual, 
            use_container_width=True, 
            num_rows="dynamic", 
            key=f"editor_{target}"
        )
        
        # BOTÓN DE GUARDADO REFORZADO
        if st.button(f"💾 GUARDAR CAMBIOS EN {target.upper()}", type="primary"):
            try:
                with st.spinner("Guardando en Google Drive..."):
                    # 1. Limpieza total de datos para evitar errores de API
                    df_final = df_editado.fillna("").astype(str)
                    
                    # 2. Preparar matriz (Encabezados + Datos)
                    datos_subir = [df_final.columns.values.tolist()] + df_final.values.tolist()
                    
                    # 3. Actualización atómica
                    ws.clear()
                    ws.update('A1', datos_subir)
                    
                    st.success(f"✅ ¡Hoja {target} actualizada!")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Fallo al guardar: {e}")
    else:
        st.error(f"Error: No existe la pestaña '{target}' en el Excel.")

# Módulo de PDF
elif menu == "📦 Extractor PDF":
    st.title("📦 Extractor de Datos de Pedidos")
    uploaded_file = st.file_uploader("Subir factura o pedido (PDF)", type="pdf")
    if uploaded_file:
        with pdfplumber.open(uploaded_file) as pdf:
            texto = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        
        st.success("Lectura completada.")
        
        # Buscar importes con decimales
        importes = re.findall(r"(\d+[\.,]\d{2})", texto)
        if importes:
            st.metric("Importe Detectado (Sugerido)", f"{importes[-1]} €")
        
        st.text_area("Contenido del PDF:", texto, height=400)
