import streamlit as st
import pandas as pd
import json
import os
from fpdf import FPDF
from datetime import datetime
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Cotizador D/CLASS & CLASSICA", layout="wide")

ARCHIVO_HISTORICO = "historico.json"
ARCHIVO_CONFIG = "config.json"

# --- 2. FUNCIONES DE BASE DE DATOS (JSON) ---
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

# Inicializar estados
if 'acceso_concedido' not in st.session_state: st.session_state.acceso_concedido = False
if 'lista_items' not in st.session_state: st.session_state.lista_items = []
if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = {"nombre": "", "telefono": "", "direccion": "", "asesora": "Asesora Principal"}
if 'cotizacion_cargada' not in st.session_state: st.session_state.cotizacion_cargada = None

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
    # --- 4. CARGAR DATOS DE EXCEL ---
    @st.cache_data
    def cargar_excel():
        # Leer modernas con armadura
        try:
            df_mod = pd.read_csv("datos_cortinas.csv", encoding="utf-8")
        except:
            df_mod = pd.read_csv("datos_cortinas.csv", encoding="latin-1")
            
        df_mod['m2'] = pd.to_numeric(df_mod['m2'].astype(str).str.replace('$', '', regex=False).str.replace(',', '.').str.strip())
        df_mod['tipo de cortina'] = df_mod['tipo de cortina'].astype(str).str.title().str.strip()
        df_mod['tipo de tela'] = df_mod['tipo de tela'].fillna('Única').astype(str).str.title().str.strip()

        # Leer tradicionales con armadura
        try:
            df_trad = pd.read_csv("datos_tradicionales.csv", encoding="utf-8")
        except:
            df_trad = pd.read_csv("datos_tradicionales.csv", encoding="latin-1")
            
        df_trad['Precio'] = pd.to_numeric(df_trad['Precio'].astype(str).str.replace('$', '', regex=False).str.replace(',', '.').str.strip())
        
        return df_mod, df_trad

    try:
        df_modernas, df_trad = cargar_excel()
        l_rieles = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'RIEL']['Producto'].tolist()
        l_visillos = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'VISILLO']['Producto'].tolist()
        l_pesadas = df_trad[df_trad['Categoría'].astype(str).str.upper() == 'CORTINA']['Producto'].tolist()
    except Exception as e:
        st.error("Error cargando los archivos CSV. Verifica que estén en la carpeta.")
        st.stop()

    # --- 5. NAVEGACIÓN LATERAL ---
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
            st.session_state.cliente_actual["asesora"] = c2.selectbox("Asesora que firma", ["Andrea Cóndor", "Celmira Zapata", "Verónica Tapia"], index=0)

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
                        "precio_u": precio_u, "total": total_item, "tipo": "m2", "medida": area
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
                    desc = f"TRADICIONAL ({confec.split(' ')[0]}) | {ancho_trad}m x {alto_trad}m"
                    
                    if riel_sel != "Ninguno": costo_ml += df_trad[df_trad['Producto']==riel_sel]['Precio'].values[0]
                    if visillo_sel != "Ninguno": costo_ml += (df_trad[df_trad['Producto']==visillo_sel]['Precio'].values[0] * factor)
                    if pesada_sel != "Ninguno": costo_ml += (df_trad[df_trad['Producto']==pesada_sel]['Precio'].values[0] * factor)
                    if extra_onda > 0 and (visillo_sel != "Ninguno" or pesada_sel != "Ninguno"): costo_ml += extra_onda
                    
                    total_item = (costo_ml * ancho_trad) * cantidad
                    st.session_state.lista_items.append({
                        "ambiente": ambiente, "cantidad": cantidad, "detalle": desc, 
                        "precio_u": costo_ml, "total": total_item, "tipo": "ml", "medida": ancho_trad
                    })
                    st.success("Añadido al carrito")
                else:
                    st.warning("Falta completar Ancho, Alto o el Ambiente.")

        st.markdown("---")
        st.subheader("Resumen y descuento")
        
        # Mostrar Carrito
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

        # ACCIONES
        ca1, ca2, ca3 = st.columns(3)
        
        # 1. Guardar en Histórico
        if ca1.button("💾 Guardar en Histórico"):
            if len(st.session_state.lista_items) > 0 and st.session_state.cliente_actual["nombre"]:
                historial = cargar_json(ARCHIVO_HISTORICO)
                codigo_cot = f"PG {datetime.now().strftime('%y-%H%M%S')}"
                nueva_cot = {
                    "codigo": codigo_cot,
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "cliente": st.session_state.cliente_actual,
                    "items": st.session_state.lista_items,
                    "subtotal": subtotal, "iva": iva, "total": total_con_iva,
                    "descuento": descuento_pct, "contado": total_contado,
                    "dias": dias_entrega
                }
                historial.append(nueva_cot)
                guardar_json(ARCHIVO_HISTORICO, historial)
                st.success(f"Cotización {codigo_cot} guardada con éxito!")
            else:
                st.error("Agrega un cliente y productos primero.")

        # 2. WhatsApp
        mensaje_wa = f"*COTIZACIÓN D/CLASS & CLASSICA*\nCliente: {st.session_state.cliente_actual['nombre']}\n\n*Resumen:*\n"
        for it in st.session_state.lista_items:
            mensaje_wa += f"- {it['ambiente']} (x{it['cantidad']}): {it['detalle']} -> ${it['total']:.2f}\n"
        mensaje_wa += f"\n*TOTAL CONTADO:* ${total_contado:.2f}\n_Entrega en {dias_entrega}_"
        link_wa = f"https://wa.me/?text={urllib.parse.quote(mensaje_wa)}"
        ca2.markdown(f'<a href="{link_wa}" target="_blank"><button style="width:100%; padding:8px; background-color:#25D366; color:white; border:none; border-radius:5px;">📱 Enviar por WhatsApp</button></a>', unsafe_allow_html=True)

        # 3. Generar PDF (Doble Logo)
        class PDFDoble(FPDF):
            def header(self):
                try:
                    self.image("logo_classica.jpg", 10, 8, 40)
                except: pass
                try:
                    self.image("logo_dclass.jpg", 160, 8, 40)
                except: pass
                self.set_font('Arial', 'B', 15)
                self.cell(0, 10, 'COTIZACION OFICIAL', 0, 1, 'C')
                self.ln(10)
                
        if ca3.button("📄 Generar PDF"):
            pdf = PDFDoble()
            pdf.add_page()
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 6, f"Cliente: {st.session_state.cliente_actual['nombre']} | Tel: {st.session_state.cliente_actual['telefono']}", 0, 1)
            pdf.cell(0, 6, f"Direccion: {st.session_state.cliente_actual['direccion']} | Asesora: {st.session_state.cliente_actual['asesora']}", 0, 1)
            pdf.cell(0, 6, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(30, 8, 'AMBIENTE', 1); pdf.cell(15, 8, 'CANT.', 1); pdf.cell(115, 8, 'DETALLE', 1); pdf.cell(30, 8, 'TOTAL', 1, 1)
            
            pdf.set_font('Arial', '', 8)
            for it in st.session_state.lista_items:
                pdf.cell(30, 8, it['ambiente'][:15], 1); pdf.cell(15, 8, str(it['cantidad']), 1, 0, 'C')
                pdf.cell(115, 8, it['detalle'], 1); pdf.cell(30, 8, f"${it['total']:.2f}", 1, 1, 'C')
                
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(160, 6, 'SUBTOTAL:', 0, 0, 'R'); pdf.cell(30, 6, f"${subtotal:.2f}", 0, 1, 'R')
            pdf.cell(160, 6, 'IVA (15%):', 0, 0, 'R'); pdf.cell(30, 6, f"${iva:.2f}", 0, 1, 'R')
            pdf.cell(160, 6, 'TOTAL NORMAL:', 0, 0, 'R'); pdf.cell(30, 6, f"${total_con_iva:.2f}", 0, 1, 'R')
            pdf.set_text_color(255, 0, 0)
            pdf.cell(160, 6, f'TOTAL CONTADO ({descuento_pct}% OFF):', 0, 0, 'R'); pdf.cell(30, 6, f"${total_contado:.2f}", 0, 1, 'R')
            
            pdf.output("cotizacion_final.pdf")
            with open("cotizacion_final.pdf", "rb") as f:
                st.download_button("Descargar PDF Listo", f, file_name="Cotizacion.pdf")

    # ==========================================
    #             MÓDULO: HISTÓRICO
    # ==========================================
    elif menu == "📂 Histórico":
        st.title("Historial de Cotizaciones")
        historial = cargar_json(ARCHIVO_HISTORICO)
        
        if not historial:
            st.info("Aún no hay cotizaciones guardadas.")
        else:
            for cot in reversed(historial):
                with st.expander(f"{cot['cliente']['nombre']} - {cot['codigo']} | {cot['fecha']} - Total: ${cot['contado']:.2f}"):
                    st.write(f"**Dirección:** {cot['cliente']['direccion']} | **Asesora:** {cot['cliente']['asesora']}")
                    for item in cot['items']:
                        st.write(f"- {item['ambiente']} (x{item['cantidad']}): {item['detalle']} -> ${item['total']:.2f}")
                    
                    if st.button("Cargar esta cotización para editar", key=f"btn_{cot['codigo']}"):
                        st.session_state.cliente_actual = cot['cliente']
                        st.session_state.lista_items = cot['items']
                        st.success("¡Cotización cargada! Ve a la pestaña 'Cotizar' para verla y editarla.")

    # ==========================================
    #             MÓDULO: CONFIGURAR
    # ==========================================
    elif menu == "⚙️ Configurar":
        st.title("Configuración de la Empresa")
        st.write("Aquí podrás actualizar los datos maestros en el futuro.")
        config_data = cargar_json(ARCHIVO_CONFIG)
        
        telf1 = st.text_input("Teléfonos CLASSICA", value=config_data.get("telf_classica", "(593-2) 2418390"))
        telf2 = st.text_input("WhatsApp Asesores", value=config_data.get("wa_asesores", "0992445061"))
        dir_matriz = st.text_input("Dirección Showroom", value=config_data.get("direccion", "Av. 6 de Diciembre N46-274"))
        
        if st.button("Guardar Configuración"):
            nueva_conf = {"telf_classica": telf1, "wa_asesores": telf2, "direccion": dir_matriz}
            guardar_json(ARCHIVO_CONFIG, nueva_conf)
            st.success("¡Datos guardados!")
