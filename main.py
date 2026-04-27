import streamlit as st
import pandas as pd
import pdfplumber
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Maxtiva ERP Ultimate", layout="wide", page_icon="🏗️")

# --- PERSISTENCIA DE DATOS (Session State) ---
def init_data():
    if "db_empleados" not in st.session_state:
        st.session_state.db_empleados = pd.DataFrame([{"ID": 1, "Nombre": "Juan Pérez", "Cargo": "Oficial 1ª", "Coste/h": 25.0}])
    if "db_obras" not in st.session_state:
        st.session_state.db_obras = pd.DataFrame([{"ID": 1, "Nombre": "Reforma CETA", "Presupuesto": 12500.0, "Estado": "Activa"}])
    if "db_pedidos" not in st.session_state:
        st.session_state.db_pedidos = pd.DataFrame([
            {"ID": 101, "Material": "Diferenciales 40A", "Proveedor": "Saltoki", "Estado": "Recibido", "Entrega": "2024-05-10", "Coste": 450.0},
            {"ID": 102, "Material": "Cable 2.5mm", "Proveedor": "Dielectro", "Estado": "Pendiente", "Entrega": "2024-05-25", "Coste": 1200.0}
        ])
    if "audit_extra" not in st.session_state:
        st.session_state.audit_extra = 0.0

init_data()

# --- LÓGICA DE AUDITORÍA (MODAL) ---
@st.dialog("⚡ UniMatch: Auditoría de Planos")
def modal_unimatch():
    st.write("Sincroniza planos para detectar adicionales de facturación.")
    f_ing = st.file_uploader("Proyecto ING", type="pdf", key="m_ing")
    f_ceta = st.file_uploader("Ejecución CETA", type="pdf", key="m_ceta")
    if f_ing and f_ceta:
        with st.spinner("Analizando discrepancias..."):
            time.sleep(1.5)
            dif = 48 
            coste = dif * 75.0
        st.metric("Desviación Detectada", f"+{dif} circuitos", f"{coste} €")
        if st.button("📥 Sincronizar Presupuesto"):
            st.session_state.audit_extra = coste
            st.rerun()

# --- MÓDULO: PEDIDOS Y LOGÍSTICA ---
def modulo_pedidos():
    st.title("📦 Gestión de Pedidos y Suministros")
    
    # Filtros de estado
    col1, col2, col3, col4 = st.columns(4)
    total = len(st.session_state.db_pedidos)
    pendientes = len(st.session_state.db_pedidos[st.session_state.db_pedidos["Estado"] == "Pendiente"])
    col1.metric("Total Pedidos", total)
    col2.metric("📦 Pendientes", pendientes, delta_color="inverse")
    
    tab_list, tab_new, tab_agenda = st.tabs(["Lista de Pedidos", "Nuevo Pedido", "📅 Agenda de Entregas"])
    
    with tab_list:
        estado_filtro = st.multiselect("Filtrar por estado", ["Pendiente", "Realizado", "Recibido"], default=["Pendiente", "Realizado", "Recibido"])
        df_mostrar = st.session_state.db_pedidos[st.session_state.db_pedidos["Estado"].isin(estado_filtro)]
        st.dataframe(df_mostrar, use_container_width=True)
        
        # Acción rápida: Marcar como recibido
        id_edit = st.number_input("ID Pedido para actualizar", min_value=0, step=1)
        nuevo_est = st.selectbox("Cambiar estado a:", ["Pendiente", "Realizado", "Recibido"])
        if st.button("Actualizar Estado"):
            st.session_state.db_pedidos.loc[st.session_state.db_pedidos["ID"] == id_edit, "Estado"] = nuevo_est
            st.success("Estado actualizado")
            st.rerun()

    with tab_new:
        with st.form("form_pedidos"):
            mat = st.text_input("Material / Equipo")
            prov = st.text_input("Proveedor")
            coste = st.number_input("Coste Estimado (€)", min_value=0.0)
            fecha_p = st.date_input("Previsión de Entrega", datetime.now() + timedelta(days=7))
            if st.form_submit_button("Lanzar Pedido"):
                new_id = st.session_state.db_pedidos["ID"].max() + 1
                new_row = {"ID": new_id, "Material": mat, "Proveedor": prov, "Estado": "Realizado", "Entrega": str(fecha_p), "Coste": coste}
                st.session_state.db_pedidos = pd.concat([st.session_state.db_pedidos, pd.DataFrame([new_row])], ignore_index=True)
                st.rerun()

    with tab_agenda:
        st.subheader("Cronograma de Suministros")
        # Gráfico simple de previsión
        fig = go.Figure(data=[go.Scatter(
            x=st.session_state.db_pedidos["Entrega"],
            y=st.session_state.db_pedidos["Material"],
            mode='markers+text',
            text=st.session_state.db_pedidos["Proveedor"],
            marker=dict(size=20, color=['red' if e == "Pendiente" else 'green' for e in st.session_state.db_pedidos["Estado"]])
        )])
        fig.update_layout(title="Próximas entregas (Rojo: Pendiente | Verde: Recibido)")
        st.plotly_chart(fig, use_container_width=True)

# --- DASHBOARD (ACTUALIZADO) ---
def modulo_dashboard():
    st.title("📊 Dashboard Maxtiva Ultimate")
    base = st.session_state.db_obras["Presupuesto"].sum()
    extra = st.session_state.audit_extra
    coste_pedidos = st.session_state.db_pedidos["Coste"].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Presupuesto Base", f"{base:,.2f} €")
    c2.metric("Extras IA (UniMatch)", f"{extra:,.2f} €")
    c3.metric("Gasto en Materiales", f"{coste_pedidos:,.2f} €")
    c4.metric("Balance Disponible", f"{(base + extra) - coste_pedidos:,.2f} €")

# --- NAVEGACIÓN ---
def main():
    st.sidebar.title("Maxtiva ERP v3.0")
    menu = st.sidebar.radio("Navegación", ["Dashboard", "Obras", "Pedidos / Agenda", "Personal"])
    
    st.sidebar.divider()
    st.sidebar.write("🛠️ **Ingeniería Eléctrica**")
    if st.sidebar.button("🔍 Auditoría UniMatch", use_container_width=True):
        modal_unimatch()

    if menu == "Dashboard": modulo_dashboard()
    elif menu == "Obras": st.write("Módulo Obras Activo") # (Se puede copiar del código anterior)
    elif menu == "Pedidos / Agenda": modulo_pedidos()
    elif menu == "Personal": st.write("Módulo Personal Activo")

if __name__ == "__main__":
    main()
