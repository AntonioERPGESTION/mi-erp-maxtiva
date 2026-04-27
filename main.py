import streamlit as st
import pdfplumber
import plotly.graph_objects as go
import pandas as pd
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Maxtiva ERP - Gestión de Obra", layout="wide", page_icon="🏗️")

# --- ESTILOS MAXTIVA ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stButton>button { border-radius: 5px; height: 3em; background-color: #004a99; color: white; }
    .stMetric { background-color: white; border: 1px solid #e0e0e0; padding: 15px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- LÓGICA DEL POP-UP (UNIMATCH) ---
@st.dialog("🔍 UniMatch: Auditoría de Planos Unifilares")
def modal_unimatch():
    st.write("Carga los esquemas para detectar desviaciones entre Proyecto y Ejecución.")
    
    c1, c2 = st.columns(2)
    f_ing = c1.file_uploader("Documento base (ING)", type="pdf", key="ing_val")
    f_ceta = c2.file_uploader("Documento ejecución (CETA)", type="pdf", key="ceta_val")

    if f_ing and f_ceta:
        with st.spinner("Escaneando nodos y etiquetas..."):
            time.sleep(2)
            # Simulación de los datos reales de tus archivos
            circuitos_base = 14
            circuitos_reales = 62 
            dif = circuitos_reales - circuitos_base
            coste_adicional = dif * 75.0 # Precio estimado por punto montado
            
            # Buscamos tus notas manuscritas
            with pdfplumber.open(f_ceta) as pdf:
                texto = " ".join([p.extract_text() for p in pdf.pages]).upper()
            
        st.success(f"Detección completada: **+{dif} circuitos** nuevos.")
        
        # Gráfica de impacto para el Pop-up
        fig = go.Figure(data=[
            go.Bar(name='Original', x=['Obra'], y=[circuitos_base * 75], marker_color='#004a99'),
            go.Bar(name='Adicional', x=['Obra'], y=[coste_adicional], marker_color='#d9534f')
        ])
        fig.update_layout(barmode='stack', height=250, margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig, use_container_width=True)

        if "MISMA ENVOLVENTE" in texto:
            st.warning("📝 Nota detectada: **MISMA ENVOLVENTE**. Se requiere recotizar armario unificado.")

        if st.button("📥 Sincronizar con Presupuesto Maxtiva"):
            st.session_state.audit_data = {
                "extra": coste_adicional,
                "diff": dif,
                "msg": "Facturación adicional generada por UniMatch"
            }
            st.rerun()

# --- CUERPO PRINCIPAL DEL ERP ---
def main():
    # Sidebar de Navegación
    st.sidebar.title("ERP Maxtiva")
    st.sidebar.selectbox("Menú", ["Dashboard", "Facturación", "Personal", "Configuración"])
    
    st.title("🏗️ Gestión de Proyecto: Reforma Eléctrica CETA")
    
    # Cabecera con Botón de Auditoría
    col_status, col_tool = st.columns([3, 1])
    with col_status:
        st.write("**Cliente:** Ingeniería Global S.L.")
        st.write("**Ubicación:** Planta Baja y 1ª")
    with col_tool:
        if st.button("🔍 Iniciar Auditoría UniMatch"):
            modal_unimatch()

    st.divider()

    # Mostrar métricas si hay datos de auditoría
    if "audit_data" in st.session_state:
        d = st.session_state.audit_data
        c1, c2, c3 = st.columns(3)
        c1.metric("Presupuesto Inicial", "4.500 €")
        c2.metric("Adicionales Detectados", f"{d['extra']:,.2f} €", f"+{d['diff']} ptos")
        c3.metric("Total Actualizado", f"{4500 + d['extra']:,.2f} €")
        
        st.success(f"✅ {d['msg']}")
        
        # Tabla de partidas para el portfolio
        df = pd.DataFrame({
            "Partida": ["Instalación Base", "Ampliación Sector CETA (Detectado por UniMatch)"],
            "Cantidad": [1, d['diff']],
            "Precio Unit.": [4500, 75],
            "Subtotal": [4500, d['extra']]
        })
        st.table(df)
    else:
        st.info("No se han detectado variaciones aún. Usa el botón superior para auditar los planos.")

if __name__ == "__main__":
    main()
