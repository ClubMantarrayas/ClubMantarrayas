import streamlit as st
import pandas as pd
from formulas_lib_funciones import formatear_a_minutos, convertir_string_a_segundos, obtener_pruebas_por_categoria

# Definimos el fragmento reactivo para aislar toda la carga de datos pesados
@st.fragment
def contenedor_formulario_entrenador():
    # 1. Selección de categoría y prueba rápidas
    u_cat = st.selectbox(
        "Categoría a Modificar u Organizar:", 
        options=["Infantil A", "Infantil B", "Juvenil A", "Juvenil B", "Máxima"],
        key="sb_categoria_entrenador"
    )
    
    lista_pruebas_restringida = obtener_pruebas_por_categoria(u_cat)
    
    titulo_grafico = st.selectbox(
        f"🏊‍♂️ Seleccione la Prueba para {u_cat}:", 
        options=lista_pruebas_restringida,
        index=1 if len(lista_pruebas_restringida) > 1 else 0,
        key="sb_prueba_entrenador_ingreso"
    )
    
    genero_atleta = st.session_state.get("nadador_seleccionado_genero", "F")
    es_preinfantil = st.session_state.get("es_preinfantil", False)

    # Control de exclusiones
    pruebas_excluidas = ['25 Libre', '25 Espalda', '25 Pecho', '25 Mariposa', '100 Combinado']
    if titulo_grafico in pruebas_excluidas or es_preinfantil:
        st.info(f"💡 **Aviso:** Las marcas de referencia para pruebas Preinfantiles ({titulo_grafico}) se calculan automáticamente.")
        return

    # 2. Carga dinámica de marcas desde Supabase
    db_m_ano, db_m_panam_b, db_m_panam_a, db_m_wa_b, db_m_wa_a, db_m_wr = None, None, None, None, None, None
    global supabase
    
    try:
        ref_dinamica = supabase.table("marcas_referencia").select("*").eq("prueba", titulo_grafico).eq("genero", genero_atleta).eq("categoria", u_cat).execute()
        if ref_dinamica.data:
            r_det = ref_dinamica.data[0]
            db_m_ano = float(r_det["m_ano"]) if r_det["m_ano"] is not None else None
            db_m_panam_b = float(r_det["m_panam_b"]) if r_det["m_panam_b"] is not None else None
            db_m_panam_a = float(r_det["m_panam_a"]) if r_det["m_panam_a"] is not None else None
            db_m_wa_b = float(r_det["m_wa_b"]) if r_det["m_wa_b"] is not None else None
            db_m_wa_a = float(r_det["m_wa_a"]) if r_det["m_wa_a"] is not None else None
            db_m_wr = float(r_det["m_wr"]) if r_det["m_wr"] is not None else None
    except Exception as e:
        st.caption(f"Nota en precarga: {e}")

    st.caption(f"📋 Configurando tiempos para **{titulo_grafico}** ({'Femenino' if genero_atleta == 'F' else 'Masculino'})")

    # 3. Formulario integrado en el fragmento para que cambie de inmediato al mover los selectboxes
    with st.form("form_update_referencias"):
        st.write("✍️ *Ingrese los tiempos en formato `mm:ss.hh` o segundos decimales*")
        
        col1, col2 = st.columns(2)
        with col1:
            in_ano = st.text_input("Marca Mínima Año (mm:ss.hh):", value=formatear_a_minutos(db_m_ano))
            in_panamb = st.text_input("PANAM Jr - Marca B (mm:ss.hh):", value=formatear_a_minutos(db_m_panam_b))
            in_panama = st.text_input("PANAM Jr - Marca A (mm:ss.hh):", value=formatear_a_minutos(db_m_panam_a))
        with col2:
            in_wab = st.text_input("World Aquatics - Marca B (mm:ss.hh):", value=formatear_a_minutos(db_m_wa_b))
            in_waa = st.text_input("World Aquatics - Marca A (mm:ss.hh):", value=formatear_a_minutos(db_m_wa_a))
            in_wr = st.text_input("Récord Mundial Absoluto (mm:ss.hh):", value=formatear_a_minutos(db_m_wr) if db_m_wr is not None else "25.00")
        
        if st.form_submit_button("⚡ Guardar Configuración de Tiempos"):
            try:
                u_ano = convertir_string_a_segundos(in_ano) if in_ano != "0.00" else None
                u_panamb = convertir_string_a_segundos(in_panamb) if in_panamb != "0.00" else None
                u_panama = convertir_string_a_segundos(in_panama) if in_panama != "0.00" else None
                u_wab = convertir_string_a_segundos(in_wab) if in_wab != "0.00" else None
                u_waa = convertir_string_a_segundos(in_waa) if in_waa != "0.00" else None
                u_wr = convertir_string_a_segundos(in_wr) if in_wr != "0.00" else None
                
                up_data = {}
                if u_ano is not None: up_data["m_ano"] = u_ano
                if u_panamb is not None: up_data["m_panam_b"] = u_panamb
                if u_panama is not None: up_data["m_panam_a"] = u_panama
                if u_wab is not None: up_data["m_wa_b"] = u_wab
                if u_waa is not None: up_data["m_wa_a"] = u_waa
                if u_wr is not None: up_data["m_wr"] = u_wr
                
                if up_data:
                    supabase.table("marcas_referencia").upsert({
                        "prueba": titulo_grafico, 
                        "genero": genero_atleta,
                        "categoria": u_cat, 
                        **up_data
                    }, on_conflict="prueba,genero,categoria").execute()
                    
                    st.success(f"🎉 Tiempos procesados y guardados con éxito para la categoría {u_cat}.")
                    st.rerun()
                else:
                    st.warning("⚠️ No se detectaron cambios numéricos válidos.")
            except Exception as e:
                st.error(f"❌ Error al procesar o guardar los tiempos: {e}")


def renderizar_tab_entrenador():
    """
    CÓDIGO MODULAR EVOLUCIONADO.
    Indentación limpia corregida a 4 espacios planos para evitar fallos de despliegue.
    """
    global supabase
    if "supabase" in st.session_state and st.session_state.supabase:
        supabase = st.session_state.supabase
    else:
        st.error("❌ Conexión no inicializada en Session State.")
        return

    if st.session_state.get("rol") not in ["Head Coach", "Administrador"]:
        st.warning("🔒 Requiere credenciales de Head Coach.")
        return

    st.markdown("### ⚙️ Umbrales de Competencia para la Categoría")
    
    # Invocamos el contenedor fragmentado de manera limpia
    contenedor_formulario_entrenador()
