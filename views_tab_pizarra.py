import streamlit as st
import pandas as pd
import datetime
import urllib.parse

# 🌐 Ajuste de orden: Importación unificada en la raíz del módulo
from formulas_lib_funciones import calcular_edad_tecnica_al_31_dic, calcular_categoria_competencia  

def renderizar_tab_pizarra(datos_sidebar):
    """
    Módulo operativo independiente para la Pizarra de Entrenamiento Diario,
    Difusión por Canales, Segmentación e Imputación Histórica de Carga.
    """
    # 🧠 ESTRATEGIA: Pre-inyección de estado para evitar el error de ciclo de vida de Streamlit
    if "piz_fecha_override" in st.session_state:
        st.session_state["piz_date_input_save"] = st.session_state.pop("piz_fecha_override")
    if "piz_carril_override" in st.session_state:
        st.session_state["piz_carril_input_save"] = st.session_state.pop("piz_carril_override")

    # Extracción de parámetros de control desde el Sidebar Maestro
    simulacion_externa = datos_sidebar.get("simulacion_externa", False)  
    supabase = st.session_state.get("supabase")  

    if simulacion_externa:  
        st.warning("⚠️ El módulo de gestión y control de entrenamientos está deshabilitado en Modo Simulación.")  
        return  

    # Restricción estricta de roles para el equipo técnico
    if st.session_state.rol not in ["Head Coach", "Entrenador", "Administrador"]:  
        st.warning("🔒 Sección restringida al equipo técnico.")  
        return  

    # Definición e inicialización de las sub-pestañas internas exactas
    subtab_crear, subtab_reportes = st.tabs(["✍️ Diseñar Menú del Día", "📊 Reportes e Historial"])  

    # =========================================================================
    # SUB-PESTAÑA 1: DISEÑO, DIFUSIÓN Y CONSOLIDACIÓN DIARIA
    # =========================================================================
    with subtab_crear:  
        st.markdown("### 📋 Estructura del Entrenamiento Activo")  
        st.caption("Configura el encabezado, añade los bloques de series y controla la asistencia para imputar la carga individual.")  

        c_fecha, c_carril = st.columns(2)
        with c_fecha:
            fecha_jornada = st.date_input("Fecha de la sesión:", datetime.date.today(), key="piz_date_input_save")
        with c_carril:
            identificador_carril = st.text_input("Identificador / Carril / Grupo:", placeholder="Ej: Carril 3, Grupo Avanzado", key="piz_carril_input_save")

        st.markdown("---")

        # Inicializar la pizarra en la memoria de sesión si no existe
        if "pizarra_entrenamiento" not in st.session_state:  
            st.session_state.pizarra_entrenamiento = []  

        # Formulario de ingreso rápido de series
        with st.expander("➕ Añadir nueva serie al entrenamiento", expanded=True):  
            c_rep, c_dist, c_est = st.columns(3)  
            with c_rep:  
                repeticiones = st.number_input("Repeticiones", min_value=1, value=1, step=1, key="piz_rep")  
            with c_dist:  
                distancia = st.number_input("Distancia (m)", min_value=15, value=100, step=25, key="piz_dist")  
            with c_est:  
                estilo = st.selectbox("Estilo / Foco", ["Libre", "Espalda", "Pecho", "Mariposa", "Combinado", "Piernas", "Brazos", "Técnica / Drills", "Afloje"], key="piz_est")  
                
            c_int, c_imp, c_not = st.columns(3)  
            with c_int:  
                intensidad = st.selectbox("Ritmo / Intensidad RPE", ["Suave (Aeróbico Ligero 3-4)", "Medio (Aeróbico Medio 5-6)", "Sostenido (Umbral 7-8)", "Ritmo de Competencia (Anaeróbico 9-10)", "Sprint (Máximo 10-11)"], key="piz_int")  
            with c_imp:  
                implementos = st.multiselect("Implementos", ["Aletas", "Paletas", "Tabla", "Pullbuoy", "Snorkel", "Paracaídas", "Ligas"], key="piz_imp")  
            with c_not:  
                notas = st.text_input("Instrucciones breves (Opcional)", placeholder="Ej: c/1:30 nado y descanso, Respiración c/3, Descanso 20s", key="piz_not")  

            if st.button("Añadir a la sesión", use_container_width=True, key="btn_add_piz"):  
                bloque = {  
                    "reps": repeticiones,  
                    "dist": distancia,  
                    "estilo": estilo,  
                    "intensidad": intensidad,  
                    "implementos": implementos,  
                    "notas": notas  
                }  
                st.session_state.pizarra_entrenamiento.append(bloque)  
                st.rerun()  

        # Visualización del entrenamiento acumulado en la sesión activa
        if st.session_state.pizarra_entrenamiento:  
            st.markdown("---")  
            volumen_total = 0  
            
            texto_exportacion = f"🏊‍♂️ *PLAN DE ENTRENAMIENTO DEL DÍA* - Fecha: {fecha_jornada.strftime('%d/%m/%Y') if hasattr(fecha_jornada, 'strftime') else fecha_jornada}\n"  
            if identificador_carril:  
                texto_exportacion += f"📍 *Grupo/Carril:* {identificador_carril}\n"  
            
            for idx, blk in enumerate(st.session_state.pizarra_entrenamiento, 1):  
                subtotal = blk['reps'] * blk['dist']  
                volumen_total += subtotal  
                txt_impl = f" [{', '.join(blk['implementos'])}]" if blk['implementos'] else ""  
                txt_not = f" - _{blk['notas']}_" if blk['notas'] else ""  
                texto_exportacion += f"• {blk['reps']} x {blk['dist']}m {blk['estilo']} | {blk['intensidad']}{txt_impl}{txt_not}\n"  

            texto_exportacion += f"\n📊 *Volumen Total:* {volumen_total:,} metros\n"  
            
            # Panel Informativo Visual y Métrica
            st.info(texto_exportacion)  
            st.metric("Volumen Total de la Sesión", f"{volumen_total:,} metros")  
            
            c_undo, c_clear = st.columns(2)  
            with c_undo:  
                if st.button("⏪ Deshacer último bloque", use_container_width=True, key="piz_btn_undo"):  
                    st.session_state.pizarra_entrenamiento.pop()  
                    st.rerun()  
            with c_clear:  
                if st.button("🗑️ Limpiar pizarra completa", use_container_width=True, key="piz_btn_clear"):  
                    st.session_state.pizarra_entrenamiento = []  
                    st.rerun()  

            # =============================================================================
            # 📢 CENTRO DE DIFUSIÓN Y EXPORTACIÓN DE LA JORNADA
            # =============================================================================
            st.markdown("---")  
            st.markdown("### 📢 Centro de Difusión y Publicación de la Pizarra")  
            st.caption("Genera el formato de comunicación para enviar a los atletas por canales digitales o preparar la hoja impresa.")  
            
            texto_url = urllib.parse.quote(texto_exportacion)  
            link_whatsapp = f"https://api.whatsapp.com/send?text={texto_url}"  
            link_correo = f"mailto:?subject=Plan%20de%20Entrenamiento%20{fecha_jornada}&body={texto_url}"  

            c_com1, c_com2, c_com3 = st.columns(3)  
            with c_com1:  
                st.link_button("🟢 Enviar por WhatsApp", link_whatsapp, use_container_width=True)  
            with c_com2:  
                st.link_button("📩 Enviar por Correo", link_correo, use_container_width=True)  
            with c_com3:  
                st.download_button(  
                    label="🖨️ Descargar Hoja de Carril (TXT)",  
                    data=texto_exportacion.replace("*", ""),  
                    file_name=f"pizarra_{fecha_jornada}_{str(identificador_carril).replace(' ', '_') if identificador_carril else 'general'}.txt",  
                    mime="text/plain",  
                    use_container_width=True  
                )  

            with st.expander("👀 Ver vista previa del mensaje a enviar"):  
                st.code(texto_exportacion, language="markdown")  

            # =============================================================================
            # 🔍 SECCIÓN DE SEGMENTACIÓN (ASISTENCIA/CARGA)
            # =============================================================================
            st.markdown("---")  
            st.markdown("### 🔍 Segmentación de Destinatarios (Asistencia/Carga)")  
            
            col_foto1, col_foto2 = st.columns(2)  
            with col_foto1:  
                filtro_genero = st.radio("Segmentar por Género:", options=["Todos", "Femenino (F)", "Masculino (M)"], horizontal=True, key="piz_radio_genero_idx")  
            with col_foto2:  
                tipo_filtro = st.radio("Segmentar adicionalmente por:", options=["Todos los Atletas", "Categoría Etaria", "Atletas Específicos"], horizontal=True, key="piz_radio_tipo_idx")  

            ctx_supabase = supabase if supabase else st.session_state.get("supabase_client")  
            atletas_pool = []  

            if ctx_supabase:  
                try:  
                    es_entrenador = st.session_state.get("rol") == "Entrenador"  
                    entrenador_id = st.session_state.get("usuario_id")  
                    permitir_consulta = True  
                    ids_autorizados = []  

                    if es_entrenador:  
                        if entrenador_id:  
                            resp_asig = ctx_supabase.table("asignaciones").select("atleta_id").eq("entrenador_id", entrenador_id).execute()  
                            if resp_asig.data:  
                                ids_autorizados = [reg["atleta_id"] for reg in resp_asig.data]  
                            if not ids_autorizados:  
                                permitir_consulta = False  
                        else:  
                            st.error("❌ Error de sesión: No se encontró el ID del entrenador.")  
                            permitir_consulta = False  

                    if permitir_consulta:  
                        query_atletas = ctx_supabase.table("usuarios").select("id, nombre, email, genero, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo")  
                        if es_entrenador:  
                            query_atletas = query_atletas.in_("id", ids_autorizados)  
                        
                        resp_sb = query_atletas.execute()  
                        if resp_sb.data:  
                            atletas_pool = resp_sb.data  
                    else:  
                        st.warning("⚠️ No tienes atletas asignados en tu perfil de Entrenador.")  
                except Exception as e:  
                    st.error(f"Error al cargar nómina desde Supabase: {e}")  

            if filtro_genero == "Femenino (F)":  
                atletas_pool = [a for a in atletas_pool if a.get("genero") == "F"]  
            elif filtro_genero == "Masculino (M)":  
                atletas_pool = [a for a in atletas_pool if a.get("genero") == "M"]  

            categorias_disponibles = sorted(list(set([  
                calcular_categoria_competencia(a["fecha_nacimiento"])[0]  
                for a in atletas_pool if a.get("fecha_nacimiento")  
            ]))) if atletas_pool else []  

            dict_nom = {a["id"]: a["nombre"] for a in atletas_pool} if atletas_pool else {}  
            atletas_finales = []  

            if tipo_filtro == "Categoría Etaria":  
                cat_sel = st.selectbox("Seleccione la Categoría Etaria:", options=categorias_disponibles if categorias_disponibles else ["Cargando categorías activos..."], key="piz_selectbox_cat")  
                if categorias_disponibles:  
                    atletas_finales = [a for a in atletas_pool if calcular_categoria_competencia(a["fecha_nacimiento"])[0] == cat_sel]  
            elif tipo_filtro == "Atletas Específicos":  
                ids_sel = st.multiselect("Seleccione Nadador(es) Individual(es):", options=list(dict_nom.keys()), format_func=lambda x: dict_nom.get(x, "Cargando atleta..."), key="piz_multiselect_atletas")  
                if ids_sel:  
                    atletas_finales = [a for a in atletas_pool if a["id"] in ids_sel]  
            else:  
                atletas_finales = atletas_pool  

            if tipo_filtro == "Atletas Específicos" and not atletas_finales:  
                st.info("💡 Despliega el selector de arriba y marca al menos un nadador para habilitar el botón de consolidation.")  
            else:  
                st.success(f"🎯 Grupo confirmado para imputación: {len(atletas_finales)} atleta(s).")  

            # =============================================================================
            # 4. CONSOLIDACIÓN E IMPUTACIÓN HISTÓRICA EN BITÁCORA
            # =============================================================================
            st.markdown("#### 💾 Consolidar y Registrar Jornada")  

            if st.button("💾 Consolidar Metros e Intensidades por Atleta", type="primary", use_container_width=True, key="btn_consolidar_piz"):  
                if atletas_finales:  
                    desglose_estilos = {}  
                    for blk in st.session_state.pizarra_entrenamiento:  
                        est = blk['estilo']  
                        mts = blk['reps'] * blk['dist']  
                        desglose_estilos[est] = desglose_estilos.get(est, 0) + mts  
                        
                    desglose_intensidad = {}  
                    for blk in st.session_state.pizarra_entrenamiento:  
                        inte = blk['intensidad']  
                        mts = blk['reps'] * blk['dist']  
                        desglose_intensidad[inte] = desglose_intensidad.get(inte, 0) + mts  

                    registros_supabase = []  
                    for at_obj in atletas_finales:  
                        fila = {  
                            "fecha": str(fecha_jornada),  
                            "atleta_id": at_obj.get("id"),  
                            "identificador_carril": identificador_carril if identificador_carril else "Carril Único",  
                            "metros_totales": int(volumen_total),  
                            "desglose_estilos": desglose_estilos,  
                            "desglose_intensidad": desglose_intensidad,  
                            "implementos_usados": list(set([imp for blk in st.session_state.pizarra_entrenamiento for imp in blk['implementos']])),  
                            "pizarra_original": st.session_state.pizarra_entrenamiento
                        }  
                        registros_supabase.append(fila)  

                    if registros_supabase and ctx_supabase:  
                        try:  
                            ctx_supabase.table("bitacora_entrenamientos").insert(registros_supabase).execute()  
                            st.cache_data.clear()
                            st.success(f"💥 ¡Base de datos actualizada! Se grabaron con éxito las cargas individuales para los {len(registros_supabase)} atleta(s).")  
                            st.session_state.pizarra_entrenamiento = []  
                            st.balloons()  
                            st.rerun()  
                        except Exception as e:  
                            st.error(f"Error crítico al escribir en Supabase: {e}")  
                else:  
                    st.warning("⚠️ No hay atletas seleccionados en el grupo para consolidar.")  
        else:  
            st.info("💡 Diseña bloques en el formulario superior para inicializar la sesión del día.")  

    # =========================================================================
    # SUB-PESTAÑA 2: HISTORIAL Y DISTRIBUCIÓN FISIOLÓGICA
    # =========================================================================
    with subtab_reportes:  
        st.markdown("### 📊 Historial y Distribución de Rutinas Consolidadas")  
        st.caption("Revisa el menú de entrenamientos de días anteriores basándose en la data consolidada del equipo técnico.")  

        ctx_supabase_rep = supabase if supabase else st.session_state.get("supabase_client")  

        if ctx_supabase_rep:  
            es_entrenador_rep = st.session_state.get("rol") == "Entrenador"  
            entrenador_id_rep = st.session_state.get("usuario_id")  
            
            permitir_consulta_rep = True  
            ids_autorizados_rep = []  

            if es_entrenador_rep:  
                if entrenador_id_rep:  
                    resp_asig_rep = ctx_supabase_rep.table("asignaciones").select("atleta_id").eq("entrenador_id", entrenador_id_rep).execute()  
                    if resp_asig_rep.data:  
                        ids_autorizados_rep = [reg["atleta_id"] for reg in resp_asig_rep.data]  
                    if not ids_autorizados_rep:  
                        permitir_consulta_rep = False  
                else:  
                    st.error("❌ Error de sesión: No se detectó ID único de Entrenador.")  
                    permitir_consulta_rep = False  

            if permitir_consulta_rep:  
                try:  
                    c_b1, c_b2 = st.columns(2)  
                    with c_b1:  
                        f_desde = st.date_input("Buscar desde:", datetime.date.today() - datetime.timedelta(days=15), key="bib_f_desde")  
                    with c_b2:  
                        f_hasta = st.date_input("Hasta:", datetime.date.today(), key="bib_f_hasta")  

                    query_records = ctx_supabase_rep.table("bitacora_entrenamientos").select("fecha, identificador_carril, metros_totales, desglose_estilos, desglose_intensidad, implementos_usados, atleta_id, pizarra_original").gte("fecha", str(f_desde)).lte("fecha", str(f_hasta))  
                    
                    if es_entrenador_rep and ids_autorizados_rep:  
                        query_records = query_records.in_("atleta_id", ids_autorizados_rep)  
                        
                    resp_bib = query_records.order("fecha", desc=True).execute()  

                    if resp_bib.data:  
                        rutinas_unicas = {}  
                        for reg in resp_bib.data:  
                            llave = (reg["fecha"], reg["identificador_carril"])  
                            if llave not in rutinas_unicas:  
                                rutinas_unicas[llave] = reg  

                        st.markdown(f"#### 🔎 Rutinas encontradas ({len(rutinas_unicas)})")  
                        
                        for (fecha_sesion, carril_sesion), datos_sesion in rutinas_unicas.items():  
                            total_metros = datos_sesion.get('metros_totales', 0)  
                            with st.expander(f"📋 {fecha_sesion} | 📍 Grupo-Carril: {carril_sesion} | Volumen: {total_metros:,}m"):  
                                
                                texto_atleta = f"**PLAN DE ENTRENAMIENTO RECONSTRUIDO** - Fecha: {fecha_sesion}\n"  
                                if carril_sesion:  
                                    texto_atleta += f"📍 Grupo/Carril: {carril_sesion}\n"  
                                texto_atleta += f"📊 Volumen Total Consolidado: {total_metros:,} metros\n\n"  
                                
                                dict_estilos = datos_sesion.get("desglose_estilos", {})  
                                for est, mts in dict_estilos.items():  
                                    texto_atleta += f"• Bloque enfocado en {est}: total de {mts:,} metros.\n"  
                                
                                st.info(texto_atleta)  
                                
                                st.markdown("#### 📉 Distribución Fisiológica")  
                                c_dist1, c_dist2 = st.columns(2)  
                                with c_dist1:  
                                    st.markdown("**Porcentaje por Estilo:**")  
                                    if dict_estilos:  
                                        datos_estilo_df = [{"Estilo / Foco": est, "Metros": mts, "%": f"{(mts/total_metros)*100:.1f}%"} for est, mts in dict_estilos.items()]  
                                        st.dataframe(pd.DataFrame(datos_estilo_df), use_container_width=True, hide_index=True)  
                                with c_dist2:  
                                    st.markdown("**Porcentaje por Intensidad:**")  
                                    dict_intensidades = datos_sesion.get("desglose_intensidad", {})  
                                    if dict_intensidades:  
                                        datos_int_df = [{"Zona": inte.split("(")[0].strip(), "Metros": mts, "%": f"{(mts/total_metros)*100:.1f}%"} for inte, mts in dict_intensidades.items()]  
                                        st.dataframe(pd.DataFrame(datos_int_df), use_container_width=True, hide_index=True)  

                                st.markdown("---")  
                                
                                c_act1, c_act2 = st.columns(2)  
                                with c_act1:  
                                    pizarra_guardada = datos_sesion.get("pizarra_original")
                                    pizarra_vacia = len(st.session_state.get("pizarra_entrenamiento", [])) == 0
                                    
                                    if pizarra_vacia:
                                        label_boton = "🔄 Cargar como Plantilla en Pizarra"
                                        color_tipo = "secondary"
                                    else:
                                        label_boton = "⚠️ Reemplazar Pizarra Activa con esta Plantilla"
                                        color_tipo = "secondary"
                                        st.caption("🚨 _Nota: Cargar esta rutina borrará las series que estás editando hoy._")
                                        
                                    if st.button(label_boton, key=f"btn_tpl_{fecha_sesion}_{carril_sesion}", type=color_tipo, use_container_width=True):  
                                        
                                        # ✨ SOLUCIÓN AL ERROR: Almacenamos el cambio en variables puentes de override
                                        st.session_state["piz_fecha_override"] = datetime.date.today()
                                        st.session_state["piz_carril_override"] = carril_sesion

                                        if pizarra_guardada and isinstance(pizarra_guardada, list) and len(pizarra_guardada) > 0:
                                            st.session_state.pizarra_entrenamiento = pizarra_guardada
                                            st.success("¡Estructura de series exacta inyectada con éxito! Revisa la pestaña de diseño.")
                                        else:
                                            bloques_reconstruidos = []  
                                            for est, mts in dict_estilos.items():  
                                                bloques_reconstruidos.append({  
                                                    "reps": 1,  
                                                    "dist": int(mts),  
                                                    "estilo": est,  
                                                    "intensidad": "Medio (Aeróbico Medio 5-6)",  
                                                    "implementos": datos_sesion.get("implementos_usados", []),  
                                                    "notas": ""  
                                                })  
                                            st.session_state.pizarra_entrenamiento = bloques_reconstruidos  
                                            st.warning("⚠️ Registro antiguo convertido: Se generó un bloque resumido por cada estilo.")
                                            
                                        st.rerun()  
                                        
                                with c_act2:  
                                    st.download_button(  
                                        label="📋 Descargar Reporte (TXT)",  
                                        data=texto_atleta.replace("**", ""),  
                                        file_name=f"reporte_{fecha_sesion}.txt",  
                                        mime="text/plain",  
                                        key=f"dl_txt_{fecha_sesion}_{carril_sesion}",  
                                        use_container_width=True  
                                    )  
                    else:  
                        st.info("💡 No se encontraron rutinas registradas en el periodo seleccionado.")  
                except Exception as err:  
                    st.error(f"Error procesando biblioteca de rutinas: {err}")  
            else:  
                st.warning("⚠️ No posees atletas asignados en este momento bajo tu perfil de Entrenador.")
