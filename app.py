import streamlit as st
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

# --- ESTILOS VISUALES: CAJAS HIGHLIGHT Y TIPOGRAFÍA GIGANTE ---
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

    /* 5. TABLA DE EDICIÓN Y CAMPOS (Fondo Blanco -> Texto Negro) */
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

    /* 6. CAJAS PERSONALIZADAS DEL RESUMEN GEOMÉTRICO (RESALTANTES) */
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
        color: #38bdf8 !important; /* Azul cian neón */
        font-size: 3.2rem !important; /* Tamaño Gigante */
        font-weight: 900 !important;
        line-height: 1.1 !important;
        text-shadow: 0 0 15px rgba(56, 189, 248, 0.6) !important;
    }

    /* 7. CAJAS DE ALERTA E INFORMACIÓN */
    div[data-testid="stAlert"] {
        background-color: #1e293b !important;
        border: 2px solid #ffffff !important;
        border-radius: 12px !important;
    }
    div[data-testid="stAlert"] p {
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }

    /* 8. PESTAÑAS (TABS) Y EXPANDER */
    button[data-baseweb="tab"], button[data-baseweb="tab"] * {
        color: #ffffff !important;
        font-size: 1.2rem !important;
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

    /* 9. FIRMA DREW CODE Y CONTACTO */
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
st.caption("⚡ Cálculo de superficie, perímetro y geolocalización en tiempo real (WGS-84 Zona 18S)")

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
st.info("💡 Edita o pega aquí tus vértices UTM. Se ajusta automáticamente en tu celular.")

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

# --- MOTOR DE CÁLCULO ---
if len(df_coords) >= 3:
    x = df_coords["Este_X"].to_numpy()
    y = df_coords["Norte_Y"].to_numpy()
    n = len(x)
    
    # Algoritmo de Gauss / Shoelace
    suma_desc = np.sum(x * np.roll(y, -1))
    suma_asc = np.sum(y * np.roll(x, -1))
    area_m2 = abs(suma_desc - suma_asc) / 2.0
    area_ha = area_m2 / 10000.0
    
    # Cálculo de Perímetro
    dx = np.roll(x, -1) - x
    dy = np.roll(y, -1) - y
    distancias = np.sqrt(dx**2 + dy**2)
    perimetro = np.sum(distancias)
    
    # --- SECCIÓN 2: RESUMEN GEOMÉTRICO (CAJAS RESALTADAS DE ALTO IMPACTO) ---
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
    
    vertices_nombres = df_coords["Vértice"].tolist()
    lados = [f"{vertices_nombres[i]} - {vertices_nombres[(i+1)%n]}" for i in range(n)]
    
    df_linderos = pd.DataFrame({
        "Lado": lados,
        "Distancia (m)": np.round(distancias, 3)
    })
    
    with st.expander("🔍 Ver detalle de medidas por lindero"):
        st.dataframe(df_linderos, use_container_width=True)
        
    # --- GEORREFERENCIACIÓN ---
    transformer = Transformer.from_crs("EPSG:32718", "EPSG:4326", always_xy=True)
    lons, lats = transformer.transform(x, y)
    
    centroide_lat = float(np.mean(lats))
    centroide_lon = float(np.mean(lons))
    
    # --- SECCIÓN 3: PESTAÑAS Y MAPA ---
    st.markdown("---")
    st.subheader("3. Visualización & Archivos")
    
    tab_mapa, tab_kml = st.tabs(["🗺️ Mapa Satelital", "📥 Exportar Archivo KML"])
    
    with tab_mapa:
        url_ge = f"https://earth.google.com/web/@{centroide_lat},{centroide_lon},2380a,35d,0y,0h,0t,0r"
        url_gm = f"https://www.google.com/maps?q={centroide_lat},{centroide_lon}"
        
        col_link1, col_link2 = st.columns(2)
        col_link1.link_button("🌐 Abrir en Google Earth Web", url_ge, use_container_width=True)
        col_link2.link_button("📍 Abrir en Google Maps", url_gm, use_container_width=True)
        
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
                icon=folium.DivIcon(html=f'<div style="font-size: 11pt; color: white; font-weight: bold; background-color: #38bdf8; padding: 3px 6px; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.5);">{vertices_nombres[i]}</div>')
            ).add_to(m)
            
        st_folium(m, use_container_width=True, height=420)
        
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
    st.warning("⚠️ Ingresa al menos 3 vértices para proyectar el polígono y calcular la superficie.")

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
