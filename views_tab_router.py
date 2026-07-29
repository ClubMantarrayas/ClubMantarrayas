# =============================================================================
# FILE: views/views_tab_router.py (Contenedor y Enrutador de Pestañas)
# =============================================================================
import streamlit as st

# 1. Importación directa (gracias al mapeo de ruta del root_app)
from views_sidebar import renderizar_sidebar_completo

# 2. IMPORTACIÓN DE CADA PESTAÑA DE MANERA DIRECTA
from views_tab_asignaciones import renderizar_tab_asignaciones
from views_tab_calendario import renderizar_tab_calendario
from views_tab_club import renderizar_tab_club
from views_tab_entrenador import renderizar_tab_entrenador
from views_tab_grafico import renderizar_tab_grafico
from views_tab_importar import renderizar_tab_importar
from views_tab_marcas import renderizar_tab_marcas
from views_tab_pizarra import renderizar_tab_pizarra
from views_tab_reportes import renderizar_tab_reportes


def mostrar_vista_enrutador():
  """Función maestra de inicialización que actúa como 'Director de Orquesta'."""
  # 1. Ejecutamos la barra lateral (aquí Soporte/Admin puede cambiar de rol en el selectbox)
  datos_sidebar = renderizar_sidebar_completo()
  st.session_state.update(datos_sidebar)

  # 2. Obtenemos el rol resultante (sea el real o el simulado desde el sidebar)
  rol_usuario = st.session_state.get("rol", "Nadador")

  # 3. SI EL ROL ES "CLUB", RENDERIZAMOS ÚNICAMENTE LA PESTAÑA DEL CLUB
  if rol_usuario == "Club":
    (tab_club,) = st.tabs(["🏛️ Gestión Administrativa"])
    with tab_club:
      renderizar_tab_club()

    st.markdown(
        """
        <style>
            .block-container.block-container { padding-top: 0.1rem; }
            .main > div { padding-bottom: 5rem; }
        </style>
    """,
        unsafe_allow_html=True,
    )
    return

  # 4. SI EL ROL CAMBIÓ A NADADOR, ENTRENADOR O HEAD COACH, DIBUJAMOS EL ENTORNO COMPLETO
  titulo_grafico = st.session_state.get("titulo_grafico")
  simulacion_externa = st.session_state.get("simulacion_externa", False)
  modo_equipo = st.session_state.get("modo_equipo", False)

  # Encabezado dinámico de atletas
  if modo_equipo:
    st.markdown(
        "### 🏊‍♂️ Planificación y control de resultados de competencia:"
        " Comparativo"
    )
  elif simulacion_externa:
    st.markdown(f"### 🧪 Simulación de Escenarios: {titulo_grafico}")
  else:
    nombre_nadador = st.session_state.get(
        "nadador_seleccionado_nombre", "Atleta"
    )
    st.markdown(
        "### 🏊‍♂️ Planificación y control de resultados de competencia:"
        f" {nombre_nadador}"
    )

  # --- CONTINÚA EL RENDERIZADO REGULAR DE LAS PESTAÑAS ---

  genero_str = (
      "Masculino (M)"
      if st.session_state.get("nadador_seleccionado_genero") == "M"
      else "Femenino (F)"
  )
  cat_str = st.session_state.get("nadador_seleccionado_categoria", "")
  st.markdown(
      f"**Género:** {genero_str} | **Categoría de Competencia Activa:**"
      f" `{cat_str}`"
  )
  st.markdown("---")

  # Segregación de pestañas según el Modo Simulación y el Rol
  if simulacion_externa:
    st.info(
        "⚠️ **Modo Simulación Externa Activo.** El módulo de gestión y control"
        " de marcas se encuentra oculto para evitar alterations en la base de"
        " datos real."
    )
    (tab_grafico,) = st.tabs(["📝 Gráfico de Proyecciones"])
  elif rol_usuario in ["Entrenador", "Nadador"]:
    (
        tab_grafico,
        tab_pizarra,
        tab_reportes,
        tab_marcas,
        tab_calendario,
    ) = st.tabs([
        "📉 Gráfico de Proyecciones",
        "📝 Pizarra Diaria",
        "📊 Reportes de Entrenamiento",
        "📋 Resultados de competencias",
        "📅 Calendario Anual de Competencias",
    ])
  else:
    (
        tab_grafico,
        tab_pizarra,
        tab_reportes,
        tab_marcas,
        tab_importar,
        tab_entrenador,
        tab_asignaciones,
        tab_calendario,
    ) = st.tabs([
        "📉 Gráfico de Proyecciones",
        "📝 Pizarra Diaria",
        "📊 Reportes de Entrenamiento",
        "📋 Resultados de competencias",
        "📋 Importar Resultados de competencias",
        "⏱️ Configurar Marcas Mínimas",
        "🎯 Asignaciones de Nadadores",
        "📅 Calendario Anual de Competencias",
    ])

  # Enrutamiento directo a los archivos
  with tab_grafico:
    renderizar_tab_grafico(datos_sidebar)

  if not simulacion_externa:
    with tab_pizarra:
      renderizar_tab_pizarra(datos_sidebar)
    with tab_reportes:
      renderizar_tab_reportes(datos_sidebar)
    with tab_marcas:
      renderizar_tab_marcas(datos_sidebar)

    # Solo renderizamos los tabs de gestión si no es Entrenador ni Nadador
    if rol_usuario not in ["Entrenador", "Nadador"]:
      with tab_importar:
        renderizar_tab_importar()
      with tab_entrenador:
        renderizar_tab_entrenador()
      with tab_asignaciones:
        renderizar_tab_asignaciones()

    with tab_calendario:
      renderizar_tab_calendario()

  # 🎨 Espaciado global para evitar el efecto de "contenido apretado"
  st.markdown(
      """
        <style>
            .block-container.block-container {
                padding-top: 0.1rem;
            }
            .main > div {
                padding-bottom: 5rem;
            }
        </style>
    """,
      unsafe_allow_html=True,
  )
