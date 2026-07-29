import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# Importación de tu librería unificada real
from formulas_lib_funciones import (
    convertir_string_a_segundos, 
    formatear_a_minutos, 
    calcular_edad_decimal, 
    calcular_categoria_competencia,
    obtener_pruebas_por_categoria
)

# Importamos la función de tu archivo dedicado
from conections_supabase_cache import obtener_todo_el_historial_cache

# =============================================================================
# EL FRAGMENTO: Todo lo que está aquí adentro se ejecuta de forma aislada
# =============================================================================
@st.fragment
def renderizar_tabs_aisladas(id_atleta_actual, cat_nadador, genero_nadador, ctx_supabase_mar, rol_usuario, id_usuario):
    # Carga ultra rápida desde la función caché dedicada
    df_marcas_raw = pd.DataFrame()
    if ctx_supabase_mar:
        datos_cacheados = obtener_todo_el_historial_cache(id_atleta_actual)
        if datos_cacheados:
            df_marcas_raw = pd.DataFrame(datos_cacheados)

    subtab_ingreso, subtab_top_tiempos, subtab_evolucion_prueba = st.tabs([
        "📥 1. Ingresar y Gestionar Marcas",
        "🥇 2. Reporte de Mejores Tiempos (Top Histórico)", 
        "📈 3. Buscador Histórico y Evolución Cronológica"
    ])

    # --- SUBTAB 1: INGRESO Y GESTIÓN ---
    with subtab_ingreso:
        lista_pruebas_restringida = obtener_pruebas_por_categoria(cat_nadador)
        
        prueba_local_activa = st.selectbox(
            f"🏊‍♂️ Seleccione la Prueba para {cat_nadador}:", 
            options=lista_pruebas_restringida,
            index=1 if len(lista_pruebas_restringida) > 1 else 0,
            key="sb_prueba_local_ingreso"
        )
        
        st.markdown("---")
        
        if prueba_local_activa.startswith("---"):
            st.warning("👆 Selecciona una distancia o estilo real de la lista (evita marcar los títulos de sección).")
        else:
            col_form, col_tabla_rapida = st.columns([1, 1.2])
            
            with col_form:
                st.markdown(f"**Ingresar Nueva Marca ➔ {prueba_local_activa}**")
                with st.form("form_insertar_marca", clear_on_submit=True):
                    ins_fecha_evento = st.date_input("Fecha de la Competencia:", value=datetime.date.today())
                    ins_tiempo_str = st.text_input("Tiempo Oficial (Formato mm:ss.hh):", placeholder="01:13.34")
                    ins_nota = st.text_input("Evento Año - Lugar:")
                    
                    if st.form_submit_button("💾 Guardar Registro"):
                        if rol_usuario in ["Head Coach", "Entrenador", "Administrador"] or id_usuario == id_atleta_actual:
                            try:
                                ins_tiempo = convertir_string_a_segundos(ins_tiempo_str)
                                
                                atleta_query = ctx_supabase_mar.table("usuarios").select("fecha_nacimiento").eq("id", id_atleta_actual).execute()
                                fecha_nacimiento_atleta = atleta_query.data[0]["fecha_nacimiento"] if atleta_query.data else None
                                
                                if not fecha_nacimiento_atleta:
                                    st.error("❌ El atleta no posee fecha de nacimiento configurada.")
                                else:
                                    edad_calculada = calcular_edad_decimal(fecha_nacimiento_atleta, ins_fecha_evento)
                                    nueva_m = {
                                        "prueba": prueba_local_activa, 
                                        "edad": float(edad_calculada), 
                                        "tiempo": float(ins_tiempo),
                                        "nota": ins_nota, 
                                        "usuario_id": id_atleta_actual
                                    }
                                    ctx_supabase_mar.table("marcas_historicas").insert(nueva_m).execute()
                                    
                                    st.cache_data.clear()
                                    st.success(f"¡Marca guardada con éxito en {prueba_local_activa}!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error al procesar: {e}")
                        else:
                            st.error("❌ No posees los permisos requeridos para modificar este registro.")
            
            with col_tabla_rapida:
                st.markdown(f"**Historial de la Prueba: {prueba_local_activa}**")
                
                if not df_marcas_raw.empty:
                    df_filtrado_local = df_marcas_raw[df_marcas_raw["prueba"] == prueba_local_activa].copy()
                    
                    if not df_filtrado_local.empty:
                        df_visual = df_filtrado_local.copy()
                        df_visual["tiempo"] = df_visual["tiempo"].apply(lambda x: formatear_a_minutos(float(x)))
                        
                        if rol_usuario in ["Head Coach", "Entrenador", "Administrador"]:
                            opciones_del = {
                                f"Edad: {round(r['edad'],2)} | T: {r['tiempo']} | {r['nota']}": r['id'] 
                                for _, r in df_filtrado_local.iterrows()
                            }
                            sel_del = st.selectbox("Eliminar Registro Histórico:", options=list(opciones_del.keys()))
                            if st.button("🗑️ Eliminar Fila Seleccionada"):
                                ctx_supabase_mar.table("marcas_historicas").delete().eq("id", int(opciones_del[sel_del])).execute()
                                st.cache_data.clear()
                                st.rerun()
                        
                        st.dataframe(df_visual[["edad", "tiempo", "nota"]], use_container_width=True, hide_index=True)
                    else:
                        st.info(f"ℹ️ El atleta no posee marcas registradas en {prueba_local_activa}.")
                else:
                    st.info("💡 Base de datos vacía para este atleta.")

    # --- SUBTABS 2 Y 3: ANÁLISIS ---
    if not df_marcas_raw.empty:
        with subtab_top_tiempos:
            st.markdown("#### 🥇 Récords Personales Absolutos (Personal Best)")
            idx_mejores = df_marcas_raw.groupby('prueba')['tiempo'].idxmin()
            df_top = df_marcas_raw.loc[idx_mejores].copy().sort_values("prueba").reset_index(drop=True)
            
            df_tabla_top = pd.DataFrame({
                "Prueba": df_top["prueba"],
                "Tiempo Oficial": df_top["tiempo"].apply(lambda x: formatear_a_minutos(float(x))),
                "Edad Crono": df_top["edad"].round(2),
                "Competición": df_top["nota"]
            })
            st.write(df_tabla_top.to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)

        with subtab_evolucion_prueba:
            st.markdown("#### 📈 Buscador Histórico Dinámico y Líneas de Campeonato")
            st.caption(f"🎯 Categoría: **{cat_nadador}** | Género: **{genero_nadador}**")
            
            lista_pruebas_existentes = sorted(df_marcas_raw["prueba"].unique().tolist())
            p_sel = st.selectbox("Seleccione la Prueba a Graficar:", options=lista_pruebas_existentes, key="sb_evolucion_analisis")
            
            df_ev = df_marcas_raw[df_marcas_raw["prueba"] == p_sel].sort_values("edad").reset_index(drop=True)
            
            if not df_ev.empty:
                plt.close('all') 
                
                fig_mar, ax = plt.subplots(figsize=(8.5, 3.5))
                ax.plot(df_ev["edad"], df_ev["tiempo"], marker="o", color="#3498db", linewidth=1.8, label="Progreso")
                
                m_minima = None
                try:
                    ref_key = f"ref_{p_sel}_{cat_nadador}_{genero_nadador}"
                    if ref_key not in st.session_state:
                        ref_db = ctx_supabase_mar.table("marcas_referencia").select("m_ano").eq("prueba", p_sel).eq("categoria", cat_nadador).eq("genero", genero_nadador).execute().data
                        st.session_state[ref_key] = ref_db
                    else:
                        ref_db = st.session_state[ref_key]

                    if ref_db and ref_db[0].get("m_ano"):
                        m_minima = float(ref_db[0]["m_ano"])
                except Exception:
                    pass
                
                if m_minima:
                    ax.axhline(m_minima, color="#b58900", linestyle=":", linewidth=1.5, label=f"Mínima {cat_nadador}")
                    ax.set_ylim(bottom=min(df_ev["tiempo"].min(), m_minima) * 0.96)
                else:
                    ax.set_ylim(bottom=df_ev["tiempo"].min() * 0.96)
                
                ax.set_ylim(top=df_ev["tiempo"].max() * 1.04)
                ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: formatear_a_minutos(x)))
                ax.set_xlabel("Edad del Nadador (Años)", fontsize=8)
                ax.set_ylabel("Tiempo de Carrera", fontsize=8)
                ax.grid(True, linestyle=":", alpha=0.4)
                ax.legend(fontsize=7)
                
                st.pyplot(fig_mar)
                plt.close(fig_mar) 
                
                df_tabla_ev = pd.DataFrame({
                    "Edad": df_ev["edad"].round(2),
                    "Prueba": df_ev["prueba"],
                    "Tiempo": df_ev["tiempo"].apply(lambda x: formatear_a_minutos(x)),
                    "Nota": df_ev["nota"]
                })
                st.write(df_tabla_ev.to_html(index=False, classes="tabla-estilizada"), unsafe_allow_html=True)


