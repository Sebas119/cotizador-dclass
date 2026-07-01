import streamlit as st
import pandas as pd
import json
import os
import glob
from fpdf import FPDF
from datetime import datetime
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Cotizador D/CLASS & CLASSICA", layout="wide")

ARCHIVO_HISTORICO = "historico.json"
ARCHIVO_CONFIG = "config.json"

# --- 2. FUNCIONES BASE ---
def cargar_json(archivo):
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return [] if archivo == ARCHIVO_HISTORICO else {}
    return [] if archivo == ARCHIVO_HISTORICO else {}

def guardar_json(archivo, datos):
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4)

def buscar_logo(prefijo):
    # Busca cualquier archivo que empiece con el prefijo, sin importar la extensión
    archivos = glob.glob(f"{prefijo}.*")
    for arch in archivos:
        if arch.lower().endswith(('.png', '.jpg', '.jpeg')):
            return arch
    return None

# Inicializar estados
if 'acceso_concedido' not in st.session_state: st.session_state.acceso_concedido = False
if 'lista_items' not in st.session_state: st.session_state.lista_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {"nombre": "", "telefono": "", "direccion": "", "asesora": "Celmira Zapata"}

# --- 3. LOGIN ---
if not st.session_state.acceso_concedido:
    st.title("🔒 Acceso Restringido - Sistema de Ventas")
    clave = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        if clave == "Dclass2026": 
            st.session_state.acceso_concedido = True
            st.rerun()
        else:
            st.error("Acceso denegado.")
