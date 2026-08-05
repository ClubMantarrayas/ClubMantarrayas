import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import streamlit as st

MAPEO_PRUEBAS = {
    "50A": "50 Libre", "100A": "100 Libre", "200A": "200 Libre", "400A": "400 Libre",
    "800A": "800 Libre", "1500A": "1500 Libre", "50B": "50 Espalda", "100B": "100 Espalda",
    "200B": "200 Espalda", "50C": "50 Pecho", "100C": "100 Pecho", "200C": "200 Pecho",
    "50D": "50 Mariposa", "100D": "100 Mariposa", "200D": "200 Mariposa",
    "200E": "200 Combinado", "400E": "400 Combinado",
}

def normalizar_prueba(codigo):
    if not codigo:
        return ""
    codigo_limpio = codigo.strip().split()[0]
    return MAPEO_PRUEBAS.get(codigo_limpio, codigo_limpio)

def limpiar_texto_nombre(texto):
    """Elimina números, caracteres especiales e iniciales sueltas de un texto de nombre/apellido."""
    if not texto:
        return ""
    # 1. Quitar cualquier dígito (ej: '5Aguilera' -> 'Aguilera')
    texto_sin_numeros = re.sub(r"\d+", "", texto)
    # 2. Quitar caracteres que no sean letras o espacios
    texto_limpio = re.sub(r"[^\w\s]", "", texto_sin_numeros, flags=re.UNICODE)
    
    # 3. Excluir iniciales sueltas de 1 sola letra al final (ej: 'Maria A' -> 'Maria')
    partes = texto_limpio.strip().split()
    if partes and len(partes[-1]) == 1 and partes[-1].isalpha():
        partes.pop()
    return " ".join(partes)

def limpiar_nombre_atleta(nombre_raw, apellido_raw):
    nom = limpiar_texto_nombre(nombre_raw)
    ape = limpiar_texto_nombre(apellido_raw)
    return f"{nom} {ape}".strip()

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
    if not fecha_nacimiento_str or not fecha_marca_str:
        return None
    try:
        fecha_nac_obj = datetime.fromisoformat(fecha_nacimiento_str).date() if isinstance(fecha_nacimiento_str, str) else fecha_nacimiento_str
        fecha_marca_obj = datetime.fromisoformat(fecha_marca_str).date() if isinstance(fecha_marca_str, str) else fecha_marca_str
        diferencia_dias = (fecha_marca_obj - fecha_nac_obj).days
        return round(diferencia_dias / 365.25, 2)
    except Exception:
        return None

import io
import re
from datetime import datetime
import pandas as pd


def parsear_hy3(archivo_texto):
    resultados = []
    nadador_actual = None
    fecha_competencia_global = datetime.now().strftime("%Y-%m-%d")

    for linea in archivo_texto:
        if len(linea) < 2:
            continue
        record_type = linea[0:2]

        # B1: Intentar extraer fecha global del evento por si E2 no la trae
        if record_type == "B1":
            match_b1 = re.search(r"(\d{8})", linea[40:70])
            if match_b1:
                raw_f = match_b1.group(1)
                try:
                    fecha_competencia_global = datetime.strptime(
                        raw_f, "%m%d%Y"
                    ).strftime("%Y-%m-%d")
                except ValueError:
                    pass

        # D1: Atleta (Estructura: D1M 3215Aguilera ... 33.895.827  18902082011 14 ...)
        elif record_type == "D1":
            # 1. Apellido y Nombre
            apellido_raw = linea[7:27].strip()
            nombre_raw = linea[27:47].strip()
            nombre_limpio = limpiar_nombre_atleta(nombre_raw, apellido_raw)

            # 2. Cédula: Busca el patrón con o sin puntos (ej: 33.895.827)
            match_cedula = re.search(r"(\d{1,3}(?:\.\d{3}){2}|\d{7,8})", linea)
            cedula_limpia = (
                re.sub(r"[^\d]", "", match_cedula.group(1))
                if match_cedula
                else ""
            )

            # 3. Fecha Nacimiento: Buscar los 8 dígitos MMDDYYYY justo después de la cédula y los 3 dígitos internos
            # Ejemplo: "33.895.827      18902082011" -> Captura "02082011"
            fecha_nac_iso = None
            match_nac = re.search(
                r"\d{7,8}\s+\d{3}(\d{8})", re.sub(r"\.", "", linea)
            )

            if match_nac:
                raw_nac = match_nac.group(1)
                try:
                    fecha_nac_iso = datetime.strptime(
                        raw_nac, "%m%d%Y"
                    ).strftime("%Y-%m-%d")
                except ValueError:
                    pass

            nadador_actual = {
                "nombre_limpio": nombre_limpio,
                "cedula": cedula_limpia,
                "fecha_nacimiento_iso": fecha_nac_iso,
            }

        # E1: Evento
        elif record_type == "E1" and nadador_actual:
            nadador_actual["evento_actual"] = linea[18:24].strip()

        # E2: Tiempo y Fecha específica de la carrera (ej: 12062025 al final de la línea)
        elif (
            record_type == "E2"
            and nadador_actual
            and nadador_actual.get("evento_actual")
        ):
            tiempo_raw = linea[5:15].strip()

            # Extraer fecha específica de la prueba desde la línea E2 (ej: 12062025)
            fecha_carrera_iso = fecha_competencia_global
            match_fecha_e2 = re.search(r"(\d{8})\s+\d+\s+\d+$", linea.strip())
            if match_fecha_e2:
                raw_e2 = match_fecha_e2.group(1)
                try:
                    fecha_carrera_iso = datetime.strptime(
                        raw_e2, "%m%d%Y"
                    ).strftime("%Y-%m-%d")
                except ValueError:
                    pass

            if tiempo_raw:
                resultados.append(
                    {
                        "Atleta_Limpio": nadador_actual["nombre_limpio"],
                        "Cedula": nadador_actual["cedula"],
                        "Fecha_Nacimiento": nadador_actual[
                            "fecha_nacimiento_iso"
                        ],
                        "Fecha_Competencia": fecha_carrera_iso,
                        "Evento": nadador_actual["evento_actual"],
                        "Tiempo_Raw": tiempo_raw,
                    }
                )
            nadador_actual["evento_actual"] = None

    return pd.DataFrame(resultados)

