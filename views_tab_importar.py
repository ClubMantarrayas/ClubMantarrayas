import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import streamlit as st

# Diccionario para normalizar los códigos del archivo .hy3
MAPEO_PRUEBAS = {
    "50A": "50 Libre",
    "100A": "100 Libre",
    "200A": "200 Libre",
    "400A": "400 Libre",
    "800A": "800 Libre",
    "1500A": "1500 Libre",
    "50B": "50 Espalda",
    "100B": "100 Espalda",
    "200B": "200 Espalda",
    "50C": "50 Pecho",
    "100C": "100 Pecho",
    "200C": "200 Pecho",
    "50D": "50 Mariposa",
    "100D": "100 Mariposa",
    "200D": "200 Mariposa",
    "200E": "200 Combinado",
    "400E": "400 Combinado",
}


def normalizar_prueba(codigo):
  # Extraer la prueba quitando sufijos de categoría si existen
  codigo_limpio = codigo.strip().split()[0] if codigo else ""
  return MAPEO_PRUEBAS.get(codigo_limpio, codigo)


def convertir_tiempo_a_segundos(valor):
  """Procesa tiempos en string como '35,00L', '1:12.50', '172,61L' o '012010'
  y los convierte a un float de segundos.
  """
  if not valor:
    return 0.0

  s = str(valor).strip().upper().replace("L", "").replace(",", ".")

  # Formato MM:SS.cc o SS.cc
  if ":" in s:
    partes = s.split(":")
    try:
      return float(partes[0]) * 60 + float(partes[1])
    except ValueError:
      return 0.0

  try:
    return float(s)
  except ValueError:
    pass

  # Fallback para enteros continuos de 6 dígitos (ej: 012010)
  if len(s) == 6 and s.isdigit():
    minutos = int(s[0:2])
    segundos = int(s[2:4])
    centesimas = int(s[4:6])
    return (minutos * 60) + segundos + (centesimas / 100)

  return 0.0


def parsear_hy3(archivo_texto):
  resultados = []
  nadador_actual = None
  evento_actual = None

  for linea in archivo_texto:
    if len(linea) < 2:
      continue
    record_type = linea[0:2]

    # Datos del Nadador (D1)
    if record_type == "D1":
      apellido = linea[12:22].strip()
      nombre = linea[27:47].strip()
      nadador_actual = f"{nombre} {apellido}".strip()

    # Evento/Prueba Individual (E1)
    elif record_type == "E1" and nadador_actual:
      # Ej: '50A', '100A', '200B'
      evento_raw = linea[18:24].strip()
      evento_actual = evento_raw

    # Tiempo del Evento (E2)
    elif record_type == "E2" and nadador_actual and evento_actual:
      tiempo_raw = linea[5:15].strip()
      if tiempo_raw:
        resultados.append({
            "Nadador": nadador_actual,
            "Evento": evento_actual,
            "Tiempo_Raw": tiempo_raw,
        })
      evento_actual = None  # Resetear para el siguiente evento

    # Fallback para estructura clásica F1
    elif record_type == "F1" and nadador_actual:
      evento = linea[12:18].strip()
      tiempo_raw = linea[32:38].strip()
      if tiempo_raw:
        resultados.append({
            "Nadador": nadador_actual,
            "Evento": evento,
            "Tiempo_Raw": tiempo_raw,
        })

  return pd.DataFrame(resultados)


def parsear_lenex(archivo_stream):
  archivo_stream.seek(0)
  tree = ET.parse(archivo_stream)
  root = tree.getroot()
  resultados = []
  for athlete in root.findall(".//ATHLETE"):
    nombre = (
        f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
    )
    for result in athlete.findall(".//RESULT"):
      tiempo_raw = result.get("swimtime", "0")
      prueba = result.get("event", "Desconocido")
      resultados.append(
          {"Nadador": nombre, "Evento": prueba, "Tiempo_Raw": tiempo_raw}
      )
  return pd.DataFrame(resultados)

