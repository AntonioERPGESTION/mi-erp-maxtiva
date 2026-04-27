import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import pdfplumber
import re
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - IA Documental", layout="wide", page_icon="🏗️")

# --- ESTILOS CORPORATIVOS AMARILLOS ---
COLOR_AMARILLO = "#FFD700" 
COLOR_TEXTO = "#1e3d59"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8f9fa; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_AMARILLO}; color: {COLOR_TEXTO}; }}
    [data-testid="stSidebar"] * {{ color: {COLOR_TEXTO} !important; }}
    .stMetric {{ background-color: white; border: 2px solid {COLOR_AMARILLO}; padding: 15px; border-radius: 10px; }}
    .stButton>button {{ background-color: {COLOR_AMARILLO}; color: {COLOR_TEXTO}; font-weight: bold; border: 1px solid {COLOR_TEXTO}; width: 100%; }}
    h1, h2, h3 {{ color: {COLOR_TEXTO}; }}
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE EXTRACCIÓN IA (OCR BÁSICO) ---
def extraer_datos_pdf(file):
    with pdfplumber.open(file) as pdf:
        texto_completo = ""
        for pagina in pdf.pages:
            texto_completo += pagina.extract_text() + "\n"
    
    # Lógica simple para encontrar el importe total (busca números cerca de € o "Total")
    importes = re.findall(r"(\d+[\.,]\d{2})\s*€", texto_completo)
    total_detectado = float(importes[-1].replace(",", ".")) if importes else 0.0
    
    # Simulación de detección de partidas (primeras líneas con texto)
    lineas = [l.strip() for l in texto_completo.split("\n") if len(l) > 10][:5]
    partidas = " | ".join(lineas)
    
    return total_detectado, partidas

# --- INICIALIZACIÓN DE DATOS ---
if "db" not in st.session_state:
    st.session_state.db = {
        "obras": pd.DataFrame([{"ID": 1, "Nombre": "Reforma CETA", "Presupuesto": 12500.0, "Estado": "Activa"}]),
        "empleados": pd.DataFrame([{"ID": 1, "Nombre": "Juan Pérez", "Cargo": "Oficial 1ª"}]),
        "pedidos": pd.DataFrame([{"ID": 101, "Material": "Diferenciales", "Partidas": "Material eléctrico vario", "Estado": "Pendiente", "Coste": 450.0}]),
        "gastos": pd.DataFrame(columns=["ID", "Obra", "Concepto", "Importe"]),
        "audit_extra": 0.0
    }

# --- VENTANA MODAL AUDITORÍA ---
@st.dialog("🔍 UniMatch: Auditoría de Planos")
def modal_unimatch():
    st.write("Sincronización de mediciones mediante IA.")
    f1 = st.file_uploader("Proyecto Referencia")
    f2 = st.file_uploader("Ejecución Real")
    if f1 and f2:
        with st.spinner("Analizando..."):
            time.sleep(1)
            st.session_state.db["audit_extra"] = 3600.0
            st.success("¡Desviación detectada! +3.600€")
            if st.button("Actualizar Presupuesto"): st.rerun()

# --- MÓDULOS ---

def modulo_pedidos():
    st.title("📦 Gestión de Pedidos con Reconocimiento de Archivos")
    t1, t2, t3 = st.tabs(["📋 Listado", "📤 Subir Pedido (PDF)", "⚙️ Gestionar"])
    
    with t1:
        st.dataframe(st.session_state.db["pedidos"], use_container_width=True)
    
    with t2:
        st.subheader("Subir Documento de Pedido")
        archivo_subido = st.file_uploader("Arrastra aquí el PDF del proveedor", type="pdf")
        
        if archivo_subido:
            with st.spinner("Leyendo partidas e importes..."):
                importe, partidas = extraer_datos_pdf(archivo_subido)
                st.success(f"Lectura completada.")
                
                with st.form("confirmar_pedido"):
                    nombre_mat = st.text_input("Nombre del Material/Pedido", value="Pedido Automático")
                    coste_final = st.number_input("Importe Reconocido (€)", value=importe)
                    partidas_det = st.text_area("Partidas Detectadas", value=partidas)
                    
                    if st.form_submit_button("Confirmar e Ingresar al ERP"):
                        new = {
                            "ID": int(time.time()), 
                            "Material": nombre_mat, 
                            "Partidas": partidas_det, 
                            "Estado": "Realizado", 
                            "Coste": coste_final
                        }
                        st.session_state.db["pedidos"] = pd.concat([st.session_state.db["pedidos"], pd.DataFrame([new])], ignore_index=True)
                        st.rerun()

    with t3:
        if not st.session_state.db["pedidos"].empty:
            sel_id = st.selectbox("Seleccionar ID para eliminar/editar", st.session_state.db["pedidos"]["ID"])
            if st.button("🗑️ Eliminar Pedido"):
                st.session_state.db["pedidos"] = st.session_state.db["pedidos"][st.session_state.db["pedidos"]["ID"] != sel_id]
                st.rerun()

