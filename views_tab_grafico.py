import streamlit as st
import io
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib
matplotlib.use('Agg')

# 📦 IMPORTACIONES DE FUNCIONES LOCALES
from formulas_lib_funciones import (
    resolver_k_individual, 
    calcular_curva_atleta, 
    formatear_a_minutos,
    procesar_mejor_marca_historica,
    calcular_puntos_wa,
    obtener_datos_hitos_atleta,
    dibujar_lineas_referencia
)

from conections_supabase_cache import (
    obtener_marcas_referencia_cache, 
    obtener_historial_hitos_cache,
    obtener_marcas_historicas_cache  # <-- NUEVO: Vital para el Modo Equipo nativo
)

def renderizar_tab_grafico(datos_sidebar):
    """
    Renderiza el gráfico de rendimiento combinando proyecciones exponenciales,
    datos históricos reales y referencias obtenidas directamente desde Supabase.
    """
    # =====================================================================
    # 1. EXTRACCIÓN DE VARIABLES Y CONTEXTO
    # =====================================================================
    modo_equipo = datos_sidebar.get("modo_equipo", False)
    simulacion_externa = datos_sidebar.get("simulacion_externa", False)
    tipo_vista = datos_sidebar.get("tipo_vista", "Macro (Historial Completo)")
    titulo_grafico = datos_sidebar.get("titulo_grafico", "Proyección de Rendimiento")
    
    t_peak = float(datos_sidebar.get("t_peak", 23.0))
    T_target = float(datos_sidebar.get("T_target", 0.0))
    h = float(datos_sidebar.get("factor_h", 0.35))
    t_intermedia = float(datos_sidebar.get("t_intermedia", 18.0))

    prueba = datos_sidebar.get("prueba_seleccionada", datos_sidebar.get("titulo_grafico", ""))
    genero = datos_sidebar.get("genero", datos_sidebar.get("genero_atleta", "M"))
    categoria = datos_sidebar.get("categoria", datos_sidebar.get("categoria_atleta", ""))
    usuario_id = datos_sidebar.get("usuario_id", datos_sidebar.get("id", ""))
    es_preinfantil = "Preinfantil" in categoria

    edad_min_zoom = datos_sidebar.get("edad_min_zoom", 10.0)
    edad_max_zoom = datos_sidebar.get("edad_max_zoom", 25.0)

    st.session_state.nadador_seleccionado_nombre = datos_sidebar.get("nombre", "Atleta")
    st.session_state.nadador_seleccionado_categoria = categoria
    st.session_state.nadador_seleccionado_id = usuario_id

    # =====================================================================
    # 2. CONSULTAS A LA CACHÉ DE SUPABASE Y MAPEADO DE REFERENCIAS
    # =====================================================================
    referencias_raw = []
    if not simulacion_externa and not modo_equipo:
        referencias_raw = obtener_marcas_referencia_cache(prueba, genero, categoria)

    m_ano = m_panam_b = m_panam_a = m_wa_b = m_wa_a = m_wr = 0.0
    for ref in referencias_raw:
        nombre_marca = ref.get("nombre_marca", ref.get("nombre", "")).upper()
        try:
            val = float(ref.get("tiempo", 0))
        except (ValueError, TypeError): continue
        
        if "MÍNIMA" in nombre_marca or "AÑO" in nombre_marca: m_ano = val
        elif "PANAM" in nombre_marca and "B" in nombre_marca: m_panam_b = val
        elif "PANAM" in nombre_marca and "A" in nombre_marca: m_panam_a = val
        elif "WA B" in nombre_marca: m_wa_b = val
        elif "WA A" in nombre_marca: m_wa_a = val
        elif "RECORD" in nombre_marca or "WR" in nombre_marca: m_wr = val

    # =====================================================================
    # 3. RECOPILACIÓN DE DATOS Y MOTOR MATEMÁTICO (INDIVIDUAL)
    # =====================================================================
    df_procesado = pd.DataFrame()
    atletas_filtrados = []

    if modo_equipo:
        atletas_filtrados = datos_sidebar.get("lista_atletas_filtrados", [])
        if not atletas_filtrados:
            st.warning("No se encontraron atletas activos con los criterios de segmentación elegidos.")
            return
    else:
        if simulacion_externa:
            t0 = float(datos_sidebar.get("t0", 10.0))
            T0 = float(datos_sidebar.get("T0", 0.0))
            t_pb = float(datos_sidebar.get("t_pb", 12.0))
            T_pb = float(datos_sidebar.get("T_pb", 0.0))
            if T0 == 0.0 or T_pb == 0.0:
                st.info("Ingrese valores válidos en el simulador del panel lateral (T0 y T_pb).")
                return
        else:
            df_procesado = datos_sidebar.get("df_procesado")
            if df_procesado is None or df_procesado.empty:
                st.info("No hay marcas históricas registradas para este nadador en la prueba seleccionada.")
                return
            t0, T0, t_pb, T_pb = procesar_mejor_marca_historica(df_procesado)

    # Variables de compatibilidad para dibujado individual
    if not modo_equipo:
        val_T0 = T0
        val_T_pb = T_pb
        k = resolver_k_individual(t0, T0, t_pb, T_pb, t_peak, T_target)
        if k is None: k = 1e6 
        edades_curva = np.linspace(t0, t_peak, 300)
        tiempos_curva = calcular_curva_atleta(edades_curva, t0, T0, t_pb, T_pb, t_peak, T_target, k, h)
        T_intermedia_val = np.interp(t_intermedia, edades_curva, tiempos_curva)

    # =====================================================================
    # 4. ENCABEZADOS E INTERFAZ (MÉTRICAS)
    # =====================================================================
    if simulacion_externa:
        st.warning("⚠️ Modo Simulación Activo: Proyecciones basadas estrictamente en los parámetros ingresados.")
        st.subheader("Modo Simulación Externa (Proyección Aislada)")
    elif modo_equipo:
        st.subheader(f"Modo Equipo: {titulo_grafico}")
    else:
        st.subheader(f"Modo Individual - Vista {tipo_vista}: {titulo_grafico}")

    if not modo_equipo and T0 != 0.0 and T_pb != 0.0:
        D_principal = T_pb - T_target
        c1, c2, c3 = st.columns(3)
        with c1: st.metric(label="Factor de Ajuste (k)", value=f"{k:.4f}")
        with c2: st.metric(label="Margen de Deriva (D)", value=f"{formatear_a_minutos(D_principal)}")
        with c3: st.metric(label=f"Proyección a los {t_intermedia} años", value=formatear_a_minutos(T_intermedia_val))

    # =====================================================================
    # 5. LIENZO Y DIBUJO ESTÉTICO
    # =====================================================================
    fig = plt.figure(figsize=(8.5, 11.0))
    ax = fig.add_axes([0.14, 0.58, 0.72, 0.33])
    formateador_eje_y = FuncFormatter(lambda x, pos: formatear_a_minutos(x))
    ax.yaxis.set_major_formatter(formateador_eje_y)

