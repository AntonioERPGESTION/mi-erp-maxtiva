import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Gestión Integral", layout="wide", page_icon="🏗️")

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
    .stTabs [data-baseweb="tab-list"] {{ gap: 24px; }}
    .stTabs [data-baseweb="tab"] {{ background-color: #f0f2f6; border-radius: 4px 4px 0px 0px; padding: 10px 20px; }}
    h1, h2, h3 {{ color: {COLOR_TEXTO}; }}
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE DATOS ---
if "db" not in st.session_state:
    st.session_state.db = {
        "obras": pd.DataFrame([{"ID": 1, "Nombre": "Reforma CETA", "Presupuesto": 12500.0, "Estado": "Activa"}]),
        "empleados": pd.DataFrame([{"ID": 1, "Nombre": "Juan Pérez", "Cargo": "Oficial 1ª"}]),
        "pedidos": pd.DataFrame([{"ID": 101, "Material": "Diferenciales", "Estado": "Pendiente", "Coste": 450.0}]),
        "gastos": pd.DataFrame([{"ID": 1, "Obra": "Reforma CETA", "Concepto": "Gasolina furgón", "Importe": 65.0}]),
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

# --- FUNCIONES AUXILIARES DE CRUD ---
def eliminar_registro(tabla, id_reg):
    st.session_state.db[tabla] = st.session_state.db[tabla][st.session_state.db[tabla]["ID"] != id_reg]
    st.rerun()

# --- MÓDULOS ---

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
            with st.form("edit_o"):
                new_n = st.text_input("Nombre", value=row["Nombre"]); new_p = st.number_input("Presupuesto", value=float(row["Presupuesto"]))
                if st.form_submit_button("Actualizar"):
                    st.session_state.db["obras"].loc[st.session_state.db["obras"]["ID"] == row["ID"], ["Nombre", "Presupuesto"]] = [new_n, new_p]
                    st.rerun()
            if st.button("🗑️ Eliminar Obra Seleccionada"): eliminar_registro("obras", row["ID"])

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
            with st.form("edit_e"):
                new_n = st.text_input("Nombre", value=row["Nombre"]); new_c = st.text_input("Cargo", value=row["Cargo"])
                if st.form_submit_button("Actualizar"):
                    st.session_state.db["empleados"].loc[st.session_state.db["empleados"]["ID"] == row["ID"], ["Nombre", "Cargo"]] = [new_n, new_c]
                    st.rerun()
            if st.button("🗑️ Eliminar Empleado"): eliminar_registro("empleados", row["ID"])

def modulo_pedidos():
    st.title("📦 Gestión de Pedidos")
    t1, t2, t3 = st.tabs(["📋 Listado", "➕ Añadir", "⚙️ Gestionar"])
    with t1: st.dataframe(st.session_state.db["pedidos"], use_container_width=True)
    with t2:
        with st.form("add_p"):
            m = st.text_input("Material"); c = st.number_input("Coste", min_value=0.0)
            if st.form_submit_button("Pedir"):
                new = {"ID": int(time.time()), "Material": m, "Estado": "Pendiente", "Coste": c}
                st.session_state.db["pedidos"] = pd.concat([st.session_state.db["pedidos"], pd.DataFrame([new])], ignore_index=True)
                st.rerun()
    with t3:
        if not st.session_state.db["pedidos"].empty:
            sel_id = st.selectbox("ID Pedido", st.session_state.db["pedidos"]["ID"])
            row = st.session_state.db["pedidos"][st.session_state.db["pedidos"]["ID"] == sel_id].iloc[0]
            with st.form("edit_p"):
                new_m = st.text_input("Material", value=row["Material"]); new_c = st.number_input("Coste", value=float(row["Coste"]))
                if st.form_submit_button("Actualizar"):
                    st.session_state.db["pedidos"].loc[st.session_state.db["pedidos"]["ID"] == row["ID"], ["Material", "Coste"]] = [new_m, new_c]
                    st.rerun()
            if st.button("🗑️ Eliminar Pedido"): eliminar_registro("pedidos", row["ID"])

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
            row = st.session_state.db["gastos"][st.session_state.db["gastos"]["ID"] == sel_id].iloc[0]
            if st.button("🗑️ Eliminar Gasto"): eliminar_registro("gastos", row["ID"])

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
