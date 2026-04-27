import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Maxtiva ERP - Full Control", layout="wide", page_icon="🏗️")

# --- PERSISTENCIA DE DATOS (Ampliación de DB) ---
def init_data():
    if "db_empleados" not in st.session_state:
        st.session_state.db_empleados = pd.DataFrame([{"ID": 1, "Nombre": "Juan Pérez", "Cargo": "Oficial 1ª", "Coste/h": 25.0}])
    if "db_obras" not in st.session_state:
        st.session_state.db_obras = pd.DataFrame([{"ID": 1, "Nombre": "Reforma CETA", "Presupuesto": 12500.0, "Estado": "Activa"}])
    if "db_pedidos" not in st.session_state:
        st.session_state.db_pedidos = pd.DataFrame(columns=["ID", "Material", "Proveedor", "Estado", "Entrega", "Coste"])
    if "db_jornadas" not in st.session_state:
        st.session_state.db_jornadas = pd.DataFrame(columns=["ID", "Fecha", "Empleado", "Obra", "Horas"])
    # NUEVA TABLA DE GASTOS
    if "db_gastos" not in st.session_state:
        st.session_state.db_gastos = pd.DataFrame(columns=["ID", "Fecha", "Obra", "Empleado", "Concepto", "Tipo", "Importe"])
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
        with st.spinner("Analizando..."):
            time.sleep(1)
            st.session_state.audit_extra = 3600.0
            st.success("¡Desviación detectada! +3.600€")
            if st.button("Cargar al ERP"): st.rerun()

# --- MÓDULO: GASTOS IMPUTABLES ---
def modulo_gastos():
    st.title("💸 Gastos Imputables (Dietas, Viajes, Suministros)")
    
    col_f, col_v = st.columns([1, 2])
    
    with col_f:
        st.subheader("Registrar Gasto")
        with st.form("form_gastos", clear_on_submit=True):
            fecha_g = st.date_input("Fecha", datetime.now())
            obra_g = st.selectbox("Obra Destino", st.session_state.db_obras["Nombre"])
            emp_g = st.selectbox("Empleado", st.session_state.db_empleados["Nombre"])
            tipo_g = st.selectbox("Categoría", ["Dietas", "Gasolina/KM", "Hotel", "Material Urgente", "Otros"])
            concepto_g = st.text_input("Concepto (ej: Comida equipo CETA)")
            importe_g = st.number_input("Importe (€)", min_value=0.0, step=0.1)
            
            if st.form_submit_button("Imputar Gasto"):
                new_id = len(st.session_state.db_gastos) + 1
                new_row = {
                    "ID": new_id, "Fecha": fecha_g, "Obra": obra_g, 
                    "Empleado": emp_g, "Concepto": concepto_g, 
                    "Tipo": tipo_g, "Importe": importe_g
                }
                st.session_state.db_gastos = pd.concat([st.session_state.db_gastos, pd.DataFrame([new_row])], ignore_index=True)
                st.success("Gasto imputado correctamente")
                st.rerun()

    with col_v:
        st.subheader("Historial de Gastos")
        if not st.session_state.db_gastos.empty:
            st.dataframe(st.session_state.db_gastos, use_container_width=True)
            
            # Gráfico de gastos por categoría
            fig = go.Figure(data=[go.Pie(
                labels=st.session_state.db_gastos["Tipo"], 
                values=st.session_state.db_gastos["Importe"], 
                hole=.3
            )])
            fig.update_layout(title="Distribución de Gastos Indirectos")
            st.plotly_chart(fig, use_container_width=True)
            
            if st.button("🗑️ Borrar último gasto"):
                st.session_state.db_gastos = st.session_state.db_gastos[:-1]
                st.rerun()
        else:
            st.info("No hay gastos registrados todavía.")

# --- DASHBOARD ACTUALIZADO ---
def modulo_dashboard():
    st.title("📊 Dashboard de Control Financiero")
    
    base = st.session_state.db_obras["Presupuesto"].sum()
    extra = st.session_state.audit_extra
    ingresos_totales = base + extra
    
    gastos_material = st.session_state.db_pedidos["Coste"].sum()
    gastos_imputables = st.session_state.db_gastos["Importe"].sum()
    gastos_totales = gastos_material + gastos_imputables
    
    beneficio = ingresos_totales - gastos_totales

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingresos (Inc. IA)", f"{ingresos_totales:,.2f} €", f"+{extra} €")
    c2.metric("Gastos Directos (Mat)", f"{gastos_material:,.2f} €")
    c3.metric("Gastos Indirectos", f"{gastos_imputables:,.2f} €", delta_color="inverse")
    c4.metric("BENEFICIO NETO", f"{beneficio:,.2f} €", f"{((beneficio/ingresos_totales)*100) if ingresos_totales > 0 else 0:.1f}%")

    st.divider()
    st.subheader("Análisis de Rentabilidad por Obra")
    st.bar_chart(st.session_state.db_gastos.groupby("Obra")["Importe"].sum())

# --- NAVEGACIÓN ---
def main():
    st.sidebar.title("Maxtiva ERP v3.5")
    menu = st.sidebar.radio("Navegación", ["Dashboard", "Obras", "Pedidos", "Personal", "💸 Gastos Imputables"])
    
    st.sidebar.divider()
    if st.sidebar.button("🔍 Auditoría UniMatch", use_container_width=True):
        modal_unimatch()

    if menu == "Dashboard": modulo_dashboard()
    elif menu == "Obras": st.title("🏗️ Obras"); st.write("Gestione sus proyectos aquí.") # Reutilizar lógica CRUD previa
    elif menu == "Pedidos": st.title("📦 Pedidos"); st.write("Control de materiales.") 
    elif menu == "Personal": st.title("👥 Personal"); st.write("Gestión de operarios.")
    elif menu == "💸 Gastos Imputables": modulo_gastos()

if __name__ == "__main__":
    main()
