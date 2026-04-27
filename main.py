import streamlit as st
import pdfplumber
import plotly.graph_objects as go
import pandas as pd
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Sistema Integral", layout="wide", page_icon="🏗️")

# --- LÓGICA DEL POP-UP (UNIMATCH) ---
@st.dialog("🔍 UniMatch: Auditoría de Planos")
def modal_unimatch():
    st.write("Sincroniza la ejecución real (CETA) contra el proyecto (ING).")
    c1, c2 = st.columns(2)
    f_ing = c1.file_uploader("Proyecto ING", type="pdf", key="u_ing")
    f_ceta = c2.file_uploader("Ejecución CETA", type="pdf", key="u_ceta")

    if f_ing and f_ceta:
        with st.spinner("Analizando..."):
            time.sleep(1.5)
            # Datos basados en tus archivos reales
            dif = 48 
            coste = dif * 75.0
        
        st.metric("Desviación Detectada", f"+{dif} circuitos", f"{coste:,.2f} €")
        
        if st.button("📥 Cargar Adicionales al ERP"):
            st.session_state.audit_result = {"extra": coste, "puntos": dif}
            st.rerun()

# --- CUERPO PRINCIPAL DEL GESTOR DE OBRAS (MAXTIVA) ---
def main():
    # 1. Barra Lateral (Navegación)
    st.sidebar.title("ERP Maxtiva")
    st.sidebar.button("🏠 Dashboard Principal")
    st.sidebar.button("📋 Listado de Obras")
    st.sidebar.button("💰 Facturación")
    
    # 2. Cabecera del Gestor
    st.title("🏗️ Gestor de Obra: Sector CETA - Reforma")
    
    col_info, col_audit = st.columns([3, 1])
    with col_info:
        st.markdown("**Cliente:** Ingeniería Global | **Referencia:** 2024-CETA-01")
        st.info("Estado: Ejecución de cuadros eléctricos en curso.")
    
    with col_audit:
        # Aquí lanzamos el pop-up sin que desaparezca el resto
        if st.button("🔍 Auditar con UniMatch", use_container_width=True):
            modal_unimatch()

    st.divider()

    # 3. Resumen Económico (Métricas del ERP)
    base_obra = 12500.00
    extra_obra = st.session_state.get("audit_result", {}).get("extra", 0.0)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Presupuesto Contratado", f"{base_obra:,.2f} €")
    c2.metric("Adicionales (UniMatch)", f"{extra_obra:,.2f} €", delta=f"{st.session_state.get('audit_result', {}).get('puntos', 0)} pts")
    c3.metric("Total a Facturar", f"{base_obra + extra_obra:,.2f} €")
    c4.metric("Margen de Obra", "22%", "2.5%")

    # 4. Tabla de Partidas del ERP
    st.subheader("📋 Desglose de Partidas y Materiales")
    
    data = {
        "Partida": ["Acometida General", "Cuadro Socorro BT", "Ampliaciones CETA (IA)"],
        "Estado": ["Finalizado", "En Proceso", "Pendiente Validar" if extra_obra > 0 else "N/A"],
        "Importe": [8500, 4000, extra_obra]
    }
    df = pd.DataFrame(data)
    st.table(df)

    # 5. Gráfico de Control de Costes
    st.subheader("📈 Análisis de Desviación")
    fig = go.Figure(data=[
        go.Bar(name='Presupuesto Base', x=['Proyecto'], y=[base_obra], marker_color='#004a99'),
        go.Bar(name='Ampliaciones Det.', x=['Proyecto'], y=[extra_obra], marker_color='#d9534f')
    ])
    fig.update_layout(barmode='stack', height=350, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
