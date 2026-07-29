# -------------------------------------------------------------
# CACHÉ INTELIGENTE PARA CONSULTAS A SUPABASE (OPTIMIZACIÓN DE RENDIMIENTO)
# -------------------------------------------------------------
import streamlit as st
import pandas as pd

def _get_db():
    return st.session_state.get("supabase")

# =============================================================================
# FUNCIONES GLOBALMENTE CACHADAS (OPTIMIZACIÓN DE SUPABASE)
# =============================================================================
@st.cache_data(ttl=3600)
def obtener_atletas_asignados_cache(id_entrenador):
  """Retorna los atletas vinculados al entrenador desde la tabla 'asignaciones'."""
  if id_entrenador is None:
    return []

  # Cliente Supabase directo de la sesión
  client = st.session_state.get("supabase") or getattr(
      st.session_state, "supabase", None
  )
  if not client:
    return []

  try:
    # 1. Consulta a la tabla correcta 'asignaciones'
    res = (
        client.table("asignaciones")
        .select("atleta_id")
        .eq("entrenador_id", id_entrenador)
        .eq("activo", True)
        .execute()
    )

    # 2. Reintento convirtiendo a int si el id vino como texto y no trajo registros
    if not res.data and str(id_entrenador).isdigit():
      res = (
          client.table("asignaciones")
          .select("atleta_id")
          .eq("entrenador_id", int(id_entrenador))
          .eq("activo", True)
          .execute()
      )

    if res.data:
      return [
          item["atleta_id"]
          for item in res.data
          if item.get("atleta_id") is not None
      ]

  except Exception as e:
    st.error(f"Error consultando tabla asignaciones: {e}")

  return []
    
@st.cache_data(ttl=300, show_spinner=False)
def obtener_bitacora_atleta_cache(atleta_id):
    """Descarga el historial completo de entrenamientos de la bitácora para un atleta de forma individual."""
    supabase = st.session_state.get("supabase")
    if not supabase or not atleta_id: 
        return []
    try:
        query_rep = supabase.table("bitacora_entrenamientos").select("*").eq("atleta_id", atleta_id).execute()
        return query_rep.data if query_rep and query_rep.data else []
    except: 
        return []
        
@st.cache_data(ttl=3600, show_spinner=False)
def obtener_nadadores_activos_cache():
  """Obtiene la nómina general de todos los nadadores activos en el sistema."""
  supabase = _get_db()
  if not supabase:
    return []
  try:
    resp = (
        supabase.table("usuarios")
        .select("id, nombre, email, genero, fecha_nacimiento")
        .eq("rol", "Nadador")
        .eq("estatus", "Activo")
        .execute()
    )
    return resp.data if resp.data else []
  except Exception:
    return []
      
def obtener_marcas_historicas_cache(prueba, usuario_id):
    supabase = _get_db()
    if not supabase: return []
    try:
        response = supabase.table("marcas_historicas").select("id, edad, tiempo, nota") \
            .eq("prueba", prueba).eq("usuario_id", usuario_id).order("edad", desc=False).execute()
        return response.data if response.data else []
    except: return []

@st.cache_data(ttl=86400, show_spinner=False)
def obtener_marcas_referencia_cache(prueba, genero, categoria):
    supabase = _get_db()
    if not supabase: return []
    try:
        ref_resp = supabase.table("marcas_referencia").select("*") \
            .eq("prueba", prueba).eq("genero", genero).eq("categoria", categoria).execute()
        return ref_resp.data if ref_resp.data else []
    except: return []

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_usuario_por_id_cache(usuario_id):
    supabase = _get_db()
    if not supabase: return None
    try:
        response = supabase.table("usuarios").select("id, nombre, genero, rol, estatus, fecha_nacimiento") \
            .eq("id", usuario_id).execute()
        return response.data[0] if response.data else None
    except Exception: return None

@st.cache_data(ttl=300, show_spinner=False)
def obtener_historial_hitos_cache(nadador_id):
    """Historial de hitos y competencias"""
    supabase = _get_db()
    if not supabase: return []
    try:
        # Nota: La relación con catalogo_competencias depende de que esté bien configurada en Supabase
        res = supabase.table("historial_hitos").select("*, catalogo_competencias(*)") \
            .eq("usuario_id", nadador_id).execute()
        return res.data if res.data else []
    except Exception: return []

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_catalogo_competencias_cache():
    supabase = _get_db()
    if not supabase: return []
    try:
        response = supabase.table("catalogo_competencias").select("*").execute()
        return response.data if response.data else []
    except Exception: return []

def obtener_marcas_equipo_cache(supabase, lista_ids_nadadores, prueba_seleccionada):
    """
    Consulta el historial de tiempos para un grupo de nadadores en una prueba específica.
    """
    if not lista_ids_nadadores:
        return pd.DataFrame() # Retorna un DataFrame vacío si no hay selección

    try:
        # Asegúrate de cambiar "marcas" por el nombre real de tu tabla de tiempos
        respuesta = supabase.table("marcas") \
            .select("usuario_id, nombre, genero, prueba, tiempo_segundos, fecha_competencia") \
            .eq("prueba", prueba_seleccionada) \
            .in_("usuario_id", lista_ids_nadadores) \
            .execute()

        datos = respuesta.data

        if datos:
            # Convertimos directamente el JSON (lista de diccionarios) a Pandas
            df_marcas = pd.DataFrame(datos)
            
            # Aseguramos que la columna de tiempo sea numérica
            df_marcas["tiempo_segundos"] = pd.to_numeric(df_marcas["tiempo_segundos"], errors="coerce")
            
            return df_marcas
        else:
            return pd.DataFrame()

    except Exception as e:
        # Silenciamos el error en la interfaz, pero puedes imprimirlo en consola para debug
        print(f"Error al consultar marcas del equipo: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def obtener_todo_el_historial_cache(usuario_id):
    """Descarga el 100% de las marcas de un atleta para procesamiento rápido en memoria."""
    supabase = _get_db()
    if not supabase: return []
    try:
        res = supabase.table("marcas_historicas").select("id, prueba, edad, tiempo, nota").eq("usuario_id", usuario_id).order("edad", desc=False).execute()
        return res.data if res.data else []
    except: return []

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_usuarios_por_rol_cache(rol="Entrenador"):
  supabase = _get_db()
  if not supabase:
    return []
  try:
    response = (
        supabase.table("usuarios")
        .select("id, nombre, genero, rol, estatus")
        .eq("rol", rol)
        .execute()
    )
    return response.data if response.data else []
  except Exception:
    return []
