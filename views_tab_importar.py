import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import streamlit as st

# Diccionario para normalizar los códigos del archivo .hy3 a nombres estándar
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
    if not codigo:
        return ""
    codigo_limpio = codigo.strip().split()[0]
    return MAPEO_PRUEBAS.get(codigo_limpio, codigo_limpio)

def limpiar_nombre_atleta(nombre_raw, apellido_raw):
    """
    Limpia y construye 'Nombre Apellido', excluyendo letras o iniciales
    aisladas posteriores al apellido que inserta Hy-Tek (ej: 'Maria A' -> 'Maria', 'Felipe N' -> 'Felipe').
    """
    nom = nombre_raw.strip()
    ape = apellido_raw.strip()
    
    # Excluir iniciales/letras sueltas al final del nombre
    partes_nombre = nom.split()
    if partes_nombre and len(partes_nombre[-1]) == 1 and partes_nombre[-1].isalpha():
        partes_nombre.pop()
    nom_limpio = " ".join(partes_nombre)
    
    # Excluir iniciales/letras sueltas al final del apellido
    partes_apellido = ape.split()
    if partes_apellido and len(partes_apellido[-1]) == 1 and partes_apellido[-1].isalpha():
        partes_apellido.pop()
    ape_limpio = " ".join(partes_apellido)
    
    return f"{nom_limpio} {ape_limpio}".strip()

def convertir_tiempo_a_segundos(valor):
    if not valor:
        return 0.0
    s = str(valor).strip().upper().replace("L", "").replace(",", ".")
    if ":" in s:
        partes = s.split(":")
        try:
            return round(float(partes[0]) * 60 + float(partes[1]), 2)
        except ValueError:
            return 0.0
    try:
        return round(float(s), 2)
    except ValueError:
        pass
    if len(s) == 6 and s.isdigit():
        minutos = int(s[0:2])
        segundos = int(s[2:4])
        centesimas = int(s[4:6])
        return round((minutos * 60) + segundos + (centesimas / 100), 2)
    return 0.0

def calcular_edad_decimal(fecha_nacimiento_str, fecha_marca_str):
    """
    Usa la función original basada en isoformat pasándole las fechas
    previamente convertidas a YYYY-MM-DD.
    """
    if not fecha_nacimiento_str or not fecha_marca_str:
        return None
    try:
        if isinstance(fecha_nacimiento_str, str):
            fecha_nac_obj = datetime.fromisoformat(fecha_nacimiento_str).date()
        else:
            fecha_nac_obj = fecha_nacimiento_str

        if isinstance(fecha_marca_str, str):
            fecha_marca_obj = datetime.fromisoformat(fecha_marca_str).date()
        else:
            fecha_marca_obj = fecha_marca_str

        diferencia_dias = (fecha_marca_obj - fecha_nac_obj).days
        edad_decimal = diferencia_dias / 365.25
        return round(edad_decimal, 2)
    except Exception:
        return None

def parsear_hy3(archivo_texto):
    resultados = []
    nadador_actual = None
    fecha_competencia_iso = datetime.now().strftime("%Y-%m-%d")

    for linea in archivo_texto:
        if len(linea) < 2:
            continue
        record_type = linea[0:2]

        # Fecha de la Competencia (B1) -> MMDDYYYY en pos 43:51 o 60:68
        if record_type == "B1":
            raw_fecha_comp = linea[43:51].strip()
            if not raw_fecha_comp.isdigit() and len(linea) >= 68:
                raw_fecha_comp = linea[60:68].strip()
            if len(raw_fecha_comp) == 8 and raw_fecha_comp.isdigit():
                try:
                    dt_comp = datetime.strptime(raw_fecha_comp, "%m%d%Y")
                    fecha_competencia_iso = dt_comp.strftime("%Y-%m-%d")
                except ValueError:
                    pass

        # Datos del Nadador (D1)
        elif record_type == "D1":
            apellido_raw = linea[7:27].strip()
            nombre_raw = linea[27:47].strip()
            
            # Limpieza del nombre y extracción de cédula/nacimiento
            nombre_limpio = limpiar_nombre_atleta(nombre_raw, apellido_raw)
            cedula_raw = linea[47:67].strip()
            cedula_limpia = re.sub(r"[^\d]", "", cedula_raw)
            
            fecha_nac_raw = linea[67:75].strip()
            fecha_nac_iso = None
            if len(fecha_nac_raw) == 8 and fecha_nac_raw.isdigit():
                try:
                    dt_nac = datetime.strptime(fecha_nac_raw, "%m%d%Y")
                    fecha_nac_iso = dt_nac.strftime("%Y-%m-%d")
                except ValueError:
                    pass

            nadador_actual = {
                "nombre_limpio": nombre_limpio,
                "nombre_original": f"{nombre_raw} {apellido_raw}".strip(),
                "cedula": cedula_limpia,
                "fecha_nacimiento_iso": fecha_nac_iso,
                "fecha_competencia_iso": fecha_competencia_iso
            }

        # Evento/Prueba Individual (E1)
        elif record_type == "E1" and nadador_actual:
            evento_raw = linea[18:24].strip()
            nadador_actual["evento_actual"] = evento_raw

        # Tiempo del Evento (E2)
        elif record_type == "E2" and nadador_actual and nadador_actual.get("evento_actual"):
            tiempo_raw = linea[5:15].strip()
            if tiempo_raw:
                resultados.append({
                    "Atleta_Limpio": nadador_actual["nombre_limpio"],
                    "Atleta_Original": nadador_actual["nombre_original"],
                    "Cedula": nadador_actual["cedula"],
                    "Fecha_Nacimiento": nadador_actual["fecha_nacimiento_iso"],
                    "Fecha_Competencia": nadador_actual["fecha_competencia_iso"],
                    "Evento": nadador_actual["evento_actual"],
                    "Tiempo_Raw": tiempo_raw,
                })
            nadador_actual["evento_actual"] = None

    return pd.DataFrame(resultados)