else:
    # --- 4. CARGAR EXCEL (CON ARMADURA) ---
    @st.cache_data
    def cargar_excel():
        try:
            df_mod = pd.read_csv("datos_cortinas.csv", encoding="utf-8")
        except:
            df_mod = pd.read_csv("datos_cortinas.csv", encoding="latin-1")
            
        df_mod['m2'] = pd.to_numeric(df_mod['m2'].astype(str).str.replace('$', '', regex=False).str.replace(',', '.').str.strip())
        df_mod['tipo de cortina'] = df_mod['tipo de cortina'].astype(str).str.title().str.strip()
        df_mod['tipo de tela'] = df_mod['tipo de tela'].fillna('Única').astype(str).str.title().str.strip()

        try:
            df_trad = pd.read_csv("datos_tradicionales.csv", encoding="utf-8")
        except:
            df_trad = pd.read_csv("datos_tradicionales.csv", encoding="latin-1")
            
        df_trad['Precio'] = pd.to_numeric(df_trad['Precio'].astype(str).str.replace('$', '', regex=False).str.replace(',', '.').str.strip())
        return df_mod, df_trad

    try:
        df_modernas, df_trad = cargar_excel()
        lista_rieles = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'RIEL']['Producto'].tolist()
        lista_visillos = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'VISILLO']['Producto'].tolist()
        lista_pesadas = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'CORTINA']['Producto'].tolist()
    except Exception as e:
        st.error("Error cargando los archivos CSV. Verifica que estén en la carpeta de GitHub.")
        st.stop()

    # --- 5. NAVEGACIÓN ---
    menu = st.sidebar.radio("Navegación", ["📝 Cotizar", "📂 Histórico", "⚙️ Configurar"])
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.acceso_concedido = False
        st.rerun()

    # ==========================================
    #             MÓDULO: COTIZAR
    # ==========================================
    if menu == "📝 Cotizar":
        st.title("Cotizador de Cortinas")
        
        st.subheader("Datos del cliente")
        with st.container():
            c1, c2 = st.columns(2)
            st.session_state.cliente_actual["nombre"] = c1.text_input("Nombre completo", value=st.session_state.cliente_actual["nombre"])
            st.session_state.cliente_actual["telefono"] = c1.text_input("Teléfono", value=st.session_state.cliente_actual["telefono"])
            st.session_state.cliente_actual["direccion"] = c2.text_input("Dirección / Sector", value=st.session_state.cliente_actual["direccion"])
            st.session_state.cliente_actual["asesora"] = c2.selectbox("Asesora que firma", ["Andrea Cóndor", "Celmira Zapata", "Verónica Tapia"], index=1)

        st.markdown("---")
        st.subheader("Agregar cortina / ítem")
        
        ambiente = st.text_input("Ambiente (ej: Sala comedor, Dormitorio master)", placeholder="Dormitorio...")
        cantidad = st.number_input("Cantidad de cortinas con esta misma medida", min_value=1, value=1, step=1)
        
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
                    detalle = f"{tipo_sel} - {tela_sel} | {ancho_mod}m x {alto_mod}m = {area:.2f}m²"
                    
                    st.session_state.lista_items.append({
                        "ambiente": ambiente, "cantidad": cantidad, "detalle": detalle, 
                        "precio_u": precio_u, "total": total_item
                    })
                    st.success("Añadido al carrito")
                else:
                    st.warning("Falta completar Ancho, Alto o el Ambiente.")

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
                    extra_onda = 3.90 if "Onda Perfecta" in confec else 0.0
                    costo_ml = 0
                    desc = f"TRAD. ({confec.split(' ')[0]}) | {ancho_trad}m x {alto_trad}m"
                    
                    if riel_sel != "Ninguno": costo_ml += df_trad[df_trad['Producto']==riel_sel]['Precio'].values[0]
                    if visillo_sel != "Ninguno": costo_ml += (df_trad[df_trad['Producto']==visillo_sel]['Precio'].values[0] * factor)
                    if pesada_sel != "Ninguno": costo_ml += (df_trad[df_trad['Producto']==pesada_sel]['Precio'].values[0] * factor)
                    if extra_onda > 0 and (visillo_sel != "Ninguno" or pesada_sel != "Ninguno"): costo_ml += extra_onda
                    
                    total_item = (costo_ml * ancho_trad) * cantidad
                    st.session_state.lista_items.append({
                        "ambiente": ambiente, "cantidad": cantidad, "detalle": desc, 
                        "precio_u": costo_ml, "total": total_item
                    })
                    st.success("Añadido al carrito")
                else:
                    st.warning("Falta completar Ancho, Alto o el Ambiente.")

        st.markdown("---")
        st.subheader("Resumen y descuento")
        
        subtotal = 0
        for i, item in enumerate(st.session_state.lista_items):
            c_amb, c_det, c_tot, c_acc = st.columns([2, 4, 2, 1])
            c_amb.write(f"🏠 **{item['ambiente']}** (x{item['cantidad']})")
            c_det.write(item['detalle'])
            c_tot.write(f"${item['total']:.2f}")
            if c_acc.button("🗑️", key=f"del_{i}"):
                st.session_state.lista_items.pop(i)
                st.rerun()
            subtotal += item['total']
            
        descuento_pct = st.slider("Descuento aplicado al pago de Contado (%)", 0, 50, 10)
        dias_entrega = st.selectbox("Días de entrega", ["3 días laborables", "5 días laborables", "8 días laborables"])
        
        iva = subtotal * 0.15
        total_con_iva = subtotal + iva
        monto_descuento = total_con_iva * (descuento_pct / 100)
        total_contado = total_con_iva - monto_descuento

        st.info(f"**Suma sin IVA:** ${subtotal:.2f} | **IVA 15%:** ${iva:.2f} | **TOTAL:** ${total_con_iva:.2f}")
        st.success(f"**TOTAL DE CONTADO ({descuento_pct}% OFF): ${total_contado:.2f}**")

        ca1, ca2, ca3 = st.columns(3)
        
        if ca1.button("💾 Guardar en Histórico"):
            if len(st.session_state.lista_items) > 0 and st.session_state.cliente_actual["nombre"]:
                historial = cargar_json(ARCHIVO_HISTORICO)
                codigo_cot = f"PG {datetime.now().strftime('%y-%H%M%S')}"
                historial.append({
                    "codigo": codigo_cot, "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "cliente": st.session_state.cliente_actual, "items": st.session_state.lista_items,
                    "subtotal": subtotal, "iva": iva, "total": total_con_iva,
                    "descuento": descuento_pct, "contado": total_contado, "dias": dias_entrega
                })
                guardar_json(ARCHIVO_HISTORICO, historial)
                st.success("Guardado con éxito!")
            else:
                st.error("Faltan datos del cliente o productos.")

        # WhatsApp
        mensaje_wa = f"*COTIZACIÓN D/CLASS & CLASSICA*\nCliente: {st.session_state.cliente_actual['nombre']}\n\n*Resumen:*\n"
        for it in st.session_state.lista_items:
            mensaje_wa += f"- {it['ambiente']} (x{it['cantidad']}): {it['detalle']} -> ${it['total']:.2f}\n"
        mensaje_wa += f"\n*TOTAL CONTADO:* ${total_contado:.2f}\n_Entrega en {dias_entrega}_"
        link_wa = f"https://wa.me/?text={urllib.parse.quote(mensaje_wa)}"
        ca2.markdown(f'<a href="{link_wa}" target="_blank"><button style="width:100%; padding:8px; background-color:#25D366; color:white; border:none; border-radius:5px;">📱 Enviar por WhatsApp</button></a>', unsafe_allow_html=True)

        # 3. Generar PDF
        if ca3.button("📄 Generar PDF"):
            if len(st.session_state.lista_items) == 0:
                st.error("Agrega productos al carrito primero.")
            else:
                pdf = FPDF()
                pdf.add_page()
                
                # --- LOGOS (Sin sobreescribir Header para evitar bugs) ---
                logo_izq = buscar_logo("logo_classica")
                if logo_izq:
                    try: pdf.image(logo_izq, 10, 8, 40)
                    except: pass
                    
                logo_der = buscar_logo("logo_dclass")
                if logo_der:
                    try: pdf.image(logo_der, 160, 8, 40)
                    except: pass
                
                pdf.set_y(15)
                pdf.set_font('Arial', 'B', 16)
                pdf.cell(0, 10, 'COTIZACION OFICIAL', 0, 1, 'C')
                
                # ESPACIO OBLIGATORIO PARA NO PISAR LOS LOGOS
                pdf.set_y(55) 
                
                # --- DATOS CLIENTE ---
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(20, 6, 'Cliente:', 0, 0); pdf.set_font('Arial', '', 10); pdf.cell(90, 6, st.session_state.cliente_actual['nombre'], 0, 0)
                pdf.set_font('Arial', 'B', 10); pdf.cell(20, 6, 'Fecha:', 0, 0); pdf.set_font('Arial', '', 10); pdf.cell(0, 6, datetime.now().strftime('%d/%m/%Y'), 0, 1)
                
                pdf.set_font('Arial', 'B', 10); pdf.cell(20, 6, 'Telefono:', 0, 0); pdf.set_font('Arial', '', 10); pdf.cell(90, 6, st.session_state.cliente_actual['telefono'], 0, 0)
                pdf.set_font('Arial', 'B', 10); pdf.cell(20, 6, 'Asesora:', 0, 0); pdf.set_font('Arial', '', 10); pdf.cell(0, 6, st.session_state.cliente_actual['asesora'], 0, 1)
                
                pdf.set_font('Arial', 'B', 10); pdf.cell(20, 6, 'Direccion:', 0, 0); pdf.set_font('Arial', '', 10); pdf.cell(0, 6, st.session_state.cliente_actual['direccion'], 0, 1)
                pdf.ln(8)
                
                # --- TABLA ---
                pdf.set_fill_color(220, 220, 220)
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(35, 8, 'AMBIENTE', 1, 0, 'C', 1); pdf.cell(15, 8, 'CANT.', 1, 0, 'C', 1)
                pdf.cell(110, 8, 'DETALLE', 1, 0, 'C', 1); pdf.cell(30, 8, 'TOTAL', 1, 1, 'C', 1)
                
                pdf.set_font('Arial', '', 8)
                for it in st.session_state.lista_items:
                    pdf.cell(35, 8, it['ambiente'][:18], 1, 0, 'L'); pdf.cell(15, 8, str(it['cantidad']), 1, 0, 'C')
                    pdf.cell(110, 8, it['detalle'], 1, 0, 'L'); pdf.cell(30, 8, f"${it['total']:.2f}", 1, 1, 'R')
                    
                pdf.ln(5)
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(160, 6, 'SUBTOTAL:', 0, 0, 'R'); pdf.cell(30, 6, f"${subtotal:.2f}", 1, 1, 'R')
                pdf.cell(160, 6, 'IVA (15%):', 0, 0, 'R'); pdf.cell(30, 6, f"${iva:.2f}", 1, 1, 'R')
                pdf.cell(160, 6, 'TOTAL NORMAL:', 0, 0, 'R'); pdf.cell(30, 6, f"${total_con_iva:.2f}", 1, 1, 'R')
                
                pdf.set_fill_color(255, 230, 230); pdf.set_text_color(200, 0, 0)
                pdf.cell(160, 8, f'TOTAL CONTADO ({descuento_pct}% OFF):', 0, 0, 'R'); pdf.cell(30, 8, f"${total_contado:.2f}", 1, 1, 'R', 1)
                
                # --- NOMBRE DE ARCHIVO DINÁMICO ---
                nombre_limpio = st.session_state.cliente_actual['nombre'].strip().replace(" ", "_")
                if not nombre_limpio: nombre_limpio = "Cliente"
                fecha_str = datetime.now().strftime('%Y%m%d_%H%M')
                nombre_archivo = f"Cotizacion_{nombre_limpio}_{fecha_str}.pdf"
                
                pdf.output("cotizacion_final.pdf")
                with open("cotizacion_final.pdf", "rb") as f:
                    st.download_button("Descargar PDF", f, file_name=nombre_archivo)

    # ==========================================
    #             MÓDULO: HISTÓRICO
    # ==========================================
    elif menu == "📂 Histórico":
        st.title("Historial de Cotizaciones")
        historial = cargar_json(ARCHIVO_HISTORICO)
        if not historial: st.info("Aún no hay cotizaciones guardadas.")
        else:
            for cot in reversed(historial):
                with st.expander(f"{cot['cliente']['nombre']} - {cot['codigo']} | {cot['fecha']} - Total: ${cot['contado']:.2f}"):
                    for item in cot['items']:
                        st.write(f"- {item['ambiente']} (x{item['cantidad']}): {item['detalle']} -> ${item['total']:.2f}")
                    if st.button("Cargar esta cotización", key=f"btn_{cot['codigo']}"):
                        st.session_state.cliente_actual = cot['cliente']
                        st.session_state.lista_items = cot['items']
                        st.success("Cargada en la pestaña 'Cotizar'.")

    # ==========================================
    #             MÓDULO: CONFIGURAR
    # ==========================================
    elif menu == "⚙️ Configurar":
        st.title("Configuración de la Empresa")
        config_data = cargar_json(ARCHIVO_CONFIG)
        telf1 = st.text_input("Teléfonos CLASSICA", value=config_data.get("telf_classica", ""))
        telf2 = st.text_input("WhatsApp Asesores", value=config_data.get("wa_asesores", ""))
        dir_matriz = st.text_input("Dirección Showroom", value=config_data.get("direccion", ""))
        if st.button("Guardar"):
            guardar_json(ARCHIVO_CONFIG, {"telf_classica": telf1, "wa_asesores": telf2, "direccion": dir_matriz})
            st.success("Guardado!")
