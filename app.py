import io
import math
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
import folium
from streamlit_folium import st_folium
from pyproj import Transformer

# --- IMPORTACIONES REPORTLAB (PDF INSTITUCIONAL) ---
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Calculadora Predial & Memoria Descriptiva | Drew Code",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CANVAS PERSONALIZADO PARA NUMERACIÓN Y MARCA DE AGUA ---
class NumberedCanvas(canvas.Canvas):
    """
    Canvas de doble pasada para calcular el total de páginas dinámicamente 
    e insertar elementos institucionales estandarizados (Trazabilidad legal).
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
            self.draw_page_elements(num_pages)
            super().showPage()
        super().save()

    def draw_page_elements(self, page_count):
        self.saveState()
        
        # 1. Marca de agua institucional corporativa
        self.setFont('Helvetica-Bold', 50)
        self.setFillColor(colors.HexColor('#CCCCCC'), alpha=0.10)
        self.saveState()
        self.translate(300, 400)
        self.rotate(45)
        self.drawCentredString(0, 0, "USO OFICIAL 2026")
        self.restoreState()
        
        # 2. Pie de página con autoría y paginación legal
        self.setFont('Helvetica', 8)
        self.setFillColor(colors.HexColor('#444444'))
        self.drawString(54, 30, "Elaborado por: Área Técnica & Saneamiento | Drew Code")
        self.drawRightString(558, 30, f"Página {self._pageNumber} de {page_count}")
        
        self.restoreState()

# --- CACHÉ DE OPTIMIZACIÓN PYPROJ ---
@st.cache_resource
def obtener_transformador(epsg_code):
    try:
        return Transformer.from_crs(epsg_code, "EPSG:4326", always_xy=True)
    except Exception:
        return None

# --- FUNCIONES DE CÁLCULO TOPOGRÁFICO Y EXPORTACIÓN ---
def decimal_a_dms(deg):
    deg = deg % 360
    d = int(deg)
    m_full = (deg - d) * 60
    m = int(m_full)
    s = (m_full - m) * 60
    return f"{d:02d}° {m:02d}' {s:05.2f}\""

def calcular_azimut(dx, dy):
    angle_rad = math.atan2(dx, dy)
    angle_deg = math.degrees(angle_rad) % 360
    return angle_deg, decimal_a_dms(angle_deg)

def verificar_autointersesion(x, y):
    n = len(x)
    if n < 4:
        return False
    
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

    def intersect(A, B, C, D):
        return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

    pts = list(zip(x, y))
    for i in range(n):
        p1, p2 = pts[i], pts[(i+1)%n]
        for j in range(i+2, n):
            if i == 0 and j == n - 1:
                continue
            p3, p4 = pts[j], pts[(j+1)%n]
            if intersect(p1, p2, p3, p4):
                return True
    return False

def generar_dxf(vertices_nombres, x, y):
    n = len(x)
    lines = [
        "0", "SECTION", "2", "HEADER", "0", "ENDSEC",
        "0", "SECTION", "2", "TABLES", "0", "ENDSEC",
        "0", "SECTION", "2", "BLOCKS", "0", "ENDSEC",
        "0", "SECTION", "2", "ENTITIES",
        "0", "LWPOLYLINE", "8", "PREDIO_LINDEROS",
        "90", str(n), "70", "1"
    ]
    for i in range(n):
        lines.extend(["10", f"{x[i]:.4f}", "20", f"{y[i]:.4f}"])
        
    for i in range(n):
        lines.extend([
            "0", "TEXT", "8", "PREDIO_VERTICES",
            "10", f"{x[i]:.4f}", "20", f"{y[i]:.4f}",
            "40", "1.5", "1", str(vertices_nombres[i]), "50", "0"
        ])
    lines.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(lines)

def generar_kml(vertices_nombres, lons, lats, area_m2, perimetro):
    coords_poligono = " ".join([f"{lon},{lat},0" for lon, lat in zip(lons, lats)])
    coords_poligono += f" {lons[0]},{lats[0]},0"
    
    marcadores_kml = ""
    for nombre, lon, lat in zip(vertices_nombres, lons, lats):
        marcadores_kml += f"""
        <Placemark>
            <name>{nombre}</name>
            <Point>
                <coordinates>{lon},{lat},0</coordinates>
            </Point>
        </Placemark>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Predio_Calculado_DrewCode</name>
    <description>Área: {area_m2:.2f} m², Perímetro: {perimetro:.2f} m</description>
    <Style id="estiloPredio">
      <LineStyle><color>ff0000ff</color><width>3</width></LineStyle>
      <PolyStyle><color>4000ffff</color></PolyStyle>
    </Style>
    <Placemark>
      <name>Polígono del Predio</name>
      <styleUrl>#estiloPredio</styleUrl>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>{coords_poligono}</coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    {marcadores_kml}
  </Document>
