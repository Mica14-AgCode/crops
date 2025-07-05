import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
import pandas as pd
import zipfile
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import base64
from datetime import datetime
import re
import tempfile
import os

st.set_page_config(
    page_title="Análisis de Rotación de Cultivos",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

@st.cache_resource
def init_earth_engine():
    """Inicializa Google Earth Engine con autenticación"""
    try:
        ee.Initialize()
        return True
    except Exception as e:
        try:
            ee.Authenticate()
            ee.Initialize()
            return True
        except Exception as e2:
            return False

def extraer_coordenadas_kml(kml_content):
    """Extrae coordenadas de polígonos de contenido KML"""
    try:
        poligonos = []
        root = ET.fromstring(kml_content)
        
        namespaces = {
            'kml': 'http://www.opengis.net/kml/2.2',
            'gx': 'http://www.google.com/kml/ext/2.2'
        }
        
        for coordinates_elem in root.findall('.//kml:coordinates', namespaces):
            if coordinates_elem is not None and coordinates_elem.text:
                coords_text = coordinates_elem.text.strip()
                if coords_text:
                    puntos = []
                    for line in coords_text.split():
                        if ',' in line:
                            parts = line.split(',')
                            if len(parts) >= 2:
                                try:
                                    lon = float(parts[0])
                                    lat = float(parts[1])
                                    puntos.append([lon, lat])
                                except ValueError:
                                    continue
                    
                    if len(puntos) >= 3:
                        if puntos[0] != puntos[-1]:
                            puntos.append(puntos[0])
                        poligonos.append(puntos)
        
        return poligonos
    except Exception as e:
        return []

def procesar_kmz_uploaded(uploaded_file):
    """Procesa archivo KMZ subido y extrae polígonos"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.kmz') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name
        
        poligonos = []
        
        with zipfile.ZipFile(tmp_file_path, 'r') as kmz:
            for file_name in kmz.namelist():
                if file_name.endswith('.kml'):
                    with kmz.open(file_name) as kml_file:
                        kml_content = kml_file.read().decode('utf-8')
                        poligonos.extend(extraer_coordenadas_kml(kml_content))
        
        os.unlink(tmp_file_path)
        return poligonos
    except Exception as e:
        return []

def crear_ee_feature_collection_web(poligonos_data):
    """Crea FeatureCollection de Earth Engine desde datos de polígonos"""
    try:
        features = []
        for i, poligono in enumerate(poligonos_data):
            feature = ee.Feature(
                ee.Geometry.Polygon([poligono]),
                {'id': i}
            )
            features.append(feature)
        
        return ee.FeatureCollection(features)
    except Exception as e:
        return None

def analizar_cultivos_web(aoi):
    """Función principal que analiza cultivos con Google Earth Engine"""
    try:
        area_total_aoi = aoi.geometry().transform('EPSG:5345', 1).area(1).divide(10000)
        area_total = area_total_aoi.getInfo()
        
        container_progreso = st.container()
        container_resultados = st.container()
        
        with container_progreso:
            progress_bar = st.progress(0.0)
            status_text = st.empty()
        
        # Paleta oficial sincronizada
        paleta_oficial = [
            '646b63', 'ffffff', 'ff6347', '0042ff', '339820', 'ffff00', 'f022db', 'a32102',
            'b7b9bd', 'ffa500', '1d1e33', 'ff0000', 'a32102', '646b63', 'e6f0c2', 'e6f0c2',
            'ff6347', '8a2be2', 'ff6347', '800080', 'ff6347', 'd2b48c', '87ceeb', '90ee90'
        ]
        
        cultivos_por_campana = {
            '19-20': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '20-21': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '21-22': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 19: 'Caña de azúcar', 21: 'No agrícola', 22: 'No agrícola', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '22-23': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 19: 'Caña de azúcar', 21: 'No agrícola', 22: 'No agrícola', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '23-24': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 19: 'Caña de azúcar', 21: 'No agrícola', 22: 'No agrícola', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'}
        }
        
        resultados_todas_campanas = []
        tiles_urls = {}
        campanas = ['19-20', '20-21', '21-22', '22-23', '23-24']
        
        for i, campana in enumerate(campanas):
            try:
                progress_bar.progress(0.1 + (i + 1) / len(campanas) * 0.8)
                status_text.text(f"Procesando campaña {campana}...")
                
                # Cargar colección
                asset_id = f'projects/cropmapping-web/assets/mapas_nacionales_de_cultivos/MAP_NAC_CAMP_{campana}'
                
                try:
                    cultivos_image = ee.Image(asset_id).clip(aoi.geometry())
                except:
                    continue
                
                # Generar tiles RGB
                def hex_to_rgb(hex_color):
                    hex_color = hex_color.lstrip('#')
                    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                
                # Crear imagen RGB
                image_classified = cultivos_image.select(['classification'])
                
                rgb_conditions = []
                for class_id in range(len(paleta_oficial)):
                    if class_id < len(paleta_oficial):
                        color_hex = paleta_oficial[class_id]
                        r, g, b = hex_to_rgb(color_hex)
                        
                        condition = image_classified.eq(class_id)
                        rgb_layer = ee.Image.constant([r, g, b]).mask(condition)
                        rgb_conditions.append(rgb_layer)
                
                if rgb_conditions:
                    rgb_image = ee.ImageCollection(rgb_conditions).mosaic().uint8()
                    tiles_url = rgb_image.getThumbURL({
                        'min': 0,
                        'max': 255,
                        'dimensions': 2048,
                        'format': 'png'
                    })
                    tiles_urls[campana] = tiles_url
                
                # Calcular estadísticas
                area_pixeles = ee.Image.pixelArea().reproject('EPSG:5345', None, 30)
                
                cultivos_actuales = cultivos_por_campana[campana]
                for class_id, nombre_cultivo in cultivos_actuales.items():
                    try:
                        mascara_cultivo = image_classified.eq(class_id)
                        area_cultivo_m2 = area_pixeles.updateMask(mascara_cultivo).reduceRegion(
                            reducer=ee.Reducer.sum(),
                            geometry=aoi.geometry(),
                            scale=30,
                            maxPixels=1e9
                        )
                        
                        area_ha = area_cultivo_m2.getInfo().get('area', 0) / 10000
                        porcentaje = (area_ha / area_total * 100) if area_total > 0 else 0
                        
                        resultados_todas_campanas.append({
                            'Campaña': campana,
                            'Cultivo': nombre_cultivo,
                            'Área (ha)': round(area_ha, 1),
                            'Porcentaje (%)': round(porcentaje, 1)
                        })
                    except:
                        continue
                        
            except Exception as e:
                continue
        
        progress_bar.progress(1.0)
        status_text.text("✅ Procesamiento completado")
        
        if resultados_todas_campanas:
            df_resultados = pd.DataFrame(resultados_todas_campanas)
            return df_resultados, area_total, tiles_urls, cultivos_por_campana
        else:
            return None, None, {}, {}
            
    except Exception as e:
        return None, None, {}, {}

def generar_grafico_rotacion_web(df_resultados):
    """Genera gráfico de rotación con colores exactos"""
    try:
        df_plot = df_resultados.pivot_table(
            index='Cultivo', 
            columns='Campaña', 
            values='Porcentaje (%)', 
            aggfunc='sum', 
            fill_value=0
        )
        
        # Colores exactos del JavaScript
        colores_cultivos = {
            "Maíz": "#0042ff",
            "Soja 1ra": "#339820", 
            "Girasol": "#FFFF00",
            "Poroto": "#f022db",
            "Girasol-CV": "#a32102",
            "Caña de azúcar": "#a32102", 
            "No agrícola": "#e6f0c2",
            "CI-Maíz 2da": "#87CEEB",
            "CI-Soja 2da": "#90ee90"
        }
        
        # Filtrar cultivos con área > 0
        df_plot = df_plot[df_plot.sum(axis=1) > 0]
        
        # Calcular promedio
        df_plot['Promedio'] = df_plot.mean(axis=1)
        df_plot = df_plot.sort_values('Promedio', ascending=False)
        
        columnas_campanas = [col for col in df_plot.columns if col != 'Promedio']
        columnas_grafico = columnas_campanas + ['Promedio']
        df_temp = df_plot[columnas_grafico]
        
        colores_ordenados = []
        for cultivo in df_temp.index:
            colores_ordenados.append(colores_cultivos.get(cultivo, "#999999"))
        
        fig, ax = plt.subplots(figsize=(14, 8))
        df_temp.T.plot(kind='bar', stacked=True, ax=ax, color=colores_ordenados, width=0.8)
        
        plt.axvline(x=len(columnas_campanas)-0.5, color='black', linestyle='--', linewidth=1.5, alpha=0.7)
        plt.text(len(columnas_campanas)-0.5, 105, 'PROMEDIO', ha='center', va='center', 
                rotation=0, size=12, bbox=dict(boxstyle="round,pad=0.3", fc='lightgray', ec="black", alpha=0.7))
        
        plt.title('Rotación de Cultivos por Campaña', fontsize=16)
        plt.xlabel('Campaña', fontsize=12)
        plt.ylabel('Porcentaje del Área Total (%)', fontsize=12)
        plt.xticks(rotation=45)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.ylim(0, 100)
        
        handles, labels = ax.get_legend_handles_labels()
        plt.legend(handles, labels, title='Cultivo', bbox_to_anchor=(1.05, 1), loc='upper left')
        
        for c in ax.containers:
            labels = [f'{int(v)}%' if v > 5 else '' for v in c.datavalues]
            ax.bar_label(c, labels=labels, label_type='center')
        
        plt.tight_layout()
        
        # Crear DataFrame para tabla
        df_rotacion_final = df_plot.copy()
        df_rotacion_final = df_rotacion_final.reset_index()
        df_rotacion_final = df_rotacion_final.rename(columns={'Cultivo': 'Cultivo_Estandarizado'})
        
        return fig, df_rotacion_final
        
    except Exception as e:
        return None, None

def get_download_link(df, filename, link_text):
    """Genera un enlace de descarga para un DataFrame"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

def crear_mapa_con_tiles_engine(aoi, tiles_urls, df_resultados, cultivos_por_campana, campana_seleccionada):
    """Crea un mapa interactivo con tiles reales de Google Earth Engine - VERSIÓN ARREGLADA"""
    
    # Centro por defecto (Argentina)
    center_lat, center_lon = -34.0, -60.0
    zoom_level = 14
    
    # Intentar obtener centro del AOI
    try:
        aoi_bounds = aoi.geometry().bounds(maxError=1)
        bounds_info = aoi_bounds.getInfo()
        
        if bounds_info and "coordinates" in bounds_info:
            coords = bounds_info["coordinates"][0]
            if len(coords) >= 4:
                lats = [c[1] for c in coords if len(c) >= 2]
                lons = [c[0] for c in coords if len(c) >= 2]
                
                if lats and lons:
                    center_lat = sum(lats) / len(lats)
                    center_lon = sum(lons) / len(lons)
                    
                    lat_range = max(lats) - min(lats)
                    lon_range = max(lons) - min(lons)
                    max_range = max(lat_range, lon_range)
                    
                    if max_range < 0.01:
                        zoom_level = 16
                    elif max_range < 0.05:
                        zoom_level = 14
                    else:
                        zoom_level = 12
    except:
        pass
    
    # Crear mapa base
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_level,
        tiles=None
    )
    
    # Capas base
    folium.TileLayer(
        "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Satellite",
        name="Satelital",
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        "OpenStreetMap", 
        name="Mapa",
        control=True
    ).add_to(m)
    
    # 🎯 CAPAS DE CULTIVOS CON ORDEN CORRECTO Y SOLO 50% ACTIVO
    if campana_seleccionada in tiles_urls and tiles_urls[campana_seleccionada]:
        try:
            # 1. OPACO 100% (primero en la lista, NO activo)
            folium.raster_layers.TileLayer(
                tiles=tiles_urls[campana_seleccionada],
                attr='Google Earth Engine',
                name=f'🌾 Cultivos {campana_seleccionada} (100%)',
                overlay=False,  # NO activo
                control=True,
                opacity=1.0
            ).add_to(m)
            
            # 2. MEDIO 70% (NO activo)
            folium.raster_layers.TileLayer(
                tiles=tiles_urls[campana_seleccionada],
                attr='Google Earth Engine',
                name=f'🌾 Cultivos {campana_seleccionada} (70%)', 
                overlay=False,  # NO activo
                control=True,
                opacity=0.7
            ).add_to(m)
            
            # 3. ✅ PREDETERMINADO 50% (ÚNICO ACTIVO)
            folium.raster_layers.TileLayer(
                tiles=tiles_urls[campana_seleccionada],
                attr='Google Earth Engine',
                name=f'🌾 Cultivos {campana_seleccionada} (50%)',
                overlay=True,   # ✅ ÚNICO ACTIVO
                control=True,
                opacity=0.5
            ).add_to(m)
            
            # 4. CLARO 30% (último, NO activo)
            folium.raster_layers.TileLayer(
                tiles=tiles_urls[campana_seleccionada],
                attr='Google Earth Engine',
                name=f'🌾 Cultivos {campana_seleccionada} (30%)',
                overlay=False,  # NO activo
                control=True,
                opacity=0.3
            ).add_to(m)
            
        except Exception as e:
            pass
    
    # 🔥 CONTORNOS DEL CAMPO QUE SÍ FUNCIONAN
    try:
        # Obtener geometría del AOI 
        aoi_geojson = aoi.getInfo()
        
        if aoi_geojson:
            # 🎯 CONTORNO SÚPER VISIBLE - 4 capas superpuestas
            
            # 1. SOMBRA NEGRA (base gruesa)
            folium.GeoJson(
                aoi_geojson,
                name="",  # Sin nombre para que no aparezca en capas
                style_function=lambda x: {
                    "fillColor": "transparent",
                    "color": "#000000", 
                    "weight": 20,
                    "fillOpacity": 0,
                    "opacity": 0.8
                }
            ).add_to(m)
            
            # 2. LÍNEA BLANCA (contraste)
            folium.GeoJson(
                aoi_geojson,
                name="",  # Sin nombre
                style_function=lambda x: {
                    "fillColor": "transparent",
                    "color": "#FFFFFF", 
                    "weight": 12,
                    "fillOpacity": 0,
                    "opacity": 1.0
                }
            ).add_to(m)
            
            # 3. LÍNEA AMARILLA NEÓN (máximo contraste)
            folium.GeoJson(
                aoi_geojson,
                name="",  # Sin nombre
                style_function=lambda x: {
                    "fillColor": "transparent",
                    "color": "#FFFF00", 
                    "weight": 6,
                    "fillOpacity": 0,
                    "opacity": 1.0
                }
            ).add_to(m)
            
            # 4. LÍNEA ROJA (núcleo final)
            folium.GeoJson(
                aoi_geojson,
                name="🔴 Límite del Campo",  # Solo este tiene nombre visible
                style_function=lambda x: {
                    "fillColor": "transparent",
                    "color": "#FF0000", 
                    "weight": 2,
                    "fillOpacity": 0,
                    "opacity": 1.0
                }
            ).add_to(m)
            
    except Exception as e:
        pass
    
    # Control de capas
    folium.LayerControl(collapsed=False).add_to(m)
    
    # 🌾 LEYENDA ABAJO DEL MAPA
    try:
        df_campana = df_resultados[df_resultados['Campaña'] == campana_seleccionada]
        
        if not df_campana.empty:
            colores_cultivos = {
                "Maíz": "#0042ff",
                "Soja 1ra": "#339820",
                "Girasol": "#FFFF00",
                "Poroto": "#f022db",
                "Girasol-CV": "#a32102",
                "Caña de azúcar": "#a32102",
                "No agrícola": "#e6f0c2",
                "CI-Maíz 2da": "#87CEEB",
                "CI-Soja 2da": "#90ee90"
            }
            
            area_total_campana = float(df_campana['Área (ha)'].sum())
            
            legend_html = f"""
            <div style="position: fixed !important; 
                        bottom: 20px !important; left: 50% !important; 
                        transform: translateX(-50%) !important;
                        width: 600px !important; max-width: 90vw !important;
                        background-color: rgba(255, 255, 255, 0.98) !important; 
                        z-index: 9999 !important; 
                        border: 3px solid #2E8B57 !important; 
                        border-radius: 10px !important;
                        padding: 15px !important; 
                        font-family: Arial, sans-serif !important;
                        box-shadow: 0 8px 16px rgba(0,0,0,0.7) !important;">
                        
            <h4 style="margin: 0 0 12px 0 !important; text-align: center !important; 
                       background: linear-gradient(135deg, #2E8B57, #3CB371) !important; 
                       color: white !important; 
                       padding: 8px !important; border-radius: 6px !important; 
                       font-size: 14px !important; font-weight: bold !important;">
                🌾 Cultivos - Campaña {campana_seleccionada} | {area_total_campana:,.0f} ha
            </h4>
            
            <div style="display: flex !important; flex-wrap: wrap !important; 
                        justify-content: center !important; gap: 8px !important;">
            """
            
            # Filtrar cultivos con área > 0
            cultivos_con_area = df_campana[df_campana['Área (ha)'] > 0].sort_values('Área (ha)', ascending=False)
            
            for _, row in cultivos_con_area.iterrows():
                cultivo = str(row['Cultivo'])
                area = float(row['Área (ha)'])
                porcentaje = float(row['Porcentaje (%)'])
                color = colores_cultivos.get(cultivo, '#999999')
                
                legend_html += f"""
                <div style="display: flex !important; align-items: center !important; 
                            background: rgba(248, 249, 250, 0.9) !important;
                            padding: 6px 10px !important; border-radius: 20px !important; 
                            border: 1px solid #dee2e6 !important;
                            font-size: 11px !important; white-space: nowrap !important;">
                    <div style="width: 16px !important; height: 12px !important; 
                                background-color: {color} !important; 
                                margin-right: 6px !important; 
                                border: 1px solid #333 !important;
                                border-radius: 2px !important; flex-shrink: 0 !important;"></div>
                    <span style="font-weight: 500 !important; color: #2c3e50 !important;">
                        {cultivo}: {area:,.0f} ha ({porcentaje:.1f}%)
                    </span>
                </div>
                """
            
            legend_html += """
            </div>
            </div>
            """
            
            m.get_root().html.add_child(folium.Element(legend_html))
            
    except Exception as e:
        pass
    
    return m

