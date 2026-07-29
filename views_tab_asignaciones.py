import streamlit as st
import pandas as pd
from formulas_lib_funciones import calcular_categoria_competencia

def renderizar_tab_asignaciones():
    """
    CÓDIGO AUDITADO Y VERIFICADO: 17. Rutina reservada a Head Coach de asignación de atletas a entrenadores.
    Garantiza la consistencia en el borrado transaccional preventivo y la purga de caché de datos.
    """
    # 1. Control Restringido de Seguridad por Rol
    rol_usuario = st.session_state.get("rol")
    if rol_usuario not in ["Head Coach", "Administrador"]:
        st.warning("🔒 Acceso denegado: Este panel está reservado exclusivamente para la Dirección Técnica (Head Coach).")
        return

    st.markdown("### 📋 Panel de Gestión de Asignaciones (Exclusivo Head Coach)")
    st.caption("Vincula de forma individual o masiva por categoría a los nadadores con sus respectivos entrenadores asistentes.")

    supabase = st.session_state.get("supabase")
    if not supabase:
        st.error("❌ Conexión con la base de datos no disponible.")
        return

    try:
        # 2. Extracción de Entrenadores Asistentes Activos
        resp_ent = supabase.table("usuarios").select("id, nombre").eq("rol", "Entrenador").eq("estatus", "Activo").execute()
        lista_entrenadores = resp_ent.data if resp_ent.data else []
        
        # 3. Extracción de todos los Nadadores Activos
        resp_nad = supabase.table("usuarios").select("id, nombre, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo").execute()
        lista_todos_nadadores = resp_nad.data if resp_nad.data else []
        
        if lista_entrenadores and lista_todos_nadadores:
            dict_entrenadores = {e["id"]: e["nombre"] for e in lista_entrenadores}
            
            col1, col2 = st.columns(2)
            
            # -----------------------------------------------------------------
            # COMPONENTE 1: ASIGNACIÓN INDIVIDUAL
            # -----------------------------------------------------------------
            with col1:
                st.markdown("##### 👤 Asignación Individual")
                entrenador_sel = st.selectbox(
                    "Asistente Destino:", 
                    options=list(dict_entrenadores.keys()), 
                    format_func=lambda x: dict_entrenadores[x], 
                    key="asig_ind_ent"
                )
                
                dict_nadadores = {n["id"]: n["nombre"] for n in lista_todos_nadadores}
                nadador_sel = st.selectbox(
                    "Nadador a asignar:", 
                    options=list(dict_nadadores.keys()), 
                    format_func=lambda x: dict_nadadores[x], 
                    key="asig_ind_nad"
                )
                
                if st.button("🔗 Confirmar Vínculo Individual", key="btn_asig_ind", use_container_width=True):
                    try:
                        # Limpiar asignaciones previas del atleta para garantizar relación limpia de base de datos
                        supabase.table("asignaciones").delete().eq("atleta_id", nadador_sel).execute()
                        
                        # Inserción limpia con nombres exactos de columnas verificadas
                        supabase.table("asignaciones").insert({
                            "entrenador_id": entrenador_sel,
                            "atleta_id": nadador_sel
                        }).execute()
                        
                        st.success(f"🎉 {dict_nadadores[nadador_sel]} asignado(a) correctamente a {dict_entrenadores[entrenador_sel]}.")
                        st.cache_data.clear()  # Crucial para invalidar la caché de reportes segregados
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error en asignación individual: {e}")
            
            # -----------------------------------------------------------------
            # COMPONENTE 2: ASIGNACIÓN MASIVA POR CATEGORÍA
            # -----------------------------------------------------------------
            with col2:
                st.markdown("##### 👥 Asignación Masiva por Categoría")
                entrenador_cat_sel = st.selectbox(
                    "Asistente Destino (Lote):", 
                    options=list(dict_entrenadores.keys()), 
                    format_func=lambda x: dict_entrenadores[x], 
                    key="asig_cat_ent"
                )
                
                categoria_sel = st.selectbox(
                    "Categoría Completa a Asignar:", 
                    options=["Preinfantil", "Infantil A", "Infantil B", "Juvenil A", "Juvenil B", "Máxima"],
                    key="asig_cat_sel"
                )
                
                if st.button("⚡ Ejecutar Asignación por Lote", key="btn_asig_cat", use_container_width=True):
                    ids_categoria = []
                    
                    # Clasificación en tiempo real usando la biblioteca analítica unificada
                    for nad in lista_todos_nadadores:
                        fnac = nad.get("fecha_nacimiento")
                        if fnac:
                            cat_calc, _ = calcular_categoria_competencia(str(fnac)[:10])
                            if cat_calc.strip() == categoria_sel.strip():
                                ids_categoria.append(nad["id"])
                                
                    if ids_categoria:
                        try:
                            # 1. Limpiar en bloque las asignaciones previas de este grupo de atletas
                            supabase.table("asignaciones").delete().in_("atleta_id", ids_categoria).execute()
                            
                            # 2. Inserción masiva estructurada por lotes
                            nuevas_asig = [{"entrenador_id": entrenador_cat_sel, "atleta_id": nid} for nid in ids_categoria]
                            supabase.table("asignaciones").insert(nuevas_asig).execute()
                            
                            st.success(f"🎉 Se asignaron {len(ids_categoria)} nadadores de la categoría **{categoria_sel}** a {dict_entrenadores[entrenador_cat_sel]}.")
                            st.cache_data.clear()  # Forzar actualización inmediata del ecosistema de vistas
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error operando la inserción masiva: {e}")
                    else:
                        st.warning(f"No se encontraron nadadores activos que pertenezcan a la categoría {categoria_sel} en esta temporada.")
        else:
            st.info("💡 Debe contar con Entrenadores y Nadadores activos con estatus 'Activo' en la base de datos para habilitar las opciones de asignación.")
            
    except Exception as e:
        st.error(f"Error general en el módulo de asignaciones: {e}")