</kml>"""

def generar_svg_plano(x, y, vertices, distancias):
    w, h = 800, 500
    pad = 100
    
    min_x, max_x = np.min(x), np.max(x)
    min_y, max_y = np.min(y), np.max(y)
    
    rx = max_x - min_x if max_x != min_x else 1.0
    ry = max_y - min_y if max_y != min_y else 1.0
    
    scale = min((w - 2 * pad) / rx, (h - 2 * pad) / ry)
    cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
    
    sx = (x - cx) * scale + w / 2
    sy = h / 2 - (y - cy) * scale
    
    pts = " ".join([f"{sx[i]:.1f},{sy[i]:.1f}" for i in range(len(x))])
    svg_elements = [f'<polygon points="{pts}" fill="rgba(56, 189, 248, 0.25)" stroke="#38bdf8" stroke-width="3.5" stroke-linejoin="round" />']
    
    n = len(x)
    for i in range(n):
        i_next = (i + 1) % n
        mx, my = (sx[i] + sx[i_next]) / 2, (sy[i] + sy[i_next]) / 2
        dist_str = f"{distancias[i]:.2f} m"
        
        dx_p = sx[i_next] - sx[i]
        dy_p = sy[i_next] - sy[i]
        angle = np.degrees(np.arctan2(dy_p, dx_p))
        if angle > 90: angle -= 180
        elif angle < -90: angle += 180

        rect_w = len(dist_str) * 9.5 + 14
        svg_elements.append(
            f'<g transform="translate({mx:.1f}, {my:.1f}) rotate({angle:.1f})">'
            f'<rect x="{-rect_w/2:.1f}" y="-13" width="{rect_w}" height="25" rx="6" fill="#1e293b" stroke="#fde047" stroke-width="1.8" />'
            f'<text x="0" y="4" fill="#fde047" font-size="12.5" font-weight="900" text-anchor="middle" font-family="sans-serif">{dist_str}</text>'
            f'</g>'
        )
        
    for i in range(n):
        vx = sx[i] + (16 if sx[i] >= w/2 else -26)
        vy = sy[i] + (16 if sy[i] >= h/2 else -10)
        svg_elements.append(f'<circle cx="{sx[i]:.1f}" cy="{sy[i]:.1f}" r="7" fill="#f472b6" stroke="#ffffff" stroke-width="2.5" />')
        svg_elements.append(f'<text x="{vx:.1f}" y="{vy:.1f}" fill="#ffffff" font-size="15" font-weight="900" font-family="sans-serif">{vertices[i]}</text>')
        
    return f'''
    <div style="width: 100%; display: flex; justify-content: center; background-color: transparent;">
        <svg viewBox="0 0 {w} {h}" style="width: 100%; max-width: 800px; height: auto; background-color: #0f172a; border-radius: 16px; border: 2.5px solid #38bdf8; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
            <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="1"/>
                </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
            {"".join(svg_elements)}
        </svg>
    </div>
    '''

# --- FUNCIÓN DE GENERACIÓN DE PDF INSTITUCIONAL CON REPORTLAB ---
def generar_pdf_memoria(prop_nombre, prop_dni, num_tramite, ubicacion_predio, zonificacion, opcion_zona, area_m2, area_ha, perimetro, vertices_nombres, rumbos_text, distancias, azimuts_dms, x, y):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontSize=14,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=4,
        alignment=1
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Heading2'],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=15,
        alignment=1
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0284C7'),
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1E293B'),
        alignment=1
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0F172A'),
        fontName="Helvetica-Bold",
        alignment=1
    )

    # Cabecera
    story.append(Paragraph("MEMORIA DESCRIPTIVA TÉCNICA OFICIAL", title_style))
    story.append(Paragraph(f"SANEAMIENTO FÍSICO LEGAL Y CATASTRAL - DATOS UTM ({opcion_zona})", subtitle_style))
    
    # Cuadro de Datos Generales
    info_data = [
        [Paragraph("<b>1. PROPIETARIO / ADMINISTRADO:</b>", body_style), Paragraph(prop_nombre, body_style)],
        [Paragraph("<b>2. D.N.I. / R.U.C.:</b>", body_style), Paragraph(prop_dni, body_style)],
        [Paragraph("<b>3. EXPEDIENTE / TRÁMITE:</b>", body_style), Paragraph(num_tramite, body_style)],
        [Paragraph("<b>4. UBICACIÓN DEL PREDIO:</b>", body_style), Paragraph(ubicacion_predio, body_style)],
        [Paragraph("<b>5. ZONIFICACIÓN / USO:</b>", body_style), Paragraph(zonificacion, body_style)]
    ]
    t_info = Table(info_data, colWidths=[150, 354])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 10))
    
    # Descripción del terreno
    story.append(Paragraph("6. DESCRIPCIÓN DEL TERRENO Y LINDEROS", section_style))
    desc_texto = f"El predio materia de la presente memoria descriptiva se encuentra ubicado en {ubicacion_predio}, con zonificación {zonificacion}. Cuenta con un área superficial plana calculada de <b>{area_m2:,.2f} m² ({area_ha:,.4f} ha)</b> y un perímetro total de <b>{perimetro:,.2f} m</b>. El terreno presenta una configuración geométrica regular con linderos rectos definidos por {len(x)} vértices principales."
    story.append(Paragraph(desc_texto, body_style))
    story.append(Spacer(1, 6))
    
    # Cuadro de Coordenadas y Linderos
    story.append(Paragraph(f"7. CUADRO DE DATOS TÉCNICOS Y COORDENADAS UTM (WGS84 - {opcion_zona})", section_style))
    
    n = len(x)
    table_rows = [[
        Paragraph("LADO", table_header_style),
        Paragraph("RUMBO", table_header_style),
        Paragraph("DISTANCIA (m)", table_header_style),
        Paragraph("AZIMUT", table_header_style),
        Paragraph("ESTE (X)", table_header_style),
        Paragraph("NORTE (Y)", table_header_style)
    ]]
    
    for i in range(n):
        i_sig = (i + 1) % n
        table_rows.append([
            Paragraph(f"{vertices_nombres[i]} - {vertices_nombres[i_sig]}", table_cell_style),
            Paragraph(str(rumbos_text[i]), table_cell_style),
            Paragraph(f"{distancias[i]:.2f}", table_cell_style),
            Paragraph(str(azimuts_dms[i]), table_cell_style),
            Paragraph(f"{x[i]:.4f}", table_cell_style),
            Paragraph(f"{y[i]:.4f}", table_cell_style)
        ])
        
    t_coords = Table(table_rows, colWidths=[65, 80, 75, 85, 95, 104])
    t_coords.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#334155')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_coords)
    
    resumen_totales = Paragraph(f"<b>Área Total: {area_m2:,.2f} m² | Perímetro Total: {perimetro:,.2f} m</b>", ParagraphStyle('TotalRight', parent=styles['Normal'], fontSize=8.5, alignment=2, spaceBefore=4, textColor=colors.HexColor('#0F172A')))
    story.append(resumen_totales)
    story.append(Spacer(1, 15))
    
    # Bloque de Firmas
    firmas_data = [
        [
            Paragraph(f"<b>{prop_nombre}</b><br/>Propietario / Administrado<br/>DNI: {prop_dni}", table_cell_style),
            Paragraph("<b>Especialista / Fiscalizador</b><br/>Área Técnica - Municipalidad", table_cell_style)
        ]
    ]
    t_firmas = Table(firmas_data, colWidths=[230, 230])
    t_firmas.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (0,0), 0.75, colors.HexColor('#334155')),
        ('LINEABOVE', (1,0), (1,0), 0.75, colors.HexColor('#334155')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(t_firmas)
    
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()

# --- ESTILOS VISUALES Y ADAPTABILIDAD MÓVIL (RESPONSIVE) ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        color: #ffffff !important;
    }
    .stApp p, .stApp span, .stApp label, .stApp div, .stApp small {
        color: #ffffff !important;
        opacity: 1 !important;
    }
    [data-testid="stCaptionContainer"], .stCaption, div[data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }
    h1, h2, h3, h4, .stSubheader {
        color: #ffffff !important;
        font-weight: 800 !important;
    }
    .title-text {
        font-size: 2.8rem;
        font-weight: 900;
        color: #38bdf8 !important;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.8), 0 0 25px rgba(56, 189, 248, 0.5);
        margin-bottom: 0.3rem;
        text-align: center !important;
    }
    div[data-testid="stDataEditor"], div[role="grid"], div[role="grid"] *, input, select, textarea {
        color: #000000 !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
    }
    div[role="grid"] {
        background-color: #ffffff !important;
        border-radius: 8px;
    }
    .metric-box {
        background: linear-gradient(145deg, #1e293b, #0f172a) !important;
        border: 3px solid #38bdf8 !important;
        border-radius: 18px !important;
        padding: 20px 15px !important;
        text-align: center !important;
        box-shadow: 0 10px 25px rgba(56, 189, 248, 0.35) !important;
        margin-bottom: 15px !important;
    }
    .metric-title {
        color: #ffffff !important;
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        margin-bottom: 8px !important;
        text-transform: uppercase;
    }
    .metric-num {
        color: #38bdf8 !important;
        font-size: 3.2rem !important;
        font-weight: 900 !important;
        line-height: 1.1 !important;
    }
    .custom-btn {
        display: block !important;
        width: 100% !important;
        padding: 12px 16px !important;
        background-color: #1e293b !important;
        color: #38bdf8 !important;
        border: 2px solid #38bdf8 !important;
        border-radius: 12px !important;
        text-align: center !important;
        font-weight: 800 !important;
        font-size: 1.05rem !important;
        text-decoration: none !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
        transition: all 0.25s ease-in-out !important;
        box-sizing: border-box !important;
        margin-bottom: 12px !important;
    }
    .custom-btn:hover {
        background-color: #38bdf8 !important;
        color: #0f172a !important;
        border-color: #ffffff !important;
    }
    div[data-testid="stDownloadButton"] button {
        background-color: #1e293b !important;
        border: 2px solid #38bdf8 !important;
        border-radius: 12px !important;
        width: 100% !important;
        padding: 12px 16px !important;
    }
    div[data-testid="stDownloadButton"] button p, div[data-testid="stDownloadButton"] button span {
        color: #38bdf8 !important;
        font-weight: 800 !important;
    }
    div[data-testid="stDownloadButton"] button:hover {
        background-color: #38bdf8 !important;
    }
    div[data-testid="stDownloadButton"] button:hover p {
        color: #0f172a !important;
    }
    button[data-baseweb="tab"], button[data-baseweb="tab"] * {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: rgba(255, 255, 255, 0.2) !important;
        border-bottom: 4px solid #38bdf8 !important;
    }
    .drew-footer {
        margin-top: 50px;
        margin-bottom: 20px;
        padding: 24px;
        background: #0f172a;
        border: 2px solid #ffffff;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
    }
    .drew-brand { font-size: 1.6rem; font-weight: 900; color: #ffffff !important; margin-bottom: 4px; }
    .drew-rights { color: #cbd5e1 !important; font-size: 0.95rem; font-weight: 600; margin-bottom: 12px; }
    .drew-contact { color: #ffffff !important; font-size: 1.1rem; font-weight: 600; margin-bottom: 14px; line-height: 1.8; }
    .drew-bless { color: #f472b6 !important; font-weight: 700; font-size: 1.1rem; margin-top: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- CABECERA CENTRADA ---
st.markdown('<div class="title-text">📐 Calculadora Predial & Memoria Descriptiva</div>', unsafe_allow_html=True)
st.markdown("""
    <div style="text-align: center; margin-bottom: 25px;">
        <p style="color: #ffffff !important; font-size: 1.15rem; font-weight: 600; margin-bottom: 4px;">
            ⚡ Cálculo UTM, Cuadro Técnico, Plano 2D y Generación de Hoja Guía para Memoria Descriptiva
        </p>
    </div>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN TÉCNICA (ZONA Y ALTITUD) ---
