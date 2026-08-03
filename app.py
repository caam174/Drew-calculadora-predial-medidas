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

# --- ESTILOS VISUALES AVANZADOS (FRESCO, JUVENIL Y MODERNO) ---
st.markdown("""
    <style>
    /* Fondo con degradado nocturno dinámico */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        color: #f8fafc;
    }
    
    /* Titulares con degradado Neón */
    .title-text {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    /* Tarjetas de Métricas con efecto Glassmorphism */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(12px);
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        transition: transform 0.25s ease, border-color 0.25s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        border-color: #38bdf8;
    }
    
    /* Personalización de Pestañas */
    button[data-baseweb="tab"] {
        font-weight: 600;
        color: #94a3b8;
        border-radius: 10px;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #38bdf8 !important;
        background-color: rgba(56, 189, 248, 0.12) !important;
    }
    
    /* Footer con Firma Drew Code */
    .drew-footer {
        margin-top: 50px;
        margin-bottom: 20px;
        padding: 24px;
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(168, 85, 247, 0.12) 100%);
        border: 1px solid rgba(168, 85, 247, 0.3);
        border-radius: 20px;
        text-align: center;
        backdrop-filter: blur(10px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
    }
    .drew-brand {
        font-size: 1.3rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        background: linear-gradient(90deg, #38bdf8, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }
    .drew-contact {
        color: #cbd5e1;
        font-size: 0.95rem;
        margin-bottom: 8px;
    }
    .drew-bless {
        color: #f472b6;
        font-weight: 600;
        font-size: 0.95rem;
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
    
    # Gauss / Shoelace
    suma_desc = np.sum(x * np.roll(y, -1))
    suma_asc = np.sum(y * np.roll(x, -1))
    area_m2 = abs(suma_desc - suma_asc) / 2.0
    area_ha = area_m2 / 10000.0
    
    # Lados y Perímetro
    dx = np.roll(x, -1) - x
    dy = np.roll(y, -1) - y
    distancias = np.sqrt(dx**2 + dy**2)
    perimetro = np.sum(distancias)
    
    # --- SECCIÓN 2: RESULTADOS ---
    st.markdown("---")
    st.subheader("2. Resumen Geométrico")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📐 Área Total", f"{area_m2:,.2f} m²")
    col2.metric("🌾 Área en Hectáreas", f"{area_ha:,.4f} ha")
    col3.metric("📏 Perímetro Total", f"{perimetro:,.2f} m")
    
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
        <div class="drew-brand">🚀 Desarrollado por DrewCode</div>
        <div class="drew-contact">📱 ¿Consultas, soporte o nuevos desarrollos? Escribe o llama con toda confianza.</div>
        <div class="drew-bless">✨ ¡Ten un excelente día! Si esta herramienta te fue de ayuda, me alegra mucho. ¡Que Dios te cuide y bendiga siempre! 🙏🏼</div>
    </div>
""", unsafe_allow_html=True)
