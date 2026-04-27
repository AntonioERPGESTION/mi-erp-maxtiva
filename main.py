import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP v5.0", layout="wide", page_icon="🏗️")

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .main { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #1e3d59; }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE BASE DE DATOS (PERSISTENCIA EN SESIÓN) ---
if "db" not in st.session_state:
    st.session_state.db = {
        "obras": pd.DataFrame([{"ID": 1, "Nombre": "Reforma CETA", "Presupuesto": 12500.0, "Estado": "Activa"}]),
        "empleados": pd.DataFrame([{"ID": 1, "Nombre": "Juan Pérez", "Cargo": "Oficial 1ª", "Coste/h": 25.0}]),
        "pedidos": pd.DataFrame([{"ID": 101, "Material": "Diferenciales", "Prov": "Saltoki", "Estado": "Pendiente", "Coste": 450.0}]),
        "gastos": pd.DataFrame(columns=["ID", "Obra", "Empleado", "Tipo", "Concepto", "Importe"]),
        "jornadas": pd.DataFrame(columns=["ID", "Fecha", "Empleado", "Obra", "Horas"]),
        "audit_extra": 0.0
    }

# --- HERRAMIENTA: AUDITORÍA UNIMATCH (VENTANA MODAL) ---
@st.dialog("⚡ UniMatch: Auditoría de Planos")
def modal_unimatch():
    st.write("Sincroniza planos para detectar adicionales de facturación no contemplados.")
    f_ing = st.file_uploader("Proyecto Referencia (ING)", type="pdf")
    f_ceta = st.file_uploader("Proyecto Ejecución (CETA)", type="pdf")
    if f_ing and f_ceta:
        with st.spinner("Analizando discrepancias técnicas..."):
            time.sleep(1.5)
            # Simulación de detección de los 48 circuitos adicionales
            st.session_state.db["audit_extra"] = 3600.0
            st.success("¡Desviación detectada! Se han encontrado 48 circuitos adicionales (+3.600€)")
            if st.button("Sincronizar con Presupuesto Real"):
                st.rerun()

# --- MÓDULO 1: DASHBOARD (VISIÓN GLOBAL) ---
def modulo_dashboard():
    st.title("📊 Panel de Control Financiero")
    
    # Cálculos en tiempo real
    base = st.session_state.db["obras"]["Presupuesto"].sum()
    extra = st.session_state.db["audit_extra"]
    total_ingresos = base + extra
    
    coste_materiales = st.session_state.db["pedidos"]["Coste"].sum()
    coste_gastos = st.session_state.db["gastos"]["Importe"].sum()
    total_costes = coste_materiales + coste_gastos
    
    beneficio = total_ingresos - total_costes

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingresos Totales", f"{total_ingresos:,.2f} €", f"+{extra} € (IA)")
    c2.metric("Gastos Totales", f"{total_costes:,.2f} €")
    c3.metric("Beneficio Neto", f"{beneficio:,.2f} €", delta_color="normal")
    c4.metric("Margen de Obra", f"{(beneficio/total_ingresos*100) if total_ingresos > 0 else 0:.1f} %")

    st.divider()
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📈 Presupuesto por Obra")
        if not st.session_state.db["obras"].empty:
            st.bar_chart(st.session_state.db["obras"].set_index("Nombre")["Presupuesto"])
            
    with col_right:
        st.subheader("💸 Desglose de Gastos Indirectos")
        if not st.session_state.db["gastos"].empty:
            fig = go.Figure(data=[go.Pie(labels=st.session_state.db["gastos"]["Tipo"], values=st.session_state.db["gastos"]["Importe"], hole=.3)])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin gastos registrados para analizar.")

# --- MÓDULO 2: GESTIÓN DE OBRAS ---
def modulo_obras():
    st.title("🏗️ Gestión de Proyectos")
    with st.expander("➕ Dar de alta nueva obra"):
        with st.form("f_obras", clear_on_submit=True):
            nom = st.text_input("Nombre de la Obra")
            pre = st.number_input("Presupuesto (€)", min_value=0.0)
            if st.form_submit_button("Registrar Obra"):
                new_row = {"ID": len(st.session_state.db["obras"])+1, "Nombre": nom, "Presupuesto": pre, "Estado": "Activa"}
                st.session_state.db["obras"] = pd.concat([st.session_state.db["obras"], pd.DataFrame([new_row])], ignore_index=True)
                st.rerun()
    
    st.write("### Obras en Curso")
    st.dataframe(st.session_state.db["obras"], use_container_width=True)
    if st.button("🗑️ Eliminar última obra"):
        st.session_state.db["obras"] = st.session_state.db["obras"][:-1]
        st.rerun()

# --- MÓDULO 3: PEDIDOS Y LOGÍSTICA ---
def modulo_pedidos():
    st.title("📦 Compras y Suministros")
    with st.expander("➕ Nuevo Pedido de Material"):
        with st.form("f_ped", clear_on_submit=True):
            mat = st.text_input("Material")
            pro = st.text_input("Proveedor")
            cos = st.number_input("Importe (€)", min_value=0.0)
            if st.form_submit_button("Lanzar Pedido"):
                new_row = {"ID": len(st.session_state.db["pedidos"])+101, "Material": mat, "Prov": pro, "Estado": "Pendiente", "Coste": cos}
                st.session_state.db["pedidos"] = pd.concat([st.session_state.db["pedidos"], pd.DataFrame([new_row])], ignore_index=True)
                st.rerun()
    
    st.table(st.session_state.db["pedidos"])

# --- MÓDULO 4: PERSONAL Y JORNADAS ---
def modulo_personal():
    st.title("👥 Gestión de Equipos")
    tab1, tab2 = st.tabs(["Listado de Personal", "Registro de Jornadas"])
    
    with tab1:
        with st.expander("➕ Alta de Operario"):
            with st.form("f_emp"):
                nom = st.text_input("Nombre")
                car = st.selectbox("Cargo", ["Oficial 1ª", "Oficial 2ª", "Ayudante", "Ingeniero"])
                if st.form_submit_button("Guardar"):
                    new_row = {"ID": len(st.session_state.db["empleados"])+1, "Nombre": nom, "Cargo": car, "Coste/h": 20.0}
                    st.session_state.db["empleados"] = pd.concat([st.session_state.db["empleados"], pd.DataFrame([new_row])], ignore_index=True)
                    st.rerun()
        st.dataframe(st.session_state.db["empleados"], use_container_width=True)

    with tab2:
        with st.form("f_jor"):
            e = st.selectbox("Empleado", st.session_state.db["empleados"]["Nombre"])
            o = st.selectbox("Obra", st.session_state.db["obras"]["Nombre"])
            h = st.number_input("Horas", min_value=1, max_value=12)
            if st.form_submit_button("Registrar Horas"):
                new_h = {"ID": len(st.session_state.db["jornadas"]), "Fecha": datetime.now().date(), "Empleado": e, "Obra": o, "Horas": h}
                st.session_state.db["jornadas"] = pd.concat([st.session_state.db["jornadas"], pd.DataFrame([new_h])], ignore_index=True)
                st.rerun()
        st.table(st.session_state.db["jornadas"])

# --- MÓDULO 5: GASTOS IMPUTABLES (DIETAS, GASOLINA, ETC) ---
def modulo_gastos():
    st.title("💸 Gastos Imputables a Obra")
    st.info("Registre aquí gastos de gasolina, dietas, hoteles o materiales urgentes pagados en efectivo.")
    
    with st.form("f_gastos", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        obr = c1.selectbox("Vincular a Obra", st.session_state.db["obras"]["Nombre"])
        emp = c2.selectbox("Responsable del Gasto", st.session_state.db["empleados"]["Nombre"])
        tip = c3.selectbox("Categoría", ["Gasolina", "Dietas/Comidas", "Hotel/Alojamiento", "Otros"])
        
        con = st.text_input("Concepto Detallado")
        imp = st.number_input("Importe del Gasto (€)", min_value=0.0)
        
        if st.form_submit_button("Imputar Gasto a Obra"):
            new_row = {"ID": len(st.session_state.db["gastos"])+1, "Obra": obr, "Empleado": emp, "Tipo": tip, "Concepto": con, "Importe": imp}
            st.session_state.db["gastos"] = pd.concat([st.session_state.db["gastos"], pd.DataFrame([new_row])], ignore_index=True)
            st.rerun()
            
    st.write("### Historial de Gastos Indirectos")
    st.dataframe(st.session_state.db["gastos"], use_container_width=True)

# --- NAVEGACIÓN Y ENRUTADOR ---
def main():
    st.sidebar.title("Maxtiva ERP v5.0")
    st.sidebar.divider()
    
    menu = st.sidebar.radio(
        "Navegación Principal", 
        ["Dashboard", "Gestión de Obras", "Pedidos / Logística", "Personal", "Gastos Imputables"]
    )
    
    st.sidebar.divider()
    st.sidebar.write("🛠️ **Ingeniería Eléctrica**")
    if st.sidebar.button("🔍 Auditoría UniMatch", use_container_width=True):
        modal_unimatch()

    # Selección de módulo activo
    if menu == "Dashboard": modulo_dashboard()
    elif menu == "Gestión de Obras": modulo_obras()
    elif menu == "Pedidos / Logística": modulo_pedidos()
    elif menu == "Personal": modulo_personal()
    elif menu == "Gastos Imputables": modulo_gastos()

if __name__ == "__main__":
    main()