def modulo_dashboard():
    st.title("📊 Resumen Ejecutivo")
    base = st.session_state.db["obras"]["Presupuesto"].sum()
    extra = st.session_state.db["audit_extra"]
    gastos = st.session_state.db["gastos"]["Importe"].sum() + st.session_state.db["pedidos"]["Coste"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos (con IA)", f"{base+extra:,.2f} €", f"+{extra} €")
    c2.metric("Gastos Totales", f"{gastos:,.2f} €")
    c3.metric("Beneficio Neto", f"{(base+extra)-gastos:,.2f} €")
    st.divider()
    if not st.session_state.db["obras"].empty:
        st.bar_chart(st.session_state.db["obras"].set_index("Nombre")["Presupuesto"])

def modulo_obras():
    st.title("🏗️ Gestión de Obras")
    t1, t2, t3 = st.tabs(["📋 Listado", "➕ Añadir", "⚙️ Gestionar"])
    with t1: st.dataframe(st.session_state.db["obras"], use_container_width=True)
    with t2:
        with st.form("add_o"):
            n = st.text_input("Nombre"); p = st.number_input("Presupuesto", min_value=0.0)
            if st.form_submit_button("Guardar"):
                new = {"ID": int(time.time()), "Nombre": n, "Presupuesto": p, "Estado": "Activa"}
                st.session_state.db["obras"] = pd.concat([st.session_state.db["obras"], pd.DataFrame([new])], ignore_index=True)
                st.rerun()
    with t3:
        if not st.session_state.db["obras"].empty:
            sel = st.selectbox("Seleccionar Obra", st.session_state.db["obras"]["Nombre"])
            row = st.session_state.db["obras"][st.session_state.db["obras"]["Nombre"] == sel].iloc[0]
            if st.button("🗑️ Eliminar Obra"):
                st.session_state.db["obras"] = st.session_state.db["obras"][st.session_state.db["obras"]["ID"] != row["ID"]]
                st.rerun()

def modulo_personal():
    st.title("👥 Gestión de Personal")
    t1, t2, t3 = st.tabs(["📋 Listado", "➕ Añadir", "⚙️ Gestionar"])
    with t1: st.table(st.session_state.db["empleados"])
    with t2:
        with st.form("add_e"):
            n = st.text_input("Nombre"); c = st.text_input("Cargo")
            if st.form_submit_button("Alta"):
                new = {"ID": int(time.time()), "Nombre": n, "Cargo": c}
                st.session_state.db["empleados"] = pd.concat([st.session_state.db["empleados"], pd.DataFrame([new])], ignore_index=True)
                st.rerun()
    with t3:
        if not st.session_state.db["empleados"].empty:
            sel = st.selectbox("Seleccionar Empleado", st.session_state.db["empleados"]["Nombre"])
            row = st.session_state.db["empleados"][st.session_state.db["empleados"]["Nombre"] == sel].iloc[0]
            if st.button("🗑️ Eliminar Empleado"):
                st.session_state.db["empleados"] = st.session_state.db["empleados"][st.session_state.db["empleados"]["ID"] != row["ID"]]
                st.rerun()

def modulo_gastos():
    st.title("💸 Gastos Imputables")
    t1, t2, t3 = st.tabs(["📋 Historial", "➕ Registrar", "⚙️ Gestionar"])
    with t1: st.dataframe(st.session_state.db["gastos"], use_container_width=True)
    with t2:
        with st.form("add_g"):
            o = st.selectbox("Obra", st.session_state.db["obras"]["Nombre"]) if not st.session_state.db["obras"].empty else st.text_input("Obra")
            c = st.text_input("Concepto"); i = st.number_input("Importe", min_value=0.0)
            if st.form_submit_button("Imputar"):
                new = {"ID": int(time.time()), "Obra": o, "Concepto": c, "Importe": i}
                st.session_state.db["gastos"] = pd.concat([st.session_state.db["gastos"], pd.DataFrame([new])], ignore_index=True)
                st.rerun()
    with t3:
        if not st.session_state.db["gastos"].empty:
            sel_id = st.selectbox("ID Gasto", st.session_state.db["gastos"]["ID"])
            if st.button("🗑️ Eliminar Gasto"):
                st.session_state.db["gastos"] = st.session_state.db["gastos"][st.session_state.db["gastos"]["ID"] != sel_id]
                st.rerun()

# --- NAVEGACIÓN ---
def main():
    with st.sidebar:
        st.write("### 🏢 GRUPO MAXTIVA")
        st.divider()
        menu = st.radio("MENÚ", ["Dashboard", "Obras", "Personal", "Pedidos", "Gastos Imputables"])
        st.divider()
        if st.button("🔍 Auditoría UniMatch"): modal_unimatch()

    if menu == "Dashboard": modulo_dashboard()
    elif menu == "Obras": modulo_obras()
    elif menu == "Personal": modulo_personal()
    elif menu == "Pedidos": modulo_pedidos()
    elif menu == "Gastos Imputables": modulo_gastos()

if __name__ == "__main__":
    main()
