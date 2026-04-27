# --- LÓGICA DE MÓDULOS (Alineación corregida) ---

# 1. DASHBOARD
if menu == "📊 Dashboard General":
    st.title("📊 Resumen de Operaciones")
    ws_o = obtener_pestaña("Obras")
    ws_g = obtener_pestaña("Gastos")
    
    c1, c2, c3 = st.columns(3)
    if ws_o:
        df_o = pd.DataFrame(ws_o.get_all_records())
        ingresos = pd.to_numeric(df_o['PRESUPUESTO'], errors='coerce').sum() if 'PRESUPUESTO' in df_o.columns else 0
        c1.metric("Ingresos Totales", f"{ingresos:,.2f} €")
    
    if ws_g:
        df_g = pd.DataFrame(ws_g.get_all_records())
        col_imp = [c for c in df_g.columns if c.lower() == 'importe']
        gastos = pd.to_numeric(df_g[col_imp[0]], errors='coerce').sum() if col_imp else 0
        c2.metric("Gastos Totales", f"{gastos:,.2f} €")
        if ws_o and ws_g:
            c3.metric("Margen Neto", f"{ingresos - gastos:,.2f} €")

# 2. MÓDULOS EDITABLES (Obras, Empleados, Horas, Gastos)
elif menu in ["🏗️ Gestión de Obras", "👥 Gestión de Empleados", "⏱️ Imputación de Horas", "💸 Adjudicación de Gastos"]:
    mapeo = {
        "🏗️ Gestión de Obras": "Obras",
        "👥 Gestión de Empleados": "Empleados",
        "⏱️ Imputación de Horas": "Horas",
        "💸 Adjudicación de Gastos": "Gastos"
    }
    target = mapeo[menu]
    st.title(f"📝 {menu}")
    
    ws = obtener_pestaña(target)
    if ws:
        raw = ws.get_all_records()
        # Si la hoja está vacía, forzamos columnas para que no se borren
        if not raw:
            cols_fix = {
                "Obras": ["ID", "CLIENTE", "NOMBRE", "PRESUPUESTO", "ESTADO"],
                "Empleados": ["NOMBRE", "DNI", "PUESTO", "TELÉFONO"],
                "Horas": ["FECHA", "EMPLEADO", "OBRA", "HORAS"],
                "Gastos": ["FECHA", "CONCEPTO", "IMPORTE", "OBRA"]
            }
            df_actual = pd.DataFrame(columns=cols_fix.get(target, []))
        else:
            df_actual = pd.DataFrame(raw)

        # EDITOR DE DATOS
        df_editado = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic", key=f"ed_{target}")
        
        if st.button(f"💾 GUARDAR CAMBIOS EN {target.upper()}", type="primary"):
            guardar_datos_seguro(ws, df_editado, target)
    else:
        st.error(f"Pestaña '{target}' no encontrada en el Excel.")

# 3. PEDIDOS PDF
elif menu == "📦 Pedidos y Facturas PDF":
    st.title("📦 Extractor de Pedidos")
    archivo = st.file_uploader("Subir PDF", type="pdf")
    if archivo:
        with pdfplumber.open(archivo) as pdf:
            texto = "\n".join([p.extract_text() for p in pdf.pages])
        
        importes = re.findall(r"(\d+[\.,]\d{2})", texto)
        if importes:
            st.success(f"💰 Importe detectado: {importes[-1]} €")
        
        st.subheader("Texto Extraído")
        st.text_area("Contenido:", texto, height=400)
