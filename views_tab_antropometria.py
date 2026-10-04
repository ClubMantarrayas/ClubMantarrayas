# =============================================================================
# FILE: views/views_tab_antropometria.py (Control Antropométrico y WA)
# =============================================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as plt_go
from datetime import datetime, date

# Importación de funciones científicas y auxiliares
from formulas_lib_funciones import (
    calcular_mirwald_offset,
    obtener_record_mundial_wa,
    calcular_proyeccion_rendimiento_wa,
    formatear_a_minutos,
    obtener_pruebas_por_categoria
)


def renderizar_tab_antropometria(datos_sidebar: dict):
    """
    Renderiza la vista principal para la evaluación somática, maduración biológica
    y proyección de Puntos World Aquatics (WA).
    """
    st.markdown("## 📏 Control Antropométrico, Maduración Biológica y Proyección WA")
    
    # -------------------------------------------------------------------------
    # 1. VERIFICACIÓN DE SESIÓN Y ATLETA ACTIVO
    # -------------------------------------------------------------------------
    supabase = st.session_state.get("supabase")
    if not supabase:
        st.error("❌ No se encontró conexión activa con la base de datos Supabase.")
        return

    atleta_id = st.session_state.get("nadador_seleccionado_id")
    nombre_atleta = st.session_state.get("nadador_seleccionado_nombre", "Atleta")
    genero_atleta = st.session_state.get("nadador_seleccionado_genero", "M")
    cat_atleta = st.session_state.get("nadador_seleccionado_categoria", "")

    if not atleta_id:
        st.warning("⚠️️ Selecciona un atleta en el panel lateral para cargar la información antropométrica.")
        return

    # Consultar fecha de nacimiento desde la tabla 'usuarios'
    res_user = supabase.table("usuarios").select("fecha_nacimiento").eq("id", atleta_id).execute()
    fecha_nac_str = res_user.data[0].get("fecha_nacimiento") if res_user.data else None

    if not fecha_nac_str:
        st.error(f"❌ El atleta **{nombre_atleta}** no tiene una fecha de nacimiento registrada en el sistema.")
        return

    st.markdown(f"**Atleta Seleccionado:** `{nombre_atleta}` | **Fecha Nacimiento:** `{fecha_nac_str}` | **Género:** `{genero_atleta}`")
    st.markdown("---")

    # -------------------------------------------------------------------------
    # 2. CONSULTA DE HISTÓRICO DE EVALUACIONES EN SUPABASE
    # -------------------------------------------------------------------------
    res_eval = supabase.table("evaluaciones_antropometricas") \
        .select("*") \
        .eq("usuario_id", atleta_id) \
        .order("fecha_evaluacion", desc=True) \
        .execute()
    
    evaluaciones = res_eval.data if res_eval.data else []

    # -------------------------------------------------------------------------
    # 3. INTERFAZ DE REGISTRO / EDICIÓN (FORMULARIO)
    # -------------------------------------------------------------------------
    with st.expander("➕ **Registrar Nueva Evaluación Antropométrica**", expanded=len(evaluaciones) == 0):
        with st.form("form_nueva_evaluacion", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                fecha_eval = st.date_input("Fecha de Evaluación", value=date.today())
                estatura = st.number_input("Estatura de Pie (cm)", min_value=80.0, max_value=230.0, value=150.0, step=0.5)
            with col2:
                estatura_sentado = st.number_input("Estatura Sentado (cm)", min_value=40.0, max_value=130.0, value=78.0, step=0.5)
                peso = st.number_input("Peso Corporal (kg)", min_value=15.0, max_value=150.0, value=40.0, step=0.5)
            with col3:
                envergadura = st.number_input("Envergadura / Wingspan (cm)", min_value=80.0, max_value=250.0, value=153.0, step=0.5)
                notas = st.text_input("Observaciones / Notas", value="")

            btn_guardar = st.form_submit_button("💾 Guardar Evaluación", use_container_width=True)

            if btn_guardar:
                if estatura_sentado >= estatura:
                    st.error("La estatura sentado debe ser menor a la estatura total de pie.")
                else:
                    payload = {
                        "usuario_id": atleta_id,
                        "fecha_evaluacion": fecha_eval.strftime("%Y-%m-%d"),
                        "estatura_cm": estatura,
                        "estatura_sentado_cm": estatura_sentado,
                        "peso_kg": peso,
                        "envergadura_cm": envergadura,
                        "observaciones": notas
                    }
                    try:
                        supabase.table("evaluaciones_antropometricas").insert(payload).execute()
                        st.success("✅ Evaluación antropométrica guardada exitosamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar en Supabase: {e}")

    if not evaluaciones:
        st.info("ℹ️ No hay registros antropométricos guardados para este atleta. Utiliza el formulario superior para añadir la primera medición.")
        return

    # -------------------------------------------------------------------------
    # 4. DIAGNÓSTICO DE MADURACIÓN DE LA EVALUACIÓN MÁS RECIENTE
    # -------------------------------------------------------------------------
    ultima_eval = evaluaciones[0]
    
    diag_mirwald = calcular_mirwald_offset(
        sexo=genero_atleta,
        fecha_nacimiento=fecha_nac_str,
        fecha_evaluacion=ultima_eval["fecha_evaluacion"],
        estatura_cm=float(ultima_eval["estatura_cm"]),
        estatura_sentado_cm=float(ultima_eval["estatura_sentado_cm"]),
        peso_kg=float(ultima_eval["peso_kg"]),
        envergadura_cm=float(ultima_eval["envergadura_cm"])
    )

    st.subheader("📌 Diagnóstico de Desarrollo Somático (Mirwald et al., 2002)")
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Edad Cronológica", f"{diag_mirwald['edad_cronologica']} yrs")
    kpi2.metric("Edad Biológica", f"{diag_mirwald['edad_biologica']} yrs", delta=f"{diag_mirwald['maturity_offset']} yrs")
    kpi3.metric("Ape Index (Brazada - Estatura)", f"{diag_mirwald['ape_index']} cm")
    kpi4.metric("Estado PHV", diag_mirwald['categoria_phv'])

    st.info(f"💡 **Etapa Puberal Estimada:** {diag_mirwald['estadio']}")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 5. SIMULADOR Y PROYECCIÓN DE RENDIMIENTO WORLD AQUATICS (WA)
    # -------------------------------------------------------------------------
    st.subheader("🎯 Proyección de Rendimiento y Puntos World Aquatics")

    # Obtener lista de pruebas reglamentarias según la categoría del atleta
    lista_pruebas_bruta = obtener_pruebas_por_categoria(cat_atleta)
    lista_pruebas = [p for p in lista_pruebas_bruta if not p.startswith("---")]

    col_p1, col_p2 = st.columns([1, 2])
    
    with col_p1:
        prueba_sel = st.selectbox("Selecciona la prueba a analizar:", options=lista_pruebas, index=0)
        meses_proy = st.select_slider("Ventana de proyección (meses):", options=[3, 6, 12, 24], value=12)

    # Consultar la mejor marca personal del atleta en marcas_historicas para esa prueba
    res_pb = supabase.table("marcas_historicas") \
        .select("tiempo, edad, created_at") \
        .eq("usuario_id", atleta_id) \
        .eq("prueba", prueba_sel) \
        .order("tiempo", desc=False) \
        .limit(1) \
        .execute()

    pb_tiempo_real = float(res_pb.data[0]["tiempo"]) if res_pb.data else None

    # Consultar el Récord Mundial (m_wr) de la tabla 'marcas_referencia'
    m_wr_seg = obtener_record_mundial_wa(prueba_sel, genero_atleta)

    with col_p2:
        if not pb_tiempo_real:
            st.warning(f"No se registraron marcas históricas para la prueba **{prueba_sel}** en este atleta.")
        elif m_wr_seg <= 0:
            st.error(f"No se encontró un récord mundial de referencia (`m_wr`) registrado para **{prueba_sel}** ({genero_atleta}).")
        else:
            es_potencia = any(d in prueba_sel for d in ["25", "50", "100"])
            
            proyeccion = calcular_proyeccion_rendimiento_wa(
                tiempo_real_seg=pb_tiempo_real,
                record_mundial_seg=m_wr_seg,
                maturity_offset=diag_mirwald["maturity_offset"],
                categoria_phv=diag_mirwald["categoria_phv"],
                ape_index=diag_mirwald["ape_index"],
                es_prueba_potencia=es_potencia,
                meses_proyeccion=meses_proy
            )

            st.markdown(f"**Mejor Marca Personal Actual:** `{formatear_a_minutos(pb_tiempo_real)} s` | **WR de Referencia:** `{formatear_a_minutos(m_wr_seg)} s`")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Puntos WA Actuales", f"{proyeccion['puntos_wa_actuales']} pts")
            m2.metric("Tiempo Normalizado", f"{formatear_a_minutos(proyeccion['tiempo_normalizado'])} s", help="Ajuste por desarrollo físico biológico")
            m3.metric(f"Proyección a {meses_proy}m", f"{formatear_a_minutos(proyeccion['tiempo_proyectado'])} s", delta=f"+{proyeccion['ganancia_puntos_wa']} pts WA")

    st.markdown("---")

# -------------------------------------------------------------------------
    # 6. GRÁFICO COMBINADO: DESARROLLO FÍSICO VS. EVOLUCIÓN PUNTOS WA
    # -------------------------------------------------------------------------
    st.subheader("📈 Evolución Longitudinal: Crecimiento Somático vs. Puntos WA")

    # Extraer el ID del atleta desde datos_sidebar
    atleta_id = datos_sidebar.get("usuario_id")

    # 1. Preparar DataFrame de evaluaciones antropométricas
    df_eval = pd.DataFrame(evaluaciones)
    df_eval["fecha_evaluacion"] = pd.to_datetime(df_eval["fecha_evaluacion"])
    df_eval = df_eval.sort_values("fecha_evaluacion")

    # 2. Consultar marcas históricas usando la columna 'edad'
    res_hist_todas = supabase.table("marcas_historicas") \
        .select("prueba, tiempo, edad") \
        .eq("usuario_id", atleta_id) \
        .execute()
    
    df_hist = pd.DataFrame(res_hist_todas.data) if res_hist_todas.data else pd.DataFrame()

    if not df_hist.empty and m_wr_seg > 0:
        # Filtrar exactamente por la prueba seleccionada
        prueba_clean = str(prueba_sel).strip().lower()
        df_hist_prueba = df_hist[
            df_hist["prueba"].astype(str).str.strip().str.lower() == prueba_clean
        ].copy()
        
        if not df_hist_prueba.empty:
            df_hist_prueba["tiempo"] = pd.to_numeric(df_hist_prueba["tiempo"], errors="coerce")
            df_hist_prueba["edad"] = pd.to_numeric(df_hist_prueba["edad"], errors="coerce")
            df_hist_prueba = df_hist_prueba[
                (df_hist_prueba["tiempo"] > 0) & (df_hist_prueba["edad"].notnull())
            ].copy()

            # --- CORRECCIÓN DE LA LÍNEA 223 ---
            fecha_nac_str = datos_sidebar.get("fecha_nacimiento", "2014-12-30")
            fecha_nac = pd.to_datetime(fecha_nac_str)

            # Reconstruir la fecha exacta del evento a partir de la edad decimal
            df_hist_prueba["fecha_calculada"] = df_hist_prueba["edad"].apply(
                lambda ed: fecha_nac + pd.Timedelta(days=float(ed) * 365.25)
            )

            # Calcular Puntos World Aquatics para cada tiempo
            df_hist_prueba["puntos_wa"] = df_hist_prueba["tiempo"].apply(
                lambda t: int(1000 * ((m_wr_seg / float(t)) ** 3))
            )

            # ORDENAR CRONOLÓGICAMENTE SEGÚN LA FECHA RECONSTRUIDA
            df_hist_prueba = df_hist_prueba.sort_values("fecha_calculada")

            # Construcción del gráfico con Plotly
            fig = plt_go.Figure()

            # Eje Y1: Estatura
            fig.add_trace(plt_go.Scatter(
                x=df_eval["fecha_evaluacion"],
                y=df_eval["estatura_cm"],
                name="Estatura (cm)",
                mode="lines+markers",
                line=dict(color="#2563eb", width=3),
                yaxis="y1"
            ))

            # Eje Y1: Envergadura
            fig.add_trace(plt_go.Scatter(
                x=df_eval["fecha_evaluacion"],
                y=df_eval["envergadura_cm"],
                name="Envergadura (cm)",
                mode="lines+markers",
                line=dict(color="#059669", width=2, dash="dash"),
                yaxis="y1"
            ))

            # Eje Y2: Puntos WA reales ordenados por fecha estimada
            fig.add_trace(plt_go.Scatter(
                x=df_hist_prueba["fecha_calculada"],
                y=df_hist_prueba["puntos_wa"],
                name=f"Puntos WA ({prueba_sel})",
                mode="lines+markers",
                marker=dict(size=8, color="#d97706"),
                line=dict(color="#d97706", width=2),
                yaxis="y2"
            ))

            fig.update_layout(
                title=f"Evolución Físico-Deportiva del Atleta en {prueba_sel}",
                xaxis=dict(title="Fecha Estimada del Evento / Evaluación"),
                yaxis=dict(title="Dimensión Antropométrica (cm)", side="left"),
                yaxis2=dict(
                    title="Puntos World Aquatics", 
                    side="right", 
                    overlaying="y", 
                    showgrid=False,
                    range=[0, 1000]
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=420,
                margin=dict(l=20, r=20, t=50, b=20)
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No hay marcas registradas para la prueba **{prueba_sel}**.")
    else:
        st.info("No se encontraron registros en el historial del atleta.")