def guardar_en_bd(df_procesado, nombre_competencia):
    supabase = st.session_state.supabase
    # Asume que 'supabase' está definido globalmente en tu app
    usuarios_db = supabase.table("usuarios").select("id, nombre, fecha_nacimiento").execute()
    usuarios_dict = {u['nombre'].lower(): {'id': u['id'], 'nacimiento': u['fecha_nacimiento']} for u in usuarios_db.data}
    
    registros_a_insertar = []
    for _, fila in df_procesado.iterrows():
        nombre_file = fila['Nadador'].lower()
        user_info = next((u for name, u in usuarios_dict.items() if name in nombre_file or nombre_file in name), None)
        
        if user_info:
            fecha_nac = pd.to_datetime(user_info['nacimiento'])
            edad_calculada = (datetime.now() - fecha_nac).days / 365.25
            registro = {
                "usuario_id": user_info['id'],
                "prueba": normalizar_prueba(fila['Evento']),
                "tiempo": float(fila['Tiempo']),
                "edad": round(edad_calculada, 2),
                "nota": nombre_competencia
            }
            registros_a_insertar.append(registro)
    
    # Debug: ver qué se va a insertar
    st.json(registros_a_insertar)
    
    if registros_a_insertar:
        try:
            # Descomenta la siguiente línea cuando estés listo para guardar de verdad
            supabase.table("marcas_historicas").insert(registros_a_insertar).execute()
            return True, len(registros_a_insertar)
        except Exception as e:
            return False, str(e)
    return False, "No se encontraron usuarios coincidentes."


def renderizar_tab_importar():
  st.markdown("### 📥 Importación de Competencias (HY3 / Lenex)")
  archivo_subido = st.file_uploader(
      "Selecciona el archivo (.hy3, .lxf, .len, .xml)",
      type=["hy3", "txt", "lxf", "len", "xml"],
  )

  if archivo_subido:
    extension = archivo_subido.name.split(".")[-1].lower()
    df = pd.DataFrame()

    try:
      if extension in ["hy3", "txt"]:
        bytes_data = archivo_subido.getvalue()
        if not bytes_data:
          st.error("❌ El archivo subido está completamente vacío (0 bytes).")
          return

        try:
          contenido_texto = bytes_data.decode("latin-1")
        except UnicodeDecodeError:
          contenido_texto = bytes_data.decode("utf-8", errors="replace")

        stringio = io.StringIO(contenido_texto)
        df = parsear_hy3(stringio)

        if df.empty:
          st.error(
              "⚠️ No se encontraron registros de atletas ni marcas en el"
              " archivo .HY3.\n\n"
              "**Posibles causas:**\n"
              "- El archivo no contiene la estructura estándar Hy-Tek (bloques"
              " D1 y E1/E2 o F1).\n"
              "- Es un archivo de inscripciones vacías o una lista de solo"
              " clubes sin marcas de tiempo."
          )
          return

      elif extension in ["lxf", "len", "xml"]:
        df = parsear_lenex(archivo_subido)
        if df.empty:
          st.error(
              "⚠️ No se encontraron resultados válidos dentro de la estructura"
              " XML/Lenex."
          )
          return
      else:
        st.error(
            "❌ Formato no soportado. Sube un archivo con extensión .hy3,"
            " .lxf, .len o .xml"
        )
        return

      # Si hay datos procesados, convertir los tiempos
      df["Tiempo"] = df["Tiempo_Raw"].apply(convertir_tiempo_a_segundos)
      st.success(
          f"✅ ¡Archivo {extension.upper()} procesado exitosamente!"
          f" ({len(df)} registros encontrados)"
      )
      st.dataframe(df, use_container_width=True)

      nombre_comp = st.text_input("Nombre de la Competencia (nota):")
      if st.button("💾 Validar y Guardar en BD"):
        if nombre_comp:
          exito, msg = guardar_en_bd(df, nombre_comp)
          if exito:
            st.success(f"✅ Se guardaron {msg} registros en la base de datos.")
          else:
            st.error(f"Error al guardar: {msg}")
        else:
          st.warning("Por favor escribe el nombre de la competencia.")

    except Exception as e:
      st.error(
          f"❌ Error crítico procesando la estructura del archivo: {str(e)}"
      )
