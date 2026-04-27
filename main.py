import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Maxtiva ERP Full", layout="wide", page_icon="🏗️")

# --- PERSISTENCIA DE DATOS (Session State) ---
def init_data():
    if "db_empleados" not in st.session_state:
        st.session_state.db_empleados = pd.DataFrame([
            {"ID": 1, "Nombre": "Juan Pérez", "Cargo": "Oficial 1ª", "Salario/h": 25.0}
        ])
    if "db_obras" not in st.session_state:
        st.session_state.db_obras = pd.DataFrame([
            {"ID": 1, "Nombre": "Reforma CETA", "Presupuesto": 12500.0, "Estado": "Activa"}
        ])
    if "db_jornadas" not in st.session_state:
        st.session_state.db_jornadas = pd.DataFrame(columns=["ID", "Fecha", "Empleado", "Obra", "Horas"])

init_data()

# --- FUNCIONES DE GESTIÓN (CRUD) ---
def borrar_registro(df_name, id_reg):
    st.session_state[df_name] = st.session_state[df_name][st.session_state[df_name]["ID"] != id_reg]
    st.rerun()

# --- MÓDULO: GESTIÓN DE OBRAS ---
def modulo_obras():
    st.title("🏗️ Gestión de Obras")
    
    with st.expander("➕ Registrar Nueva Obra"):
        with st.form("nueva_obra"):
            nom = st.text_input("Nombre de la Obra")
            pre = st.number_input("Presupuesto Inicial (€)", min_value=0.0)
            if st.form_submit_button("Crear Obra"):
                new_id = st.session_state.db_obras["ID"].max() + 1 if not st.session_state.db_obras.empty else 1
                new_row = {"ID": new_id, "Nombre": nom, "Presupuesto": pre, "Estado": "Activa"}
                st.session_state.db_obras = pd.concat([st.session_state.db_obras, pd.DataFrame([new_row])], ignore_index=True)
                st.success("Obra registrada")
                st.rerun()

    st.subheader("Listado de Proyectos")
    for i, row in st.session_state.db_obras.iterrows():
        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
        c1.write(f"**{row['Nombre']}**")
        c2.write(f"{row['Presupuesto']:,.2f} €")
        if c3.button("✏️ Edit", key=f"ed_ob_{row['ID']}"):
            st.info("Función de edición rápida: cambia el presupuesto en el código o base de datos.")
        if c4.button("🗑️", key=f"del_ob_{row['ID']}"):
            borrar_registro("db_obras", row["ID"])

# --- MÓDULO: GESTIÓN DE PERSONAL ---
def modulo_personal():
    st.title("👥 Gestión de Personal")
    
    tab1, tab2 = st.tabs(["Empleados", "Jornadas / Horas"])
    
    with tab1:
        with st.expander("➕ Alta de Empleado"):
            with st.form("nuevo_emp"):
                nom = st.text_input("Nombre Completo")
                car = st.selectbox("Cargo", ["Oficial 1ª", "Oficial 2ª", "Peón", "Ingeniero"])
                sal = st.number_input("Coste Hora (€)", min_value=0.0)
                if st.form_submit_button("Guardar"):
                    new_id = st.session_state.db_empleados["ID"].max() + 1 if not st.session_state.db_empleados.empty else 1
                    new_row = {"ID": new_id, "Nombre": nom, "Cargo": car, "Salario/h": sal}
                    st.session_state.db_empleados = pd.concat([st.session_state.db_empleados, pd.DataFrame([new_row])], ignore_index=True)
                    st.rerun()
        
        st.dataframe(st.session_state.db_empleados, use_container_width=True)
        id_del = st.number_input("ID a eliminar", min_value=1, step=1, key="del_emp_id")
        if st.button("Eliminar Empleado Seleccionado"):
            borrar_registro("db_empleados", id_del)

    with tab2:
        st.subheader("Registro de Jornadas")
        with st.form("registro_jornada"):
            c1, c2, c3 = st.columns(3)
            f_emp = c1.selectbox("Empleado", st.session_state.db_empleados["Nombre"])
            f_obr = c2.selectbox("Obra", st.session_state.db_obras["Nombre"])
            f_hor = c3.number_input("Horas", min_value=1)
            if st.form_submit_button("Registrar Horas"):
                new_id = st.session_state.db_jornadas["ID"].max() + 1 if not st.session_state.db_jornadas.empty else 1
                new_row = {"ID": new_id, "Fecha": datetime.now().strftime("%d/%m/%Y"), "Empleado": f_emp, "Obra": f_obr, "Horas": f_hor}
                st.session_state.db_jornadas = pd.concat([st.session_state.db_jornadas, pd.DataFrame([new_row])], ignore_index=True)
                st.rerun()
        st.table(st.session_state.db_jornadas)

# --- DASHBOARD PRINCIPAL ---
def modulo_dashboard():
    st.title("📊 Dashboard Maxtiva")
    total_pre = st.session_state.db_obras["Presupuesto"].sum()
    total_emp = len(st.session_state.db_empleados)
    total_hrs = st.session_state.db_jornadas["Horas"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Cartera de Obras", f"{total_pre:,.2f} €")
    c2.metric("Personal Activo", total_emp)
    c3.metric("Total Horas Reportadas", f"{total_hrs} h")
    
    st.divider()
    st.subheader("Resumen por Proyecto")
    st.bar_chart(st.session_state.db_obras.set_index("Nombre")["Presupuesto"])

# --- NAVEGACIÓN ---
def main():
    st.sidebar.title("Maxtiva ERP PRO")
    menu = st.sidebar.radio("Menú Principal", ["Dashboard", "Obras", "Personal"])
    
    if menu == "Dashboard":
        modulo_dashboard()
    elif menu == "Obras":
        modulo_obras()
    elif menu == "Personal":
        modulo_personal()

if __name__ == "__main__":
    main()