# =============================================================================
# FUNCIÓN PRINCIPAL: Punto de entrada del módulo
# =============================================================================
def renderizar_tab_marcas(datos_sidebar=None):
    st.markdown("### ⏱️ Panel de Control Curricular y Marcas Oficiales")
    st.caption("Módulo centralizado para la gestión de marcas oficiales, análisis de récords personales y exportación curricular.")

    ctx_supabase_mar = st.session_state.get("supabase")
    rol_usuario = st.session_state.get("rol")
    id_usuario = st.session_state.get("usuario_id")
    id_atleta_actual = st.session_state.get("nadador_seleccionado_id")

    if not id_atleta_actual:
        st.info("💡 Por favor, selecciona un nadador en la barra lateral para gestionar sus marcas oficiales.")
        return

    # Extraemos metadatos una sola vez fuera del fragmento para evitar reprocesos
    cat_nadador, genero_nadador = "Desconocida", "F"
    if ctx_supabase_mar:
        meta_key = f"meta_atleta_{id_atleta_actual}"
        if meta_key not in st.session_state:
            try:
                atleta_meta = ctx_supabase_mar.table("usuarios").select("fecha_nacimiento, genero").eq("id", id_atleta_actual).execute().data
                st.session_state[meta_key] = atleta_meta
            except Exception as e:
                st.error(f"Error al calcular metadatos del atleta: {e}")
                atleta_meta = None
        else:
            atleta_meta = st.session_state[meta_key]

        if atleta_meta:
            genero_nadador = atleta_meta[0].get("genero", "F")
            cat_nadador, _ = calcular_categoria_competencia(str(atleta_meta[0]["fecha_nacimiento"])[:10])

    # Ejecutamos toda la lógica visual pesada dentro del entorno aislado
    renderizar_tabs_aisladas(id_atleta_actual, cat_nadador, genero_nadador, ctx_supabase_mar, rol_usuario, id_usuario)
