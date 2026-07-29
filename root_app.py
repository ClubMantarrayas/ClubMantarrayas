import streamlit as st
import time
import hmac
import hashlib
import base64
import os
import sys

# **********************************************************************************
# 1. CONFIGURACIÓN ÚNICA DE LA PÁGINA
# **********************************************************************************
st.set_page_config(
    page_title="Swimming Club Training Control and Performance Forecasting System", 
    layout="wide"
)
# --- INYECCIÓN DE CSS GLOBAL OPTIMIZADO ---
st.markdown(
    """
    <style>
        /* 1. Ajuste del lienzo superior */
        .block-container {
            padding-top: 1rem !important; 
            padding-bottom: 0rem !important;
            max-width: 98% !important;     
        }
        
        /* 2. Compactar espacio muerto */
        div[data-testid="stVerticalBlock"] {
            gap: 0rem !important; 
        }
        .element-container {
            margin-bottom: 4px !important;
        }
      
        /* SegmentedControl */
        div[data-testid="stSegmentedControl"] {
            margin-top: 2px !important;    
            margin-bottom: 4px !important;
        }

        /* 4. Subpestañas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background-color: #f8f9fa;
            padding: 4px 6px 0px 6px;
            border-radius: 8px 8px 0px 0px;
            border-bottom: 1px solid #e5e7eb;
        }
        .stTabs [data-baseweb="tab"] {
            height: 32px !important;
            background-color: transparent;
            border-radius: 6px 6px 0px 0px;
            padding: 2px 10px !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            color: #6b7280 !important;
            border: none !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #ffffff !important;
            color: #1f2937 !important;
            font-weight: 600 !important;
            border-bottom: 3px solid #3b82f6 !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)


def validar_token_handshake(token_b64, secret_key_local):
    """
    Decodifica el token recibido por URL, verifica que corresponda al club,
    comprueba la firma criptográfica HMAC y valida la ventana de 30 segundos.
    """
    try:
        # 1. Decodificar Base64 de forma limpia
        token_decript = base64.b64decode(token_b64.encode()).decode()
        nombre_club, timestamp_str, firma_recibida = token_decript.split("|")
        
        # 2. Comprobar expiración estricta (Máximo 30 segundos)
        tiempo_transcurrido = time.time() - int(timestamp_str)
        if tiempo_transcurrido > 30 or tiempo_transcurrido < -5:
            return False, f"El ticket digital de acceso ha expirado. (Transcurrido: {int(tiempo_transcurrido)}s) Debe ingresar por la aplicación principal y escoger de la lista el Club al que esta adscrito"
            
        # 3. Re-calcular firma con la clave local exacta
        # Forzamos un strip() para eliminar espacios invisibles que puedan venir de la BD o los Secrets
        mensaje_esperado = f"{nombre_club}|{timestamp_str}"
        firma_esperada = hmac.new(
            secret_key_local.strip().encode(), 
            mensaje_esperado.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(firma_esperada, firma_recibida):
            return True, nombre_club
            
        # 💡 DEBUG AUXILIAR: Si falla, dejamos una pista en el log interno
        return False, "Firma digital del Hub inválida (No coincide el secreto interclubes)."
    except Exception as e:
        return False, f"Formato de token corrupto: {str(e)}"


# =============================================================================
# 🛑 CANDADO DE SEGURIDAD INTERCLUBES (MULTI-TENANT PURO)
# =============================================================================

SECRET_EXCLUSIVO_LOCAL = st.secrets["CLUB_SECRET_KEY"]
URL_HUB_CENTRAL = st.secrets["URL_HUB_CENTRAL"]

if "puente_validado" not in st.session_state:
  st.session_state["puente_validado"] = False

params = st.query_params
token_url = params.get("auth")

if not st.session_state["puente_validado"]:

  # CSS DEDICADO PARA FORZAR LA VISIBILIDAD DE LAS ALERTAS EN PANTALLA
  css_alertas_visibles = """
    <style>
    /* Forzar margen superior para que las alertas no se metan debajo del header de Streamlit */
    .block-container {
        padding-top: 3rem !important;
    }
    
    /* Resaltar la caja de alerta y asegurar que esté por encima de cualquier capa */
    [data-testid="stNotification"], [data-testid="stAlert"] {
        z-index: 999999 !important;
        margin-top: 15px !important;
        box-shadow: 0px 6px 20px rgba(0, 0, 0, 0.25) !important;
        border-radius: 10px !important;
    }
    </style>
    """
  st.markdown(css_alertas_visibles, unsafe_allow_html=True)

  # 1. Acceso directo sin token
  if not token_url:
    st.error(
        "🔒 **Acceso Denegado:** Debe iniciar sesión a través del Hub Central."
    )
    st.link_button(
        "🔄 Ir al Hub Central", URL_HUB_CENTRAL, use_container_width=True
    )
    st.stop()

  # 2. Validación criptográfica de apretón de manos
  es_valido, resultado_o_error = validar_token_handshake(
      token_url, SECRET_EXCLUSIVO_LOCAL
  )

  if not es_valido:
    # Renderizado garantizado y visible en el centro de la pantalla
    st.error(f"🔒 **Acceso Denegado:** {resultado_o_error}")
    st.info(
        "💡 Los enlaces de acceso rápido vencen a los 30 segundos por razones"
        " de seguridad."
    )
    st.link_button(
        "🔄 Volver al Hub Central para Generar Nuevo Enlace",
        URL_HUB_CENTRAL,
        use_container_width=True,
    )
    st.stop()

  # 3. Acceso autorizado
  st.session_state["puente_validado"] = True

# =============================================================================
# 🔑 ENTORNO OPERATIVO DEL CLUB (EJECUCIÓN DIRECTA POST-HANDSHAKE)
# =============================================================================

if st.session_state["puente_validado"]:
    # Inyección de estilos globales
    from views_styles import aplicar_estilos_globales
    aplicar_estilos_globales()

    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    # Renderizado directo sin recargas de servidor web
    if not st.session_state["autenticado"]:
        from login_general_app import mostrar_pantalla_login
        mostrar_pantalla_login()
    else:
        from views_tab_router import mostrar_vista_enrutador
        mostrar_vista_enrutador()
