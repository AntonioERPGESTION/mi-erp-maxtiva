import streamlit as st
import pdfplumber
import plotly.graph_objects as go
import pandas as pd
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Sistema Integral", layout="wide", page_icon="🏗️")

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #1e3d59; color: white; }
    .stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE VARIABLES DE ESTADO ---
if "audit_result" not in st.session_state:
    st.session_state.audit_result = {"extra": 0.0, "puntos": 0}

# --- LÓGICA DEL POP-UP (UNIMATCH) ---
@st.dialog("🔍 UniMatch: Auditoría de Planos")
def modal_unimatch():
    st.write("Sincroniza la ejecución real (CETA) contra el proyecto (ING).")
    c1, c2 = st.columns(2)
    f_ing = c1.file_uploader("Proyecto ING", type="pdf", key="u_ing")
    f_ceta = c2.file_uploader("Ejecución CETA", type="pdf", key="u_ceta")

    if f_ing and f_ceta:
        with st.spinner("Analizando esquemas..."):
            time.sleep(1.5)
            # Simulación basada en tus archivos reales
            dif = 48 
            coste = dif * 75.0
        
        st.metric("Desviación Detectada", f"+{dif} circuitos", f"{coste:,.2f} €")
        
        if st.button("📥 Cargar Adicionales al ERP"):
            st.session_state.audit_result = {"extra": coste, "puntos": dif}
            st.rerun()

# --- COMPONENTES DEL ERP ---

def modulo_dashboard():
    st.title("🏗️ Dashboard de Gestión de Obra")
    
    # Métricas Principales
    base_obra = 12500.00
    extra_obra = st.session_state.audit_result["extra"]
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Presupuesto Base", f"{base_obra:,.2f} €")
    c2.metric("Adicionales Detectados", f"{extra_obra:,.2f} €", delta=f"{st.session_state.audit_result['puntos']} pts")
    c3.metric("Total Proyecto", f"{base_obra + extra_obra:,.2f} €")
    c4.metric("Margen Estimado", "22%", "2.5%")

    st.divider()
    
    col_t, col_g = st.columns([2, 1])
    with col_t:
        st.subheader("📋 Partidas del Proyecto")
        data = {
            "Partida": ["Acometida General", "Cuadro Socorro BT", "Ampliaciones Detectadas (IA)"],
            "Estado": ["Finalizado", "En Proceso", "Pendiente" if extra_obra > 0 else "N/A"],
            "Importe": [8500, 4000, extra_obra]
        }
        st.table(pd.DataFrame(data))
    
    with col_g:
        st.subheader("📊 Distribución Costes")
        fig = go.Figure(data=[go.Pie(labels=['Base', 'Adicionales'], values=[base_obra, extra_obra], hole=.3)])
        st.plotly_chart(fig, use_container_width=True)

def modulo_facturacion():
    st.title("💰 Facturación y Cobros")
    st.write("Gestión de certificaciones y facturas emitidas.")
    df_fac = pd.DataFrame({
        "Nº Factura": ["FAC-001", "FAC-002"],
        "Concepto": ["Entrega Inicial", "Certificación Mes 1"],
        "Importe": ["3.500 €", "4.000 €"],
        "Estado": ["Cobrado", "Pendiente"]
    })
    st.dataframe(df_fac, use_container_width=True)

def modulo_personal():
    st.title("👥 Gestión de Personal")
    st.write("Control de operarios y horas asignadas a la obra.")
    st.info("Operarios activos: 4 | Total horas mes: 160h")

# --- NAVEGACIÓN Y ESTRUCTURA PRINCIPAL ---

def main():
    # Menú Lateral
    with st.sidebar:
        st.title("Maxtiva ERP")
        st.markdown("---")
        # Selección de módulos
        menu = st.radio("Menú Principal", ["🏠 Dashboard", "💰 Facturación", "👥 Personal"])
        st.markdown("---")
        st.write("🛠️ **Herramientas Avanzadas**")
        if st.button("🔍 Auditoría UniMatch", use_container_width=True):
            modal_unimatch()

    # Lógica de cambio de módulos
    if menu == "🏠 Dashboard":
        modulo_dashboard()
    elif menu == "💰 Facturación":
        modulo_facturacion()
    elif menu == "👥 Personal":
        modulo_personal()

if __name__ == "__main__":
    main()
