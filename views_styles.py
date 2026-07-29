import base64
import streamlit as st


def obtener_base64_imagen(ruta_imagen):
  """Convierte una imagen local de la raíz a Base64 para inyectarla por CSS."""
  try:
    with open(ruta_imagen, "rb") as f:
      data = f.read()
    return base64.b64encode(data).decode()
  except Exception:
    return ""


def aplicar_estilos_globales():
  nombre_archivo_fondo = "Fondo_de_pantalla_Swimprojecttraining.png"
  base64_img = obtener_base64_imagen(nombre_archivo_fondo)

  # Construimos la línea de fondo de manera limpia fuera del bloque masivo de CSS
  css_fondo_regla = (
      f"background-image: url('data:image/png;base64,{base64_img}');"
      if base64_img
      else ""
  )

  st.markdown(
      f"""
    <style>
    /* =================================================================
       1. CONTENEDOR PRINCIPAL Y HEADER
       ================================================================= */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }}
    
    stDecoration {{
        display: none !important;
    }}
    
    [data-testid="stHeader"] {{
        background-color: rgba(0,0,0,0) !important;
        background-image: none !important;
        height: 2.5rem !important;
    }}

    /* =================================================================
       2. ESTILOS EXISTENTES (MÉTRICAS Y SIDEBAR)
       ================================================================= */
    div[data-testid="stMetricValue"] {{ font-size: 16px !important; }}
    div[data-testid="stMetricLabel"] {{ font-size: 11px !important; }}
    
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] .css-10trblm, 
    section[data-testid="stSidebar"] h4 {{
        font-size: 12px !important;
    }}

    /* =================================================================
       3. ESQUEMA DE ESTILIZACIÓN GLOBAL PARA TABLAS
       ================================================================= */
    .stDataFrame div[data-testid="stTable"] table, table.dataframe, .tabla-estilizada {{
        border-collapse: collapse !important;
        width: 100% !important;
        max-width: 100% !important;
        table-layout: auto !important;
        border: none !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }}
    
    .stDataFrame div[data-testid="stTable"] th, table.dataframe th, .tabla-estilizada th {{
        background-color: #F2F4F4 !important;  
        color: #2C3E50 !important;             
        font-weight: 600 !important;            
        padding: 6px 10px !important;           
        border-top: 1px solid #111111 !important;    
        border-bottom: 1px solid #111111 !important; 
        border-left: none !important;
        border-right: none !important;
        font-size: 11px !important;            
        text-align: center !important;
        white-space: nowrap !important;        
    }}
    
    .stDataFrame div[data-testid="stTable"] td, table.dataframe td, .tabla-estilizada td {{
        padding: 6px 10px !important;           
        border-bottom: 1px solid #E5E7E9 !important; 
        border-top: none !important;
        border-left: none !important;
        border-right: none !important;
        font-size: 11px !important;            
        color: #34495E !important;
        text-align: center !important;
    }}
    
    table.dataframe tr:last-child td, .tabla-estilizada tr:last-child td {{
        font-weight: bold !important;
        border-bottom: 2px solid #111111 !important;
        background-color: #FAFAFA !important;
    }}

    /* =================================================================
       4. FONDO DE PANTALLA Y FORMULARIO DE LOGIN (VELO AZULADO Y CENTRADO)
       ================================================================= */
    [data-testid="stAppViewContainer"] {{
        {css_fondo_regla}
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}
    
    /* Velo azulado elegante en lugar de gris opaco */
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(20, 50, 80, 0.22); 
        pointer-events: none;
        z-index: 0;
    }}

    [data-testid="stForm"] {{
        background-color: rgba(255, 255, 255, 0.94);
        padding: 2.5rem;
        border-radius: 14px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
    }}

    /* =================================================================
       5. BOTONES Y PESTAÑAS FLUIDAS (ADAPTATIVOS)
       ================================================================= */
    div[data-testid="stTabBar"] {{
        background-color: transparent !important;
        border-bottom: 2px solid #E5E7E9 !important;
        padding: 0px 0px 8px 0px !important;        
        gap: 10px !important;                        
        margin-top: -10px !important;
        overflow-x: auto !important;
        display: flex !important;
        flex-wrap: nowrap !important;
    }}

    button[data-testid="stTab"] {{
        font-size: 13px !important;  
        font-weight: 600 !important;                
        color: #566573 !important;                     
        background-color: #F8F9F9 !important;      
        border: 1px solid #D5DBDB !important;      
        border-radius: 8px !important;             
        padding: 8px 16px !important;              
        white-space: nowrap !important;             
        flex-shrink: 0 !important;                  
        box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s ease !important;
    }}

    button[data-testid="stTab"]:hover {{
        background-color: #EBEDEF !important; 
        color: #1C2833 !important;          
        border-color: #AEB6BF !important;
        box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1) !important; 
        transform: translateY(-1px) !important;   
    }}

    button[data-testid="stTab"][aria-selected="true"] {{
        background-color: #2C3E50 !important; 
        color: #FFFFFF !important;          
        border-color: #2C3E50 !important;
        font-weight: bold !important;
        box-shadow: inset 0px 2px 4px rgba(0, 0, 0, 0.2), 0px 4px 6px rgba(0, 0, 0, 0.15) !important;
    }}

    div[data-testid="stTabHighlight"] {{
        background-color: transparent !important;
        display: none !important;
    }}

    /* =================================================================
       6. REGLAS PARA MÓVILES Y PRINT
       ================================================================= */
    @media screen and (max-width: 640px) {{
        .stDataFrame, .tabla-estilizada, div[data-testid="stTable"] {{
            display: block !important;
            width: 100% !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
        }}
        
        div[data-testid="stHorizontalBlock"] {{
            flex-direction: column !important;
            gap: 8px !important;
        }}
        div[data-testid="stMetric"] {{
            width: 100% !important;
            padding: 4px 0px !important;
        }}
    }}

    @media print {{
        .no-print {{ display: none !important; }}
        .print-only {{ display: block !important; }}
    }}
    </style>
    """,
      unsafe_allow_html=True,
  )


def spc():
  st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
