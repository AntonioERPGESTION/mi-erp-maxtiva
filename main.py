import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os, sys, time

# --- CONFIGURACION VISUAL ---
st.set_page_config(page_title="SISTEMA ERP", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    [data-testid="stMetricValue"] { font-size: 26px; color: #004a99; font-weight: bold; }
    div.stButton > button:first-child {
        background-color: #004a99; color: white; border-radius: 8px; height: 3em; width: 100%;
        font-weight: bold; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

def resource_path(r):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, r)

URL = "https://docs.google.com/spreadsheets/d/1dJWM1dBQ5DfWQBIRKHja_YoMH_JeNXVu0ruOzlHQ3BM/edit"

@st.cache_resource
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(resource_path("llave.json"), scope)
    return gspread.authorize(creds).open_by_url(URL)

if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': None, 'user': None})

# --- LOGICA DE ACCESO ---
if not st.session_state['autenticado']:
    st.markdown("<h1 style='text-align: center;'>🔐 ACCESO ERP</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contrasena", type="password")
            if st.form_submit_button("ENTRAR"):
                try:
                    sh = conectar()
                    users = pd.DataFrame(sh.worksheet("Usuarios").get_all_records())
                    match = users[(users['Usuario'] == u) & (users['Password'].astype(str) == p)]
                    if not match.empty:
                        st.session_state.update({'autenticado': True, 'rol': match.iloc[0]['Rol'], 'user': u})
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas")
                except Exception as e:
                    st.error(f"Error de conexion: {e}")
else:
    # --- INTERFAZ PRINCIPAL (Alineacion protegida) ---
    try:
        sh = conectar()
        rol = st.session_state['rol']
        todas_las_hojas = [h.title for h in sh.worksheets() if h.title != "Usuarios"]
        
        with st.sidebar:
            st.markdown("<h3 style='text-align: center;'>EMPRESAS</h3>", unsafe_allow_html=True)
            c_l = st.columns(3)
            for i, l in enumerate(["logo_maxtiva.png", "logo_ceta.png", "logo_ipalux.png"]):
                if os.path.exists(resource_path(l)):
                    c_l[i].image(resource_path(l))
            
            st.divider()
            st.write(f"👤 **{st.session_state['user']}** | {rol}")
            st.divider()

            if rol == "Admin":
                menu = st.radio("MODULOS MAESTROS", ["📊 DASHBOARD"] + todas_las_hojas)
            else:
                permitidos = ["Reportes", "Agenda", "Incidencias"]
                opciones = [h for h in todas_las_hojas if h in permitidos]
                menu = st.radio("MENU EMPLEADO", ["📊 DASHBOARD"] + opciones)
            
            st.divider()
            if st.button("Cerrar Sesion"):
                st.session_state.update({'autenticado': False, 'rol': None, 'user': None})
                st.rerun()

        # --- CONTENIDO ---
        if menu == "📊 DASHBOARD":
            st.title(f"🚀 Panel de Control - {st.session_state['user']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Empresas", "3 Activas")
            c2.metric("Modulos", len(todas_las_hojas))
            c3.metric("Nube", "Sincronizada")
            st.success(f"Sesion activa como {rol}. Seleccione un modulo en el menu lateral.")
        else:
            st.title(f"📂 Modulo: {menu}")
            ws = sh.worksheet(menu)
            data = ws.get_all_values()
            df = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 1 else pd.DataFrame(columns=data[0] if data else [])

            if rol == "Admin":
                ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                if st.button(f"💾 GUARDAR CAMBIOS EN {menu.upper()}"):
                    ws.clear()
                    ws.update([ed.columns.tolist()] + ed.values.tolist())
                    st.balloons()
                    st.toast("Datos guardados")
                    time.sleep(1)
                    st.rerun()
            else:
                st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Error en el modulo {menu}: {e}")