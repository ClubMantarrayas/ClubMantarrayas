import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import streamlit as st

# ==========================================
# 1. FUNCIONES DE LIMPIEZA Y TRANSFORMACIÓN
# ==========================================
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
    if not texto:
        return ""
    texto_sin_numeros = re.sub(r"\d+", "", texto)
    texto_limpio = re.sub(r"[^\w\s]", "", texto_sin_numeros, flags=re.UNICODE)
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

# ==========================================
# 2. PARSERS (Solo extracción de datos)
# ==========================================
def parsear_hy3(archivo_texto):
    resultados = []
    nadadores_procesados = {} # INTEGRACIÓN: Diccionario para unificar bloques D1 duplicados (leadoffs)
    nadador_actual = None

    for linea in archivo_texto:
        if len(linea) < 2:
            continue
        record_type = linea[0:2]

        if record_type == "D1":
            apellido_raw = linea[7:27].strip()
            nombre_raw = linea[27:47].strip()
            nombre_limpio = limpiar_nombre_atleta(nombre_raw, apellido_raw)

            match_cedula = re.search(r"(\d{1,3}(?:\.\d{3}){2}|\d{7,8})", linea)
            cedula_limpia = re.sub(r"[^\d]", "", match_cedula.group(1)) if match_cedula else ""

            # Clave única para agrupar (cédula, o nombre si falla la cédula)
            id_nadador = cedula_limpia if cedula_limpia else nombre_limpio

            match_nac = re.search(r"(\d{8})\s+(\d{1,2})\b", linea)
            fecha_nac_raw = None
            edad_entera = None
            
            if match_nac:
                raw_nac = match_nac.group(1)
                edad_entera = int(match_nac.group(2))
                try:
                    fecha_nac_raw = datetime.strptime(raw_nac, "%m%d%Y").strftime("%Y-%m-%d")
                except ValueError:
                    pass

            info_nadador = {
                "Atleta_Limpio": nombre_limpio,
                "Cedula": cedula_limpia,
                "Edad_Entera_Raw": edad_entera,
                "Fecha_Nac_Raw": fecha_nac_raw,
            }

            # INTEGRACIÓN: Si el nadador ya fue leído (ej. prueba leadoff), reutilizamos su perfil
            if id_nadador in nadadores_procesados:
                nadador_actual = nadadores_procesados[id_nadador]
            else:
                nadadores_procesados[id_nadador] = info_nadador
                nadador_actual = nadadores_procesados[id_nadador]

        elif record_type == "E1" and nadador_actual:
            codigo_prueba = linea[18:24].strip()
            # INTEGRACIÓN: Se limpia el sufijo "L" de los relevos aquí para que el normalizador no falle
            codigo_limpio = re.sub(r"L$", "", codigo_prueba.split()[0])
            nadador_actual["Evento"] = codigo_limpio

        elif record_type == "E2" and nadador_actual and nadador_actual.get("Evento"):
            tiempo_raw = linea[5:15].strip()
            if tiempo_raw:
                res = nadador_actual.copy()
                res["Tiempo_Raw"] = tiempo_raw
                resultados.append(res)
            nadador_actual["Evento"] = None

    return pd.DataFrame(resultados)

def parsear_lenex(archivo_stream):
    archivo_stream.seek(0)
    tree = ET.parse(archivo_stream)
    root = tree.getroot()
    resultados = []

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
                "Edad_Entera_Raw": None,
                "Fecha_Nac_Raw": fecha_nac_iso,
                "Evento": result.get("event", "Desconocido"),
                "Tiempo_Raw": result.get("swimtime", "0"),
            })

    return pd.DataFrame(resultados)

