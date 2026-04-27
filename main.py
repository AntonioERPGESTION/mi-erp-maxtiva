import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import pdfplumber
import re
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Extracción Pro", layout="wide", page_icon="🏗️")

# --- ESTILOS CORPORATIVOS AMARILLOS ---
COLOR_AMARILLO = "#FFD700" 
COLOR_TEXTO = "#1e3d59"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8f9fa; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_AMARILLO}; color: {COLOR_TEXTO}; }}
    [data-testid="stSidebar"] * {{ color: {COLOR_TEXTO} !important; }}
    .stMetric {{ background-color: white; border: 2px solid {COLOR_AMARILLO}; padding: 15px; border-radius: 10px; }}
    .stButton>button {{ background-color: {COLOR_AMARILLO}; color: {COLOR_TEXTO}; font-weight: bold; border: 1px solid {COLOR_TEXTO}; }}
    h1, h2, h3 {{ color: {COLOR_TEXTO}; }}
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN DE EXTRACCIÓN MEJORADA ---
def extraer_datos_pro(file):
    with pdfplumber.open(file) as pdf:
        texto = ""
        for pagina in pdf.pages:
            texto += pagina.extract_text() + "\n"
    
    # 1. Búsqueda de Importe (Patrón robusto para: 1.250,50€, 450.00, 1200,30, etc)
    # Buscamos números con decimales que estén cerca de palabras clave o símbolos
    patrones_importe = [
        r"TOTAL.*?(\d+[\.,]\d{2})", # Busca después de la palabra TOTAL
        r"BASE.*?(\d+[\.,]\d{2})",  # Busca base imponible
        r"(\d+[\.,]\d{2})\s*€",      # Busca número seguido de €
        r"€\s*(\d+[\.,]\d{2})"       # Busca € seguido de número
    ]
    
    importe_encontrado = 0.0
    for pat in patrones_importe:
        match = re.search(pat, texto, re.IGNORECASE)
        if match:
            raw_val = match.group(1)
            # Limpieza de formato europeo (1.250,45 -> 1250.45)
            if "." in raw_val and "," in raw_val:
                raw_val = raw_val.replace(".", "").replace(",", ".")
            elif "," in raw_val:
                raw_val = raw_val.replace(",", ".")
            importe_encontrado = float(raw_val)
            break

    # 2. Búsqueda de Partidas (Detectar líneas que parecen artículos)
    lineas = texto.split("\n")
    partidas_candidatas = []
    for l in lineas:
        # Filtramos líneas que tengan sentido (que no sean solo cabeceras de empresa)
        if len(l) > 15 and any(char.isdigit() for char in l):
            partidas_candidatas.append(l.strip())
    
    partidas_texto = "\n".join(partidas_candidatas[:8]) # Cogemos las 8 primeras líneas relevantes
    return importe_encontrado, partidas_texto

# --- INICIALIZACIÓN DE DATOS ---
if "db" not in st.session_state:
    st.session_state.db = {
        "obras": pd.DataFrame([{"ID": 1, "Nombre": "Reforma CETA", "Presupuesto": 12500.0, "Estado": "Activa"}]),
        "empleados": pd.DataFrame([{"ID": 1, "Nombre": "Juan Pérez", "Cargo": "Oficial 1ª"}]),
        "pedidos": pd.DataFrame(columns=["ID", "Material", "Partidas", "Estado", "Coste"]),
        "gastos": pd.DataFrame(columns=["ID", "Obra", "Concepto", "Importe"]),
        "audit_extra": 0.0
    }

# --- MODAL AUDITORÍA ---
@st.dialog("🔍 UniMatch")
def modal_unimatch():
    st.write("Auditoría IA de desviaciones.")
    if st.button("Simular Escaneo"):
        st.session_state.db["audit_extra"] = 3600.0
        st.rerun()

# --- MÓDULO PEDIDOS (MEJORADO) ---
def modulo_pedidos():
    st.title("📦 Pedidos e Importación de Presupuestos")
    t1, t2, t3 = st.tabs(["📋 Histórico", "📂 Subir PDF Proveedor", "⚙️ Gestionar"])
    
    with t1:
        st.dataframe(st.session_state.db["pedidos"], use_container_width=True)
    
    with t2:
        col_up, col_res = st.columns([1, 1])
        with col_up:
            st.subheader("Cargar Documento")
            doc = st.file_uploader("PDF de Pedido / Factura / Presupuesto", type="pdf")
            
        if doc:
            imp, part = extraer_datos_pro(doc)
            with col_res:
                st.subheader("Datos Extraídos")
                with st.form("confirm_pdf"):
                    st.info("Valide los datos antes de guardar:")
                    nom = st.text_input("Nombre del Pedido", value=doc.name)
                    final_imp = st.number_input("Importe Total Detectado (€)", value=imp, step=0.01)
                    final_part = st.text_area("Desglose de Partidas", value=part, height=150)
                    
                    if st.form_submit_button("Confirmar y Guardar"):
                        new = {
                            "ID": int(time.time()), "Material": nom, 
                            "Partidas": final_part, "Estado": "Recibido", "Coste": final_imp
                        }
                        st.session_state.db["pedidos"] = pd.concat([st.session_state.db["pedidos"], pd.DataFrame([new])], ignore_index=True)
                        st.success("Guardado en el ERP")
                        st.rerun()

    with t3:
        if not st.session_state.db["pedidos"].empty:
            sel = st.selectbox("ID Pedido", st.session_state.db["pedidos"]["ID"])
            if st.button("🗑️ Eliminar"):
                st.session_state.db["pedidos"] = st.session_state.db["pedidos"][st.session_state.db["pedidos"]["ID"] != sel]
                st.rerun()

# --- NAVEGACIÓN ---
def main():
    with st.sidebar:
        st.header("GRUPO MAXTIVA")
        st.divider()
        menu = st.radio("MENÚ", ["Dashboard", "Obras", "Personal", "Pedidos", "Gastos"])
        if st.button("🔍 Auditoría UniMatch"): modal_unimatch()

    if menu == "Dashboard":
        st.title("📊 Dashboard")
        base = st.session_state.db["obras"]["Presupuesto"].sum()
        extra = st.session_state.db["audit_extra"]
        gastos = st.session_state.db["gastos"]["Importe"].sum() + st.session_state.db["pedidos"]["Coste"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos", f"{base+extra:,.2f} €")
        c2.metric("Gastos", f"{gastos:,.2f} €")
        c3.metric("Margen", f"{(base+extra)-gastos:,.2f} €")
    elif menu == "Obras": 
        # Lógica simplificada para el ejemplo, reponer CRUD anterior aquí
        st.title("🏗️ Obras")
        st.dataframe(st.session_state.db["obras"])
    elif menu == "Pedidos": modulo_pedidos()
    # ... Resto de módulos ...

if __name__ == "__main__":
    main()
