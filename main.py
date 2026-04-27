import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
import pdfplumber
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="MAXTIVA ERP - SISTEMA INTEGRAL", layout="wide", page_icon="🏢")

# --- CONEXIÓN SEGURA ---
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

def obtener_pestaña(nombre_posible):
    gc = conectar_google()
    if gc:
        try:
            sh = gc.open("ERP MAXTIVA")
            # Intentamos buscar la hoja. Si falla "Gastos", intentará con "gastos"
            for sheet in sh.worksheets():
                if sheet.title.lower() == nombre_posible.lower():
                    return sheet
            return None
        except Exception as e:
            return None
    return None

# --- MENÚ LATERAL (RESTAURADO COMPLETO) ---
with st.sidebar:
    st.title("🏢 GRUPO MAXTIVA")
    st.markdown("---")
    menu = st.selectbox("SELECCIONE MÓDULO", [
        "📊 Dashboard General",
        "🏗️ Gestión de Obras",
        "👥 Gestión de Empleados",
        "⏱️ Imputación de Horas",
        "💸 Adjudicación de Gastos",
        "📦 Pedidos y Facturas PDF"
    ])
    st.markdown("---")
    if st.button("🔄 Sincronizar con Drive"):
        st.cache_data.clear()
        st.rerun()

# --- LÓGICA DE MÓDULOS ---

# 1. DASHBOARD
if menu == "📊 Dashboard General":
    st.title("📊 Resumen de Operaciones")
    # Intentamos leer Obras y Gastos para métricas
    ws_o = obtener_pestaña("Obras")
    ws_g = obtener_pestaña("Gastos")
    
    c1, c2, c3 = st.columns(3)
    if ws_o:
        df_o = pd.DataFrame(ws_o.get_all_records())
        ingresos = pd.to_numeric(df_o['PRESUPUESTO'], errors='coerce').sum() if 'PRESUPUESTO' in df_o.columns else 0
        c1.metric("Ingresos Totales", f"{ingresos:,.2f} €")
    
    if ws_g:
        df_g = pd.DataFrame(ws_g.get_all_records())
        # Buscamos columna 'IMPORTE' o 'Importe'
        col_imp = [c for c in df_g.columns if c.lower() == 'importe']
        gastos = pd.to_numeric(df_g[col_imp[0]], errors='coerce').sum() if col_imp else 0
        c2.metric("Gastos Totales", f"{gastos:,.2f} €")
        if ws_o and ws_g:
            c3.metric("Margen Neto", f"{ingresos - gastos:,.2f} €")

# 2. MÓDULOS EDITABLES (Obras, Empleados, Horas, Gastos)
elif menu in ["🏗️ Gestión de Obras", "👥 Gestión de Empleados", "⏱️ Imputación de Horas", "💸 Adjudicación de Gastos"]:
    # Extraer el nombre de la hoja según el menú
    mapeo = {
        "🏗️ Gestión de Obras": "Obras",
        "👥 Gestión de Empleados": "Empleados",
        "⏱️ Imputación de Horas": "Horas",
        "💸 Adjudicación de Gastos": "Gastos"
    }
    target = mapeo[menu]
    st.title(f"📝 {menu}")
    
    ws = obtener_pestaña(target)
    if ws:
        df_actual = pd.DataFrame(ws.get_all_records())
        
        st.write(f"Editando hoja: **{ws.title}**")
        st.info("💡 Doble clic para editar celdas. Pulsa el botón inferior para guardar.")
        
        # EDITOR DE DATOS
        df_editado = st.data_editor(
            df_actual, 
            use_container_width=True, 
            num_rows="dynamic", 
            key=f"editor_{target}"
        )
        
        if st.button(f"💾 Guardar Cambios en {target}", type="primary"):
            try:
                ws.clear()
                # Escribir encabezados + datos
                ws.update([df_editado.columns.values.tolist()] + df_editado.astype(str).values.tolist())
                st.success(f"✅ ¡Hoja {target} actualizada en Google Drive!")
                st.balloons()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
    else:
        st.error(f"❌ No se encontró la pestaña '{target}' en el Excel 'ERP MAXTIVA'.")
        st.info(f"Crea una pestaña llamada exactamente '{target}' en tu Google Sheets para activarla.")

# 3. PEDIDOS PDF
elif menu == "📦 Pedidos y Facturas PDF":
    st.title("📦 Extractor de Pedidos")
    archivo = st.file_uploader("Subir PDF", type="pdf")
    if archivo:
        with pdfplumber.open(archivo) as pdf:
            texto = "\n".join([p.extract_text() for p in pdf.pages])
        
        importes = re.findall(r"(\d+[\.,]\d{2})", texto)
        if importes:
            st.success(f"💰 Importe detectado: {importes[-1]} €")
        
        st.subheader("Texto Extraído")
        st.text_area("Contenido:", texto, height=400)