col_zone, col_alt = st.columns(2)

with col_zone:
    opcion_zona = st.selectbox(
        "🌐 Zona UTM (Hemisferio Sur)",
        ["Zona 18S (EPSG:32718) - Perú Centro/Sur", "Zona 17S (EPSG:32717) - Perú Norte", "Zona 19S (EPSG:32719) - Perú Este"],
        index=0
    )
    
epsg_dict = {
    "Zona 18S (EPSG:32718) - Perú Centro/Sur": "EPSG:32718",
    "Zona 17S (EPSG:32717) - Perú Norte": "EPSG:32717",
    "Zona 19S (EPSG:32719) - Perú Este": "EPSG:32719"
}
epsg_actual = epsg_dict[opcion_zona]

with col_alt:
    altitud_msnm = st.number_input(
        "⛰️ Altitud Media (m.s.n.m. - Opcional)",
        min_value=0.0, max_value=6000.0, value=0.0, step=50.0,
        help="Permite proyectar el área plana UTM al área real en superficie de terreno."
    )

# --- DATOS POR DEFECTO ---
datos_defecto = pd.DataFrame({
    "Vértice": ["P1", "P2", "P3", "P4"],
    "Este_X": [728670.0326, 728664.5288, 728673.0635, 728678.5659],
    "Norte_Y": [8493435.2353, 8493431.3970, 8493419.1684, 8493423.0087]
})

