import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cotizador D/CLASS", layout="wide")

# --- 2. CANDADO DE SEGURIDAD (PANTALLA DE LOGIN) ---
if 'acceso_concedido' not in st.session_state:
    st.session_state.acceso_concedido = False

if not st.session_state.acceso_concedido:
    # Lo que ve el público / la competencia
    st.title("🔒 Acceso Restringido - D/CLASS")
    st.warning("Este portal es de uso exclusivo para el personal autorizado. Ingresa la credencial para continuar.")
    
    clave = st.text_input("Contraseña:", type="password")
    
    if st.button("Entrar"):
        if clave == "Dclass2026":  # <--- CAMBIA ESTA CONTRASEÑA POR LA QUE QUIERAS
            st.session_state.acceso_concedido = True
            st.rerun()
        else:
            st.error("Acceso denegado. Contraseña incorrecta.")

else:
    # --- LO QUE VE TU FAMILIA DESPUÉS DE PONER LA CLAVE ---
    st.title("Cotizador Automático - D/CLASS")

    # Memoria del carrito
    if 'lista_items' not in st.session_state:
        st.session_state.lista_items = []

    # Cargar datos
    @st.cache_data
    def cargar_datos():
        ruta_mod = "datos_cortinas.csv"
        ruta_trad = "datos_tradicionales.csv"
        
        try:
            df_mod = pd.read_csv(ruta_mod, encoding="utf-8")
        except:
            df_mod = pd.read_csv(ruta_mod, encoding="latin-1")
        df_mod['m2'] = df_mod['m2'].astype(str).str.replace('$', '', regex=False).str.replace(',', '.').str.strip()
        df_mod['m2'] = pd.to_numeric(df_mod['m2'])
        df_mod['tipo de cortina'] = df_mod['tipo de cortina'].astype(str).str.title().str.strip()
        df_mod['tipo de tela'] = df_mod['tipo de tela'].fillna('Única').astype(str).str.title().str.strip()

        try:
            df_trad = pd.read_csv(ruta_trad, encoding="utf-8")
        except:
            df_trad = pd.read_csv(ruta_trad, encoding="latin-1")
        df_trad['Precio'] = df_trad['Precio'].astype(str).str.replace('$', '', regex=False).str.replace(',', '.').str.strip()
        df_trad['Precio'] = pd.to_numeric(df_trad['Precio'])
        
        l_rieles = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'RIEL']['Producto'].tolist()
        l_visillos = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'VISILLO']['Producto'].tolist()
        l_pesadas = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'CORTINA']['Producto'].tolist()
        
        return df_mod, df_trad, l_rieles, l_visillos, l_pesadas

    df_modernas, df_trad, lista_rieles, lista_visillos, lista_pesadas = cargar_datos()

    st.header("1. Datos del Cliente")
    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Nombre del Cliente:", value="Consumidor Final")
    with col2:
        telefono = st.text_input("Teléfono:")

    st.header("2. Agregar Productos")
    tab1, tab2 = st.tabs(["Cortinas Modernas (m2)", "Cortinas Tradicionales (Metro Lineal)"])

    # -- PESTAÑA MODERNAS --
    with tab1:
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            tipos_disp = df_modernas['tipo de cortina'].unique().tolist()
            tipo_sel = st.selectbox("Modelo:", tipos_disp)
        with col_m2:
            telas_disp = df_modernas[df_modernas['tipo de cortina'] == tipo_sel]['tipo de tela'].tolist()
            tela_sel = st.selectbox("Tipo de Tela:", telas_disp)
        with col_m3:
            ancho_mod = st.number_input("Ancho (m) Modernas:", min_value=0.0, step=0.1, format="%.2f")
        with col_m4:
            alto_mod = st.number_input("Alto (m) Modernas:", min_value=0.0, step=0.1, format="%.2f")
        
        if st.button("➕ Añadir Moderna"):
            if ancho_mod > 0 and alto_mod > 0:
                area = ancho_mod * alto_mod
                nombre = f"Cortina {tipo_sel} - {tela_sel}\n(Ancho: {ancho_mod:.2f}m x Alto: {alto_mod:.2f}m)"
                precio_u = df_modernas[(df_modernas['tipo de cortina'] == tipo_sel) & (df_modernas['tipo de tela'] == tela_sel)]['m2'].values[0]
                total = area * precio_u
                
                st.session_state.lista_items.append({
                    'producto': nombre, 'medida': area, 'unidad': 'm2', 'precio_u': precio_u, 'total': total
                })
                st.success("¡Cortina añadida al carrito!")
            else:
                st.warning("Completa el Ancho y Alto.")

    # -- PESTAÑA TRADICIONALES --
    with tab2:
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            ancho_trad = st.number_input("Ancho (m) Tradicional:", min_value=0.0, step=0.1, format="%.2f")
        with col_t2:
            alto_trad = st.number_input("Alto (m) Tradicional:", min_value=0.0, step=0.1, format="%.2f")
        with col_t3:
            confec = st.selectbox("Confección:", ["Pliegue (x2.2)", "Onda Perfecta (x2.5 + $3.90/m)"])
            
        col_t4, col_t5, col_t6 = st.columns(3)
        with col_t4:
            riel_sel = st.selectbox("Riel / Sistema:", ["Ninguno"] + lista_rieles)
        with col_t5:
            visillo_sel = st.selectbox("Visillo:", ["Ninguno"] + lista_visillos)
        with col_t6:
            pesada_sel = st.selectbox("Cortina Pesada:", ["Ninguno"] + lista_pesadas)

        if st.button("➕ Añadir Tradicional"):
            if ancho_trad > 0 and alto_trad > 0:
                if riel_sel == "Ninguno" and visillo_sel == "Ninguno" and pesada_sel == "Ninguno":
                    st.warning("Selecciona al menos una tela o riel.")
                else:
                    factor_tela = 2.5 if "Onda Perfecta" in confec else 2.2
                    adicional_onda = 3.90 if "Onda Perfecta" in confec else 0.0
                    
                    num_rieles = 0
                    if visillo_sel != "Ninguno": num_rieles += 1
                    if pesada_sel != "Ninguno": num_rieles += 1
                    if num_rieles == 0 and riel_sel != "Ninguno": num_rieles = 1
                    
                    costo_ml = 0
                    detalle = f"CORTINA TRADICIONAL - {confec.split(' ')[0]}\n(Ancho: {ancho_trad:.2f}m x Alto: {alto_trad:.2f}m)"
                    
                    if riel_sel != "Ninguno":
                        p_riel = df_trad[df_trad['Producto'] == riel_sel]['Precio'].values[0]
                        costo_ml += (p_riel * num_rieles)
                        detalle += f"\n  - Riel: {riel_sel} (x{num_rieles})"
                    if visillo_sel != "Ninguno":
                        p_visillo = df_trad[df_trad['Producto'] == visillo_sel]['Precio'].values[0]
                        costo_ml += (p_visillo * factor_tela)
                        detalle += f"\n  - Visillo: {visillo_sel}"
                    if pesada_sel != "Ninguno":
                        p_pesada = df_trad[df_trad['Producto'] == pesada_sel]['Precio'].values[0]
                        costo_ml += (p_pesada * factor_tela)
                        detalle += f"\n  - Pesada: {pesada_sel}"
                    if adicional_onda > 0 and (visillo_sel != "Ninguno" or pesada_sel != "Ninguno"):
                        costo_ml += adicional_onda
                        
                    total_calculado = costo_ml * ancho_trad
                    
                    st.session_state.lista_items.append({
                        'producto': detalle, 'medida': ancho_trad, 'unidad': 'ml', 'precio_u': costo_ml, 'total': total_calculado
                    })
                    st.success("¡Cortina tradicional añadida al carrito!")
            else:
                st.warning("Completa el Ancho y Alto.")

    # --- 5. CARRITO Y PDF ---
    st.header("3. Resumen de Cotización")
    if len(st.session_state.lista_items) > 0:
        df_carrito = pd.DataFrame(st.session_state.lista_items)
        df_mostrar = df_carrito.copy()
        df_mostrar['precio_u'] = df_mostrar['precio_u'].apply(lambda x: f"${x:.2f}")
        df_mostrar['total'] = df_mostrar['total'].apply(lambda x: f"${x:.2f}")
        st.table(df_mostrar[['producto', 'medida', 'unidad', 'precio_u', 'total']])
        
        if st.button("🗑️ Vaciar Cotización"):
            st.session_state.lista_items = []
            st.rerun()

        class CotizacionPDF(FPDF):
            def header(self):
                try:
                    self.image("logo_dclass_limpio.jpg", x=150, y=10, w=50)
                    self.ln(15) 
                except:
                    self.set_font('Arial', 'B', 20)
                    self.cell(0, 10, 'D/CLASS', 0, 1, 'R')
                    self.ln(10)

        pdf = CotizacionPDF()
        pdf.add_page()
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        num_cot = f"{datetime.now().strftime('%Y%m%d-%H%M')}"
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(30, 6, 'Fecha:', 0, 0); pdf.set_font('Arial', '', 10); pdf.cell(80, 6, fecha_actual, 0, 0)
        pdf.set_font('Arial', 'B', 10); pdf.cell(40, 6, 'Cotizacion No.', 0, 0); pdf.set_font('Arial', '', 10); pdf.cell(40, 6, num_cot, 0, 1)
        pdf.set_font('Arial', 'B', 10); pdf.cell(30, 6, 'Cliente:', 0, 0); pdf.set_font('Arial', '', 10); pdf.cell(80, 6, cliente, 0, 1)
        pdf.set_font('Arial', 'B', 10); pdf.cell(30, 6, 'Telefono:', 0, 0); pdf.set_font('Arial', '', 10); pdf.cell(80, 6, telefono, 0, 1)
        pdf.ln(10)
        
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(20, 8, 'CANTIDAD', 1, 0, 'C', 1); pdf.cell(10, 8, 'U', 1, 0, 'C', 1)
        pdf.cell(130, 8, 'DETALLE', 1, 0, 'C', 1); pdf.cell(30, 8, 'P. TOTAL', 1, 1, 'C', 1)
        
        pdf.set_font('Arial', '', 8)
        subtotal = 0
        for item in st.session_state.lista_items:
            start_y = pdf.get_y()
            pdf.set_xy(40, start_y); pdf.multi_cell(130, 5, item['producto'], 0, 'L')
            altura_fila = pdf.get_y() - start_y
            pdf.set_xy(10, start_y); pdf.cell(20, altura_fila, f"{item['medida']:.2f}", 'LR', 0, 'C')
            pdf.cell(10, altura_fila, item['unidad'], 'LR', 0, 'C')
            pdf.set_xy(170, start_y); pdf.cell(30, altura_fila, f"${item['total']:.2f}", 'LR', 1, 'C')
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            subtotal += item['total']
        
        iva = subtotal * 0.15
        total_final = subtotal + iva
        total_contado = total_final - (total_final * 0.10)
        
        pdf.ln(5); pdf.set_font('Arial', 'B', 9)
        pdf.cell(130, 6, '', 0, 0); pdf.cell(30, 6, 'SUMAN', 1, 0, 'R', 1); pdf.cell(30, 6, f"${subtotal:.2f}", 1, 1, 'R')
        pdf.cell(130, 6, '', 0, 0); pdf.cell(30, 6, '15% IVA.', 1, 0, 'R', 1); pdf.cell(30, 6, f"${iva:.2f}", 1, 1, 'R')
        pdf.cell(130, 6, '', 0, 0); pdf.cell(30, 6, 'TOTAL $.', 1, 0, 'R', 1); pdf.cell(30, 6, f"${total_final:.2f}", 1, 1, 'R')
        pdf.set_text_color(0, 100, 0) 
        pdf.cell(130, 6, '', 0, 0); pdf.cell(30, 6, 'DE CONTADO', 1, 0, 'R', 1); pdf.cell(30, 6, f"${total_contado:.2f}", 1, 1, 'R')
        
        pdf_archivo = "cotizacion_temporal.pdf"
        pdf.output(pdf_archivo)
        
        with open(pdf_archivo, "rb") as pdf_file:
            PDFbyte = pdf_file.read()
        
        st.download_button(
            label="📄 DESCARGAR COTIZACIÓN EN PDF",
            data=PDFbyte,
            file_name=f"Cotizacion_{cliente.replace(' ', '_')}.pdf",
            mime='application/octet-stream'
        )
    else:
        st.info("Agrega productos en las pestañas de arriba para comenzar tu cotización.")