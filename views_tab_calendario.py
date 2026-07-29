import streamlit as st
import pandas as pd
import datetime

# Importación de funciones core de soporte analítico
from formulas_lib_funciones import (
    calcular_edad_tecnica_al_31_dic,
    evaluar_elegibilidad_internacional,
    calcular_fecha_alerta
)

def renderizar_tab_calendario():
    """
    CÓDIGO CORREGIDO Y OPTIMIZADO: 16. Rutina reservada de captura de calendario 
    y generación masiva de hitos. Aplica optimización de consultas SQL y validación.
    """
    st.markdown("### 📅 Gestión del Calendario de Competencias")
    
    supabase = st.session_state.get("supabase")
    rol_usuario = st.session_state.get("rol")
    id_usuario = st.session_state.get("usuario_id")
    
    if not supabase:
        st.error("❌ Conexión con el servidor no disponible.")
        return

    temporada_actual = datetime.date.today().year
    st.markdown(f"**Competencias Programadas - Temporada {temporada_actual}**")
    
    # 1. Carga de datos inicial con manejo seguro
    dict_comps = {}
    try:
        resp_comp = supabase.table("catalogo_competencias").select("*").eq("temporada", temporada_actual).order("fecha_inicio", desc=False).execute()
        resp_comp_data = resp_comp.data if resp_comp.data else []
    except Exception as e:
        st.error(f"Error cargando calendario: {e}")
        resp_comp_data = []

    # Visualización pública
    if resp_comp_data:
        df_comp = pd.DataFrame(resp_comp_data)
        df_comp["fecha_inicio"] = pd.to_datetime(df_comp["fecha_inicio"]).dt.strftime('%d-%m-%Y')
        df_comp["fecha_fin"] = pd.to_datetime(df_comp["fecha_fin"]).dt.strftime('%d-%m-%Y')
        st.dataframe(df_comp[["nombre_evento", "ente_rector", "categoria_evento", "fecha_inicio", "fecha_fin"]], use_container_width=True, hide_index=True)
        dict_comps = {f"{c['nombre_evento']} ({c['fecha_inicio']})": c for c in resp_comp_data}
    else:
        st.info(f"No hay competencias registradas para la temporada {temporada_actual}.")

    # 2. Controles de Edición (Restringido)
    if rol_usuario in ["Head Coach", "Administrador"]:
        st.markdown("---")
        col_add, col_edit = st.columns(2)
        
        with col_add:
            st.markdown("**➕ Programar Nueva Competencia**")
            with st.form("form_add_comp", clear_on_submit=True):
                add_temp = st.number_input("Temporada:", min_value=2024, value=temporada_actual)
                add_nombre = st.text_input("Nombre del Evento:")
                add_ente = st.selectbox("Ente Rector:", ["FEVEDA", "PANAM", "SURAM", "WA"])
                add_cat = st.selectbox("Nivel:", ["Nacional", "Internacional"])
                c1, c2 = st.columns(2)
                add_f_ini = c1.date_input("Inicio:")
                add_f_fin = c2.date_input("Fin:")
                
                if st.form_submit_button("💾 Guardar"):
                    if add_f_fin < add_f_ini:
                        st.error("La fecha de fin no puede ser anterior a la de inicio.")
                    elif not add_nombre:
                        st.error("Nombre obligatorio.")
                    else:
                        supabase.table("catalogo_competencias").insert({
                            "temporada": add_temp, "nombre_evento": add_nombre, "ente_rector": add_ente,
                            "categoria_evento": add_cat, "fecha_inicio": add_f_ini.isoformat(),
                            "fecha_fin": add_f_fin.isoformat(), "creador_id": id_usuario
                        }).execute()
                        st.rerun()

        with col_edit:
            st.markdown("**✏️ Auditar / Posponer**")
            if dict_comps:
                comp_sel = st.selectbox("Seleccionar:", list(dict_comps.keys()))
                datos_c = dict_comps[comp_sel]
                with st.form("form_edit_comp"):
                    edit_nombre = st.text_input("Nombre:", value=datos_c["nombre_evento"])
                    c_i, c_f = st.columns(2)
                    edit_f_ini = c_i.date_input("Inicio:", value=datetime.date.fromisoformat(datos_c["fecha_inicio"]))
                    edit_f_fin = c_f.date_input("Fin:", value=datetime.date.fromisoformat(datos_c["fecha_fin"]))
                    if st.form_submit_button("🔄 Aplicar"):
                        supabase.table("catalogo_competencias").update({
                            "fecha_inicio": edit_f_ini.isoformat(), "fecha_fin": edit_f_fin.isoformat(), "nombre_evento": edit_nombre
                        }).eq("id", datos_c["id"]).execute()
                        st.rerun()

        # 3. Generador de Hitos (Optimizado)
        st.markdown("---")
        st.markdown("### 🎯 Generación de Hitos")
        if dict_comps:
            comp_ins = st.selectbox("Competencia a procesar:", options=list(dict_comps.keys()))
            datos_ins = dict_comps[comp_ins]
            
            if st.button("🚀 Procesar Nómina"):
                with st.spinner("Evaluando normativas..."):
                    try:
                        # Consulta optimizada: 1 solo hit a la BD para obtener todos los hitos existentes
                        hitos_existentes = supabase.table("historial_hitos").select("usuario_id").eq("competencia_id", datos_ins["id"]).execute()
                        set_ids_existentes = {h["usuario_id"] for h in hitos_existentes.data} if hitos_existentes.data else set()
                        
                        atletas = supabase.table("usuarios").select("id, nombre, fecha_nacimiento").eq("rol", "Nadador").eq("estatus", "Activo").execute().data
                        
                        contadores = {"elegibles": 0, "ineligibles": 0, "omitidos": 0}
                        for atleta in atletas:
                            if atleta["id"] in set_ids_existentes:
                                contadores["omitidos"] += 1
                                continue
                            
                            edad_t = calcular_edad_tecnica_al_31_dic(atleta["fecha_nacimiento"], datos_ins["temporada"])
                            elegible, motivo = evaluar_elegibilidad_internacional(edad_t, datos_ins["ente_rector"])
                            f_alerta = calcular_fecha_alerta(datos_ins["fecha_inicio"], 15)
                            
                            supabase.table("historial_hitos").insert({
                                "usuario_id": atleta["id"], "competencia_id": datos_ins["id"],
                                "temporada_auditada": datos_ins["temporada"], "elegible": elegible,
                                "motivo_ineligibilidad": motivo if not elegible else None,
                                "estado_cumplimiento": "Pendiente", "fecha_alerta": f_alerta.isoformat()
                            }).execute()
                            
                            contadores["elegibles" if elegible else "ineligibles"] += 1
                        
                        st.success("✅ Proceso completado.")
                        st.info(f"📊 {contadores['elegibles']} elegibles | {contadores['ineligibles']} ineligibles | {contadores['omitidos']} ya registrados.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error técnico: {e}")
