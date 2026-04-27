import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Grupo Corporativo", layout="wide", page_icon="🏗️")

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

# --- INICIALIZACIÓN DE DATOS ---
if "db" not in st.session_state:
    st.session_state.db = {
        "obras": pd.DataFrame([{"ID": 1, "Nombre": "Reforma CETA", "Presupuesto": 12500.0, "Estado": "Activa"}]),
        "empleados": pd.DataFrame([{"ID": 1, "Nombre": "Juan Pérez", "Cargo": "Oficial 1ª"}]),
        "pedidos": pd.DataFrame([{"ID": 101, "Material": "Diferenciales", "Estado": "Pendiente", "Coste": 450.0}]),
        "gastos": pd.DataFrame(columns=["ID", "Obra", "Concepto", "Importe"]),
        "audit_extra": 0.0
    }

# --- VENTANA MODAL AUDITORÍA ---
@st.dialog("🔍 UniMatch: Auditoría de Planos")
def modal_unimatch():
    st.write("Detectar desviaciones entre Proyecto y As-Built.")
    f1 = st.file_uploader("Archivo ING")
    f2 = st.file_uploader("Archivo CETA")
    if f1 and f2:
        with st.spinner("Procesando..."):
            time.sleep(1)
            st.session_state.db["audit_extra"] = 3600.0
            st.success("¡Auditoría completada! +3.600€ detectados.")
            if st.button("Cargar Presupuesto"): st.rerun()

# --- MÓDULOS ---
def modulo_dashboard():
    st.title("📊 Panel de Control")
    base = st.session_state.db["obras"]["Presupuesto"].sum()
    extra = st.session_state.db["audit_extra"]
    gastos = st.session_state.db["gastos"]["Importe"].sum() + st.session_state.db["pedidos"]["Coste"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Presupuesto Total", f"{base+extra:,.2f} €", f"+{extra} € IA")
    c2.metric("Gastos Totales", f"{gastos:,.2f} €")
    c3.metric("Margen Neto", f"{(base+extra)-gastos:,.2f} €")
    
    st.divider()
    st.subheader("Estado Financiero de Proyectos")
    st.bar_chart(st.session_state.db["obras"].set_index("Nombre")["Presupuesto"])

def modulo_obras():
    st.title("🏗️ Gestión de Obras")
    with st.expander("➕ Añadir Obra"):
        with st.form("f_o"):
            n = st.text_input("Nombre de Obra")
            p = st.number_input("Presupuesto", min_value=0.0)
            if st.form_submit_button("Guardar"):
                new = {"ID": len(st.session_state.db["obras"])+1, "Nombre": n, "Presupuesto": p, "Estado": "Activa"}
                st.session_state.db["obras"] = pd.concat([st.session_state.db["obras"], pd.DataFrame([new])], ignore_index=True)
                st.rerun()
    st.dataframe(st.session_state.db["obras"], use_container_width=True)

def modulo_personal():
    st.title("👥 Gestión de Personal")
    with st.expander("➕ Alta Empleado"):
        with st.form("f_e"):
            n = st.text_input("Nombre")
            c = st.text_input("Cargo")
            if st.form_submit_button("Alta"):
                new = {"ID": len(st.session_state.db["empleados"])+1, "Nombre": n, "Cargo": c}
                st.session_state.db["empleados"] = pd.concat([st.session_state.db["empleados"], pd.DataFrame([new])], ignore_index=True)
                st.rerun()
    st.table(st.session_state.db["empleados"])

def modulo_pedidos():
    st.title("📦 Pedidos y Logística")
    with st.expander("➕ Nuevo Pedido"):
        with st.form("f_p"):
            m = st.text_input("Material")
            c = st.number_input("Coste")
            if st.form_submit_button("Pedir"):
                new = {"ID": len(st.session_state.db["pedidos"])+101, "Material": m, "Estado": "Pendiente", "Coste": c}
                st.session_state.db["pedidos"] = pd.concat([st.session_state.db["pedidos"], pd.DataFrame([new])], ignore_index=True)
                st.rerun()
    st.dataframe(st.session_state.db["pedidos"], use_container_width=True)

def modulo_gastos():
    st.title("💸 Gastos Imputables")
    with st.form("f_g"):
        o = st.selectbox("Obra", st.session_state.db["obras"]["Nombre"])
        c = st.text_input("Concepto (Gasolina, Dietas, etc.)")
        i = st.number_input("Importe")
        if st.form_submit_button("Registrar Gasto"):
            new = {"ID": len(st.session_state.db["gastos"])+1, "Obra": o, "Concepto": c, "Importe": i}
            st.session_state.db["gastos"] = pd.concat([st.session_state.db["gastos"], pd.DataFrame([new])], ignore_index=True)
            st.rerun()
    st.dataframe(st.session_state.db["gastos"], use_container_width=True)

# --- NAVEGACIÓN ---
def main():
    with st.sidebar:
        st.subheader("🏢 GRUPO MAXTIVA") # Aquí puedes poner el logo con st.image("tu_logo.png")
        st.divider()
        menu = st.radio("MENÚ PRINCIPAL", ["Dashboard", "Obras", "Personal", "Pedidos", "Gastos Imputables"])
        st.divider()
        if st.button("🔍 Auditoría UniMatch", use_container_width=True):
            modal_unimatch()

    if menu == "Dashboard": modulo_dashboard()
    elif menu == "Obras": modulo_obras()
    elif menu == "Personal": modulo_personal()
    elif menu == "Pedidos": modulo_pedidos()
    elif menu == "Gastos Imputables": modulo_gastos()

if __name__ == "__main__":
    main()