def parsear_lenex(archivo_stream):
    archivo_stream.seek(0)
    tree = ET.parse(archivo_stream)
    root = tree.getroot()
    resultados = []
    fecha_competencia_iso = datetime.now().strftime("%Y-%m-%d")

    # Extraer fecha de competencia si está en el XML
    meet = root.find(".//MEET")
    if meet is not None and meet.get("startdate"):
        fecha_competencia_iso = meet.get("startdate")

    for athlete in root.findall(".//ATHLETE"):
        nombre_raw = athlete.get("firstname", "")
        apellido_raw = athlete.get("lastname", "")
        nombre_limpio = limpiar_nombre_atleta(nombre_raw, apellido_raw)
        cedula_limpia = re.sub(r"[^\d]", "", athlete.get("license", ""))
        fecha_nac_iso = athlete.get("birthdate", None)

        for result in athlete.findall(".//RESULT"):
            tiempo_raw = result.get("swimtime", "0")
            prueba = result.get("event", "Desconocido")
            resultados.append({
                "Atleta_Limpio": nombre_limpio,
                "Atleta_Original": f"{nombre_raw} {apellido_raw}".strip(),
                "Cedula": cedula_limpia,
                "Fecha_Nacimiento": fecha_nac_iso,
                "Fecha_Competencia": fecha_competencia_iso,
                "Evento": prueba,
                "Tiempo_Raw": tiempo_raw,
            })

    return pd.DataFrame(resultados)

def procesar_y_clasificar_marcas(df_crudo, nombre_competencia):
    """
    Cruza los datos del archivo con la base de datos y divide la información en 3 listas:
    1. Válidos para BD
    2. Marcas Duplicadas
    3. Atletas No Encontrados
    """
    supabase = st.session_state.supabase

    # Cargar usuarios registrados en la nómina
    res_usuarios = supabase.table("usuarios").select("id, nombre, cedula").execute()
    usuarios_db = res_usuarios.data if res_usuarios.data else []

    # Cargar marcas históricas existentes para detección de duplicados
    res_marcas = supabase.table("marcas_historicas").select("usuario_id, prueba, tiempo, edad").execute()
    marcas_existentes = res_marcas.data if res_marcas.data else []
    
    # Crear set de tuplas para búsqueda rápida de duplicados
    set_duplicados = {
        (m["usuario_id"], str(m["prueba"]).strip().lower(), float(m["tiempo"]), float(m["edad"]))
        for m in marcas_existentes if m["usuario_id"] is not None and m["tiempo"] is not None and m["edad"] is not None
    }

    validos_bd = []
    ui_validos = []
    ui_duplicados = []
    ui_no_encontrados = []

    for _, fila in df_crudo.iterrows():
        nombre_file = fila["Atleta_Limpio"].lower()
        cedula_file = fila["Cedula"]
        prueba_norm = normalizar_prueba(fila["Evento"])
        tiempo_sec = convertir_tiempo_a_segundos(fila["Tiempo_Raw"])
        edad_dec = calcular_edad_decimal(fila["Fecha_Nacimiento"], fila["Fecha_Competencia"])

        # Buscar usuario por cédula o coincidencia de nombre
        usuario_match = None
        for u in usuarios_db:
            u_cedula = re.sub(r"[^\d]", "", str(u.get("cedula", "")))
            u_nombre = str(u.get("nombre", "")).strip().lower()
            if cedula_file and u_cedula and cedula_file == u_cedula:
                usuario_match = u
                break
            if u_nombre and (u_nombre == nombre_file or nombre_file in u_nombre or u_nombre in nombre_file):
                usuario_match = u
                break

        if not usuario_match:
            # TABLA 3: Atleta no está en la plantilla
            ui_no_encontrados.append({
                "Atleta (Archivo)": fila["Atleta_Original"],
                "Atleta (Procesado)": fila["Atleta_Limpio"],
                "Cédula": cedula_file if cedula_file else "N/A",
                "Prueba": prueba_norm,
                "Motivo": "No pertenece a la plantilla del club"
            })
        else:
            usr_id = usuario_match["id"]
            clave_duplicado = (usr_id, prueba_norm.lower(), float(tiempo_sec), float(edad_dec) if edad_dec else 0.0)

            if clave_duplicado in set_duplicados:
                # TABLA 2: Marca duplicada
                ui_duplicados.append({
                    "Atleta": fila["Atleta_Limpio"],
                    "Cédula": usuario_match.get("cedula", cedula_file),
                    "Prueba": prueba_norm,
                    "Edad (Decimal)": edad_dec,
                    "Tiempo (seg)": tiempo_sec,
                    "Motivo": "Marca ya registrada previamente"
                })
            else:
                # TABLA 1: Registro válido listo para BD
                validos_bd.append({
                    "usuario_id": usr_id,
                    "prueba": prueba_norm,
                    "edad": edad_dec,
                    "tiempo": tiempo_sec,
                    "nota": nombre_competencia
                })
                ui_validos.append({
                    "Atleta": fila["Atleta_Limpio"],
                    "Cédula": usuario_match.get("cedula", cedula_file),
                    "Prueba": prueba_norm,
                    "Edad (Decimal)": edad_dec,
                    "Tiempo (seg)": tiempo_sec,
                    "Nota": nombre_competencia
                })

    return validos_bd, pd.DataFrame(ui_validos), pd.DataFrame(ui_duplicados), pd.DataFrame(ui_no_encontrados)

