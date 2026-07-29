import datetime
from datetime import timedelta
import pandas as pd
import streamlit as st

# 🎨 IMPORTACIÓN DESDE TU MÓDULO DE ESTILOS VISUALES
from views_styles import spc

# 📦 IMPORTACIÓN DESDE TU LIBRERÍA REAL DE FUNCIONES
from formulas_lib_funciones import (
    calcular_categoria_competencia,
    convertir_string_a_segundos,
    formatear_a_minutos,
    obtener_pruebas_por_categoria,
    procesar_mejor_marca_historica,
)

# 🚀 IMPORTACIÓN DESDE TU CAPA DE CACHÉ
from conections_supabase_cache import (
    obtener_atletas_asignados_cache,
    obtener_marcas_equipo_cache,
    obtener_marcas_historicas_cache,
    obtener_marcas_referencia_cache,
    obtener_nadadores_activos_cache,
    obtener_usuario_por_id_cache,
    obtener_usuarios_por_rol_cache,
)


def renderizar_sidebar_completo():
  """Renderiza el sidebar completo con soporte de emulación para el Administrador."""
  if "supabase" not in st.session_state or st.session_state.supabase is None:
    st.error("No hay una conexión activa a la base de datos.")
    st.stop()

  # -------------------------------------------------------------
  # 0. INICIALIZACIÓN DE VARIABLES GLOBALES
  # -------------------------------------------------------------
  edad_min_zoom = 0.0
  edad_max_zoom = 100.0
  t0 = 10.0
  T0 = 30.0
  t_peak = 23.0
  T_target = 25.0
  t_pb = 12.0
  T_pb = 28.0
  factor_h = 0.35
  t_intermedia = 16.5
  tipo_vista = "Macro (Historial Completo)"
  simulacion_externa = False
  modo_equipo = False
  filtro_genero = "Todos"
  tipo_filtro = "Todos los Atletas"
  cat_sel = None
  ids_sel = []
  lista_atletas = []
  df_global = pd.DataFrame()
  df_procesado = pd.DataFrame()

  m_ano, m_panam_b, m_panam_a, m_wa_b, m_wa_a, m_wr = (
      0.0,
      0.0,
      0.0,
      0.0,
      0.0,
      25.0,
  )

  # -------------------------------------------------------------
  # 1. IDENTIFICACIÓN Y EMULACIÓN DE ROL (ADMINISTRADOR)
  # -------------------------------------------------------------
  ROLES_OFICIALES = [
      "Nadador",
      "Entrenador",
      "Head Coach",
      "Club",
      "Administrador",
  ]

  if "rol_real" not in st.session_state:
    st.session_state["rol_real"] = st.session_state.get("rol", "Nadador")

  rol_real = st.session_state["rol_real"]
  nombre_mostrar = st.session_state.get("nombre_usuario") or st.session_state.get(
      "nombre_nadador", "Usuario"
  )

  st.sidebar.markdown(
      f"**Usuario:** {nombre_mostrar}  \n**Nivel Real:** `{rol_real}`"
  )

  if rol_real == "Administrador":
    st.sidebar.markdown(
        "<hr style='margin: 8px 0; border-top: 1px solid #0055ff;'/>",
        unsafe_allow_html=True,
    )
    st.sidebar.caption("🛠️ **Modo Emulación (Administrador)**")

    rol_actual_simulado = st.session_state.get("rol", "Administrador")
    idx_defecto = (
        ROLES_OFICIALES.index(rol_actual_simulado)
        if rol_actual_simulado in ROLES_OFICIALES
        else 4
    )

    rol_efectivo = st.sidebar.selectbox(
        "Simular vista como:",
        options=ROLES_OFICIALES,
        index=idx_defecto,
        key="selector_emulacion_rol",
    )

    if rol_efectivo != st.session_state.get("rol"):
      st.session_state["rol"] = rol_efectivo
      st.rerun()

  if st.sidebar.button("🚪 Salir del Sistema"):
    st.session_state.autenticado = False
    st.rerun()

  rol_activo = st.session_state.get("rol", "Nadador")

  # -------------------------------------------------------------
  # 2. SALIDA TEMPRANA SI EL ROL EMULADO ES "CLUB"
  # -------------------------------------------------------------
  if rol_activo == "Club":
    st.sidebar.markdown(
        "<hr style='margin: 12px 0; border-top: 1px solid #ccc;'/>",
        unsafe_allow_html=True,
    )
    st.sidebar.subheader("🏛️ Sesión del Club")
    st.sidebar.info("Panel de gestión administrativa activo.")

    return {
        "usuario_id": st.session_state.get("usuario_logueado_id")
        or st.session_state.get("usuario_id"),
        "genero": "M",
        "nombre": nombre_mostrar,
        "categoria": "",
        "titulo_grafico": "Gestión de Club",
        "simulacion_externa": simulacion_externa,
        "modo_equipo": modo_equipo,
        "filtro_genero": filtro_genero,
        "tipo_filtro": tipo_filtro,
        "cat_sel": cat_sel,
        "ids_sel": ids_sel,
        "lista_atletas_filtrados": lista_atletas,
        "df_global_marcas": df_global,
        "t0": t0,
        "T0": T0,
        "t_peak": t_peak,
        "T_target": T_target,
        "t_pb": t_pb,
        "T_pb": T_pb,
        "tipo_vista": tipo_vista,
        "edad_min_zoom": edad_min_zoom,
        "edad_max_zoom": edad_max_zoom,
        "factor_h": factor_h,
        "t_intermedia": t_intermedia,
        "df_procesado": df_procesado,
        "m_ano": m_ano,
        "m_panam_b": m_panam_b,
        "m_panam_a": m_panam_a,
        "m_wa_b": m_wa_b,
        "m_wa_a": m_wa_a,
        "m_wr": m_wr,
    }

  # -------------------------------------------------------------
  # 3. PANEL UNIFICADO DE NAVEGACIÓN Y SELECCIÓN DE ATLETAS
  # -------------------------------------------------------------
  if rol_activo in ["Head Coach", "Administrador"]:
    spc()
    st.sidebar.subheader("🎯 Panel de Navegación de Atletas")
    try:
      atletas_disponibles = obtener_nadadores_activos_cache() or []
      if atletas_disponibles:
        df_atl = pd.DataFrame(atletas_disponibles)
        dict_atletas = dict(zip(df_atl["id"], df_atl["nombre"]))

        sel_id = st.sidebar.selectbox(
            "Monitorear Nadador:",
            options=list(dict_atletas.keys()),
            format_func=lambda x: dict_atletas[x],
            key="sb_atleta_selector",
        )
        atleta_row = df_atl[df_atl["id"] == sel_id].iloc[0]

        st.session_state["nadador_seleccionado_id"] = int(atleta_row["id"])
        st.session_state["nadador_seleccionado_nombre"] = atleta_row["nombre"]
        st.session_state["nadador_seleccionado_genero"] = atleta_row.get(
            "genero", "M"
        )

        cat_calc, _ = (
            calcular_categoria_competencia(atleta_row["fecha_nacimiento"])
            if atleta_row.get("fecha_nacimiento")
            else ("Sin Categoría", 0)
        )
        st.session_state["nadador_seleccionado_categoria"] = cat_calc
      else:
        st.sidebar.warning("⚠️ No hay nadadores registrados.")
    except Exception as e:
      st.error(f"Error cargando atletas: {e}")

  elif rol_activo == "Entrenador":
    spc()
    st.sidebar.subheader("🎯 Panel de Entrenador")
    try:
      id_entrenador_evaluar = None

      # CASO A: Administrador Emulando Rol Entrenador
      if rol_real == "Administrador":
        todos_entrenadores = (
            obtener_usuarios_por_rol_cache("Entrenador") or []
        )

        dict_entrenadores = {}
        for u in todos_entrenadores:
          if isinstance(u, dict):
            uid = u.get("id") if u.get("id") is not None else u.get("usuario_id")
            nom = (
                u.get("nombre")
                or u.get("nombre_completo")
                or f"Entrenador {uid}"
            )
            if uid is not None:
              dict_entrenadores[uid] = nom

        if dict_entrenadores:
          id_entrenador_evaluar = st.sidebar.selectbox(
              "👨‍🏫 Seleccionar Entrenador a Simular:",
              options=list(dict_entrenadores.keys()),
              format_func=lambda x: dict_entrenadores.get(x, "Entrenador"),
              key="sb_entrenador_simular_selector",
          )
        else:
          st.sidebar.warning("⚠️ No hay entrenadores registrados en la tabla de usuarios.")

      # CASO B: Entrenador Real en su sesión
      else:
        id_entrenador_evaluar = st.session_state.get(
            "usuario_logueado_id"
        ) or st.session_state.get("usuario_id")

      # CONSULTA DE ASIGNACIONES (Filtro por ID de Entrenador)
      if id_entrenador_evaluar is not None:
        raw_asignados = (
            obtener_atletas_asignados_cache(id_entrenador_evaluar) or []
        )

        set_ids_asignados = set()
        for item in raw_asignados:
          if isinstance(item, dict):
            val = (
                item.get("atleta_id")
                or item.get("id")
                or item.get("usuario_id")
            )
            if val is not None:
              set_ids_asignados.add(str(val))
          elif item is not None:
            set_ids_asignados.add(str(item))

        todos_nadadores = obtener_nadadores_activos_cache() or []
        atletas_disponibles = [
            a
            for a in todos_nadadores
            if isinstance(a, dict)
            and str(
                a.get("id") if a.get("id") is not None else a.get("usuario_id")
            )
            in set_ids_asignados
        ]

        if atletas_disponibles:
          df_atl = pd.DataFrame(atletas_disponibles)
          dict_atletas = dict(zip(df_atl["id"], df_atl["nombre"]))

          sel_id = st.sidebar.selectbox(
              "🏊‍♂️ Atletas Asignados:",
              options=list(dict_atletas.keys()),
              format_func=lambda x: dict_atletas[x],
              key="sb_atleta_entrenador_selector",
          )
          atleta_row = df_atl[df_atl["id"] == sel_id].iloc[0]

          st.session_state["nadador_seleccionado_id"] = int(atleta_row["id"])
          st.session_state["nadador_seleccionado_nombre"] = atleta_row[
              "nombre"
          ]
          st.session_state["nadador_seleccionado_genero"] = atleta_row.get(
              "genero", "M"
          )

          cat_calc, _ = (
              calcular_categoria_competencia(atleta_row["fecha_nacimiento"])
              if atleta_row.get("fecha_nacimiento")
              else ("Sin Categoría", 0)
          )
          st.session_state["nadador_seleccionado_categoria"] = cat_calc
        else:
          st.sidebar.warning(
              "⚠️ No hay nadadores asignados a este entrenador."
          )
    except Exception as e:
      st.error(f"Error cargando atletas asignados: {e}")

  else:
    # 🏊‍♂️ ROL NADADOR
    if rol_real == "Administrador":
      spc()
      st.sidebar.subheader("🏊‍♂️ Selección de Nadador a Simular")
      atletas_disponibles = obtener_nadadores_activos_cache() or []

      if atletas_disponibles:
        df_atl = pd.DataFrame(atletas_disponibles)
        dict_atletas = dict(zip(df_atl["id"], df_atl["nombre"]))

        sel_id = st.sidebar.selectbox(
            "Simular sesión del atleta:",
            options=list(dict_atletas.keys()),
            format_func=lambda x: dict_atletas[x],
            key="sb_atleta_simular_nadador",
        )
        atleta_row = df_atl[df_atl["id"] == sel_id].iloc[0]

        st.session_state["nadador_seleccionado_id"] = int(atleta_row["id"])
        st.session_state["nadador_seleccionado_nombre"] = atleta_row[
            "nombre"
        ]
        st.session_state["nadador_seleccionado_genero"] = atleta_row.get(
            "genero", "M"
        )

        cat_calc, _ = (
            calcular_categoria_competencia(atleta_row["fecha_nacimiento"])
            if atleta_row.get("fecha_nacimiento")
            else ("Sin Categoría", 0)
        )
        st.session_state["nadador_seleccionado_categoria"] = cat_calc
      else:
        st.sidebar.warning("⚠️ No hay atletas disponibles.")
    else:
      st.session_state["nadador_seleccionado_id"] = st.session_state.get(
          "usuario_logueado_id"
      ) or st.session_state.get("usuario_id")
      st.session_state["nadador_seleccionado_nombre"] = st.session_state.get(
          "nombre_nadador"
      )
      st.session_state["nadador_seleccionado_genero"] = st.session_state.get(
          "genero", "M"
      )
      st.session_state["nadador_seleccionado_categoria"] = (
          st.session_state.get("categoria_atleta", "")
      )

  # -------------------------------------------------------------
  # 4. SELECCIÓN DE PRUEBA
  # -------------------------------------------------------------
  spc()
  st.sidebar.subheader("📊 Ajustes por prueba")

  cat_atleta = st.session_state.get("nadador_seleccionado_categoria") or ""
  es_preinfantil = (
      cat_atleta.startswith("Preinfantil") if cat_atleta else False
  )

  lista_pruebas = (
      obtener_pruebas_por_categoria(cat_atleta)
      if cat_atleta
      else ["--- Seleccione Nadador ---"]
  )
  if not lista_pruebas:
    lista_pruebas = ["--- Sin Pruebas Disponibles ---"]

  index_default = 1 if len(lista_pruebas) > 1 else 0
  titulo_grafico = st.sidebar.selectbox(
      "Estilo y Distancia:", options=lista_pruebas, index=index_default
  )

  if titulo_grafico.startswith("---"):
    st.sidebar.info("👆 Selecciona un atleta o prueba válida para continuar.")
    st.stop()

  st.session_state["prueba_seleccionada"] = titulo_grafico

  # -------------------------------------------------------------
  # 5. ANÁLISIS COLECTIVO (MODO EQUIPO)
  # -------------------------------------------------------------
  if rol_activo in ["Head Coach", "Administrador", "Entrenador"]:
    spc()
    st.sidebar.subheader("👥 Análisis Colectivo")
    modo_equipo = st.sidebar.checkbox(
        "Activar Comparativa de Equipo", value=False
    )

    if modo_equipo:
      spc()
      st.sidebar.subheader("🔍 Filtros de Segmentación de Equipo")
      filtro_genero = st.sidebar.radio(
          "Segmentar por Género:",
          options=["Todos", "Femenino (F)", "Masculino (M)"],
      )
      tipo_filtro = st.sidebar.radio(
          "Segmentar adicionalmente por:",
          options=[
              "Todos los Atletas",
              "Categoría Etaria",
              "Atletas Específicos",
          ],
      )

      try:
        atletas_preload = obtener_nadadores_activos_cache() or []

        if rol_activo == "Entrenador" and rol_real != "Administrador":
          id_coach = st.session_state.get(
              "usuario_logueado_id"
          ) or st.session_state.get("usuario_id")
          raw_asig = obtener_atletas_asignados_cache(id_coach) or []

          set_asig_str = set()
          for item in raw_asig:
            if isinstance(item, dict):
              v = (
                  item.get("atleta_id")
                  or item.get("id")
                  or item.get("usuario_id")
              )
              if v is not None:
                set_asig_str.add(str(v))
            elif item is not None:
              set_asig_str.add(str(item))

          atletas_preload = [
              a
              for a in atletas_preload
              if isinstance(a, dict)
              and str(
                  a.get("id") if a.get("id") is not None else a.get("usuario_id")
              )
              in set_asig_str
          ]

        if filtro_genero == "Femenino (F)":
          atletas_preload = [
              a for a in atletas_preload if a.get("genero") == "F"
          ]
        elif filtro_genero == "Masculino (M)":
          atletas_preload = [
              a for a in atletas_preload if a.get("genero") == "M"
          ]

        if tipo_filtro == "Categoría Etaria" and atletas_preload:
          cat_list = [
              calcular_categoria_competencia(a.get("fecha_nacimiento"))[0]
              for a in atletas_preload
              if a.get("fecha_nacimiento")
          ]
          categorias_disponibles = sorted(list(set(cat_list)))
          if categorias_disponibles:
            cat_sel = st.sidebar.selectbox(
                "Seleccione la categoría:", options=categorias_disponibles
            )
            lista_atletas = [
                a
                for a in atletas_preload
                if a.get("fecha_nacimiento")
                and calcular_categoria_competencia(a.get("fecha_nacimiento"))[0]
                == cat_sel
            ]

        elif tipo_filtro == "Atletas Específicos" and atletas_preload:
          dict_nom = {
              a["id"]: a["nombre"]
              for a in atletas_preload
              if "id" in a and "nombre" in a
          }
          if dict_nom:
            ids_sel = st.sidebar.multiselect(
                "Seleccione nadadores:",
                options=list(dict_nom.keys()),
                format_func=lambda x: dict_nom[x],
            )
            lista_atletas = [
                a for a in atletas_preload if a.get("id") in ids_sel
            ]
        else:
          lista_atletas = atletas_preload

        if (
            lista_atletas
            and titulo_grafico
            and not titulo_grafico.startswith("---")
        ):
          lista_ids_filtrados = [a["id"] for a in lista_atletas if "id" in a]
          df_global = obtener_marcas_equipo_cache(
              st.session_state.supabase, lista_ids_filtrados, titulo_grafico
          )

      except Exception as e:
        st.sidebar.error(f"Error cargando los filtros secundarios: {e}")

  # -------------------------------------------------------------
  # 6. EXTRACCIÓN ALINEADA CON 'marcas_referencia'
  # -------------------------------------------------------------
  contenedor_sliders = st.sidebar.container()

  if es_preinfantil:

    def get_m_ano_infantil_a(prueba_str):
      try:
        ref_resp = obtener_marcas_referencia_cache(
            prueba_str,
            st.session_state.get("nadador_seleccionado_genero", "M"),
            "Infantil A",
        )
        if ref_resp and ref_resp[0].get("m_ano") is not None:
          return float(ref_resp[0]["m_ano"])
      except Exception:
        pass
      return 0.0

    if titulo_grafico.startswith("25 "):
      estilo = titulo_grafico.split(" ")[1]
      ref_50 = get_m_ano_infantil_a(f"50 {estilo}")
      m_ano = ref_50 / 2.0
      m_wr = m_ano * 0.8 if m_ano > 0 else 15.0
    elif titulo_grafico == "50 Libre":
      m_ano = get_m_ano_infantil_a("50 Libre")
      m_wr = m_ano * 0.8 if m_ano > 0 else 30.0
    elif titulo_grafico == "100 Combinado":
      m_l = get_m_ano_infantil_a("50 Libre")
      m_e = get_m_ano_infantil_a("50 Espalda")
      m_p = get_m_ano_infantil_a("50 Pecho")
      m_m = get_m_ano_infantil_a("50 Mariposa")

      if all(v > 0 for v in [m_l, m_e, m_p, m_m]):
        m_ano = ((m_l + m_e + m_p + m_m) / 2.0) * 1.15
      else:
        m_ano = 0.0
      m_wr = m_ano * 0.8 if m_ano > 0 else 70.0
  else:
    try:
      genero_sel = st.session_state.get("nadador_seleccionado_genero", "M")
      cat_sel_atleta = st.session_state.get(
          "nadador_seleccionado_categoria", ""
      )

      if cat_sel_atleta:
        ref_resp = obtener_marcas_referencia_cache(
            titulo_grafico, genero_sel, cat_sel_atleta
        )
        if ref_resp:
          ref_data = ref_resp[0]
          m_ano = (
              float(ref_data["m_ano"])
              if ref_data.get("m_ano") is not None
              else 0.0
          )
          m_panam_b = (
              float(ref_data["m_panam_b"])
              if ref_data.get("m_panam_b") is not None
              else 0.0
          )
          m_panam_a = (
              float(ref_data["m_panam_a"])
              if ref_data.get("m_panam_a") is not None
              else 0.0
          )
          m_wa_b = (
              float(ref_data["m_wa_b"])
              if ref_data.get("m_wa_b") is not None
              else 0.0
          )
          m_wa_a = (
              float(ref_data["m_wa_a"])
              if ref_data.get("m_wa_a") is not None
              else 0.0
          )
          m_wr = (
              float(ref_data["m_wr"])
              if ref_data.get("m_wr") is not None
              else 25.0
          )
    except Exception as e:
      st.error(f"Error extrayendo marcas de la categoría: {e}")

  # -------------------------------------------------------------
  # 7. MODO SIMULACIÓN Y EXTRACCIÓN HISTÓRICA DE PB
  # -------------------------------------------------------------
  spc()
  st.sidebar.subheader("🚨 Simulación de Escenarios")
  simulacion_externa = st.sidebar.checkbox(
      "Activar Modo Simulación Externa", value=False
  )

  try:
    id_atleta_sel = st.session_state.get("nadador_seleccionado_id")
    datos_historicos = (
        obtener_marcas_historicas_cache(titulo_grafico, id_atleta_sel)
        if id_atleta_sel
        else None
    )

    if datos_historicos:
      df_procesado = pd.DataFrame(datos_historicos)
      df_procesado = df_procesado.rename(
          columns={
              "edad": "Edad",
              "tiempo": "Tiempo",
              "nota": "Evento / Fecha",
          }
      )
      db_t0, db_T0, db_t_pb, db_T_pb = procesar_mejor_marca_historica(
          df_procesado
      )
    else:
      db_t0, db_T0, db_t_pb, db_T_pb = None, None, None, None
  except Exception:
    db_t0, db_T0, db_t_pb, db_T_pb = None, None, None, None

  inputs_bloqueados = not simulacion_externa

  val_t0 = db_t0 if (db_t0 is not None) else 10.0
  val_T0 = db_T0 if (db_T0 is not None) else float(round(m_wr * 1.8, 2))
  val_t_pb = db_t_pb if (db_t_pb is not None) else 12.0
  val_T_pb = db_T_pb if (db_T_pb is not None) else float(round(m_wr * 1.3, 2))

  st.session_state["val_t0"] = val_t0
  st.session_state["val_T0"] = val_T0
  st.session_state["val_t_pb"] = val_t_pb
  st.session_state["val_T_pb"] = val_T_pb

  if es_preinfantil:
    val_T_target = float(round(m_ano, 2)) if m_ano > 0 else 25.0
  else:
    val_T_target = (
        float(round(m_wa_a * 0.99, 2))
        if m_wa_a > 0
        else float(round(m_wr * 1.08, 2))
    )

  # -------------------------------------------------------------
  # 8. PARÁMETROS DE LÍMITES Y PB
  # -------------------------------------------------------------
  spc()
  st.sidebar.subheader(
      "📐 Parámetros de Límites y PB " + ("🔓" if simulacion_externa else "🔒")
  )

  t0 = st.sidebar.number_input(
      "1. Edad Start (t0):",
      min_value=4.0,
      value=val_t0,
      step=0.1,
      disabled=inputs_bloqueados,
  )

  T0_str = st.sidebar.text_input(
      "2. Tiempo Inicial (T0):",
      value=formatear_a_minutos(val_T0).replace(" s", ""),
      disabled=inputs_bloqueados,
      help="Formato mm:ss.00 o ss.00",
  )
  try:
    T0 = float(convertir_string_a_segundos(T0_str))
  except ValueError:
    st.sidebar.error("❌ Formato T0 inválido. Use 'mm:ss.00'")
    T0 = float(val_T0)

  t_peak = st.sidebar.number_input(
      "3. Edad Peak Proyectado (t_peak):",
      min_value=5.0,
      max_value=30.0,
      step=1.0,
      value=23.0,
  )

  T_target_str = st.sidebar.text_input(
      "4. Tiempo Objetivo Peak (T_target):",
      value=formatear_a_minutos(val_T_target).replace(" s", ""),
      help="Formato mm:ss.00 o ss.00",
  )
  try:
    T_target = float(convertir_string_a_segundos(T_target_str))
  except ValueError:
    st.sidebar.error("❌ Formato T_target inválido. Use 'mm:ss.00'")
    T_target = float(val_T_target)

  t_pb = st.sidebar.number_input(
      "5. Edad del PB de Control (t_pb):",
      min_value=4.0,
      value=val_t_pb,
      step=0.05,
      disabled=inputs_bloqueados,
  )

  T_pb_str = st.sidebar.text_input(
      "6. Tiempo del PB de Control (T_pb):",
      value=formatear_a_minutos(val_T_pb).replace(" s", ""),
      disabled=inputs_bloqueados,
      help="Formato mm:ss.00 o ss.00",
  )
  try:
    T_pb = float(convertir_string_a_segundos(T_pb_str))
  except ValueError:
    st.sidebar.error("❌ Formato T_pb inválido. Use 'mm:ss.00'")
    T_pb = float(val_T_pb)

  st.session_state["t0_segundos"] = T0
  st.session_state["ttarget_segundos"] = T_target
  st.session_state["tpb_segundos"] = T_pb

  # -------------------------------------------------------------
  # 9. CONTROLES DE VISTA
  # -------------------------------------------------------------
  tipo_vista = st.sidebar.selectbox(
      "Enfoque del Gráfico",
      ["Macro (Historial Completo)", "Micro (Ventana Anual)"],
  )

  if tipo_vista == "Micro (Ventana Anual)":
    usuario_id = st.session_state.get("nadador_seleccionado_id")
    user = obtener_usuario_por_id_cache(usuario_id) if usuario_id else None

    if user and user.get("fecha_nacimiento"):
      birth_date = datetime.date.fromisoformat(
          str(user["fecha_nacimiento"])[:10]
      )
      min_date = birth_date + timedelta(days=int(float(t0) * 365.25))
      max_date = birth_date + timedelta(days=int(float(t_peak) * 365.25))

      año_actual = datetime.date.today().year
      if año_actual < min_date.year:
        año_actual = min_date.year
      elif año_actual > max_date.year:
        año_actual = max_date.year

      default_start = max(min_date, datetime.date(año_actual, 1, 1))
      default_end = min(max_date, datetime.date(año_actual, 12, 31))

      rango_fechas = st.sidebar.slider(
          "🔎 Rango de la Ventana (Fechas)",
          min_value=min_date,
          max_value=max_date,
          value=(default_start, default_end),
          step=timedelta(days=1),
          format="DD/MM/YYYY",
      )

      edad_min_zoom = (rango_fechas[0] - birth_date).days / 365.25
      edad_max_zoom = (rango_fechas[1] - birth_date).days / 365.25
    else:
      limite_inf_abs = float(t0)
      limite_sup_abs = float(t_peak)
      rango_def_min = max(limite_inf_abs, min(float(t_pb), limite_sup_abs))
      rango_def_max = min(rango_def_min + 1.0, limite_sup_abs)

      edad_min_zoom, edad_max_zoom = st.sidebar.slider(
          "🔎 Rango de la Ventana (Edad)",
          min_value=limite_inf_abs,
          max_value=limite_sup_abs,
          value=(rango_def_min, rango_def_max),
          step=0.1,
          format="%.2f años",
      )

  # -------------------------------------------------------------
  # 10. CONTENEDOR DE SLIDERS Y NOTA
  # -------------------------------------------------------------
  with contenedor_sliders:
    spc()
    st.markdown("**⏱️ Rapidez de Deriva e Intervalo**")

    factor_h = st.slider(
        "Factor ajustable de rapidez de deriva (h):",
        min_value=0.1,
        max_value=1.0,
        value=0.35,
        step=0.05,
    )
    t_intermedia = st.slider(
        "Consultar Edad Intermedia:",
        min_value=float(t0),
        max_value=float(t_peak),
        value=float(round((t0 + t_peak) / 2, 1)),
        step=0.1,
    )

  if not modo_equipo and rol_activo == "Nadador":
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "📅 *Requerido proyectar cada 3 meses hasta los 18 años para verificar"
        " marcas, asistir a campeonatos y optar por becas universitarias"
        " nacionales e internacionales.*"
    )

  # -------------------------------------------------------------
  # 11. RETORNO DE DATOS EMPAQUETADOS
  # -------------------------------------------------------------
  return {
      "usuario_id": st.session_state.get("nadador_seleccionado_id"),
      "genero": st.session_state.get("nadador_seleccionado_genero", "M"),
      "nombre": st.session_state.get("nadador_seleccionado_nombre", "Atleta"),
      "categoria": st.session_state.get("nadador_seleccionado_categoria", ""),
      "titulo_grafico": titulo_grafico,
      "simulacion_externa": simulacion_externa,
      "modo_equipo": modo_equipo,
      "filtro_genero": filtro_genero,
      "tipo_filtro": tipo_filtro,
      "cat_sel": cat_sel,
      "ids_sel": ids_sel,
      "lista_atletas_filtrados": lista_atletas,
      "df_global_marcas": df_global,
      "t0": t0,
      "T0": T0,
      "t_peak": t_peak,
      "T_target": T_target,
      "t_pb": t_pb,
      "T_pb": T_pb,
      "tipo_vista": tipo_vista,
      "edad_min_zoom": edad_min_zoom,
      "edad_max_zoom": edad_max_zoom,
      "factor_h": factor_h,
      "t_intermedia": t_intermedia,
      "df_procesado": df_procesado,
      "m_ano": m_ano,
      "m_panam_b": m_panam_b,
      "m_panam_a": m_panam_a,
      "m_wa_b": m_wa_b,
      "m_wa_a": m_wa_a,
      "m_wr": m_wr,
  }
