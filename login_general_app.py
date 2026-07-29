import base64
import datetime
import hashlib
import hmac
import random
import time
import os
# 📦 IMPORTACIÓN DIRECTA DESDE TU LIBRERÍA REAL DE FUNCIONES
from formulas_lib_funciones import (
    calcular_categoria_competencia,
    desencriptar_credencial,
    enviar_email,
    hash_password,
)
import streamlit as st
from supabase import Client, create_client


def aplicar_fondo_pantalla_institucional(
    nombre_archivo_imagen="Fondo_de_pantalla_Swimprojecttraining.png",
):
  """Lee una imagen desde la raíz del proyecto, la convierte a Base64 e inyecta CSS
  seguro en stApp con velo agua fresco y centrado vertical/horizontal.
  """
  # Verificar que el archivo existe en la raíz
  if os.path.exists(nombre_archivo_imagen):
    with open(nombre_archivo_imagen, "rb") as f:
      data_imagen = f.read()
    encoded_imagen = base64.b64encode(data_imagen).decode()

    # Determinamos la extensión del archivo para el MIME tipo
    ext = nombre_archivo_imagen.split(".")[-1].lower()
    mime_type = "png" if ext == "png" else "jpeg"

    css_fondo = f"""
        <style>
        /* Aplicar el fondo con un velo Azul Agua muy claro y luminoso (Frescura marina) */
        .stApp {{
            background-image: linear-gradient(135deg, rgba(186, 230, 253, 0.70), rgba(207, 250, 254, 0.82)), url("data:image/{mime_type};base64,{encoded_imagen}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        
        /* Contenedor principal: bajar un poco más verticalmente */
        .block-container {{
            padding-top: 3.5rem !important;
            max-width: 1100px !important;
        }}

        /* Tarjeta del formulario limpia, blanca con ligera transparencia y bordes suaves */
        [data-testid="stForm"] {{
            background-color: rgba(255, 255, 255, 0.96) !important;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0px 10px 30px rgba(6, 182, 212, 0.25);
            border: 1.5px solid rgba(103, 232, 249, 0.8);
        }}

        /* Garantizar que los botones siempre capturen el puntero */
        button {{
            pointer-events: auto !important;
            z-index: 99999 !important;
        }}
        </style>
        """
    st.markdown(css_fondo, unsafe_allow_html=True)
  else:
    pass

# ============================================================
# ⚙️ CONEXIÓN GLOBAL CACHEADA (A nivel raíz del archivo)
# ============================================================
@st.cache_resource
def obtener_cliente_supabase():
  return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


# ============================================================
# 🧹 PURGA DE SEGURIDAD (CONSERVA SOLO LA INFRAESTRUCTURA)
# ============================================================
def limpiar_sesion_al_autenticar():
  LLAVES_INFRAESTRUCTURA = {"puente_validado", "supabase"}

  for key in list(st.session_state.keys()):
    if key not in LLAVES_INFRAESTRUCTURA:
      del st.session_state[key]


def login_usuario(user, password, client_db):
  try:
    user_lower = user.strip().lower()
    hashed_pw = hash_password(password)

    response = (
        client_db.table("usuarios")
        .select("id, nombre, genero, rol, estatus, fecha_nacimiento")
        .eq("usuario", user_lower)
        .eq("contrasena", hashed_pw)
        .execute()
    )

    if response.data:
      user_data = response.data[0]

      if user_data.get("estatus") == "Inactivo":
        st.error(
            "⚠️  Aún no puedes ingresar. Debes contactar con la administración."
        )
        return False

      limpiar_sesion_al_autenticar()

      st.session_state.autenticado = True
      st.session_state.usuario_id = user_data["id"]
      st.session_state.usuario_logueado_id = user_data["id"]
      st.session_state.nombre_usuario = user_data["nombre"]
      st.session_state.nombre_nadador = user_data["nombre"]
      st.session_state.genero = user_data.get("genero", "M")

      rol_db = str(user_data.get("rol", "Nadador")).strip()
      st.session_state.rol = rol_db
      st.session_state.rol_real = rol_db
      st.session_state.rol_emulado = None

      st.session_state.fecha_nacimiento = user_data.get("fecha_nacimiento")

      if st.session_state.rol == "Nadador":
        if st.session_state.fecha_nacimiento:
          cat, ed_c = calcular_categoria_competencia(
              st.session_state.fecha_nacimiento
          )
        else:
          cat, ed_c = "Sin Categoría", 0

        st.session_state.categoria_atleta = cat
        st.session_state.edad_comp_atleta = ed_c
        st.session_state.nadador_seleccionado_id = user_data["id"]
        st.session_state.nadador_seleccionado_nombre = user_data["nombre"]
        st.session_state.nadador_seleccionado_genero = user_data.get(
            "genero", "F"
        )
        st.session_state.nadador_seleccionado_categoria = cat
      else:
        st.session_state.categoria_atleta = None
        st.session_state.edad_comp_atleta = None
        st.session_state.nadador_seleccionado_id = None
        st.session_state.nadador_seleccionado_nombre = None
        st.session_state.nadador_seleccionado_genero = None
        st.session_state.nadador_seleccionado_categoria = None

      return True
    return False
  except Exception as e:
    st.error(f"Error en Login: {e}")
    return False


