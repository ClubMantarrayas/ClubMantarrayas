import datetime
import io
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# =============================================================================
# IMPORTACIÓN CENTRALIZADA DE CACHÉ
# =============================================================================
from conections_supabase_cache import (
  obtener_atletas_asignados_cache,
  obtener_bitacora_atleta_cache,
  obtener_nadadores_activos_cache,
  obtener_usuario_por_id_cache,
)


def renderizar_tab_reportes(datos_sidebar=None):
  """CÓDIGO MODULAR OPTIMIZADO Y 100% CACHEADO (PRODUCCIÓN)

  Version: 3.1 (Aislamiento de Rol Simulado y Asignaciones)
  """
  st.markdown("### 📊 Panel de Control y Análisis de Carga Individual")
  st.caption(
      "Selecciona a un atleta y la ventana temporal para evaluar su volumen"
      " biomecánico o modelar su rendimiento científico."
  )

  # =============================================================================
  # 1. RESOLUCIÓN DE NÓMINA DESDE CACHÉ (BLINDADO CONTRA MUTACIÓN DE SESIÓN)
  # =============================================================================
  user_raw = (
      st.session_state.get("usuario_logueado_id")
      or st.session_state.get("usuario_id")
      or st.session_state.get("user")
  )
  
  if isinstance(user_raw, dict):
      id_usuario_logueado = user_raw.get("id") or user_raw.get("usuario_id")
  else:
      id_usuario_logueado = user_raw

  rol_real = st.session_state.get(
      "rol_real", st.session_state.get("rol", "Nadador")
  )
  rol_activo = st.session_state.get("rol", "Nadador")

  atletas_pool_rep = []

  if rol_activo == "Nadador":
    if id_usuario_logueado:
      usr = obtener_usuario_por_id_cache(id_usuario_logueado)
      if usr:
        atletas_pool_rep = [usr]

  elif rol_activo == "Entrenador":
    id_entrenador_evaluar = None
    
    # 1. Resolver ID del entrenador de forma aislada
    if rol_real == "Administrador":
      id_entrenador_evaluar = st.session_state.get("sb_entrenador_simular_selector")
    else:
      id_entrenador_evaluar = id_usuario_logueado

    # 2. Consultar asignaciones solo si existe un ID de entrenador válido
    if id_entrenador_evaluar is not None:
      ids_autorizados = obtener_atletas_asignados_cache(id_entrenador_evaluar) or []

      set_ids_str = set()
      for item in ids_autorizados:
        if isinstance(item, dict):
          val = item.get("atleta_id") or item.get("id") or item.get("usuario_id")
          if val is not None:
            set_ids_str.add(str(val))
        elif item is not None:
          set_ids_str.add(str(item))

      if set_ids_str:
        todos_nadadores = obtener_nadadores_activos_cache() or []

        atletas_pool_rep = [
            a for a in todos_nadadores
            if str(a.get("id") if a.get("id") is not None else a.get("usuario_id")) in set_ids_str
        ]

  elif rol_activo in ["Head Coach", "Administrador"]:
    atletas_pool_rep = obtener_nadadores_activos_cache() or []

  if not atletas_pool_rep:
    st.warning("⚠️ No se detectaron atletas disponibles para generar reportes.")
    return

  # =============================================================================
  # 2. SELECTOR LOCAL E INDEPENDIENTE DE ATLETA Y TEMPORALIDAD
  # =============================================================================
  dict_nom_rep = {}
  for a in atletas_pool_rep:
    atleta_id = a.get("id") if a.get("id") is not None else a.get("usuario_id")
    nombre = a.get("nombre") or a.get("nombre_completo") or f"Atleta {atleta_id}"
    if atleta_id is not None:
      dict_nom_rep[atleta_id] = nombre

  ids_disponibles = list(dict_nom_rep.keys())

  col_atleta, col_tiempo = st.columns([1.2, 1])

  with col_atleta:
    atleta_sel_id = st.selectbox(
        "🏊‍♂️ Seleccione el Nadador a Analizar:",
        options=ids_disponibles,
        format_func=lambda x: dict_nom_rep.get(x, "Cargando atleta..."),
        key="rep_atleta_local_selector",
    )
  with col_tiempo:
    opciones_tiempo = {
        "7 días (Última semana - ATL)": 7,
        "28 días (Ciclo Corto)": 28,
        "30 días (Mensual)": 30,
        "42 días (Carga Crónica - CTL)": 42,
        "90 días (Macrociclo Trimestral)": 90,
        "180 días (Semestral)": 180,
        "365 días (Anual)": 365,
        "Total Histórico": None,
    }
    ventana_sel = st.selectbox(
        "⏳ Ventana Temporal:",
        options=list(opciones_tiempo.keys()),
        index=3,
        key="rep_selectbox_temporalidad",
    )

  if atleta_sel_id not in dict_nom_rep:
    st.error("🔒 Acción denegada: Intento de acceso a un registro no autorizado.")
    st.stop()

  dias_atras = opciones_tiempo[ventana_sel]
  fecha_fin_rep = datetime.date.today()

  if dias_atras:
    fecha_limite = fecha_fin_rep - datetime.timedelta(days=dias_atras)
    rango_fechas_completo = pd.date_range(
        start=fecha_limite + datetime.timedelta(days=1), end=fecha_fin_rep
    ).date
  else:
    fecha_limite = None
    rango_fechas_completo = None

  nombre_atleta_safename = dict_nom_rep[atleta_sel_id].lower().replace(" ", "_")
  st.success(f"🎯 Reporte activo para: **{dict_nom_rep[atleta_sel_id]}**")
  st.markdown("---")

  # =============================================================================
  # 3. EXTRACCIÓN Y PREPARACIÓN DE DATOS
  # =============================================================================
  with st.spinner("Compilando históricos de entrenamiento..."):
    try:
      records_crudos = obtener_bitacora_atleta_cache(atleta_sel_id)

      records = []
      for r in records_crudos:
        if r.get("fecha"):
          f_rec = (
              datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date()
              if isinstance(r["fecha"], str)
              else r["fecha"]
          )
          if fecha_limite is None or f_rec >= fecha_limite:
            records.append(r)

      records_hasta_hoy = [
          r
          for r in records
          if r.get("fecha")
          and (
              datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date()
              if isinstance(r["fecha"], str)
              else r["fecha"]
          )
          <= fecha_fin_rep
      ]

      if not records_hasta_hoy:
        st.warning(
            "📭 El nadador seleccionado no registra entrenamientos en la"
            " ventana temporal definida."
        )
      else:
        subtab_volumen, subtab_fisiologico = st.tabs([
            "🏊‍♂️ Distribución y Carga de Volumen",
            "📈 Modelo Fisiológico (CTL / ATL / TSB)",
        ])

        if rango_fechas_completo is None:
          fechas_instancias = [
              datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date()
              for r in records_hasta_hoy
              if r.get("fecha")
          ]
          rango_analisis = (
              pd.date_range(
                  start=min(fechas_instancias), end=max(fechas_instancias)
              ).date
              if fechas_instancias
              else [datetime.date.today()]
          )
        else:
          rango_analisis = rango_fechas_completo

        # =============================================================================
        # SUBTAB 1: DISTRIBUCIÓN Y CARGA DE VOLUMEN
        # =============================================================================
        with subtab_volumen:
          st.markdown("#### 📈 Diagnóstico de Carga Acumulada y Bloques Fijos")

          hoy_date = datetime.date.today()

          def calcular_volumen_bloque(dias_bloque):
            limite_bloque = hoy_date - datetime.timedelta(days=dias_bloque)
            return sum([
                r.get("metros_totales", 0)
                for r in records_hasta_hoy
                if r.get("fecha")
                and (
                    datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date()
                    if isinstance(r["fecha"], str)
                    else r["fecha"]
                )
                >= limite_bloque
            ])

          vol_7d = calcular_volumen_bloque(7)
          vol_30d = calcular_volumen_bloque(30)
          vol_42d = calcular_volumen_bloque(42)
          vol_90d = calcular_volumen_bloque(90)

          c_b1, c_b2, c_b3, c_b4 = st.columns(4)
          with c_b1:
            st.metric(label="📆 Últimos 7 días", value=f"{vol_7d:,} m")
          with c_b2:
            st.metric(label="📅 Últimos 30 días", value=f"{vol_30d:,} m")
          with c_b3:
            st.metric(label="💪 Últimos 42 días (CTL)", value=f"{vol_42d:,} m")
          with c_b4:
            st.metric(label="🌀 Trimestre (90d)", value=f"{vol_90d:,} m")

          st.markdown("---")

          estilos_lista = [
              "Libre",
              "Espalda",
              "Pecho",
              "Mariposa",
              "Combinado",
              "Otros",
          ]
          intensidades_lista = [
              "Aeróbico Ligero",
              "Aeróbico Medio",
              "Umbral",
              "Anaeróbico",
          ]
          columnas_vol = (
              ["Fecha"] + estilos_lista + intensidades_lista + ["Total Día"]
          )

          matriz_volumen = []
          for f in rango_analisis:
            dia_recs = [
                r
                for r in records_hasta_hoy
                if (
                    datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date()
                    if isinstance(r["fecha"], str)
                    else r["fecha"]
                )
                == f
            ]
            row_vol = {col: 0 for col in columnas_vol}
            row_vol["Fecha"] = f

            for r in dia_recs:
              dict_est = r.get("desglose_estilos") or {}
              for k_est, v_m in dict_est.items():
                target_est = k_est if k_est in estilos_lista else "Otros"
                row_vol[target_est] += v_m
                row_vol["Total Día"] += v_m

              dict_int = (
                  r.get("desglose_intensity")
                  or r.get("desglose_intensidad")
                  or {}
              )
              for k_int, v_m in dict_int.items():
                target_int = "Aeróbico Ligero"
                if "Medio" in k_int:
                  target_int = "Aeróbico Medio"
                elif "Umbral" in k_int or "Sostenido" in k_int:
                  target_int = "Umbral"
                elif "Sprint" in k_int or "Anaeróbico" in k_int:
                  target_int = "Anaeróbico"
                row_vol[target_int] += v_m

            matriz_volumen.append(row_vol)

          df_vol_diario = (
              pd.DataFrame(matriz_volumen)
              .sort_values("Fecha")
              .reset_index(drop=True)
          )

          df_vol_acum = df_vol_diario.copy()
          for est in estilos_lista:
            df_vol_acum[est] = df_vol_acum[est].cumsum()
          for inten in intensidades_lista:
            df_vol_acum[inten] = df_vol_acum[inten].cumsum()

          fig_est, ax_est = plt.subplots(figsize=(8.5, 3.2))
          ax_est.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
          ax_est.xaxis.set_major_locator(
              mdates.DayLocator(interval=max(1, len(df_vol_acum) // 6))
          )
          ax_est.stackplot(
              df_vol_acum["Fecha"],
              *[df_vol_acum[est].values for est in estilos_lista],
              labels=estilos_lista,
              colors=[
                  "#2ecc71",
                  "#3498db",
                  "#9b59b6",
                  "#e67e22",
                  "#f1c40f",
                  "#95a5a6",
              ],
              alpha=0.80,
          )
          ax_est.set_ylabel("Metros Acumulados", fontsize=8)
          ax_est.legend(loc="upper left", fontsize=7, ncol=3)
          plt.tight_layout()
          st.pyplot(fig_est)

          buf_png_vol = io.BytesIO()
          fig_est.savefig(buf_png_vol, format="png", dpi=300)
          st.download_button(
              "🖼️ Guardar Tendencia de Estilos (PNG)",
              data=buf_png_vol.getvalue(),
              file_name=f"acumulado_estilos_{nombre_atleta_safename}.png",
              mime="image/png",
          )

          st.markdown("##### 📋 Matriz de Auditoría de Volúmenes Diarios")
          df_tabla_vol = df_vol_diario.copy()
          fila_totales_vol = {"Fecha": "TOTAL ACUMULADO"}
          for col in columnas_vol[1:]:
            fila_totales_vol[col] = df_tabla_vol[col].sum()

          df_tabla_vol["Fecha"] = df_tabla_vol["Fecha"].map(
              lambda x: (
                  x.strftime("%Y-%m-%d")
                  if isinstance(x, (datetime.date, datetime.datetime))
                  else str(x)
              )
          )
          df_tabla_vol = pd.concat(
              [df_tabla_vol, pd.DataFrame([fila_totales_vol])],
              ignore_index=True,
          )
          st.write(
              df_tabla_vol.to_html(index=False, classes="tabla-estilizada"),
              unsafe_allow_html=True,
          )

          csv_unificado_data = df_tabla_vol.to_csv(index=False).encode("utf-8")
          st.download_button(
              label="📥 Descargar Historial de Auditoría (CSV)",
              data=csv_unificado_data,
              file_name=f"auditoria_volumen_{nombre_atleta_safename}.csv",
              mime="text/csv",
              use_container_width=True,
          )

        # =============================================================================
        # SUBTAB 2: MODELO FISIOLÓGICO TRIMP
        # =============================================================================
        with subtab_fisiologico:
          st.markdown("### 📈 Modelo Fisiológico TRIMP Exponencial")

          carga_diaria_au = {f: 0.0 for f in rango_analisis}
          mapeo_rpe_zonas = {
              "Aeróbico Ligero": 3.5,
              "Aeróbico Medio": 5.5,
              "Umbral": 7.5,
              "Anaeróbico": 9.5,
              "Sprint": 10.0,
          }

          for r in records_hasta_hoy:
            f_rec = (
                datetime.datetime.strptime(r["fecha"], "%Y-%m-%d").date()
                if isinstance(r["fecha"], str)
                else r["fecha"]
            )
            if f_rec in carga_diaria_au:
              rpe_global = r.get("rpe") or r.get("factor_exigencia")
              if rpe_global and float(rpe_global) > 0:
                carga_sesion = (
                    r.get("metros_totales", 0) / 1000.0
                ) * np.exp(0.218 * float(rpe_global))
              else:
                carga_sesion = 0.0
                int_dict = (
                    r.get("desglose_intensity")
                    or r.get("desglose_intensidad")
                    or {}
                )
                for k_int, m_int in int_dict.items():
                  rpe_zona = next(
                      (
                          val
                          for key, val in mapeo_rpe_zonas.items()
                          if key in k_int
                      ),
                      3.5,
                  )
                  carga_sesion += (m_int / 1000.0) * np.exp(0.218 * rpe_zona)

                if not int_dict and r.get("metros_totales", 0) > 0:
                  carga_sesion = (
                      r.get("metros_totales", 0) / 1000.0
                  ) * np.exp(0.218 * 5.0)

              carga_diaria_au[f_rec] += carga_sesion

          df_cargas = pd.DataFrame([
              {"Fecha": f, "Carga_AU": carga_diaria_au[f]}
              for f in rango_analisis
          ])
          df_cargas["Fecha"] = pd.to_datetime(df_cargas["Fecha"])
          df_cargas = df_cargas.sort_values("Fecha").reset_index(drop=True)

          df_cargas["CTL"] = (
              df_cargas["Carga_AU"].ewm(span=42, adjust=False).mean()
          )
          df_cargas["ATL"] = (
              df_cargas["Carga_AU"].ewm(span=7, adjust=False).mean()
          )
          df_cargas["TSB"] = df_cargas["CTL"] - df_cargas["ATL"]

          max_denominador = np.maximum(df_cargas["CTL"], df_cargas["ATL"])
          df_cargas["TSB_Pct"] = (
              (df_cargas["TSB"] / max_denominador) * 100
          ).fillna(0.0)

          if not df_cargas.empty:
            ultima_fila = df_cargas.iloc[-1]
            val_ctl, val_atl, val_tsb = (
                round(float(ultima_fila["CTL"]), 1),
                round(float(ultima_fila["ATL"]), 1),
                round(float(ultima_fila["TSB"]), 1),
            )
            pct_tsb = round(float(ultima_fila["TSB_Pct"]), 1)

            if pct_tsb <= -35.0:
              estado_forma = f"🔴 Fatiga Severa ({pct_tsb}%)"
            elif -35.0 < pct_tsb < -10.0:
              estado_forma = f"⚠️ Bloque de Sobrecarga ({pct_tsb}%)"
            elif -10.0 <= pct_tsb <= 10.0:
              estado_forma = f"🟡 Balance de Adaptación ({pct_tsb}%)"
            elif 10.0 < pct_tsb <= 40.0:
              estado_forma = f"🟢 Supercompensación / Taper (+{pct_tsb}%)"
            else:
              estado_forma = f"❌ Desentrenamiento (+{pct_tsb}%)"

            c_m1, c_m2, c_m3 = st.columns(3)
            with c_m1:
              st.metric("💪 Fitness (CTL)", value=f"{val_ctl} AU")
            with c_m2:
              st.metric("🔥 Fatiga (ATL)", value=f"{val_atl} AU")
            with c_m3:
              st.metric(
                  "🎯 Balance Fisiológico",
                  value=f"{val_tsb} AU",
                  delta=estado_forma,
              )

            fig_ban, ax1 = plt.subplots(figsize=(8.5, 3.8))
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))

            l_ctl = ax1.plot(
                df_cargas["Fecha"],
                df_cargas["CTL"],
                label="Fitness Crónico (CTL)",
                color="#1f77b4",
                linewidth=2.0,
            )
            l_atl = ax1.plot(
                df_cargas["Fecha"],
                df_cargas["ATL"],
                label="Fatiga Aguda (ATL)",
                color="#d62728",
                linewidth=1.5,
                linestyle="--",
            )
            b_tsb = ax1.bar(
                df_cargas["Fecha"],
                df_cargas["Carga_AU"],
                label="Estrés Diario (AU)",
                color="#2ca02c",
                alpha=0.15,
                width=1.0,
            )

            ax1.set_ylabel(
                "Métricas de Carga (AU)", color="#1f77b4", fontsize=8
            )
            ax1.grid(True, linestyle=":", alpha=0.3)

            ax2 = ax1.twinx()
            l_pct = ax2.plot(
                df_cargas["Fecha"],
                df_cargas["TSB_Pct"],
                label="Índice TSB (%)",
                color="#2c3e50",
                linewidth=1.8,
            )
            ax2.axhspan(10.0, 40.0, color="#abebc6", alpha=0.25)
            ax2.axhspan(-35.0, -10.0, color="#f9e79f", alpha=0.20)
            ax2.axhline(0.0, color="#2c3e50", linestyle="-", alpha=0.4)
            ax2.set_ylim(-105, 105)

            lineas_totales = l_ctl + l_atl + [b_tsb] + l_pct
            etiquetas_totales = [l.get_label() for l in lineas_totales]
            ax1.legend(
                lineas_totales,
                etiquetas_totales,
                loc="upper left",
                fontsize=7,
                ncol=2,
            )

            plt.tight_layout()
            st.pyplot(fig_ban)

            buf_png_ban = io.BytesIO()
            fig_ban.savefig(buf_png_ban, format="png", dpi=300)
            st.download_button(
                "🖼️ Guardar Perfil Fisiológico (PNG)",
                data=buf_png_ban.getvalue(),
                file_name=f"fisiologico_{nombre_atleta_safename}.png",
                mime="image/png",
            )

            st.markdown("##### 📋 Tabla de Valores Diarios y Métricas")
            df_tabla_ban = df_cargas.copy()
            df_tabla_ban["Fecha"] = df_tabla_ban["Fecha"].dt.strftime(
                "%Y-%m-%d"
            )
            df_tabla_ban["Carga_AU"] = df_tabla_ban["Carga_AU"].round(1)
            df_tabla_ban["CTL"] = df_tabla_ban["CTL"].round(1)
            df_tabla_ban["ATL"] = df_tabla_ban["ATL"].round(1)
            df_tabla_ban["TSB"] = df_tabla_ban["TSB"].round(1)
            df_tabla_ban["TSB_Pct"] = (
                df_tabla_ban["TSB_Pct"].round(1).astype(str) + " %"
            )

            df_tabla_ban.columns = [
                "Fecha",
                "Carga TRIMP (AU/Día)",
                "CTL (Fitness AU)",
                "ATL (Fatiga AU)",
                "TSB (Forma AU)",
                "TSB Relativo (% Máx)",
            ]
            st.write(
                df_tabla_ban.to_html(index=False, classes="tabla-estilizada"),
                unsafe_allow_html=True,
            )

            csv_ban_data = df_tabla_ban.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Descargar Métricas Fisiológicas (CSV)",
                data=csv_ban_data,
                file_name=f"fisiologico_{nombre_atleta_safename}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    except Exception as e:
      st.error(f"Error al computar el reporte analítico avanzado: {e}")