# -------------------------------------------------------------
    # MODO EQUIPO - ARQUITECTURA NATIVA (EXTRACCIÓN + VALLES)
    # -------------------------------------------------------------
    df_global_marcas_reconstruido = []
    
    if modo_equipo:
        colores = plt.get_cmap("tab10", len(atletas_filtrados))
        hay_datos_visibles = False
        linea_fisiologica_anotada = False
        
        todas_las_edades_0 = []
        todos_los_tiempos_colectivo = []
        datos_atletas_cargados = []
        
        # --- 1. PROCESAMIENTO: Extracción de datos ---
        for idx, atl in enumerate(atletas_filtrados):
            a_id = atl.get("usuario_id", atl.get("id"))
            a_nom = atl.get("nombre", f"Atleta {idx+1}")
            
            try:
                marcas_raw = obtener_marcas_historicas_cache(usuario_id=a_id, prueba=prueba)
            except Exception:
                marcas_raw = []
                
            if not marcas_raw: continue
            
            df_raw = pd.DataFrame(marcas_raw)
            if df_raw.empty: continue
            
            if "prueba" in df_raw.columns:
                df_prueba = df_raw[df_raw["prueba"].astype(str).str.strip().str.lower() == prueba.strip().lower()].copy()
            else:
                df_prueba = df_raw.copy()
            
            if df_prueba.empty: continue
            
            df_atl_m = df_prueba.rename(columns={"edad": "Edad", "tiempo": "Tiempo", "nota": "Evento / Fecha"})
            if "Tiempo" not in df_atl_m.columns or "Edad" not in df_atl_m.columns:
                continue
                
            df_atl_m["Tiempo"] = pd.to_numeric(df_atl_m["Tiempo"], errors="coerce")
            df_atl_m["Edad"] = pd.to_numeric(df_atl_m["Edad"], errors="coerce")
            df_atl_m = df_atl_m.dropna(subset=["Tiempo", "Edad"]).sort_values(by="Edad").reset_index(drop=True)
            
            if df_atl_m.empty: continue
            
            hay_datos_visibles = True
            todas_las_edades_0.append(float(df_atl_m.iloc[0]["Edad"]))
            todos_los_tiempos_colectivo.extend(df_atl_m["Tiempo"].tolist())
            datos_atletas_cargados.append({"nom": a_nom, "df": df_atl_m, "color": colores(idx)})
            
            df_export = df_atl_m.copy()
            df_export["Atleta"] = a_nom
            df_global_marcas_reconstruido.append(df_export)

        # --- 2. RENDERIZADO: Gráfico único (FUERA DEL BUCLE) ---
        if hay_datos_visibles:
            # Configuración ejes X
            edad_0_min_colectivo = min(todas_las_edades_0)
            lim_x_min = max(4.0, edad_0_min_colectivo - 0.5)
            lim_x_max = t_peak + 1.0 
            ax.set_xlim(lim_x_min, lim_x_max)
            
