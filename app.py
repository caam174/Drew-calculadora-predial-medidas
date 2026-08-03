import streamlit as st
import pandas as pd
import numpy as np
from pyproj import Transformer
import folium
from streamlit_folium import st_folium

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Calculadora Predial UTM",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📐 Calculadora Predial UTM")
st.caption("Cálculo de área, perímetro y exportación KML (WGS-84 Zona 18S)")

# --- FUNCIÓN PARA GENERAR KML ---
def generar_kml(vertices_nombres, lons, lats, area_m2, perimetro):
    # Cierre del anillo poligonal (repetir primer punto al final)
    coords_poligono = " ".join([f"{lon},{lat},0" for lon, lat in zip(lons, lats)])
    coords_poligono += f" {lons[0]},{lats[0]},0"
    
    # Generación de marcadores individuales por vértice
    marcadores_kml = ""
    for nombre, lon, lat in zip(vertices_nombres, lons, lats):
        marcadores_kml += f"""
        <Placemark>
            <name>{nombre}</name>
            <Point>
                <coordinates>{lon},{lat},0</coordinates>
            </Point>
        </Placemark>"""

    # Estructura del XML KML
    kml_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Predio_UTM_18S</name>
    <description>Polígono calculado. Área: {area_m2:.2f} m², Perímetro: {perimetro:.2f} m</description>
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

# --- VALORES POR DEFECTO ---
datos_defecto = pd.DataFrame({
    "Vértice": ["P1", "P2", "P3", "P4"],
    "Este_X": [728670.0326, 728664.5288, 728673.0635, 728678.5659],
    "Norte_Y": [8493435.2353, 8493431.3970, 8493419.1684, 8493423.0087]
})

# --- INGRESO DE DATOS ---
st.subheader("1. Coordenadas UTM del Predio")
st.info("Puedes modificar los valores, agregar más filas o pegar coordenadas desde Excel/WhatsApp.")

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

# --- CÁLCULO TOPOGRÁFICO ---
if len(df_coords) >= 3:
    x = df_coords["Este_X"].to_numpy()
    y = df_coords["Norte_Y"].to_numpy()
    n = len(x)
    
    # Método de Gauss (Shoelace)
    suma_desc = np.sum(x * np.roll(y, -1))
    suma_asc = np.sum(y * np.roll(x, -1))
    area_m2 = abs(suma_desc - suma_asc) / 2.0
    area_ha = area_m2 / 10000.0
    
    # Distancias de lados y perímetro
    dx = np.roll(x, -1) - x
    dy = np.roll(y, -1) - y
    distancias = np.sqrt(dx**2 + dy**2)
    perimetro = np.sum(distancias)
    
    # --- MOSTRAR RESULTADOS ---
    st.markdown("---")
    st.subheader("2. Resultados Geométricos")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Área Total (m²)", f"{area_m2:,.2f} m²")
    col2.metric("Área en Hectáreas", f"{area_ha:,.4f} ha")
    col3.metric("Perímetro Total", f"{perimetro:,.2f} m")
    
    # Detalle de linderos
    vertices_nombres = df_coords["Vértice"].tolist()
    lados = [f"{vertices_nombres[i]} - {vertices_nombres[(i+1)%n]}" for i in range(n)]
    
    df_linderos = pd.DataFrame({
        "Lado": lados,
        "Distancia (m)": np.round(distancias, 3)
    })
    
    with st.expander("Ver Detalle de Distancias por Lado"):
        st.dataframe(df_linderos, use_container_width=True)
        
    # --- GEORREFERENCIACIÓN Y CONVERSIÓN ---
    transformer = Transformer.from_crs("EPSG:32718", "EPSG:4326", always_xy=True)
    lons, lats = transformer.transform(x, y)
    
    centroide_lat = float(np.mean(lats))
    centroide_lon = float(np.mean(lons))
    
    st.markdown("---")
    st.subheader("3. Ubicación y Exportación")
    
    # Creación de Pestañas
    tab_mapa, tab_kml = st.tabs(["🗺️ Vista Satelital", "📥 Exportar Archivo KML"])
    
    # PESTAÑA 1: MAPA Y ENLACES
    with tab_mapa:
        url_ge = f"https://earth.google.com/web/@{centroide_lat},{centroide_lon},2380a,35d,0y,0h,0t,0r"
        url_gm = f"https://www.google.com/maps?q={centroide_lat},{centroide_lon}"
        
        col_link1, col_link2 = st.columns(2)
        col_link1.link_button("🌐 Abrir en Google Earth Web", url_ge, use_container_width=True)
        col_link2.link_button("📍 Abrir en Google Maps", url_gm, use_container_width=True)
        
        # Mapa Folium
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
            color="red",
            weight=3,
            fill=True,
            fill_color="yellow",
            fill_opacity=0.35,
            popup=f"Área: {area_m2:.2f} m²"
        ).add_to(m)
        
        for i in range(n):
            folium.Marker(
                location=[lats[i], lons[i]],
                popup=f"{vertices_nombres[i]}: ({x[i]:.2f}, {y[i]:.2f})",
                icon=folium.DivIcon(html=f'<div style="font-size: 11pt; color: white; font-weight: bold; background-color: red; padding: 2px 4px; border-radius: 3px;">{vertices_nombres[i]}</div>')
            ).add_to(m)
            
        st_folium(m, use_container_width=True, height=400)
        
    # PESTAÑA 2: DESCARGA KML
    with tab_kml:
        st.write("Genera y descarga un archivo **.KML** georreferenciado para abrirlo en Google Earth Pro o software GIS.")
        
        kml_data = generar_kml(vertices_nombres, lons, lats, area_m2, perimetro)
        
        st.download_button(
            label="⬇️ Descargar archivo Predio.kml",
            data=kml_data,
            file_name="predio_utm_18s.kml",
            mime="application/vnd.google-earth.kml+xml",
            use_container_width=True
        )
        
        st.code(kml_data[:350] + "\n...", language="xml")

else:
    st.warning("Ingresa al menos 3 vértices para realizar los cálculos.")
