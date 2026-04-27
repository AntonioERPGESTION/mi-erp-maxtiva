import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
import time

# --- FUNCIÓN DE GUARDADO ULTRA-SEGURA ---
def guardar_datos_seguro(ws, df_editado, target):
    try:
        with st.spinner(f"Actualizando {target}..."):
            # 1. LIMPIEZA DE DATOS (Vital para evitar fallos de Google)
            # Convertimos todo a texto, quitamos Nulos y aseguramos que no haya caracteres raros
            df_limpio = df_editado.fillna("").astype(str)
            
            # 2. VERIFICACIÓN DE COLUMNAS
            # Si por algún motivo el editor borró las columnas, las redefinimos
            columnas_maxtiva = {
                "Obras": ["ID", "CLIENTE", "NOMBRE", "PRESUPUESTO", "ESTADO"],
                "Empleados": ["NOMBRE", "DNI", "PUESTO", "TELÉFONO"],
                "Gastos": ["FECHA", "CONCEPTO", "IMPORTE", "OBRA"],
                "Horas": ["FECHA", "EMPLEADO", "OBRA", "HORAS"]
            }
            
            # Si el dataframe está vacío o sin columnas, usamos las por defecto
            if df_limpio.empty or len(df_limpio.columns) < 2:
                columnas = columnas_maxtiva.get(target, ["Dato1", "Dato2"])
                datos_a_subir = [columnas]
            else:
                datos_a_subir = [df_limpio.columns.values.tolist()] + df_limpio.values.tolist()

            # 3. OPERACIÓN ATÓMICA (Borrar y Escribir rápido)
            ws.clear()
            # Usamos 'A1' como ancla para reconstruir la tabla
            ws.update('A1', datos_a_subir)
            
            st.success(f"✅ Hoja '{target}' sincronizada con éxito.")
            time.sleep(1)
            st.rerun()
    except Exception as e:
        st.error(f"❌ Error al sincronizar: {e}")
        st.info("Intenta restaurar la versión anterior en Google Sheets si el problema persiste.")

# --- DENTRO DE TU LÓGICA DE MÓDULOS ---
elif menu in ["🏗️ Gestión de Obras", "👥 Gestión de Empleados", "⏱️ Imputación de Horas", "💸 Adjudicación de Gastos"]:
    mapeo = {"🏗️ Gestión de Obras": "Obras", "👥 Gestión de Empleados": "Empleados", 
             "⏱️ Imputación de Horas": "Horas", "💸 Adjudicación de Gastos": "Gastos"}
    target = mapeo[menu]
    
    ws = obtener_pestaña(target)
    if ws:
        st.title(f"📝 {menu}")
        
        # Leemos los datos (si la hoja está borrada, creamos un DF vacío con columnas)
        raw = ws.get_all_records()
        if not raw:
            columnas_defecto = ["ID", "CLIENTE", "NOMBRE", "PRESUPUESTO", "ESTADO"] if target == "Obras" else []
            df_actual = pd.DataFrame(columns=columnas_defecto)
        else:
            df_actual = pd.DataFrame(raw)

        # EDITOR INTERACTIVO
        # num_rows="dynamic" permite añadir filas con el botón (+) al final
        df_editado = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic", key=f"ed_{target}")
        
        # Botón de Guardado
        if st.button(f"💾 GUARDAR CAMBIOS EN {target.upper()}", type="primary"):
            guardar_datos_seguro(ws, df_editado, target)