def renderizar_tab_importar():
    st.markdown("### 📥 Importación de Competencias (HY3 / Lenex)")
    archivo_subido = st.file_uploader(
        "Selecciona el archivo (.hy3, .lxf, .len, .xml)",
        type=["hy3", "txt", "lxf", "len", "xml"],
    )

    if archivo_subido:
        extension = archivo_subido.name.split(".")[-1].lower()
        df_crudo = pd.DataFrame()

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
                df_crudo = parsear_hy3(stringio)

            elif extension in ["lxf", "len", "xml"]:
                df_crudo = parsear_lenex(archivo_subido)
            else:
                st.error("❌ Formato no soportado. Sube un archivo con extensión .hy3, .lxf, .len o .xml")
                return

            if df_crudo.empty:
                st.error("⚠️ No se encontraron resultados válidos en la estructura del archivo.")
                return

            nombre_comp = st.text_input("Nombre de la Competencia (nota):", placeholder="Ej: Campeonato Regional Oriente 2026")

            if nombre_comp:
                validos_bd, df_validos, df_duplicados, df_no_encontrados = procesar_y_clasificar_marcas(df_crudo, nombre_comp)

                st.markdown("---")
                # TABLA 1: REGISTROS VÁLIDOS
                st.subheader(f"1. Registros Válidos a Guardar en BD ({len(df_validos)})")
                if not df_validos.empty:
                    st.dataframe(df_validos, use_container_width=True)
                else:
                    st.info("No hay registros nuevos válidos para insertar.")

                # TABLA 2: REGISTROS DUPLICADOS
                st.subheader(f"2. Marcas Omitidas por Estar Duplicadas ({len(df_duplicados)})")
                if not df_duplicados.empty:
                    st.dataframe(df_duplicados, use_container_width=True)
                else:
                    st.caption("No se detectaron marcas duplicadas.")

                # TABLA 3: ATLETAS NO ENCONTRADOS
                st.subheader(f"3. Atletas Omitidos por No Estar en la Plantilla ({len(df_no_encontrados)})")
                if not df_no_encontrados.empty:
                    st.dataframe(df_no_encontrados, use_container_width=True)
                else:
                    st.caption("Todos los atletas del archivo coinciden con la nómina del club.")

                # BOTÓN DE GUARDADO REAL EN BD
                if not df_validos.empty:
                    if st.button("💾 Confirmar e Insertar en BD", type="primary"):
                        try:
                            supabase = st.session_state.supabase
                            supabase.table("marcas_historicas").insert(validos_bd).execute()
                            st.success(f"✅ ¡Se han insertado exitosamente {len(validos_bd)} marcas en la base de datos!")
                        except Exception as e:
                            st.error(f"❌ Error al guardar en la base de datos: {str(e)}")
            else:
                st.warning("⚠️ Por favor ingresa el nombre de la competencia para procesar la vista previa.")

        except Exception as e:
            st.error(f"❌ Error crítico procesando la estructura del archivo: {str(e)}")