# 2. Consultar BD usando filtros reales del usuario
            ref_wr_data = obtener_marcas_referencia_cache(prueba=prueba, genero=genero, categoria=categoria)
            
            m_wr = None
            if ref_wr_data and isinstance(ref_wr_data, list) and len(ref_wr_data) > 0:
                datos = ref_wr_data[0]
                # Accedemos a la columna 'm_wr' tal como aparece en tu tabla
                if isinstance(datos, dict) and 'm_wr' in datos:
                    val_wr = datos['m_wr']
                    if val_wr is not None:
                        m_wr = float(val_wr)
            # Límites Y
            peor_tiempo = max(todos_los_tiempos_colectivo)
            mejor_tiempo = min(todos_los_tiempos_colectivo)
            lim_y_inferior = m_wr * 0.92 if m_wr else mejor_tiempo * 0.95
            lim_y_superior = peor_tiempo * 1.05
            ax.set_ylim(lim_y_inferior, lim_y_superior)

            # Dibujado de atletas y curvas
            for item in datos_atletas_cargados:
                df_atl_m = item["df"]
                color_curr = item["color"]
                a_nom = item["nom"]
                
                # Algoritmo de Valles
                t0_i, T0_i, t_pb_i, T_pb_i = procesar_mejor_marca_historica(df_atl_m)
                k_i = resolver_k_individual(t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target)
                if k_i is None: k_i = 1e6
                edades_curva_i = np.linspace(t0_i, t_peak, 300)
                tiempos_curva_i = calcular_curva_atleta(edades_curva_i, t0_i, T0_i, t_pb_i, T_pb_i, t_peak, T_target, k_i, h)
                
                # Plot fisiológico
                ax.plot(edades_curva_i, tiempos_curva_i, color="#7F8C8D", linestyle=":", linewidth=1.2, label="Proyección" if not linea_fisiologica_anotada else "")
                linea_fisiologica_anotada = True
                
                # Plot Atleta
                ax.plot(df_atl_m["Edad"], df_atl_m["Tiempo"], color=color_curr, linestyle="-", linewidth=1.5, label=f"{a_nom}")
                ax.scatter(df_atl_m["Edad"], df_atl_m["Tiempo"], color=color_curr, edgecolor="black", s=25, linewidths=0.5, zorder=3)
                ax.scatter(t_pb_i, T_pb_i, color=color_curr, marker="*", edgecolor="black", s=80, linewidths=0.5, zorder=5)

            ref_wr_data = obtener_marcas_referencia_cache(prueba=prueba, genero=genero, categoria=categoria)
            dibujar_lineas_referencia(ax, ref_wr_data, lim_x_min, lim_x_max, peor_tiempo)

            # Finalización
            ax.set_title(f"Análisis Comparativo de Equipo - {titulo_grafico}", fontsize=12, pad=10)
            ax.set_xlabel("Edad del Atleta (Años)", fontsize=9.5)
            ax.set_ylabel("Tiempo de Carrera (Segundos)", fontsize=9.5)
            ax.grid(True, which="both", axis="both", linestyle=":", color="#CCD1D1", linewidth=0.5)
            ax.set_axisbelow(True)
            ax.legend(loc="upper right", fontsize=8, framealpha=0.8)
            st.pyplot(fig, use_container_width=True)
        else:
            st.info(f"Ninguno de los atletas seleccionados tiene marcas registradas para: {prueba}.")
            return

    # -------------------------------------------------------------
    # MODO INDIVIDUAL O SIMULACIÓN
    # -------------------------------------------------------------
    else:
        todos_los_tiempos_ind = [T0, T_pb, T_target]
        if not simulacion_externa and len(df_procesado) > 0:
            todos_los_tiempos_ind.extend(df_procesado["Tiempo"].tolist())

        if tipo_vista == "Micro (Ventana Anual)":
            edades_ventana = np.linspace(edad_min_zoom, edad_max_zoom, 300)
            tiempos_curva_ventana = calcular_curva_atleta(edades_ventana, t0, T0, t_pb, T_pb, t_peak, T_target, k, h).tolist()
            
            tiempos_reales_ventana = []
            if not simulacion_externa and len(df_procesado) > 0:
                for _, row in df_procesado.iterrows():
                    if edad_min_zoom <= row["Edad"] <= edad_max_zoom:
                        tiempos_reales_ventana.append(row["Tiempo"])
                        
            todos_tiempos_v = tiempos_curva_ventana + tiempos_reales_ventana
            
            if todos_tiempos_v:
                t_min_v = min(todos_tiempos_v)
                t_max_v = max(todos_tiempos_v)
            else:
                t_min_v = min(tiempos_curva)
                t_max_v = max(tiempos_curva)

            margen_y = max(0.5, (t_max_v - t_min_v) * 0.15)
            lim_y_inferior = t_min_v - margen_y
            lim_y_superior = t_max_v + margen_y
            lim_x_min = edad_min_zoom
            lim_x_max = edad_max_zoom
        else:
            peor_tiempo_ind = max(todos_los_tiempos_ind)
            lim_y_inferior = m_wr * 0.92 if m_wr > 0 else min(todos_los_tiempos_ind) * 0.90
            lim_y_superior = peor_tiempo_ind + (peor_tiempo_ind * 0.08)
            
            if len(df_procesado) > 0:
                min_edad_real = float(df_procesado["Edad"].min())
                lim_x_min = min(float(t0), min_edad_real) - 0.5
            else:
                lim_x_min = max(4.0, float(t0) - 0.5)
                
            lim_x_max = t_peak + 1.0

        ax.set_xlim(lim_x_min, lim_x_max)
        ax.set_ylim(lim_y_inferior, lim_y_superior)
        ax.set_autoscale_on(False)

        datos_tabla_micro = []
        if usuario_id and tipo_vista == "Micro (Ventana Anual)":
            datos_atleta = obtener_datos_hitos_atleta(usuario_id)
            if datos_atleta and datos_atleta.get("fecha_nacimiento"):
                try:
                    fecha_nacimiento_real = datetime.date.fromisoformat(str(datos_atleta["fecha_nacimiento"])[:10])
                except Exception:
                    fecha_nacimiento_real = None
                
                if fecha_nacimiento_real:
                    for hito in datos_atleta.get("hitos", []):
                        try:
                            comp_info = hito.get("catalogo_competencias")
                            if not comp_info: continue
                            
                            fecha_comp_str = comp_info.get("fecha_inicio") or comp_info.get("fecha")
                            if not fecha_comp_str: continue
                            
                            if isinstance(fecha_comp_str, str):
                                fecha_evento_real = datetime.date.fromisoformat(fecha_comp_str[:10])
                            elif isinstance(fecha_comp_str, (datetime.date, datetime.datetime)):
                                fecha_evento_real = fecha_comp_str if isinstance(fecha_comp_str, datetime.date) else fecha_comp_str.date()
                            else: continue
                            
                            dias_de_vida = (fecha_evento_real - fecha_nacimiento_real).days
                            edad_hito_calculada = dias_de_vida / 365.25

                            if lim_x_min <= edad_hito_calculada <= lim_x_max:
                                es_elegible = hito.get("elegible", True)
                                color_linea = "#2ECC71" if es_elegible else "#E74C3C" 
                                estilo_linea = "--" if es_elegible else ":"
                                
                                ax.axvline(x=edad_hito_calculada, color=color_linea, linestyle=estilo_linea, linewidth=0.7, alpha=0.6, zorder=5)
                                
                                y_pos = lim_y_inferior + ((lim_y_superior - lim_y_inferior) * 0.03)
                                nombre_evento = comp_info.get("nombre_evento") or "Competencia"
                                nombre_corto = nombre_evento[:18] + "..." if len(nombre_evento) > 18 else nombre_evento
                                
                                ax.text(x=edad_hito_calculada + 0.015, y=y_pos, s=f"{nombre_corto} {fecha_evento_real.strftime('%d/%m/%Y')}", color=color_linea, fontsize=7.5, weight="light", rotation=90, va="bottom", ha="left", alpha=0.85, zorder=6)

                                tiempo_proyectado_val = calcular_curva_atleta([edad_hito_calculada], t0, T0, t_pb, T_pb, t_peak, T_target, k, h)[0]
                                
                                datos_tabla_micro.append({
                                    "Competencia / Evento": nombre_evento,
                                    "Fecha": fecha_evento_real.strftime('%d/%m/%Y'),
                                    "Edad": f"{edad_hito_calculada:.2f} a",
                                    "Marca Proyectada": f"{formatear_a_minutos(tiempo_proyectado_val)} s"
                                })
                        except Exception as e_hito:
                            pass

        if datos_tabla_micro:
            datos_tabla_micro.sort(key=lambda x: float(x["Edad"].replace(" a", "").strip()))

        ax.plot(edades_curva, tiempos_curva, color="#007A87", linewidth=1.8, label="Proyección Fisiológica")

        if not simulacion_externa and len(df_procesado) > 0:
            ax.plot(df_procesado["Edad"], df_procesado["Tiempo"], color="#D55E00", linestyle="--", linewidth=1.0, alpha=0.6, label="Evolución Real (PBs)")
            ax.scatter(df_procesado["Edad"], df_procesado["Tiempo"], color="#D55E00", edgecolor="black", s=25, linewidths=0.6, zorder=3)

        offset_y = (lim_y_superior - lim_y_inferior) * 0.025
        estilo_bbox = dict(boxstyle="round,pad=0.25", fc="#F8F9F9", ec="#BDC3C7", alpha=0.9, linewidth=0.5)

        if lim_x_min <= t0 <= lim_x_max and lim_y_inferior <= T0 <= lim_y_superior:
            ax.scatter(t0, T0, color="#7F8C8D", edgecolor="black", s=35, linewidths=0.6, zorder=4)
            ax.text(t0 + 0.1, T0, f"P. Start\n{t0:.2f}a\n{formatear_a_minutos(val_T0)}", fontsize=8, va="bottom", ha="left", bbox=estilo_bbox)
            ax.axvline(x=t0, color="#7F8C8D", linestyle=":", linewidth=0.7, alpha=0.5)

        if lim_x_min <= t_pb <= lim_x_max and lim_y_inferior <= T_pb <= lim_y_superior:
            ax.scatter(t_pb, T_pb, color="#F1C40F", marker="*", edgecolor="black", s=100, linewidths=0.6, zorder=5, label="PB Actual de Control")
            ax.text(t_pb + 0.15, T_pb, f"PB Actual\n{t_pb:.2f}a\n{formatear_a_minutos(val_T_pb)}", fontsize=8, va="center", ha="left", bbox=estilo_bbox)
            ax.axvline(x=t_pb, color="red", linestyle="--", linewidth=0.7, alpha=0.4)

        if lim_x_min <= t_intermedia <= lim_x_max and lim_y_inferior <= T_intermedia_val <= lim_y_superior:
            ax.scatter(t_intermedia, T_intermedia_val, color="red", marker="o", s=30, zorder=5, label="Punto Consultado")
            ax.text(t_intermedia, T_intermedia_val + offset_y, f"Consulta: {t_intermedia:.1f}a\n{formatear_a_minutos(T_intermedia_val)}", fontsize=8, va="bottom", ha="center", bbox=estilo_bbox)
            ax.axvline(x=t_intermedia, color="red", linestyle=":", linewidth=0.7, alpha=0.4)

        if lim_x_min <= t_peak <= lim_x_max and lim_y_inferior <= T_target <= lim_y_superior:
            ax.scatter(t_peak, T_target, color="#2ECC71", marker="s", edgecolor="black", s=35, linewidths=0.6, zorder=4, label="Meta Peak")
            ax.text(t_peak - 0.1, T_target, f"Meta Peak\n{t_peak:.2f}a\n{formatear_a_minutos(T_target)}", fontsize=8, va="bottom", ha="right", bbox=estilo_bbox)
            ax.axvline(x=t_peak, color="#2ECC71", linestyle=":", linewidth=0.7, alpha=0.5)

        x_texto = lim_x_min + (lim_x_max - lim_x_min) * 0.05
        ref_wr_data = obtener_marcas_referencia_cache(prueba=prueba, genero=genero, categoria=categoria)
        
        # 2. Dibujar las líneas
        if not es_preinfantil:
            dibujar_lineas_referencia(ax, ref_wr_data, lim_x_min, lim_x_max)
        
        if simulacion_externa:
            ax.set_title(f"Simulación de Escenarios - {titulo_grafico}", fontsize=12, pad=10)
        else:
            ax.set_title(f"Curva de Rendimiento Asintótica - {titulo_grafico}\nAtleta: {st.session_state.nadador_seleccionado_nombre} | Categoría: {st.session_state.nadador_seleccionado_categoria}", fontsize=12, pad=10)

        ax.set_xlabel("Edad del Atleta (Años)", fontsize=9.5)
        ax.set_ylabel("Tiempo de Carrera (Segundos)", fontsize=9.5)
        ax.grid(True, which="both", axis="both", linestyle=":", color="#CCD1D1", linewidth=0.5)
        ax.set_axisbelow(True) 
        
        tamano_leyenda = 6.5 if tipo_vista == "Micro (Ventana Anual)" else 8
        ax.legend(loc="upper right", fontsize=tamano_leyenda, framealpha=0.8)

        # -------------------------------------------------------------
        # TABLA NATIVA INFERIOR
        # -------------------------------------------------------------
        df_table_render = None
        es_modo_micro_tabla = (tipo_vista == "Micro (Ventana Anual)")

        if es_modo_micro_tabla:
            if datos_tabla_micro:
                df_table_render = pd.DataFrame(datos_tabla_micro)
                anchos_columnas = [0.46, 0.18, 0.16, 0.20]
            else:
                df_table_render = pd.DataFrame([{
                    "Competencia / Evento": "No hay hitos o competencias en este rango de edad",
                    "Fecha": "-",
                    "Edad": "-",
                    "Tiempo Prog.": "-"
                }])
                anchos_columnas = [0.52, 0.16, 0.16, 0.16]
        else:
            if not simulacion_externa and len(df_procesado) > 0:
                df_table_render = df_procesado[["Edad", "Tiempo", "Evento / Fecha"]].copy()
                wr_referencia_real = m_wr
                
                df_table_render["WA"] = df_table_render["Tiempo"].apply(lambda x: calcular_puntos_wa(x, wr_referencia_real))
                df_table_render = df_table_render[["Edad", "Tiempo", "WA", "Evento / Fecha"]]
                
                df_table_render["Edad"] = df_table_render["Edad"].map(lambda x: f"{x:.2f} a")
                df_table_render["Tiempo"] = df_table_render["Tiempo"].apply(formatear_a_minutos)
                df_table_render["WA"] = df_table_render["WA"].map(lambda x: f"{x} pts" if x > 0 else "-")
                
                anchos_columnas = [0.13, 0.13, 0.14, 0.60]
            else:
                df_table_render = pd.DataFrame([{
                    "Edad": "-", 
                    "Tiempo": "-", 
                    "WA": "-",
                    "Evento / Fecha": "Sin marcas históricas registradas"
                }])
                anchos_columnas = [0.13, 0.13, 0.14, 0.60]

        if df_table_render is not None and not df_table_render.empty:
            total_filas = len(df_table_render)
            limite_filas_por_bloque = 18
            
            def estilizar_tabla_nativo(instancia_tabla):
                instancia_tabla.auto_set_font_size(False)
                instancia_tabla.set_fontsize(8.5)
                instancia_tabla.scale(1.0, 1.3)
                for (row, col), cell in instancia_tabla.get_celld().items():
                    cell.set_linewidth(0.5)            
                    cell.set_edgecolor('#E5E7EB')       
                    if row == 0:
                        cell.set_text_props(color='black', weight='light')
                        cell.set_facecolor('#C0C0C0')
                    else:
                        cell.set_facecolor('#F8F9F9' if row % 2 == 0 else 'white')

            if total_filas <= limite_filas_por_bloque:
                ax_table = fig.add_axes([0.14, 0.054, 0.72, 0.48])
                ax_table.axis('off')
                mpl_table = ax_table.table(
                    cellText=df_table_render.values, 
                    colLabels=df_table_render.columns, 
                    cellLoc='center', 
                    loc='upper center', 
                    colWidths=anchos_columnas
                )
                estilizar_tabla_nativo(mpl_table)
            else:
                if total_filas > 36: 
                    df_table_render = df_table_render.iloc[:32]
                df_bloque_izq = df_table_render.iloc[:limite_filas_por_bloque]
                df_bloque_der = df_table_render.iloc[limite_filas_por_bloque:]
                
                anchos_doble = anchos_columnas if es_modo_micro_tabla else [0.15, 0.15, 0.16, 0.54]
                
                ax_table1 = fig.add_axes([0.14, 0.054, 0.34, 0.48])
                ax_table1.axis('off')
                mpl_table1 = ax_table1.table(cellText=df_bloque_izq.values, colLabels=df_bloque_izq.columns, cellLoc='center', loc='upper center', colWidths=anchos_doble)
                estilizar_tabla_nativo(mpl_table1)
                
                ax_table2 = fig.add_axes([0.52, 0.054, 0.34, 0.54])
                ax_table2.axis('off')
                mpl_table2 = ax_table2.table(cellText=df_bloque_der.values, colLabels=df_bloque_der.columns, cellLoc='center', loc='upper center', colWidths=anchos_doble)
                estilizar_tabla_nativo(mpl_table2)

        st.pyplot(fig, use_container_width=True)

    # =====================================================================
    # 6. CENTRO DE EXPORTACIÓN
    # =====================================================================
    st.markdown("---")
    st.markdown("### 🖨️ Centro de Exportación de Reportes y Gráficos")
    
    if (not modo_equipo and len(df_procesado) > 0) or (modo_equipo and df_global_marcas_reconstruido):
        
        # Unimos las datas reconstruidas si es modo equipo
        if modo_equipo:
            export_df = pd.concat(df_global_marcas_reconstruido, ignore_index=True)
        else:
            export_df = df_procesado.copy()
            export_df["Atleta"] = st.session_state.nadador_seleccionado_nombre
        
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.download_button(
                label="⬇️ Descargar Datos Históricos (CSV)",
                data=csv_data,
                file_name=f"historial_{prueba}_{genero}_{categoria}.csv",
                mime="text/csv",
                help="Exporta la base de datos de las marcas utilizadas para generar este gráfico en formato CSV para Excel."
            )
        with c2:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
            buf.seek(0)
            
            nombre_archivo = f"Grafico_Equipo_{prueba}_{categoria}.png" if modo_equipo else f"Grafico_{st.session_state.nadador_seleccionado_nombre}_{prueba}.png"
            
            st.download_button(
                label="⬇️ Descargar Gráfico (Alta Resolución)",
                data=buf,
                file_name=nombre_archivo,
                mime="image/png",
                help="Exporta el gráfico completo con la tabla y referencias fisiológicas integradas en calidad lista para impresión."
            )
        with c3:
            st.button(
                label="📥 Generar Reporte PDF (En Desarrollo)", 
                disabled=True,
                help="Próximamente: Exportación de informe técnico detallado con curvas asintóticas y variables de stress (TSB) incluidas."
            )
    else:
        st.info("Opciones de exportación desactivadas: No se encontraron marcas reales para exportar en este modo.")
