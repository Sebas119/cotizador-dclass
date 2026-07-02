import streamlit as st
import pandas as pd
import json
import os
import glob
from fpdf import FPDF
from datetime import datetime
import urllib.parse
from PIL import Image

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Cotizador D/CLASS & CLASSICA", layout="wide")

ARCHIVO_HISTORICO = "historico.json"
ARCHIVO_CONFIG = "config.json"

# --- 2. FUNCIONES BASE ---
def cargar_json(archivo):
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f: return json.load(f)
        except: return [] if archivo == ARCHIVO_HISTORICO else {}
    return [] if archivo == ARCHIVO_HISTORICO else {}

def guardar_json(archivo, datos):
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4)

def buscar_logo(prefijo):
    archivos = glob.glob(f"{prefijo}.*")
    for arch in archivos:
        if arch.lower().endswith(('.png', '.jpg', '.jpeg')): return arch
    return None

def fecha_espanol():
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    hoy = datetime.now()
    return f"{hoy.day:02d} de {meses[hoy.month - 1]} de {hoy.year}"

if 'acceso_concedido' not in st.session_state: st.session_state.acceso_concedido = False
if 'lista_items' not in st.session_state: st.session_state.lista_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {"nombre": "", "telefono": "", "direccion": "", "asesora": "Celmira Zapata"}

# --- 3. LOGIN ---
if not st.session_state.acceso_concedido:
    st.title("🔒 Acceso Restringido")
    clave = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        if clave == "Dclass2026": 
            st.session_state.acceso_concedido = True
            st.rerun()
        else: st.error("Acceso denegado.")
