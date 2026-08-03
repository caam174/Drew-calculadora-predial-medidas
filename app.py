import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
from pyproj import Transformer
import folium
from streamlit_folium import st_folium

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Calculadora Predial UTM | Drew Code",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS VISUALES DE ALTO IMPACTO ---
st.markdown("""
    <style>
    /* 1. FONDO PRINCIPAL */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        color: #ffffff !important;
    }

    /* 2. REGLA GENERAL DE TEXTO EN FONDO OSCURO */
    .stApp p, .stApp span, .stApp label, .stApp div, .stApp small {
        color: #ffffff !important;
        opacity: 1 !important;
    }

    /* 3. CAPTIONS Y SUBTÍTULOS */
    [data-testid="stCaptionContainer"], .stCaption, div[data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }

    /* 4. ENCABEZADOS Y TITULARES */
    h1, h2, h3, h4, .stSubheader {
        color: #ffffff !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px;
    }

    .title-text {
        font-size: 2.6rem;
        font-weight: 900;
        color: #ffffff !important;
        margin-bottom: 0.3rem;
    }

    /* 5. TABLA DE EDICIÓN Y CAMPOS */
    div[data-testid="stDataEditor"], 
    div[role="grid"], 
    div[role="grid"] *,
    input, select, textarea {
        color: #000000 !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
    }

    div[role="grid"] {
        background-color: #ffffff !important;
        border-radius: 8px;
    }

    /* 6. CAJAS DEL RESUMEN GEOMÉTRICO (TARJETAS GIGANTES) */
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
        letter-spacing: 1px;
    }

    .metric-num {
        color: #38bdf8 !important;
        font-size: 3.2rem !important;
        font-weight: 900 !important;
        line-height: 1.1 !important;
        text-shadow: 0 0 15px rgba(56, 189, 248, 0.6) !important;
    }

    /* 7. BOTONES PERSONALIZADOS HTML (GOOGLE EARTH / MAPS) */
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
        box-shadow: 0 6px 18px rgba(56, 189, 248, 0.6) !important;
    }

    /* 8. BOTÓN DE DESCARGA KML (CORREGIDO DE FORMA DEFINITIVA) */
    div[data-testid="stDownloadButton"] button {
        background-color: #1e293b !important;
        border: 2px solid #38bdf8 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
        transition: all 0.25s ease-in-out !important;
        width: 100% !important;
        padding: 12px 16px !important;
    }

    div[data-testid="stDownloadButton"] button p, 
    div[data-testid="stDownloadButton"] button span,
    div[data-testid="stDownloadButton"] button div {
        color: #38bdf8 !important;
        font-weight: 800 !important;
        font-size: 1.05rem !important;
    }

    div[data-testid="stDownloadButton"] button:hover {
        background-color: #38bdf8 !important;
        border-color: #ffffff !important;
    }

    div[data-testid="stDownloadButton"] button:hover p, 
    div[data-testid="stDownloadButton"] button:hover span {
        color: #0f172a !important;
    }

    /* 9. PESTAÑAS (TABS) Y EXPANDER */
    button[data-baseweb="tab"], button[data-baseweb="tab"] * {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: rgba(255, 255, 255, 0.2) !important;
        border-bottom: 4px solid #38bdf8 !important;
    }

    details summary, details summary * {
        color: #ffffff !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
    }

    /* 10. FIRMA DREW CODE Y CONTACTO */
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
    .drew-brand {
        font-size: 1.6rem;
        font-weight: 900;
        color: #ffffff !important;
        margin-bottom: 10px;
    }
    .drew-contact {
        color: #ffffff !important;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 14px;
        line-height: 1.8;
    }
    .drew-bless {
        color: #f472b6 !important;
        font-weight: 700;
        font-size: 1.1rem;
        margin-top: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABECERA ---
st.markdown('<div class="title-text">📐 Calculadora Predial UTM</div>', unsafe_allow_html=True)
st.caption("⚡ Cálculo de superficie, perímetro, plano perimétrico y geolocalización (WGS-84 Zona 18S)")

# --- FUNCIÓN DIBUJO VECTORIAL SVG DEL PLANO 2D ---
def generar_svg_plano(x, y, vertices, distancias):
    w, h = 800, 500
    pad = 100
    
    min_x, max_x = np.min(x), np.max(x)
    min_y, max_y = np.min(y), np.max(y)
    
    rx = max_x - min_x if max_x != min_x else 1.0
    ry = max_y - min_y if max_y != min_y else 1.0
    
    scale = min((w - 2 * pad) / rx, (h - 2 * pad) / ry)
    
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    
    sx = (x - cx) * scale + w / 2
    sy = h / 2 - (y - cy) * scale
    
    pts = " ".join([f"{sx[i]:.1f},{sy[i]:.1f}" for i in range(len(x))])
    
    svg_elements = []
    
    # Polígono base
    svg_elements.append(f'<polygon points="{pts}" fill="rgba(56, 189, 248, 0.25)" stroke="#38bdf8" stroke-width="3.5" stroke-linejoin="round" />')
    
    n = len(x)
    # Linderos con cotas rotadas tipo CAD
    for i in range(n):
        i_next = (i + 1) % n
        mx = (sx[i] + sx[i_next]) / 2
        my = (sy[i] + sy[i_next]) / 2
        dist_str = f"{distancias[i]:.2f} m"
        
        dx_p = sx[i_next] - sx[i]
        dy_p = sy[i_next] - sy[i]
        angle = np.degrees(np.arctan2(dy_p, dx_p))
        if angle > 90:
            angle -= 180
        elif angle < -90:
            angle += 180

        rect_w = len(dist_str) * 9.5 + 14
        svg_elements.append(
            f'<g transform="translate({mx:.1f}, {my:.1f}) rotate({angle:.1f})">'
            f'<rect x="{-rect_w/2:.1f}" y="-13" width="{rect_w}" height="25" rx="6" fill="#1e293b" stroke="#fde047" stroke-width="1.8" />'
            f'<text x="0" y="4" fill="#fde047" font-size="12.5" font-weight="900" text-anchor="middle" font-family="sans-serif">{dist_str}</text>'
            f'</g>'
        )
        
    # Vértices con identificadores
    for i in range(n):
        vx = sx[i] + (16 if sx[i] >= w/2 else -26)
        vy = sy[i] + (16 if sy[i] >= h/2 else -10)
        svg_elements.append(f'<circle cx="{sx[i]:.1f}" cy="{sy[i]:.1f}" r="7" fill="#f472b6" stroke="#ffffff" stroke-width="2.5" />')
        svg_elements.append(f'<text x="{vx:.1f}" y="{vy:.1f}" fill="#ffffff" font-size="15" font-weight="900" font-family="sans-serif">{vertices[i]}</text>')
        
    svg_code = f'''
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
    return svg_code

# --- FUNCIÓN GENERADORA DE KML ---
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

    kml_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Predio_Calculado_DrewCode</name>
    <description>Área: {area_m2:.2f} m², Perímetro: {perimetro:.2f} m</description>
    <Style id="estiloPredio">
      <LineStyle>
        <color>ff0000ff</color>
        <width>3</width>
      </LineStyle>
      <PolyStyle>
        <color>4000ffff</color>
      </PolyStyle>
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
    return kml_str

# --- DATOS POR DEFECTO ---
datos_defecto = pd.DataFrame({
    "Vértice": ["P1", "P2", "P3", "P4"],
    "Este_X": [728670.0326, 728664.5288, 728673.0635, 728678.5659],
    "Norte_Y": [8493435.2353, 8493431.3970, 8493419.1684, 8493423.0087]
})

# --- SECCIÓN 1: ENTRADA DE DATOS ---
st.subheader("1. Coordenadas del Predio")
st.info("💡 Edita o agrega vértices UTM. Si habilitas una fila sin datos por error, el sistema la descartará automáticamente.")

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

# --- LIMPIEZA AUTOMÁTICA DE FILAS INCOMPLETAS ---
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
    
    # Algoritmo de Gauss / Shoelace
    suma_desc = np.sum(x * np.roll(y, -1))
    suma_asc = np.sum(y * np.roll(x, -1))
    area_m2 = abs(suma_desc - suma_asc) / 2.0
    area_ha = area_m2 / 10000.0
    
    # Perímetro y Distancias de Linderos
    dx = np.roll(x, -1) - x
    dy = np.roll(y, -1) - y
    distancias = np.sqrt(dx**2 + dy**2)
    perimetro = np.sum(distancias)
    
    # --- SECCIÓN 2: RESUMEN GEOMÉTRICO ---
    st.markdown("---")
    st.subheader("2. Resumen Geométrico")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-title">📐 Área Total</div>
                <div class="metric-num">{area_m2:,.2f} m²</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-title">🌾 Hectáreas</div>
                <div class="metric-num">{area_ha:,.4f} ha</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-title">📏 Perímetro Total</div>
                <div class="metric-num">{perimetro:,.2f} m</div>
            </div>
        """, unsafe_allow_html=True)
    
    lados = [f"{vertices_nombres[i]} - {vertices_nombres[(i+1)%n]}" for i in range(n)]
    df_linderos = pd.DataFrame({
        "Lado": lados,
        "Distancia (m)": np.round(distancias, 3)
    })
    
    with st.expander("🔍 Ver detalle de medidas por lindero en tabla"):
        st.dataframe(df_linderos, use_container_width=True)

    # --- SECCIÓN 3: PLANO 2D PERIMÉTRICO (ITEM INDEPENDIENTE) ---
    st.markdown("---")
    st.subheader("3. Plano 2D Perimétrico (Medidas)")
    svg_plano = generar_svg_plano(x, y, vertices_nombres, distancias)
    components.html(svg_plano, height=520)
        
    # --- GEORREFERENCIACIÓN Y TRANSFORMACIÓN ---
    transformer = Transformer.from_crs("EPSG:32718", "EPSG:4326", always_xy=True)
    lons, lats = transformer.transform(x, y)
    
    centroide_lat = float(np.mean(lats))
    centroide_lon = float(np.mean(lons))
    
    # --- SECCIÓN 4: GEOLOCALIZACIÓN & ARCHIVOS ---
    st.markdown("---")
    st.subheader("4. Geolocalización & Archivos")
    
    tab_mapa, tab_kml = st.tabs(["🗺️ Mapa Satelital", "📥 Exportar Archivo KML"])

    # TAB MAPA SATELITAL
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
                icon=folium.DivIcon(html=f'<div style="font-size: 10pt; color: white; font-weight: bold; background-color: #38bdf8; padding: 2px 6px; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.5);">{vertices_nombres[i]}</div>')
            ).add_to(m)
            
            lat_mid = (lats[i] + lats[(i+1)%n]) / 2
            lon_mid = (lons[i] + lons[(i+1)%n]) / 2
            folium.Marker(
                location=[lat_mid, lon_mid],
                icon=folium.DivIcon(html=f'<div style="font-size: 8.5pt; color: #000; font-weight: bold; background-color: #fde047; padding: 2px 4px; border-radius: 3px; border: 1px solid #000; box-shadow: 0 2px 4px rgba(0,0,0,0.4);">{distancias[i]:.2f}m</div>')
            ).add_to(m)
            
        st_folium(m, use_container_width=True, height=450)
        
    # TAB DESCARGA KML
    with tab_kml:
        st.write("Descarga la poligonal georreferenciada para abrirla directamente en **Google Earth Pro**, **AutoCAD** o **QGIS**.")
        
        kml_data = generar_kml(vertices_nombres, lons, lats, area_m2, perimetro)
        
        st.download_button(
            label="🚀 Descargar archivo Predio.kml",
            data=kml_data,
            file_name="predio_utm_18s.kml",
            mime="application/vnd.google-earth.kml+xml",
            use_container_width=True
        )

else:
    st.warning("⚠️ Ingresa al menos 3 vértices válidos con coordenadas Este (X) y Norte (Y) para generar los cálculos y el plano.")

# --- FIRMA DE AUTOR (DREW CODE) ---
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
        <div class="drew-contact">
            📧 <b>Email:</b> <a href="mailto:caam174@gmail.com" style="color: #38bdf8; text-decoration: none;">caam174@gmail.com</a> <br>
            📱 <b>WhatsApp / Llama al:</b> <a href="https://wa.me/51983761229" target="_blank" style="color: #4ade80; text-decoration: none; font-weight: bold;">+51 983761229</a>
        </div>
        <div class="drew-bless">✨ Ten un buen día, y si te ayudó me alegra mucho. ¡Que Dios te cuide siempre! 🙏🏼</div>
    </div>
""", unsafe_allow_html=True)