def mostrar_pantalla_login():
  """Función principal que renderiza el Login, Certificación por Pre-Alta (OTP) y
  Recuperación.
  """
  aplicar_fondo_pantalla_institucional(
      "Fondo_de_pantalla_Swimprojecttraining.png"
  )
  if "rec_codigo_verificacion" not in st.session_state:
    st.session_state.rec_codigo_verificacion = None
  if "rec_datos_temporales" not in st.session_state:
    st.session_state.rec_datos_temporales = None

  if "supabase" not in st.session_state:
    st.session_state.supabase = None
  if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

  if not st.session_state.supabase:
    try:
      st.session_state.supabase = create_client(
          st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
      )
    except Exception as e:
      st.error(
          f"❌ Error de infraestructura al conectar base de datos local: {e}"
      )
      st.stop()

  # ------------------------------------------------------------
  # 2. INTERFAZ CENTRADA Y BALANCEADA
  # ------------------------------------------------------------
  if not st.session_state.autenticado:
    nombre_club = st.secrets.get("NOMBRE_CLUB_LOCAL", "Swimming Club")
    
    # Encabezado Centralizado Superior
    st.markdown(
        f"<h2 style='text-align: center; color: #0F172A; margin-bottom: 2px;'>🏊‍♂️ {nombre_club}</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h4 style='text-align: center; color: #475569; margin-bottom: 25px;'>Sistema de Control de"
        " Entrenamientos y Rendimiento</h4>",
        unsafe_allow_html=True,
    )

    instancia_supabase_club = st.session_state.supabase

    # Estructura de columnas centrada vertical y horizontalmente
    col_izq, col_centro, col_der = st.columns([1, 2.2, 1])

    with col_centro:
      tab_login, tab_registro_otp, tab_recuperar = st.tabs([
          "🔑 Iniciar Sesión",
          "📝 Registro (Pre-Alta OTP)",
          "🔄 Recuperar Contraseña",
      ])

      # --- TAB LOGIN ---
      with tab_login:
        st.caption("Nota: Los nombres de usuario se procesan en minúsculas.")
        with st.form("form_login"):
          usuario_input = st.text_input("Usuario:")
          usuario_lower = usuario_input.lower()
          contrasena_input = st.text_input("Contraseña:", type="password")

          if st.form_submit_button("Ingresar", use_container_width=True):
            if login_usuario(
                usuario_lower, contrasena_input, instancia_supabase_club
            ):
              st.success("Acceso autorizado.")
              st.rerun()
              st.stop()
            else:
              st.error(
                  "Credenciales incorrectas o cuenta en revisión. Verifique sus"
                  " datos."
              )

      # --- TAB ÚNICO DE REGISTRO: CERTIFICACIÓN DE PRE-ALTA VIA OTP ---
      with tab_registro_otp:
        st.markdown("### 📝 Registro de Usuarios (Pre-Alta)")
        st.caption(
            "Introduce el código OTP enviado por el club para verificar tus"
            " datos institucionales y activar tu cuenta."
        )

        with st.form("form_activar_prealta"):
          otp_token_input = st.text_input(
              "Código OTP (6 dígitos):", max_chars=6, placeholder="Ej: 489123"
          )
          email_prealta_input = st.text_input(
              "Correo electrónico registrado en la pre-alta:"
          )

          st.markdown("---")
          st.markdown("##### 🔐 Credenciales y Acceso Definitivo")
          nuevo_alias_pa = st.text_input(
              "Nombre de Usuario (Alias) deseado:",
              placeholder="ej: alberto_jordan",
          )
          nueva_clave_pa = st.text_input(
              "Establecer Contraseña:", type="password"
          )
          confirmar_clave_pa = st.text_input(
              "Confirmar Contraseña:", type="password"
          )

          if st.form_submit_button(
              "🚀 Certificar y Crear Cuenta", use_container_width=True
          ):
            if (
                not otp_token_input
                or not email_prealta_input
                or not nuevo_alias_pa
                or not nueva_clave_pa
            ):
              st.error("⚠️ Todos los campos de acceso son obligatorios.")
            elif nueva_clave_pa != confirmar_clave_pa:
              st.error("❌ Las contraseñas no coinciden.")
            else:
              try:
                res_inv = (
                    instancia_supabase_club.table("invitaciones")
                    .select("*")
                    .eq("token", otp_token_input.strip())
                    .eq("email", email_prealta_input.strip().lower())
                    .eq("usado", False)
                    .execute()
                )

                if not res_inv.data:
                  st.error(
                      "❌ Código OTP inválido, expirado o el correo no"
                      " coincide."
                  )
                else:
                  invitacion = res_inv.data[0]
                  expira_en = datetime.datetime.fromisoformat(
                      invitacion["expira_en"]
                  )

                  if datetime.datetime.now(
                      datetime.timezone.utc
                  ) > expira_en.replace(tzinfo=datetime.timezone.utc):
                    st.error(
                        "⌛ El código OTP ha expirado (vigencia de 24 horas)."
                        " Solicite uno nuevo a la administración."
                    )
                  else:
                    datos_perfil = invitacion.get("datos_perfil", {})

                    nombre_val = invitacion.get("nombre")
                    email_val = invitacion.get("email")
                    rol_val = invitacion.get("rol")

                    raw_genero = datos_perfil.get("genero") or datos_perfil.get(
                        "sexo"
                    )
                    genero_val = (
                        "F"
                        if raw_genero in ["F", "Femenino"]
                        else (
                            "M"
                            if raw_genero in ["M", "Masculino"]
                            else None
                        )
                    )

                    fecha_nac_val = datos_perfil.get("fecha_nacimiento")

                    faltantes = []
                    if not nombre_val:
                      faltantes.append("Nombre")
                    if not email_val:
                      faltantes.append("Email")
                    if not rol_val:
                      faltantes.append("Rol")
                    if not genero_val:
                      faltantes.append("Género")
                    if not fecha_nac_val:
                      faltantes.append("Fecha de Nacimiento")

                    if faltantes:
                      st.error(
                          "❌ Error de Pre-Alta: La invitación carece de los"
                          " siguientes datos obligatorios:"
                          f" **{', '.join(faltantes)}**. Contacte al"
                          " administrador."
                      )
                    else:
                      usuario_oficial = {
                          "nombre": nombre_val,
                          "usuario": nuevo_alias_pa.strip().lower(),
                          "email": email_val.strip().lower(),
                          "contrasena": hash_password(nueva_clave_pa),
                          "rol": rol_val,
                          "estatus": "Activo",
                          "cedula": datos_perfil.get("cedula", ""),
                          "telefono": datos_perfil.get("telefono", ""),
                          "genero": genero_val,
                          "fecha_nacimiento": fecha_nac_val,
                      }

                      instancia_supabase_club.table("usuarios").insert(
                          usuario_oficial
                      ).execute()
                      instancia_supabase_club.table("invitaciones").update(
                          {"usado": True}
                      ).eq("id", invitacion["id"]).execute()

                      st.success(
                          f"🎉 ¡Registro completado exitosamente para"
                          f" **{nombre_val}** como **{rol_val}**! Ya puedes"
                          " iniciar sesión."
                      )
              except Exception as pa_err:
                st.error(f"Error al procesar el registro: {pa_err}")

      # --- TAB RECUPERAR ---
      with tab_recuperar:
        st.markdown("### Restablecer Contraseña")
        if st.session_state.rec_codigo_verificacion:
          st.info(
              "Se ha enviado un código de seguridad a la dirección vinculada."
          )
          with st.form("form_verificacion_recuperacion"):
            codigo_rec_ingresado = st.text_input(
                "Ingrese el código temporal de recuperación:"
            )

            if st.form_submit_button(
                "Validar Código y Cambiar Contraseña", use_container_width=True
            ):
              if str(codigo_rec_ingresado).strip() == str(
                  st.session_state.rec_codigo_verificacion
              ):
                try:
                  datos = st.session_state.rec_datos_temporales
                  instancia_supabase_club.table("usuarios").update(
                      {"contrasena": datos["nueva_contrasena"]}
                  ).eq("id", datos["user_id"]).execute()
                  st.success(
                      "✅ Contraseña actualizada correctamente. Ya puede"
                      " iniciar sesión."
                  )
                  st.session_state.rec_codigo_verificacion = None
                  st.session_state.rec_datos_temporales = None
                except Exception as rec_err:
                  st.error(f"Error al actualizar la contraseña: {rec_err}")
              else:
                st.error("❌ El código ingresado es incorrecto.")

          if st.button("❌ Cancelar Recuperación", use_container_width=True):
            st.session_state.rec_codigo_verificacion = None
            st.session_state.rec_datos_temporales = None
            st.rerun()
        else:
          with st.form("form_recuperacion"):
            rec_usuario = st.text_input("Nombre de Usuario (Alias):")
            rec_email = st.text_input("Correo Electrónico Asociado:")
            nueva_clave = st.text_input(
                "Nueva Contraseña Deseada:", type="password"
            )
            confirmar_clave = st.text_input(
                "Confirmar Nueva Contraseña:", type="password"
            )

            if st.form_submit_button(
                "🔄 Solicitar Código de Recuperación", use_container_width=True
            ):
              if not (
                  rec_usuario and rec_email and nueva_clave and confirmar_clave
              ):
                st.error(
                    "Todos los campos del formulario de recuperación son"
                    " obligatorios."
                )
              elif nueva_clave != confirmar_clave:
                st.error(
                    "La confirmación no coincide con la nueva contraseña"
                    " introducida."
                )
              else:
                rec_usuario_clean = rec_usuario.strip().lower()
                try:
                  verificacion = (
                      instancia_supabase_club.table("usuarios")
                      .select("id, estatus, nombre")
                      .eq("usuario", rec_usuario_clean)
                      .eq("email", rec_email.strip())
                      .execute()
                  )
                  if verificacion.data:
                    user_info = verificacion.data[0]
                    if user_info.get("estatus") in ["Suspendido", "Bloqueado"]:
                      st.error(
                          "Esta cuenta se encuentra suspendida o bloqueada por"
                          " la administración."
                      )
                    else:
                      codigo_rec_temp = random.randint(100000, 999999)
                      st.session_state.rec_datos_temporales = {
                          "user_id": user_info["id"],
                          "nueva_contrasena": hash_password(nueva_clave),
                      }

                      cuerpo_rec_mail = (
                          f"Hola {user_info['nombre']},\n\nHas solicitado un"
                          " restablecimiento de contraseña. Tu código de"
                          f" seguridad temporal es: {codigo_rec_temp}\n\nSi no"
                          " realizaste esta acción, contacta de inmediato al"
                          " administrador."
                      )
                      if enviar_email(
                          "Código de Seguridad - Recuperación de Contraseña",
                          cuerpo_rec_mail,
                          rec_email.strip(),
                      ):
                        st.session_state.rec_codigo_verificacion = (
                            codigo_rec_temp
                        )
                        st.success(
                            "📩 Código de seguridad enviado al correo"
                            " electrónico."
                        )
                        st.rerun()
                      else:
                        st.error("Error al enviar el correo de recuperación.")
                  else:
                    st.error(
                        "❌ Los datos proporcionados no coinciden con ningún"
                        " registro activo."
                    )
                except Exception as rec_err:
                  st.error(
                      "Error durante el proceso de restablecimiento:"
                      f" {rec_err}"
                  )
    st.stop()