# ==========================================
# 3. PROCESADOR CENTRAL Y MOTOR HÍBRIDO
# ==========================================
def procesar_y_clasificar_marcas(df_crudo, nombre_competencia, fecha_inicio_comp_obj):
    supabase = st.session_state.supabase

    res_usuarios = supabase.table("usuarios").select("id, nombre, cedula, fecha_nacimiento").execute()
    usuarios_db = res_usuarios.data if res_usuarios.data else []

    res_marcas = supabase.table("marcas_historicas").select("usuario_id, prueba, tiempo, edad").execute()
    marcas_existentes = res_marcas.data if res_marcas.data else []

    marcas_por_usuario = {}
    for m in marcas_existentes:
        uid = m.get("usuario_id")
        if uid:
            if uid not in marcas_por_usuario:
                marcas_por_usuario[uid] = []
            marcas_por_usuario[uid].append({
                "prueba": str(m["prueba"]).strip().lower() if m["prueba"] else "",
                "tiempo": float(m["tiempo"]) if m["tiempo"] is not None else 0.0,
                "edad": float(m["edad"]) if m["edad"] is not None else 0.0
            })

    validos_bd = []
    lista_validos, lista_duplicados, lista_no_encontrados = [], [], []

    for _, fila in df_crudo.iterrows():
        nombre_file = fila["Atleta_Limpio"]
        cedula_file = fila["Cedula"] if fila["Cedula"] else "N/A"
        prueba_norm = normalizar_prueba(fila["Evento"])
        tiempo_sec = convertir_tiempo_a_segundos(fila["Tiempo_Raw"])

        usuario_match = None
        for u in usuarios_db:
            u_cedula = re.sub(r"[^\d]", "", str(u.get("cedula", "")))
            u_nombre = str(u.get("nombre", "")).strip().lower()

            if cedula_file != "N/A" and u_cedula and cedula_file == u_cedula:
                usuario_match = u
                break
            if u_nombre and (u_nombre == nombre_file.lower() or nombre_file.lower() in u_nombre or u_nombre in nombre_file.lower()):
                usuario_match = u
                break

        edad_dec = None
        if usuario_match and usuario_match.get("fecha_nacimiento"):
            try:
                fn_dt = datetime.strptime(usuario_match["fecha_nacimiento"], "%Y-%m-%d").date()
                dias_diferencia = (fecha_inicio_comp_obj - fn_dt).days
                edad_dec = round(dias_diferencia / 365.25, 2)
            except Exception:
                edad_dec = None
        else:
            if fila.get("Fecha_Nac_Raw"):
                try:
                    fn_dt = datetime.strptime(fila["Fecha_Nac_Raw"], "%Y-%m-%d").date()
                    edad_dec = round((fecha_inicio_comp_obj - fn_dt).days / 365.25, 2)
                except Exception:
                    pass
            
            if edad_dec is None and pd.notna(fila.get("Edad_Entera_Raw")):
                edad_dec = round(float(fila["Edad_Entera_Raw"]), 2)

        registro_ui = {
            "Atleta": usuario_match.get("nombre", nombre_file) if usuario_match else nombre_file,
            "Cédula": usuario_match.get("cedula", cedula_file) if usuario_match else cedula_file,
            "Prueba": prueba_norm,
            "Edad (Decimal)": edad_dec if edad_dec is not None else "N/A",
            "Tiempo (seg)": tiempo_sec,
            "Nota": nombre_competencia,
        }

        if not usuario_match:
            lista_no_encontrados.append(registro_ui)
        else:
            usr_id = usuario_match["id"]
            
            es_duplicado = False
            marcas_hist_usuario = marcas_por_usuario.get(usr_id, [])
            
            for m in marcas_hist_usuario:
                if m["prueba"] == prueba_norm.lower() and m["tiempo"] == float(tiempo_sec):
                    if edad_dec is not None:
                        if abs(m["edad"] - edad_dec) <= 0.021:
                            es_duplicado = True
                            break
                    else:
                        es_duplicado = True
                        break

            if es_duplicado:
                lista_duplicados.append(registro_ui)
            else:
                validos_bd.append({
                    "usuario_id": usr_id,
                    "prueba": prueba_norm,
                    "edad": edad_dec,
                    "tiempo": tiempo_sec,
                    "nota": nombre_competencia,
                })
                lista_validos.append(registro_ui)

    return (
        validos_bd,
        pd.DataFrame(lista_validos),
        pd.DataFrame(lista_duplicados),
        pd.DataFrame(lista_no_encontrados),
    )

# ==========================================
# 4. VISTA (UI en Streamlit)
# ==========================================
def renderizar_tab_importar():
    st.markdown("### 📥 Importación de Competencias (HY3 / Lenex)")
    
    nombre_comp = st.text_input("Nombre de la Competencia (nota):", placeholder="Ej: Campeonato Regional Oriente 2026")
    fecha_inicio = st.date_input("Fecha de Inicio del Campeonato", datetime.now())
    
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

            if nombre_comp:
                validos_bd, df_validos, df_duplicados, df_no_encontrados = procesar_y_clasificar_marcas(
                    df_crudo, 
                    nombre_comp,
                    fecha_inicio
                )

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