def main():
    st.title("🌾 Análisis de Rotación de Cultivos")
    
    # Inicializar session state
    if 'resultados_analisis' not in st.session_state:
        st.session_state.resultados_analisis = None
    if 'analisis_completado' not in st.session_state:
        st.session_state.analisis_completado = False
    
    # Inicializar Earth Engine
    if 'ee_initialized' not in st.session_state:
        with st.spinner("Inicializando Google Earth Engine..."):
            st.session_state.ee_initialized = init_earth_engine()
    
    if not st.session_state.ee_initialized:
        st.error("❌ No se pudo conectar con Google Earth Engine")
        return
    
    st.success("✅ Google Earth Engine conectado correctamente")
    
    # Upload de archivos
    st.subheader("📁 Sube tus archivos KMZ")
    uploaded_files = st.file_uploader(
        "Selecciona uno o más archivos KMZ",
        type=['kmz'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} archivo(s) subido(s)")
        
        # Botón de análisis
        if st.button("🚀 Analizar Cultivos y Rotación", type="primary"):
            with st.spinner("🔄 Procesando análisis completo..."):
                # Procesar archivos KMZ
                todos_los_poligonos = []
                
                for uploaded_file in uploaded_files:
                    poligonos = procesar_kmz_uploaded(uploaded_file)
                    todos_los_poligonos.extend(poligonos)
                
                if not todos_los_poligonos:
                    st.error("❌ No se encontraron polígonos válidos")
                    return
                
                # Crear AOI
                aoi = crear_ee_feature_collection_web(todos_los_poligonos)
                if not aoi:
                    st.error("❌ No se pudo crear el área de interés")
                    return
                
                # Ejecutar análisis
                resultado = analizar_cultivos_web(aoi)
                df_cultivos, area_total, tiles_urls, cultivos_por_campana = resultado
                
                if df_cultivos is not None and not df_cultivos.empty:
                    # Guardar en session state
                    st.session_state.resultados_analisis = {
                        'df_cultivos': df_cultivos,
                        'area_total': area_total,
                        'tiles_urls': tiles_urls,
                        'cultivos_por_campana': cultivos_por_campana,
                        'aoi': aoi
                    }
                    st.session_state.analisis_completado = True
                    st.success("🎉 ¡Análisis completado exitosamente!")
                    st.rerun()
                else:
                    st.error("❌ No se pudieron analizar los cultivos")
    
    # Mostrar resultados
    if st.session_state.analisis_completado and st.session_state.resultados_analisis:
        st.markdown("---")
        st.markdown("## 📊 Resultados del Análisis")
        
        datos = st.session_state.resultados_analisis
        df_cultivos = datos['df_cultivos']
        area_total = datos['area_total']
        tiles_urls = datos['tiles_urls']
        cultivos_por_campana = datos['cultivos_por_campana']
        aoi = datos['aoi']
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Área Total", f"{area_total:,.1f} ha")
        with col2:
            cultivos_detectados = df_cultivos[df_cultivos['Área (ha)'] > 0]['Cultivo'].nunique()
            st.metric("Cultivos Detectados", f"{cultivos_detectados:,}")
        with col3:
            area_agricola_por_campana = df_cultivos[~df_cultivos['Cultivo'].str.contains('No agrícola', na=False)].groupby('Campaña')['Área (ha)'].sum()
            area_agricola = area_agricola_por_campana.mean()
            st.metric("Área Agrícola", f"{area_agricola:,.1f} ha")
        with col4:
            porcentaje_agricola = (area_agricola / area_total * 100) if area_total > 0 else 0
            st.metric("% Agrícola", f"{porcentaje_agricola:.1f}%")
        
        # Gráfico de rotación
        fig, df_rotacion = generar_grafico_rotacion_web(df_cultivos)
        
        if fig is not None:
            st.subheader("🎨 Gráfico de Rotación de Cultivos")
            st.pyplot(fig)
            
            st.subheader("📋 Tabla de Rotación (%)")
            df_display = df_rotacion.copy()
            df_display = df_display.rename(columns={'Cultivo_Estandarizado': 'Cultivo'})
            st.dataframe(df_display, use_container_width=True)
        
        # Mapa interactivo
        st.subheader("🗺️ Mapa Interactivo de Cultivos")
        st.write("Explora los píxeles de cultivos reales de Google Earth Engine:")
        
        campanas_disponibles = sorted(df_cultivos['Campaña'].unique())
        
        col_dropdown, col_info = st.columns([1, 2])
        with col_dropdown:
            campana_seleccionada = st.selectbox(
                "🗓️ Seleccionar Campaña:",
                campanas_disponibles,
                index=len(campanas_disponibles)-1
            )
        
        with col_info:
            df_sel = df_cultivos[df_cultivos['Campaña'] == campana_seleccionada]
            cultivos_sel = len(df_sel[df_sel['Área (ha)'] > 0])
            area_agricola_sel = df_sel[~df_sel['Cultivo'].str.contains('No agrícola', na=False)]['Área (ha)'].sum()
            
            st.metric(
                f"Campaña {campana_seleccionada}", 
                f"{area_agricola_sel:,.1f} ha agrícolas",
                help=f"{cultivos_sel:,} cultivos detectados"
            )
        
        # Mostrar mapa
        if tiles_urls and campana_seleccionada in tiles_urls:
            mapa_tiles = crear_mapa_con_tiles_engine(
                aoi, tiles_urls, df_cultivos, 
                cultivos_por_campana, campana_seleccionada
            )
            
            map_data = st_folium(mapa_tiles, width=None, height=500)
            
            st.success("✅ **Mapa con píxeles reales de Google Earth Engine**")
            
            st.info("""
            **💡 Cómo usar el mapa:**
            
            🎯 **Solo 50% activo por defecto** - Cambia en el control de capas si necesitas
            
            🔴 **Límites del campo** - Contornos rojos súper visibles del área analizada
            
            🌾 **Leyenda en la parte inferior** - Muestra cultivos, áreas y porcentajes
            
            📊 **Colores exactos** - En el gráfico de rotación ⬆️
            """)
        
        # Descargas
        st.markdown("---")
        st.subheader("💾 Descargar Resultados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_hectareas = f"cultivos_hectareas_{timestamp}.csv"
            download_link_hectareas = get_download_link(df_cultivos, filename_hectareas, "📊 Descargar CSV - Hectáreas")
            st.markdown(download_link_hectareas, unsafe_allow_html=True)
        
        with col2:
            filename_porcentajes = f"rotacion_porcentajes_{timestamp}.csv"
            download_link_porcentajes = get_download_link(df_display, filename_porcentajes, "🔄 Descargar CSV - Rotación")
            st.markdown(download_link_porcentajes, unsafe_allow_html=True)
        
        # Botón para limpiar
        if st.button("🗑️ Limpiar Resultados"):
            st.session_state.analisis_completado = False
            st.session_state.resultados_analisis = None
            st.rerun()

if __name__ == "__main__":
    main() 