else:
    # --- 4. CARGAR EXCEL ---
    @st.cache_data
    def cargar_excel():
        try: df_mod = pd.read_csv("datos_cortinas.csv", encoding="utf-8")
        except: df_mod = pd.read_csv("datos_cortinas.csv", encoding="latin-1")
        df_mod['m2'] = pd.to_numeric(df_mod['m2'].astype(str).str.replace('$', '', regex=False).str.replace(',', '.').str.strip())
        df_mod['tipo de cortina'] = df_mod['tipo de cortina'].astype(str).str.title().str.strip()
        df_mod['tipo de tela'] = df_mod['tipo de tela'].fillna('Única').astype(str).str.title().str.strip()

        try: df_trad = pd.read_csv("datos_tradicionales.csv", encoding="utf-8")
        except: df_trad = pd.read_csv("datos_tradicionales.csv", encoding="latin-1")
        df_trad['Precio'] = pd.to_numeric(df_trad['Precio'].astype(str).str.replace('$', '', regex=False).str.replace(',', '.').str.strip())
        
        return df_mod, df_trad

    try:
        df_modernas, df_trad = cargar_excel()
        lista_rieles = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'RIEL']['Producto'].tolist()
        lista_visillos = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'VISILLO']['Producto'].tolist()
        lista_pesadas = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'CORTINA']['Producto'].tolist()
    except:
        st.error("Error cargando los CSV.")
        st.stop()

    menu = st.sidebar.radio("Navegación", ["📝 Cotizar", "📂 Histórico", "⚙️ Configurar"])
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.acceso_concedido = False
        st.rerun()

    config_data = cargar_json(ARCHIVO_CONFIG)
    telf_empresa = config_data.get("telf_classica", "(593-2) 2418390")
    wa_empresa = config_data.get("wa_asesores", "0992445061")
    dir_empresa = config_data.get("direccion", "Av. 6 de Diciembre N46-274")

    # ==========================================
    #             MÓDULO: COTIZAR
    # ==========================================
    if menu == "📝 Cotizar":
        st.title("Cotizador de Cortinas")
        
        st.subheader("Datos del cliente")
        c1, c2 = st.columns(2)
        st.session_state.cliente_actual["nombre"] = c1.text_input("Nombre completo", value=st.session_state.cliente_actual["nombre"])
        st.session_state.cliente_actual["telefono"] = c1.text_input("Teléfono", value=st.session_state.cliente_actual["telefono"])
        st.session_state.cliente_actual["direccion"] = c2.text_input("Dirección", value=st.session_state.cliente_actual["direccion"])
        st.session_state.cliente_actual["asesora"] = c2.selectbox("Asesora que firma", ["Andrea Cóndor", "Celmira Zapata", "Verónica Tapia"], index=1)

        st.markdown("---")
        st.subheader("Agregar cortina")
        
        ambiente = st.text_input("Ambiente (ej: GENERAL, Dormitorio master)", placeholder="GENERAL")
        cantidad = st.number_input("Cantidad de cortinas", min_value=1, value=1, step=1)
        
        t1, t2 = st.tabs(["Modernas", "Tradicionales"])
        with t1:
            cm1, cm2, cm3, cm4 = st.columns(4)
            tipo_sel = cm1.selectbox("Modelo:", df_modernas['tipo de cortina'].unique().tolist())
            tela_sel = cm2.selectbox("Tipo de Tela:", df_modernas[df_modernas['tipo de cortina'] == tipo_sel]['tipo de tela'].tolist())
            ancho_mod = cm3.number_input("Ancho (m) Mod:", min_value=0.0, step=0.1)
            alto_mod = cm4.number_input("Alto (m) Mod:", min_value=0.0, step=0.1)
            
            if st.button("➕ Añadir Moderna"):
                if ancho_mod > 0 and alto_mod > 0 and ambiente:
                    area = ancho_mod * alto_mod
                    precio_u = df_modernas[(df_modernas['tipo de cortina'] == tipo_sel) & (df_modernas['tipo de tela'] == tela_sel)]['m2'].values[0]
                    total_item = (area * precio_u) * cantidad
                    st.session_state.lista_items.append({
                        "ambiente": ambiente, "cantidad": cantidad, "medida": area, "unidad": "m²",
                        "detalle": f"{tipo_sel} - {tela_sel} | {ancho_mod}m x {alto_mod}m = {area:.2f}m²", 
                        "detalle_corto": f"{tipo_sel} - {tela_sel}", "precio_u": precio_u, "total": total_item
                    })
                    st.success("Añadido al carrito")

        with t2:
            ct1, ct2, ct3 = st.columns(3)
            ancho_trad = ct1.number_input("Ancho (m) Trad:", min_value=0.0, step=0.1)
            alto_trad = ct2.number_input("Alto (m) Trad:", min_value=0.0, step=0.1)
            confec = ct3.selectbox("Confección:", ["Pliegue (x2.2)", "Onda Perfecta (x2.5 + $3.90/m)"])
            ct4, ct5, ct6 = st.columns(3)
            riel_sel = ct4.selectbox("Riel:", ["Ninguno"] + lista_rieles)
            visillo_sel = ct5.selectbox("Visillo:", ["Ninguno"] + lista_visillos)
            pesada_sel = ct6.selectbox("Pesada:", ["Ninguno"] + lista_pesadas)
            
            if st.button("➕ Añadir Tradicional"):
                if ancho_trad > 0 and alto_trad > 0 and ambiente:
                    factor = 2.5 if "Onda Perfecta" in confec else 2.2
                    extra = 3.90 if "Onda Perfecta" in confec else 0.0
                    costo_ml = 0
                    if riel_sel != "Ninguno": costo_ml += df_trad[df_trad['Producto']==riel_sel]['Precio'].values[0]
                    if visillo_sel != "Ninguno": costo_ml += (df_trad[df_trad['Producto']==visillo_sel]['Precio'].values[0] * factor)
                    if pesada_sel != "Ninguno": costo_ml += (df_trad[df_trad['Producto']==pesada_sel]['Precio'].values[0] * factor)
                    if extra > 0 and (visillo_sel != "Ninguno" or pesada_sel != "Ninguno"): costo_ml += extra
                    
                    total_item = (costo_ml * ancho_trad) * cantidad
                    st.session_state.lista_items.append({
                        "ambiente": ambiente, "cantidad": cantidad, "medida": ancho_trad, "unidad": "ml",
                        "detalle": f"TRAD. ({confec.split(' ')[0]}) | {ancho_trad}m x {alto_trad}m", 
                        "detalle_corto": f"TRAD. ({confec.split(' ')[0]})", "precio_u": costo_ml, "total": total_item
                    })
                    st.success("Añadido al carrito")

        st.markdown("---")
        subtotal = sum(it['total'] for it in st.session_state.lista_items)
        
        for i, it in enumerate(st.session_state.lista_items):
            c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
            c1.write(f"🏠 **{it['ambiente']}**")
            c2.write(it['detalle'])
            c3.write(f"${it['total']:.2f}")
            if c4.button("🗑️", key=f"del_{i}"): st.session_state.lista_items.pop(i); st.rerun()
            
        descuento_pct = st.slider("Descuento (Contado %)", 0, 50, 10)
        dias_entrega = st.selectbox("Días de entrega", ["3 días laborables", "5 días laborables", "8 días laborables"])
        
        iva = subtotal * 0.15
        total_con_iva = subtotal + iva
        monto_descuento = total_con_iva * (descuento_pct / 100)
        total_contado = total_con_iva - monto_descuento

        st.info(f"Subtotal: ${subtotal:.2f} | IVA: ${iva:.2f} | TOTAL: ${total_con_iva:.2f}")
        st.success(f"**CONTADO: ${total_contado:.2f}**")

        ca1, ca2, ca3 = st.columns(3)
        if ca1.button("💾 Guardar Histórico"):
            if st.session_state.lista_items and st.session_state.cliente_actual["nombre"]:
                historial = cargar_json(ARCHIVO_HISTORICO)
                codigo_cot = f"PG {datetime.now().strftime('%y-%H%M%S')}"
                historial.append({
                    "codigo": codigo_cot, "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "cliente": st.session_state.cliente_actual, "items": st.session_state.lista_items,
                    "subtotal": subtotal, "iva": iva, "total": total_con_iva,
                    "descuento": descuento_pct, "contado": total_contado, "dias": dias_entrega
                })
                guardar_json(ARCHIVO_HISTORICO, historial)
                st.success("Guardado!")

        mensaje_wa = f"*COTIZACIÓN*\nCliente: {st.session_state.cliente_actual['nombre']}\n*Resumen:*\n"
        for it in st.session_state.lista_items: mensaje_wa += f"• {it['ambiente']}: {it['detalle_corto']} -> ${it['total']:.2f}\n"
        mensaje_wa += f"*SUBTOTAL:* ${subtotal:.2f}\n*IVA (15%):* ${iva:.2f}\n*TOTAL CONTADO:* ${total_contado:.2f}\n_Entrega: {dias_entrega}_"
        link_wa = f"https://wa.me/?text={urllib.parse.quote(mensaje_wa)}"
        ca2.markdown(f'<a href="{link_wa}" target="_blank"><button style="width:100%; padding:8px; background-color:#25D366; color:white; border:none; border-radius:5px;">📱 Enviar por WhatsApp</button></a>', unsafe_allow_html=True)

        # 3. GENERAR PDF NIVEL PROFESIONAL (Basado en PG 26-1043)
        if ca3.button("📄 Generar PDF"):
            if not st.session_state.lista_items:
                st.error("Agrega productos.")
            else:
                class PDFPro(FPDF):
                    def footer(self):
                        self.set_y(-15)
                        self.set_font('Arial', 'I', 8)
                        self.cell(0, 10, 'Esta proforma tiene validez de 15 dias desde la fecha de emision  ·  Gracias por su preferencia', 0, 0, 'C')

                pdf = PDFPro()
                pdf.add_page()
                
                # --- Encabezado Corporativo ---
                def estampar_logo_proporcional(prefijo, x, y, w):
                    ruta = buscar_logo(prefijo)
                    if ruta:
                        try:
                            img = Image.open(ruta)
                            if img.mode != 'RGB': img = img.convert('RGB')
                            img.save(f"temp_{prefijo}.jpg", "JPEG")
                            # Al mandar h=0, FPDF calcula el alto proporcionalmente
                            pdf.image(f"temp_{prefijo}.jpg", x, y, w=w) 
                        except: pass

                estampar_logo_proporcional("logo_classica", 10, 10, 45)
                estampar_logo_proporcional("logo_dclass", 155, 10, 45)

                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 5, 'CLASSICA DECORACIONES', 0, 1, 'C')
                pdf.set_font('Arial', '', 9)
                pdf.cell(0, 5, 'Cortinas · Decoracion · Persianas · Domotica', 0, 1, 'C')
                pdf.ln(2)
                pdf.set_font('Arial', '', 8)
                pdf.cell(0, 4, f'Showroom: {dir_empresa}', 0, 1, 'C')
                pdf.cell(0, 4, f'Telfs.: {telf_empresa}  ·  WhatsApp: {wa_empresa}', 0, 1, 'C')
                pdf.cell(0, 4, 'classica@classica-decoraciones.com  ·  www.classica-decoraciones.com', 0, 1, 'C')
                pdf.cell(0, 4, 'info@dclass.com.ec  ·  www.dclass.com.ec', 0, 1, 'C')

                pdf.ln(3)
                pdf.set_draw_color(200, 200, 200)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)

                # --- Datos Proforma y Cliente ---
                codigo_pdf = f"PG {datetime.now().strftime('%y-%H%M')}"
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(100, 5, f'PROFORMA N° {codigo_pdf}', 0, 0, 'L')
                pdf.set_font('Arial', '', 9)
                pdf.cell(90, 5, f'Quito, {fecha_espanol()}', 0, 1, 'R')
                pdf.ln(2)

                pdf.set_fill_color(240, 240, 240)
                pdf.set_font('Arial', 'B', 8)
                pdf.cell(100, 5, 'CLIENTE', 0, 0, 'L', 1)
                pdf.cell(90, 5, 'TELEFONO', 0, 1, 'L', 1)
                pdf.set_font('Arial', '', 9)
                pdf.cell(100, 6, st.session_state.cliente_actual['nombre'], 0, 0, 'L')
                pdf.cell(90, 6, st.session_state.cliente_actual['telefono'], 0, 1, 'L')

                pdf.set_font('Arial', 'B', 8)
                pdf.cell(190, 5, 'DIRECCION', 0, 1, 'L', 1)
                pdf.set_font('Arial', '', 9)
                pdf.cell(190, 6, st.session_state.cliente_actual['direccion'], 0, 1, 'L')
                pdf.ln(5)

                # --- Tabla de Productos ---
                pdf.set_font('Arial', 'B', 8)
                pdf.set_fill_color(230, 230, 230)
                pdf.cell(15, 6, 'CANT.', 0, 0, 'C', 1)
                pdf.cell(15, 6, 'U.', 0, 0, 'C', 1)
                pdf.cell(100, 6, 'DETALLE', 0, 0, 'L', 1)
                pdf.cell(30, 6, 'P. UNITARIO', 0, 0, 'C', 1)
                pdf.cell(30, 6, 'P. TOTAL', 0, 1, 'C', 1)

                # Agrupador por Ambientes (¡El Toque de Oro!)
                ambientes_dict = {}
                for it in st.session_state.lista_items:
                    amb = it['ambiente'].upper()
                    if amb not in ambientes_dict: ambientes_dict[amb] = []
                    ambientes_dict[amb].append(it)

                for amb, items in ambientes_dict.items():
                    pdf.set_font('Arial', 'B', 8)
                    pdf.set_fill_color(245, 245, 245)
                    pdf.cell(190, 6, amb, 0, 1, 'L', 1) # Fila sombreada del ambiente
                    
                    pdf.set_font('Arial', '', 8)
                    for it in items:
                        cant_medida = it['medida'] * it['cantidad']
                        pdf.cell(15, 6, f"{cant_medida:.2f}", 0, 0, 'C')
                        pdf.cell(15, 6, it['unidad'], 0, 0, 'C')
                        pdf.cell(100, 6, it['detalle_corto'][:60], 0, 0, 'L')
                        pdf.cell(30, 6, f"${it['precio_u']:.2f}", 0, 0, 'C')
                        pdf.cell(30, 6, f"${it['total']:.2f}", 0, 1, 'C')

                # --- Totales (Derecha) ---
                pdf.ln(5)
                pdf.set_font('Arial', '', 9)
                pdf.cell(130, 5, '', 0, 0); pdf.cell(30, 5, 'Suma sin IVA', 0, 0, 'R'); pdf.cell(30, 5, f"${subtotal:.2f}", 0, 1, 'R')
                pdf.cell(130, 5, '', 0, 0); pdf.cell(30, 5, 'IVA 15%', 0, 0, 'R'); pdf.cell(30, 5, f"${iva:.2f}", 0, 1, 'R')
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(130, 5, '', 0, 0); pdf.cell(30, 5, 'TOTAL', 0, 0, 'R'); pdf.cell(30, 5, f"${total_con_iva:.2f}", 0, 1, 'R')
                
                pdf.set_font('Arial', '', 9)
                pdf.cell(130, 5, '', 0, 0); pdf.cell(30, 5, f'Descuento ({descuento_pct}%)', 0, 0, 'R'); pdf.cell(30, 5, f"-${monto_descuento:.2f}", 0, 1, 'R')
                
                pdf.set_font('Arial', 'B', 9)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(130, 6, '', 0, 0); pdf.cell(30, 6, 'VALOR CONTADO', 0, 0, 'R', 1); pdf.cell(30, 6, f"${total_contado:.2f}", 0, 1, 'R', 1)

                # --- Pie de página y Firma ---
                pdf.ln(10)
                y_firma = pdf.get_y()

                pdf.set_font('Arial', 'B', 8)
                pdf.cell(60, 5, 'TIEMPO DE ENTREGA', 0, 1, 'L')
                pdf.set_font('Arial', '', 8)
                pdf.cell(60, 4, dias_entrega, 0, 1, 'L')
                pdf.set_text_color(100, 100, 100)
                pdf.cell(60, 4, 'A partir de la confirmacion del anticipo', 0, 1, 'L')
                pdf.cell(60, 4, 'y aprobacion de la cotizacion.', 0, 1, 'L')

                pdf.set_xy(80, y_firma)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', 'B', 8)
                pdf.cell(60, 5, 'FORMAS DE PAGO', 0, 1, 'L')
                pdf.set_x(80)
                pdf.set_font('Arial', '', 8)
                pdf.cell(60, 4, '3 a 6 meses sin interes con tarjeta de credito', 0, 1, 'L')
                pdf.set_x(80); pdf.cell(60, 4, 'Diferido hasta 24 meses con interes', 0, 1, 'L')
                pdf.set_x(80); pdf.cell(60, 4, 'Contado: 50% anticipo, saldo contra entrega', 0, 1, 'L')

                # Firma (Asesora Dinámica)
                pdf.set_xy(140, y_firma + 12)
                pdf.set_draw_color(150, 150, 150)
                pdf.line(145, pdf.get_y(), 195, pdf.get_y())
                pdf.ln(2)
                pdf.set_x(140)
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(60, 4, st.session_state.cliente_actual['asesora'], 0, 1, 'C')
                pdf.set_x(140)
                pdf.set_font('Arial', '', 8)
                pdf.cell(60, 4, 'Asesora de ventas', 0, 1, 'C')
                pdf.set_x(140)
                pdf.cell(60, 4, 'CLASSICA Decoraciones', 0, 1, 'C')

                nom_cl = st.session_state.cliente_actual['nombre'].strip().replace(" ", "_")
                nom_arch = f"Cotizacion_{nom_cl}_{datetime.now().strftime('%Y%m%d')}.pdf"
                pdf.output("cotizacion_final.pdf")
                with open("cotizacion_final.pdf", "rb") as f:
                    st.download_button("Descargar PDF", f, file_name=nom_arch)

    # ==========================================
    #             MÓDULO: HISTÓRICO Y CONFIG
    # ==========================================
    elif menu == "📂 Histórico":
        st.title("Historial de Cotizaciones")
        historial = cargar_json(ARCHIVO_HISTORICO)
        if not historial: st.info("Sin datos.")
        else:
            for cot in reversed(historial):
                with st.expander(f"{cot['codigo']} | {cot['cliente']['nombre']} - Total: ${cot['contado']:.2f}"):
                    if st.button("Cargar esta cotización", key=f"btn_{cot['codigo']}"):
                        st.session_state.cliente_actual = cot['cliente']
                        st.session_state.lista_items = cot['items']
                        st.success("Cargada en la pestaña 'Cotizar'.")

    elif menu == "⚙️ Configurar":
        st.title("Configuración de la Empresa")
        t1 = st.text_input("Teléfonos", value=config_data.get("telf_classica", ""))
        t2 = st.text_input("WhatsApp Asesores", value=config_data.get("wa_asesores", ""))
        d1 = st.text_input("Dirección Showroom", value=config_data.get("direccion", ""))
        if st.button("Guardar"):
            guardar_json(ARCHIVO_CONFIG, {"telf_classica": t1, "wa_asesores": t2, "direccion": d1})
            st.success("Guardado!")