def parsear_lenex(archivo_stream):
    archivo_stream.seek(0)
    tree = ET.parse(archivo_stream)
    root = tree.getroot()
    resultados = []
    fecha_competencia_iso = datetime.now().strftime("%Y-%m-%d")

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
            resultados.append({
                "Atleta_Limpio": nombre_limpio,
                "Cedula": cedula_limpia,
                "Fecha_Nacimiento": fecha_nac_iso,
                "Fecha_Competencia": fecha_competencia_iso,
                "Evento": result.get("event", "Desconocido"),
                "Tiempo_Raw": result.get("swimtime", "0"),
            })

    return pd.DataFrame(resultados)

def procesar_y_clasificar_marcas(df_crudo, nombre_competencia):
    supabase = st.session_state.supabase

    # Plantilla de usuarios y marcas registradas
    res_usuarios = (
        supabase.table("usuarios")
        .select("id, nombre, cedula, fecha_nacimiento")
        .execute()
    )
    usuarios_db = res_usuarios.data if res_usuarios.data else []

    res_marcas = (
        supabase.table("marcas_historicas")
        .select("usuario_id, prueba, tiempo, edad")
        .execute()
    )
    marcas_existentes = res_marcas.data if res_marcas.data else []

    set_duplicados = {
        (
            m["usuario_id"],
            str(m["prueba"]).strip().lower(),
            float(m["tiempo"]),
            float(m["edad"]),
        )
        for m in marcas_existentes
        if m["usuario_id"] is not None
        and m["tiempo"] is not None
        and m["edad"] is not None
    }

    validos_bd = []
    lista_validos, lista_duplicados, lista_no_encontrados = [], [], []

    for _, fila in df_crudo.iterrows():
        nombre_file = fila["Atleta_Limpio"]
        cedula_file = fila["Cedula"] if fila["Cedula"] else "N/A"
        fecha_nac_file = fila["Fecha_Nacimiento"]
        prueba_norm = normalizar_prueba(fila["Evento"])
        tiempo_sec = convertir_tiempo_a_segundos(fila["Tiempo_Raw"])
        fecha_comp_file = fila["Fecha_Competencia"]

        # Coincidencia en la plantilla
        usuario_match = None
        for u in usuarios_db:
            u_cedula = re.sub(r"[^\d]", "", str(u.get("cedula", "")))
            u_nombre = str(u.get("nombre", "")).strip().lower()

            if (
                cedula_file != "N/A"
                and u_cedula
                and cedula_file == u_cedula
            ):
                usuario_match = u
                break
            if u_nombre and (
                u_nombre == nombre_file.lower()
                or nombre_file.lower() in u_nombre
                or u_nombre in nombre_file.lower()
            ):
                usuario_match = u
                break

        # Resolver Fecha de Nacimiento (Archivo -> Base de datos)
        fecha_nac_definitiva = fecha_nac_file
        if (
            not fecha_nac_definitiva or fecha_nac_definitiva == "N/A"
        ) and usuario_match:
            fecha_nac_definitiva = usuario_match.get("fecha_nacimiento")

        # Calcular Edad Decimal
        edad_dec = calcular_edad_decimal(fecha_nac_definitiva, fecha_comp_file)

        # Diccionario único y estandarizado para las 3 tablas UI
        registro_ui = {
            "Atleta": usuario_match.get("nombre", nombre_file)
            if usuario_match
            else nombre_file,
            "Cédula": usuario_match.get("cedula", cedula_file)
            if usuario_match
            else cedula_file,
            "Prueba": prueba_norm,
            "Edad (Decimal)": edad_dec if edad_dec is not None else "N/A",
            "Tiempo (seg)": tiempo_sec,
            "Nota": nombre_competencia,
        }

        if not usuario_match:
            # Tabla 3: No pertenecen al club
            lista_no_encontrados.append(registro_ui)
        else:
            usr_id = usuario_match["id"]
            clave_duplicado = (
                usr_id,
                prueba_norm.lower(),
                float(tiempo_sec),
                float(edad_dec) if edad_dec is not None else 0.0,
            )

            if clave_duplicado in set_duplicados:
                # Tabla 2: Repetidos
                lista_duplicados.append(registro_ui)
            else:
                # Tabla 1: Admitidos válidos
                validos_bd.append(
                    {
                        "usuario_id": usr_id,
                        "prueba": prueba_norm,
                        "edad": edad_dec,
                        "tiempo": tiempo_sec,
                        "nota": nombre_competencia,
                    }
                )
                lista_validos.append(registro_ui)

    return (
        validos_bd,
        pd.DataFrame(lista_validos),
        pd.DataFrame(lista_duplicados),
        pd.DataFrame(lista_no_encontrados),
    )
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
                    st.error("❌ El archivo subido está completamente vacío.")
                    return
                try:
                    contenido_texto = bytes_data.decode("latin-1")
                except UnicodeDecodeError:
                    contenido_texto = bytes_data.decode("utf-8", errors="replace")

                df_crudo = parsear_hy3(io.StringIO(contenido_texto))

            elif extension in ["lxf", "len", "xml"]:
                df_crudo = parsear_lenex(archivo_subido)

            if df_crudo.empty:
                st.error("⚠️ No se encontraron resultados válidos en el archivo.")
                return

            nombre_comp = st.text_input("Nombre de la Competencia (nota):", placeholder="Ej: Campeonato Regional Oriente 2026")

            if nombre_comp:
                validos_bd, df_validos, df_duplicados, df_no_encontrados = procesar_y_clasificar_marcas(df_crudo, nombre_comp)

                st.markdown("---")
                st.subheader(f"1. Registros Válidos a Guardar en BD ({len(df_validos)})")
                if not df_validos.empty:
                    st.dataframe(df_validos, use_container_width=True)
                else:
                    st.info("No hay registros nuevos válidos para insertar.")

                st.subheader(f"2. Marcas Omitidas por Estar Duplicadas ({len(df_duplicados)})")
                if not df_duplicados.empty:
                    st.dataframe(df_duplicados, use_container_width=True)
                else:
                    st.caption("No se detectaron marcas duplicadas.")

                st.subheader(f"3. Atletas Omitidos por No Estar en la Plantilla ({len(df_no_encontrados)})")
                if not df_no_encontrados.empty:
                    st.dataframe(df_no_encontrados, use_container_width=True)
                else:
                    st.caption("Todos los atletas del archivo coinciden con la plantilla.")

                if not df_validos.empty:
                    if st.button("💾 Confirmar e Insertar en BD", type="primary"):
                        try:
                            supabase = st.session_state.supabase
                            supabase.table("marcas_historicas").insert(validos_bd).execute()
                            st.success(f"✅ ¡Se han insertado exitosamente {len(validos_bd)} marcas!")
                        except Exception as e:
                            st.error(f"❌ Error al guardar en la base de datos: {str(e)}")
            else:
                st.warning("⚠️ Por favor ingresa el nombre de la competencia para continuar.")

        except Exception as e:
            st.error(f"❌ Error procesando el archivo: {str(e)}")