# --- SECCIÓN 1: ENTRADA DE DATOS (MANUAL O CARGA MASIVA) ---
st.subheader("1. Coordenadas del Predio")
st.info("💡 Edita directamente los vértices o carga un archivo CSV/Excel con las columnas: Vértice, Este_X, Norte_Y.")

archivo_subido = st.file_uploader("📂 Importar vértices desde archivo CSV o Excel", type=["csv", "xlsx"])

if archivo_subido is not None:
    try:
        if archivo_subido.name.endswith('.csv'):
            df_entrada = pd.read_csv(archivo_subido)
        else:
            df_entrada = pd.read_excel(archivo_subido)
        
        if all(col in df_entrada.columns for col in ["Vértice", "Este_X", "Norte_Y"]):
            datos_defecto = df_entrada[["Vértice", "Este_X", "Norte_Y"]]
            st.success("¡Datos cargados correctamente desde el archivo!")
        else:
            st.error("El archivo debe contener las columnas exactas: Vértice, Este_X, Norte_Y")
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

df_coords = st.data_editor(
    datos_defecto,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Vértice": st.column_config.TextColumn("Vértice", required=True),
        "Este_X": st.column_config.NumberColumn("Este (X)", format="%.4f", required=True),
        "Norte_Y": st.column_config.NumberColumn("Norte (Y)", format="%.4f", required=True)
    }
)

