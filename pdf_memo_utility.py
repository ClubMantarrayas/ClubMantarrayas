#pdf_memo_utility.py
import io
import os
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

class NumberedCanvasClub(canvas.Canvas):
    """
    Canvas dinámico de 2 pasadas para calcular el número total de páginas
    y dibujar el pie de página institucional en papel membrete.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor('#64748b'))
        
        # Pie de página: Izquierda (Identificador) | Derecha (Página X de Y)
        self.drawString(36, 20, "Documento Oficial • Centro Gallego / Comisión de Natación")
        texto_pagina = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(612 - 36, 20, texto_pagina)
        
        # Línea separadora decorativa inferior
        self.setStrokeColor(colors.HexColor('#cbd5e1'))
        self.setLineWidth(0.5)
        self.line(36, 30, 612 - 36, 30)
        
        self.restoreState()


def generar_pdf_memorandum_nativo():
    buffer = io.BytesIO()
    
    # Tamaño Carta (612 x 792 pt) con márgenes de 0.5 in (36 pt)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45
    )
    
    styles = getSampleStyleSheet()
    
    # Styles tipográficos
    style_normal = ParagraphStyle(
        'DocNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b')
    )
    
    style_meta_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#0f172a')
    )
    
    style_meta_val = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    story = []
    
    # 1. Encabezado / Logo Membrete
    logo_nombre = "encabezado_paleta.png"  # Sustituir por el logo institucional
    ruta_script = os.path.join(os.path.dirname(__file__), logo_nombre)
    ruta_raiz = os.path.join(os.getcwd(), logo_nombre)
    ruta_final = ruta_script if os.path.exists(ruta_script) else (ruta_raiz if os.path.exists(ruta_raiz) else None)
    
    if ruta_final:
        story.append(Image(ruta_final, width=432, height=76, hAlign='CENTER'))
        story.append(Spacer(1, 10))

    # 2. Encabezado de Metadatos del Memorandum
    meta = st.session_state.get("meta_memo", {})
    
    codigo_doc = str(meta.get('codigo', 'MEMO-2026-000')).upper()
    tipo_doc = str(meta.get('tipo', 'MEMORANDUM')).upper()
    para_doc = str(meta.get('para', 'N/A'))
    de_doc = str(meta.get('de', 'N/A'))
    fecha_doc = str(meta.get('fecha', 'N/A'))
    asunto_doc = str(meta.get('asunto', 'N/A'))

    # Banner del Tipo de Documento
    style_banner = ParagraphStyle('BStyle', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#FFFFFF'), alignment=1)
    banner_tabla = Table([[Paragraph(f"{tipo_doc} N° {codigo_doc}", style_banner)]], colWidths=[540])
    banner_tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1e3a8a')), # Azul Institucional
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(banner_tabla)
    story.append(Spacer(1, 10))

    # Tabla de Cabecera (PARA, DE, FECHA, ASUNTO)
    tabla_cabecera_data = [
        [Paragraph("<b>PARA:</b>", style_meta_label), Paragraph(para_doc, style_meta_val)],
        [Paragraph("<b>DE:</b>", style_meta_label), Paragraph(de_doc, style_meta_val)],
        [Paragraph("<b>FECHA:</b>", style_meta_label), Paragraph(fecha_doc, style_meta_val)],
        [Paragraph("<b>ASUNTO:</b>", style_meta_label), Paragraph(asunto_doc, style_meta_val)]
    ]
    
    tabla_cabecera = Table(tabla_cabecera_data, colWidths=[70, 470])
    tabla_cabecera.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(tabla_cabecera)
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#94a3b8'), spaceBefore=8, spaceAfter=12))

    # 3. Cuerpo del Mensaje / Secciones Dinámicas
    cuerpo_secciones = st.session_state.get("cuerpo_memo_secciones", [])
    for sec in cuerpo_secciones:
        subtitulo = sec.get('subtitulo', '').strip()
        texto = sec.get('texto', '').strip().replace("\n", "<br/>")
        
        if subtitulo:
            style_sub = ParagraphStyle('SubT', fontName='Helvetica-Bold', fontSize=10.5, textColor=colors.HexColor('#0f172a'))
            story.append(Paragraph(subtitulo.upper(), style_sub))
            story.append(Spacer(1, 4))
            
        if texto:
            story.append(Paragraph(texto, style_normal))
            story.append(Spacer(1, 10))

    # 4. Cláusulas, Notas o Bases Reglamentarias
    clausulas_txt = st.session_state.get("clausulas_memo", "")
    if clausulas_txt.strip():
        story.append(Spacer(1, 5))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceBefore=5, spaceAfter=8))
        story.append(Paragraph("DISPOSICIONES Y NOTAS:", ParagraphStyle('CT', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#b91c1c'))))
        story.append(Spacer(1, 3))
        clausulas_html = str(clausulas_txt).replace("\n", "<br/>")
        story.append(Paragraph(clausulas_html, ParagraphStyle('CB', fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#334155'), leading=11)))

    # 5. Bloque de Firmas
    firmas = st.session_state.get("firmas_memo", [
        {"cargo": "Comisión de Natación", "nombre": "Firma Autorizada"},
        {"cargo": "Junta Directiva", "nombre": "Firma Autorizada"}
    ])
    
    if firmas:
        story.append(Spacer(1, 35)) # Espacio para firmar a mano o sello
        
        cols_count = len(firmas)
        width_col = 540 / cols_count
        
        filas_firmas = []
        fila_lineas = []
        fila_nombres = []
        fila_cargos = []
        
        for f in firmas:
            fila_lineas.append(Paragraph("_________________________", ParagraphStyle('FC', parent=style_normal, alignment=1)))
            fila_nombres.append(Paragraph(f"<b>{f.get('nombre', '')}</b>", ParagraphStyle('FN', parent=style_normal, alignment=1, fontSize=9)))
            fila_cargos.append(Paragraph(f.get('cargo', ''), ParagraphStyle('FC2', parent=style_normal, alignment=1, fontSize=8.5, textColor=colors.HexColor('#64748b'))))
            
        tabla_firmas_data = [fila_lineas, fila_nombres, fila_cargos]
        tabla_firmas = Table(tabla_firmas_data, colWidths=[width_col] * cols_count)
        tabla_firmas.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(tabla_firmas)

    # Construcción final del PDF con 2 pasadas de canvas
    doc.build(story, canvasmaker=NumberedCanvasClub)
    buffer.seek(0)
    return buffer.getvalue()