# --- LIMPIEZA AUTOMÁTICA ---
df_clean = df_coords.copy()
df_clean["Este_X"] = pd.to_numeric(df_clean["Este_X"], errors="coerce")
df_clean["Norte_Y"] = pd.to_numeric(df_clean["Norte_Y"], errors="coerce")
df_clean = df_clean.dropna(subset=["Este_X", "Norte_Y"])
df_clean = df_clean[df_clean["Vértice"].astype(str).str.strip() != ""]

# --- MOTOR DE CÁLCULO ---
if len(df_clean) >= 3:
    x = df_clean["Este_X"].to_numpy()
    y = df_clean["Norte_Y"].to_numpy()
    vertices_nombres = df_clean["Vértice"].astype(str).tolist()
    n = len(x)
    
    if verificar_autointersesion(x, y):
        st.warning("⚠️ **Atención:** Se ha detectado una intersección entre linderos (polígono autointersectado). Verifica el orden secuencial de los vértices.")

    suma_desc = np.sum(x * np.roll(y, -1))
    suma_asc = np.sum(y * np.roll(x, -1))
    area_m2 = abs(suma_desc - suma_asc) / 2.0
    area_ha = area_m2 / 10000.0
    
    r_tierra = 6371000.0
    k_elev = r_tierra / (r_tierra + altitud_msnm) if altitud_msnm > 0 else 1.0
    area_terreno_m2 = area_m2 / (k_elev ** 2)
    
    dx = np.roll(x, -1) - x
    dy = np.roll(y, -1) - y
    distancias = np.sqrt(dx**2 + dy**2)
    perimetro = np.sum(distancias)
    
    azimuts_dms = []
    azimuts_deg = []
    rumbos_text = []
    
    for i in range(n):
        az_d, az_str = calcular_azimut(dx[i], dy[i])
        azimuts_deg.append(az_d)
        azimuts_dms.append(az_str)
        
        dx_val = dx[i]
        dy_val = dy[i]
        val_ang = math.degrees(math.atan2(abs(dx_val), abs(dy_val)))
        d_r = int(val_ang)
        m_r = int((val_ang - d_r) * 60)
        s_r = ((val_ang - d_r) * 60 - m_r) * 60
        ang_str = f"{d_r}°{m_r}'{s_r:.2f}\""
        
        if dx_val >= 0 and dy_val >= 0:
            rumbos_text.append(f"N {ang_str} E")
        elif dx_val >= 0 and dy_val < 0:
            rumbos_text.append(f"S {ang_str} E")
        elif dx_val < 0 and dy_val < 0:
            rumbos_text.append(f"S {ang_str} W")
        else:
            rumbos_text.append(f"N {ang_str} W")

    # --- SECCIÓN 2: RESUMEN GEOMÉTRICO ---
    st.markdown("---")
    st.subheader("2. Resumen Geométrico")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-box"><div class="metric-title">📐 Área Plana UTM</div><div class="metric-num">{area_m2:,.2f} m²</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="metric-title">🌾 Hectáreas</div><div class="metric-num">{area_ha:,.4f} ha</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><div class="metric-title">📏 Perímetro Total</div><div class="metric-num">{perimetro:,.2f} m</div></div>', unsafe_allow_html=True)
    
    if altitud_msnm > 0:
        st.info(f"⛰️ **Proyección de Superficie Real:** Para una altitud media de **{altitud_msnm:,.0f} m.s.n.m.**, el Área en Terreno proyectada es **{area_terreno_m2:,.2f} m²**.")

    lados = [f"{vertices_nombres[i]} - {vertices_nombres[(i+1)%n]}" for i in range(n)]
    df_linderos = pd.DataFrame({
        "Lado": lados,
        "Rumbo": rumbos_text,
        "Distancia (m)": np.round(distancias, 3),
        "Azimut": azimuts_dms,
        "Este (X)": np.round(x, 4),
        "Norte (Y)": np.round(y, 4)
    })
    
    with st.expander("🔍 Ver Cuadro Técnico Oficial (Linderos, Rumbos, Azimuts y Coordenadas)"):
        st.dataframe(df_linderos, use_container_width=True)

    # --- SECCIÓN 3: PLANO 2D PERIMÉTRICO ---
    st.markdown("---")
    st.subheader("3. Plano 2D Perimétrico (Medidas)")
    svg_plano = generar_svg_plano(x, y, vertices_nombres, distancias)
    components.html(svg_plano, height=520)
        
    # --- GEORREFERENCIACIÓN Y TRANSFORMACIÓN CACHEADA ---
    transformer = obtener_transformador(epsg_actual)
    if transformer:
        lons, lats = transformer.transform(x, y)
    else:
        lons, lats = x, y  # Resguardo predeterminado
        
    centroide_lat = float(np.mean(lats))
    centroide_lon = float(np.mean(lons))
    
    # --- SECCIÓN 4: GEOLOCALIZACIÓN & ARCHIVOS ---
    st.markdown("---")
    st.subheader("4. Geolocalización & Archivos CAD")
    
    tab_mapa, tab_kml, tab_dxf = st.tabs(["🗺️ Mapa Satelital", "📥 Exportar KML (Google Earth)", "📐 Exportar DXF (AutoCAD)"])

    with tab_mapa:
        url_ge = f"https://earth.google.com/web/@{centroide_lat},{centroide_lon},2380a,35d,0y,0h,0t,0r"
        url_gm = f"https://www.google.com/maps?q={centroide_lat},{centroide_lon}"
        
        col_link1, col_link2 = st.columns(2)
        with col_link1:
            st.markdown(f'<a href="{url_ge}" target="_blank" class="custom-btn">🌐 Abrir en Google Earth Web</a>', unsafe_allow_html=True)
        with col_link2:
            st.markdown(f'<a href="{url_gm}" target="_blank" class="custom-btn">📍 Abrir en Google Maps</a>', unsafe_allow_html=True)
        
        m = folium.Map(
            location=[centroide_lat, centroide_lon],
            zoom_start=19,
            max_zoom=21,
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite'
        )
        
        puntos_mapa = list(zip(lats, lons))
        folium.Polygon(
            locations=puntos_mapa,
            color="#38bdf8",
            weight=3,
            fill=True,
            fill_color="#a855f7",
            fill_opacity=0.35,
            popup=f"Área: {area_m2:.2f} m²"
        ).add_to(m)
        
        for i in range(n):
            folium.Marker(
                location=[lats[i], lons[i]],
                popup=f"{vertices_nombres[i]}: ({x[i]:.2f}, {y[i]:.2f})",
                icon=folium.DivIcon(html=f'<div style="font-size: 10pt; color: white; font-weight: bold; background-color: #38bdf8; padding: 2px 6px; border-radius: 4px;">{vertices_nombres[i]}</div>')
            ).add_to(m)
            
            lat_mid = (lats[i] + lats[(i+1)%n]) / 2
            lon_mid = (lons[i] + lons[(i+1)%n]) / 2
            folium.Marker(
                location=[lat_mid, lon_mid],
                icon=folium.DivIcon(html=f'<div style="font-size: 8.5pt; color: #000; font-weight: bold; background-color: #fde047; padding: 2px 4px; border-radius: 3px; border: 1px solid #000;">{distancias[i]:.2f}m</div>')
            ).add_to(m)
            
        st_folium(m, use_container_width=True, height=520)
        
    with tab_kml:
        st.write("Descarga la poligonal georreferenciada para abrirla en **Google Earth Pro** o **QGIS**.")
        kml_data = generar_kml(vertices_nombres, lons, lats, area_m2, perimetro)
        st.download_button(label="🚀 Descargar archivo Predio.kml", data=kml_data, file_name="predio_utm.kml", mime="application/vnd.google-earth.kml+xml", use_container_width=True)

    with tab_dxf:
        st.write("Descarga la poligonal vectorial directa en **formato `.DXF`** para AutoCAD o Civil 3D.")
        dxf_data = generar_dxf(vertices_nombres, x, y)
        st.download_button(label="✏️ Descargar plano en formato AutoCAD (.DXF)", data=dxf_data, file_name="plano_perimetrico_utm.dxf", mime="application/dxf", use_container_width=True)

    # --- SECCIÓN 5: MEMORIA DESCRIPTIVA Y HOJA GUÍA OFICIAL (PDF REPORTLAB) ---
    st.markdown("---")
    st.subheader("5. Memoria Descriptiva & Hoja Guía Oficial (PDF)")
    st.info("💡 Ingresa los datos del administrado/propietario, expediente y parámetros urbanísticos para generar el formato institucional formal en PDF.")

    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        prop_nombre = st.text_input("👤 Nombres y Apellidos del Propietario", "Maximo Decimo Meridio")
    with col_p2:
        prop_dni = st.text_input("🆔 D.N.I. / R.U.C.", "26247302")
    with col_p3:
        num_tramite = st.text_input("📁 N° de Trámite Administrativo / Expediente", "EXP-2026-00894")

    col_ub1, col_ub2 = st.columns([3, 1])
    with col_ub1:
        ubicacion_predio = st.text_input("📍 Ubicación del Predio (Sector, Distrito, Provincia, Departamento)", "Sector Urbano / Expansión, Abancay, Apurímac")
    with col_ub2:
        zonificacion = st.text_input("🏙️ Zonificación", "RDM / CZ")

    # Generación e inserción directa del botón de descarga (un solo clic)
    pdf_bytes = generar_pdf_memoria(
        prop_nombre, prop_dni, num_tramite, ubicacion_predio, zonificacion, 
        opcion_zona, area_m2, area_ha, perimetro, 
        vertices_nombres, rumbos_text, distancias, azimuts_dms, x, y
    )

    st.download_button(
        label="💾 Descargar Memoria Descriptiva en PDF",
        data=pdf_bytes,
        file_name=f"{num_tramite.replace('/', '_')}_memoria_descriptiva.pdf",
        mime="application/pdf",
        use_container_width=True
    )

else:
    st.warning("⚠️ Ingresa al menos 3 vértices válidos con coordenadas Este (X) y Norte (Y) para generar los cálculos, planos y la memoria descriptiva.")

# --- FIRMA DE AUTOR (DREWCODE) ---
st.markdown("""
    <div class="drew-footer">
        <div style="text-align: center; margin-bottom: 12px;">
            <svg width="90" height="80" viewBox="0 0 100 90" style="filter: drop-shadow(0px 0px 10px rgba(244, 114, 182, 0.8));">
                <path d="M 50,85 A 25,25 0 0,1 10,40 A 20,20 0 0,1 50,20 A 20,20 0 0,1 90,40 A 25,25 0 0,1 50,85 Z" fill="url(#gradHeart)" />
                <defs>
                    <linearGradient id="gradHeart" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#ec4899;stop-opacity:1" />
                        <stop offset="100%" style="stop-color:#ef4444;stop-opacity:1" />
                    </linearGradient>
                </defs>
                <text x="50%" y="46%" dominant-baseline="middle" text-anchor="middle" fill="#ffffff" font-size="13" font-weight="900" font-family="sans-serif" letter-spacing="1">NOLAN</text>
            </svg>
        </div>
        <div class="drew-brand">🚀 Creado por Drew Code</div>
        <div class="drew-rights">© Todos los Derechos Reservados</div>
        <div class="drew-contact">
            📧 <b>Email:</b> <a href="mailto:caam174@gmail.com" style="color: #38bdf8; text-decoration: none;">caam174@gmail.com</a> <br>
            📱 <b>WhatsApp / Llama al:</b> <a href="https://wa.me/51983761229" target="_blank" style="color: #4ade80; text-decoration: none; font-weight: bold;">+51 983761229</a>
        </div>
        <div class="drew-bless">✨ Ten un buen día, y si te ayudó me alegra mucho. ¡Que Dios te cuide siempre! 🙏🏼</div>
    </div>
""", unsafe_allow_html=True)
