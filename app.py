# ===================================================================
# APLICACIÓN WEB - ANÁLISIS DE ROTACIÓN DE CULTIVOS DESDE KMZ
# Powered by Streamlit + Google Earth Engine
# ===================================================================

import streamlit as st
import os
import time
import json
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import ee
import tempfile
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import io
import base64
from datetime import datetime
import folium
from streamlit_folium import st_folium

# Configuración de la página
st.set_page_config(
    page_title="Análisis de Rotación de Cultivos",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
    }
    .upload-section {
        border: 2px dashed #2E8B57;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    .results-section {
        background-color: #f0f8f0;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<h1 class="main-header">🌾 Análisis de Rotación de Cultivos</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Sube tus archivos KMZ y obtén análisis detallado de cultivos y rotación</p>', unsafe_allow_html=True)

# Inicialización de Earth Engine
@st.cache_resource
def init_earth_engine():
    """Inicializa Google Earth Engine con Service Account"""
    try:
        proyecto_id = "carbide-kayak-459911-n3"
        
        # Intentar autenticación con Service Account
        if "google_credentials" in st.secrets:
            # Producción: usar Service Account desde Streamlit Secrets
            credentials = st.secrets["google_credentials"]
            ee.Initialize(ee.ServiceAccountCredentials(
                email=credentials["client_email"],
                key_data=json.dumps(dict(credentials))
            ), project=proyecto_id)
            st.success("🔐 Autenticado con Service Account (Streamlit Cloud)")
            
        elif 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            # Desarrollo: usar Service Account desde archivo local
            credentials_path = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
            ee.Initialize(ee.ServiceAccountCredentials(
                email=None,
                key_file=credentials_path
            ), project=proyecto_id)
            st.success("🔐 Autenticado con Service Account (Local)")
            
        else:
            # Fallback: autenticación interactiva para desarrollo
            ee.Authenticate()
            ee.Initialize(project=proyecto_id)
            st.success("🔐 Autenticado interactivamente")
        
        # Verificar conexión
        ee.Number(1).getInfo()
        return True
        
    except Exception as e:
        st.error(f"❌ Error conectando con Google Earth Engine: {e}")
        st.info("💡 Asegúrate de que las credenciales estén configuradas correctamente")
        return False

def extraer_coordenadas_kml(kml_content):
    """Extrae coordenadas de un archivo KML - VERSIÓN MEJORADA Y ROBUSTA"""
    poligonos = []
    
    try:
        root = ET.fromstring(kml_content)
        
        # Buscar todos los Placemark sin importar el namespace
        placemarks = []
        
        # Probar múltiples formas de encontrar placemarks
        for xpath in ['.//Placemark', './/{*}Placemark', './/{http://www.opengis.net/kml/2.2}Placemark', './/{http://earth.google.com/kml/2.2}Placemark']:
            try:
                found = root.findall(xpath)
                if found:
                    placemarks = found
                    break
            except:
                continue
        
        st.info(f"🔍 Encontrados {len(placemarks)} placemarks en el KML")
        
        for i, placemark in enumerate(placemarks):
            nombre = f"Polígono_{i+1}"
            
            # Buscar nombre (múltiples formas)
            for xpath in ['.//name', './/{*}name', './/{http://www.opengis.net/kml/2.2}name']:
                try:
                    name_elem = placemark.find(xpath)
                    if name_elem is not None and name_elem.text:
                        nombre = name_elem.text.strip()
                        break
                except:
                    continue
            
            # Buscar coordenadas en MÚLTIPLES ubicaciones posibles
            coords_text = ""
            
            # Lista ampliada de posibles rutas para coordenadas
            posibles_rutas = [
                './/coordinates',
                './/{*}coordinates',
                './/{http://www.opengis.net/kml/2.2}coordinates',
                './/{http://earth.google.com/kml/2.2}coordinates',
                './/Polygon//coordinates',
                './/LinearRing//coordinates',
                './/Point//coordinates',
                './/{*}Polygon//{*}coordinates',
                './/{*}LinearRing//{*}coordinates', 
                './/{*}Point//{*}coordinates'
            ]
            
            for ruta in posibles_rutas:
                try:
                    coords_elem = placemark.find(ruta)
                    if coords_elem is not None and coords_elem.text:
                        coords_text = coords_elem.text.strip()
                        break
                except:
                    continue
            
            if coords_text:
                coordenadas = []
                
                # Limpiar y normalizar el texto de coordenadas
                coords_text = coords_text.replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')
                
                # Intentar diferentes métodos de parsing
                coord_strings = []
                
                # Método 1: Separar por espacios
                if ' ' in coords_text:
                    coord_strings = [s.strip() for s in coords_text.split(' ') if s.strip()]
                # Método 2: Una sola línea de coordenadas
                else:
                    coord_strings = [coords_text.strip()]
                
                for coord_str in coord_strings:
                    if coord_str.strip():
                        # Separar lon,lat,alt por comas
                        parts = [p.strip() for p in coord_str.split(',')]
                        if len(parts) >= 2:
                            try:
                                lon = float(parts[0])
                                lat = float(parts[1])
                                
                                # Validar rango válido de coordenadas
                                if -180 <= lon <= 180 and -90 <= lat <= 90:
                                    coordenadas.append([lon, lat])
                            except (ValueError, IndexError):
                                continue
                
                # Validar polígono y agregarlo
                if coordenadas and len(coordenadas) >= 3:  # VALIDACIÓN: Al menos 3 puntos
                    # Cerrar polígono si no está cerrado
                    if coordenadas[0] != coordenadas[-1]:
                        coordenadas.append(coordenadas[0])
                    
                    poligono = {
                        'nombre': nombre,
                        'coords': coordenadas,
                        'numero': i + 1
                    }
                    poligonos.append(poligono)
                    
                elif coordenadas:
                    st.warning(f"⚠️ Polígono '{nombre}' omitido: tiene solo {len(coordenadas)} puntos (mínimo 3)")
                
    except Exception as e:
        st.error(f"❌ Error procesando KML: {e}")
    
    return poligonos
def procesar_kmz_uploaded(uploaded_file):
    """Procesa un archivo KMZ subido a Streamlit"""
    poligonos = []
    
    try:
        with zipfile.ZipFile(uploaded_file, 'r') as kmz_zip:
            kml_files = [f for f in kmz_zip.namelist() if f.endswith('.kml')]
            
            if not kml_files:
                st.warning(f"No se encontraron archivos KML en {uploaded_file.name}")
                return poligonos
            
            for kml_file in kml_files:
                with kmz_zip.open(kml_file) as kml:
                    kml_content = kml.read().decode('utf-8')
                    poligonos_kml = extraer_coordenadas_kml(kml_content)
                    
                    for pol in poligonos_kml:
                        pol['archivo_origen'] = uploaded_file.name
                        pol['kml_origen'] = kml_file
                    
                    poligonos.extend(poligonos_kml)
    
    except Exception as e:
        st.error(f"Error procesando {uploaded_file.name}: {e}")
    
    return poligonos

def crear_ee_feature_collection_web(poligonos_data):
    """Crea una colección de features de Earth Engine para la web"""
    features = []
    
    for i, pol in enumerate(poligonos_data):
        if 'coords' not in pol or not pol['coords']:
            continue
        
        coords = pol['coords']
        properties = {
            'nombre': pol.get('nombre', f'Poligono_{i+1}'),
            'numero': pol.get('numero', i+1),
            'archivo': pol.get('archivo_origen', 'desconocido')
        }
        
        try:
            geometry = ee.Geometry.Polygon([coords], 'EPSG:4326')
            geometry_projected = geometry.transform('EPSG:5345', maxError=1)
            feature = ee.Feature(geometry_projected, properties)
            features.append(feature)
        except Exception as e:
            st.warning(f"Error creando feature para {properties['nombre']}: {e}")
            continue
    
    if features:
        collection = ee.FeatureCollection(features)
        return collection
    
    return None

def analizar_cultivos_web(aoi):
    """Análisis de cultivos optimizado para la web"""
    try:
        area_total_aoi = aoi.geometry().transform('EPSG:5345', maxError=1).area(maxError=1).divide(10000)
        area_total = area_total_aoi.getInfo()
        
        # Paleta oficial de colores (misma que usas en los mapas oficiales)
        paleta_oficial = [
            '#ffffff', '#ffffff', '#ffffff', '#ffffff', '#ffffff', 
            '#ffffff', '#ffffff', '#ffffff', '#ffffff', '#ffffff', 
            '#0042ff', '#339820', '#FFFF00', '#f022db', '#ffffff', 
            '#b7b9bd', '#FFA500', '#1d1e33', '#FF0000', '#a32102',
            '#ffffff', '#646b63', '#e6f0c2', '#612517', '#94d200', '#ffffff', 
            '#8A2BE2', '#ffffff', '#800080', '#ffffff', '#D2B48C',
            '#87CEEB', '#90ee90'
        ]
        
        capas = {}
        tiles_urls = {}  # Para almacenar URLs de tiles
        campanas = ['19-20', '20-21', '21-22', '22-23', '23-24']
        
        asset_map = {
            '19-20': {'inv': 'inv19', 'ver': 'ver20'},
            '20-21': {'inv': 'inv20', 'ver': 'ver21'},
            '21-22': {'inv': 'inv21', 'ver': 'ver22'},
            '22-23': {'inv': 'inv22', 'ver': 'ver23'},
            '23-24': {'inv': 'inv23', 'ver': 'ver24'}
        }
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, campana in enumerate(campanas):
            status_text.text(f"Cargando campaña {campana}...")
            progress_bar.progress((i + 1) / len(campanas) * 0.3)
            
            try:
                inv_name = asset_map[campana]['inv']
                ver_name = asset_map[campana]['ver']
                
                inv_asset = ee.Image(f'projects/carbide-kayak-459911-n3/assets/{inv_name}')
                ver_asset = ee.Image(f'projects/carbide-kayak-459911-n3/assets/{ver_name}')
                
                inv_asset_projected = inv_asset.reproject('EPSG:5345', None, 30)
                ver_asset_projected = ver_asset.reproject('EPSG:5345', None, 30)
                
                inv_aoi = inv_asset_projected.clip(aoi.geometry())
                ver_aoi = ver_asset_projected.clip(aoi.geometry())
                
                if campana == '19-20':
                    capa_combinada = ee.Image().expression(
                        '(verano == 10 && (invierno == 0 || invierno == 6)) ? 31 : ' +
                        '(verano == 11 && (invierno == 0 || invierno == 6)) ? 32 : ' +
                        '(verano == 10) ? 10 : (verano == 11) ? 11 : (verano == 14) ? 14 : (verano == 19) ? 19 : verano',
                        {'verano': ver_aoi, 'invierno': inv_aoi}
                    )
                else:
                    capa_combinada = ee.Image().expression(
                        '(verano == 10 && (invierno == 6 || invierno == 16 || invierno == 24)) ? 31 : ' +
                        '(verano == 11 && (invierno == 6 || invierno == 16 || invierno == 24)) ? 32 : ' +
                        '(verano == 10) ? 10 : (verano == 11) ? 11 : (verano == 14) ? 14 : (verano == 19) ? 19 : (verano == 26) ? 26 : verano',
                        {'verano': ver_aoi, 'invierno': inv_aoi}
                    )
                
                capas[campana] = capa_combinada
                
                # Generar tiles URL para el mapa interactivo
                try:
                    vis_params = {'min': 0, 'max': 32, 'palette': paleta_oficial}
                    map_id = capa_combinada.getMapId(vis_params)
                    
                    # MÉTODO ACTUALIZADO para Earth Engine moderno
                    st.info(f"🔍 Generando tiles para {campana}")
                    
                    # Método 1: tile_fetcher.url_template (atributo)
                    if 'tile_fetcher' in map_id and hasattr(map_id['tile_fetcher'], 'url_template'):
                        tiles_urls[campana] = map_id['tile_fetcher'].url_template
                        st.success(f"✅ Tiles (método 1) para {campana}")
                    
                    # Método 2: tile_fetcher['url_template'] (diccionario)  
                    elif 'tile_fetcher' in map_id and isinstance(map_id['tile_fetcher'], dict) and 'url_template' in map_id['tile_fetcher']:
                        tiles_urls[campana] = map_id['tile_fetcher']['url_template']
                        st.success(f"✅ Tiles (método 2) para {campana}")
                    
                    # Método 3: urlTemplate directo
                    elif 'urlTemplate' in map_id:
                        tiles_urls[campana] = map_id['urlTemplate']
                        st.success(f"✅ Tiles (método 3) para {campana}")
                    
                    # Método 4: tile_fetcher es un objeto de Earth Engine
                    elif 'tile_fetcher' in map_id:
                        tile_fetcher = map_id['tile_fetcher']
                        
                        # ee.data.TileFetcher necesita métodos específicos
                        try:
                            st.info(f"🔍 tile_fetcher para {campana}: {type(tile_fetcher)}")
                            
                            # MÉTODO CORRECTO para ee.data.TileFetcher
                            if hasattr(tile_fetcher, 'url_format'):
                                # Método 1: url_format directo
                                url_format = tile_fetcher.url_format
                                tiles_urls[campana] = url_format
                                st.success(f"✅ Tiles (url_format) para {campana}: {url_format[:50]}...")
                                
                            elif hasattr(tile_fetcher, 'format_url'):
                                # Método 2: format_url con parámetros de ejemplo
                                try:
                                    example_url = tile_fetcher.format_url(x=0, y=0, z=1)
                                    # Convertir ejemplo a template
                                    template_url = example_url.replace('/0/0/1', '/{x}/{y}/{z}')
                                    tiles_urls[campana] = template_url
                                    st.success(f"✅ Tiles (format_url) para {campana}: {template_url[:50]}...")
                                except:
                                    pass
                                    
                            # Si no funciona, explorar todas las propiedades
                            if campana not in tiles_urls:
                                attrs = [attr for attr in dir(tile_fetcher) if not attr.startswith('_')]
                                st.info(f"🔍 Atributos de TileFetcher: {attrs[:10]}")
                                
                                # Probar diferentes propiedades conocidas de TileFetcher
                                for prop_name in ['url_format', 'urlFormat', 'baseUrl', 'base_url', 'template', 'url_template']:
                                    if hasattr(tile_fetcher, prop_name):
                                        try:
                                            prop_val = getattr(tile_fetcher, prop_name)
                                            if prop_val and isinstance(prop_val, str) and 'http' in prop_val:
                                                tiles_urls[campana] = prop_val
                                                st.success(f"✅ Tiles ({prop_name}) para {campana}")
                                                break
                                        except:
                                            continue
                                            
                        except Exception as tf_error:
                            st.warning(f"Error explorando tile_fetcher para {campana}: {tf_error}")
                            
                            # Como último recurso, intentar convertir a string y buscar patterns
                            tf_str = str(tile_fetcher)
                            if 'earthengine' in tf_str.lower():
                                st.info(f"tile_fetcher es objeto EE: {tf_str[:200]}...")
                                # Intentar generar URL manualmente
                                try:
                                    # Usar el map_id directamente para construir URL
                                    if 'mapid' in map_id:
                                        mapid = map_id['mapid']
                                        token = map_id.get('token', '')
                                        base_url = "https://earthengine.googleapis.com/v1alpha/projects/earthengine-legacy/maps"
                                        manual_url = f"{base_url}/{mapid}/tiles/{{z}}/{{x}}/{{y}}?token={token}"
                                        tiles_urls[campana] = manual_url
                                        st.success(f"✅ URL manual generada para {campana}")
                                except Exception as manual_error:
                                    st.error(f"Error generando URL manual: {manual_error}")
                    else:
                        keys_disponibles = list(map_id.keys()) if hasattr(map_id, 'keys') else []
                        st.error(f"❌ No hay tile_fetcher para {campana}. Keys: {keys_disponibles}")
                        
                except Exception as tile_error:
                    st.warning(f"❌ Error generando tiles para {campana}: {tile_error}")
                    
                    # MÉTODO ALTERNATIVO: Usar visualize
                    try:
                        st.info(f"🔄 Probando método alternativo para {campana}...")
                        # Crear una versión simplificada para visualización
                        vis_image = capa_combinada.visualize(**vis_params)
                        simple_map_id = vis_image.getMapId({})
                        
                        if 'tile_fetcher' in simple_map_id:
                            tiles_urls[campana] = simple_map_id['tile_fetcher'].url_template
                            st.success(f"✅ Método alternativo exitoso para {campana}")
                        else:
                            st.error(f"❌ Método alternativo también falló para {campana}")
                            
                    except Exception as alt_error:
                        st.error(f"❌ Método alternativo falló para {campana}: {alt_error}")
                        # Como último recurso, usar el método de fallback
                        pass
                
            except Exception as e:
                st.warning(f"Error cargando campaña {campana}: {e}")
        
        cultivos_por_campana = {
            '19-20': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 14: 'Caña de azúcar', 15: 'Algodón', 16: 'Maní', 17: 'Arroz', 18: 'Sorgo GR', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '20-21': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 14: 'Caña de azúcar', 15: 'Algodón', 16: 'Maní', 17: 'Arroz', 18: 'Sorgo GR', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 26: 'Papa', 28: 'Verdeo de Sorgo', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '21-22': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 14: 'Caña de azúcar', 15: 'Algodón', 16: 'Maní', 17: 'Arroz', 18: 'Sorgo GR', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 26: 'Papa', 28: 'Verdeo de Sorgo', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '22-23': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 14: 'Caña de azúcar', 15: 'Algodón', 16: 'Maní', 17: 'Arroz', 18: 'Sorgo GR', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 26: 'Papa', 28: 'Verdeo de Sorgo', 30: 'Tabaco', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '23-24': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 14: 'Caña de azúcar', 15: 'Algodón', 16: 'Maní', 17: 'Arroz', 18: 'Sorgo GR', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 26: 'Papa', 28: 'Verdeo de Sorgo', 30: 'Tabaco', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'}
        }
        
        status_text.text("Calculando áreas por cultivo...")
        progress_bar.progress(0.4)
        
        # MOSTRAR ESTADO DE TILES GENERADOS
        tiles_generados = len([c for c in tiles_urls.values() if c])
        total_campanas = len(campanas)
        status_text.text(f"Tiles generados: {tiles_generados}/{total_campanas} campañas")
        
        if tiles_generados > 0:
            campanas_con_tiles = [c for c, url in tiles_urls.items() if url]
            status_text.text(f"✅ Tiles OK: {', '.join(campanas_con_tiles)}")
        else:
            status_text.text("⚠️ No se generaron tiles - usando visualización alternativa")
        
        resultados_todas_campanas = []
        area_pixeles = ee.Image.pixelArea().reproject('EPSG:5345', None, 30)
        
        for j, campana in enumerate(campanas):
            if campana in capas:
                try:
                    cultivos = cultivos_por_campana[campana]
                    capa = capas[campana]
                    
                    for cultivo_id, nombre_cultivo in cultivos.items():
                        try:
                            cultivo_id_int = int(cultivo_id)
                            mascara_cultivo = capa.eq(cultivo_id_int)
                            area_img = area_pixeles.multiply(mascara_cultivo)
                            
                            area_dict = area_img.reduceRegion(
                                reducer=ee.Reducer.sum(),
                                geometry=aoi.geometry(),
                                scale=30,
                                maxPixels=1e13,
                                bestEffort=False,
                                tileScale=4
                            )
                            
                            area_value = area_dict.get('area')
                            area_cultivo = ee.Number(area_value).getInfo()
                            area_cultivo_ha = round(area_cultivo / 10000) if area_cultivo else 0
                            porcentaje_cultivo = round((area_cultivo_ha / area_total) * 100) if area_total > 0 else 0
                            
                            resultados_todas_campanas.append({
                                'Campaña': campana,
                                'Cultivo': nombre_cultivo,
                                'ID': cultivo_id_int,
                                'Área (ha)': area_cultivo_ha,
                                'Porcentaje (%)': porcentaje_cultivo
                            })
                            
                        except Exception as e:
                            continue
                    
                    progress_bar.progress(0.4 + (j + 1) / len(campanas) * 0.5)
                    
                except Exception as e:
                    continue
        
        status_text.text("✅ Análisis completado exitosamente!")
        progress_bar.progress(1.0)
        # NO borrar los elementos - mantenerlos visibles
        
        return pd.DataFrame(resultados_todas_campanas), area_total, tiles_urls, cultivos_por_campana
        
    except Exception as e:
        st.error(f"Error en análisis de cultivos: {e}")
        return None, 0, {}, {}

def generar_grafico_rotacion_web(df_resultados):
    """Genera el gráfico de rotación para la web"""
    try:
        df = df_resultados.copy()
        df['Cultivo_Normalizado'] = df['Cultivo'].str.lower().str.strip()
        no_agricola_mask = df['Cultivo_Normalizado'].str.contains('no agr[ií]cola', regex=True, na=False)
        df['Cultivo_Estandarizado'] = df['Cultivo']
        df.loc[no_agricola_mask, 'Cultivo_Estandarizado'] = 'No Agrícola'
        
        area_total_por_campana = df.groupby('Campaña')['Área (ha)'].sum().reset_index()
        area_total_por_campana.rename(columns={'Área (ha)': 'Área Total'}, inplace=True)
        
        area_por_cultivo_campana = df.groupby(['Campaña', 'Cultivo_Estandarizado'])['Área (ha)'].sum().reset_index()
        rotacion_cultivos = pd.merge(area_por_cultivo_campana, area_total_por_campana, on='Campaña')
        rotacion_cultivos['Porcentaje'] = (rotacion_cultivos['Área (ha)'] / rotacion_cultivos['Área Total']) * 100
        
        porcentaje_promedio_cultivo = rotacion_cultivos.groupby('Cultivo_Estandarizado')['Porcentaje'].mean().reset_index()
        porcentaje_promedio_cultivo = porcentaje_promedio_cultivo.sort_values('Porcentaje', ascending=False)
        
        umbral_porcentaje = 1.0
        cultivos_principales = porcentaje_promedio_cultivo[porcentaje_promedio_cultivo['Porcentaje'] >= umbral_porcentaje]['Cultivo_Estandarizado'].tolist()
        
        if 'No Agrícola' not in cultivos_principales:
            cultivos_principales.insert(0, 'No Agrícola')
        
        pivote_rotacion = rotacion_cultivos.pivot_table(
            index='Cultivo_Estandarizado',
            columns='Campaña',
            values='Porcentaje',
            fill_value=0
        ).reset_index()
        
        pivote_rotacion_filtrado = pivote_rotacion[pivote_rotacion['Cultivo_Estandarizado'].isin(cultivos_principales)]
        
        orden_personalizado = ['No Agrícola'] + [c for c in cultivos_principales if c != 'No Agrícola']
        pivote_rotacion_filtrado = pivote_rotacion_filtrado.copy()
        pivote_rotacion_filtrado.loc[:, 'orden'] = pivote_rotacion_filtrado['Cultivo_Estandarizado'].apply(
            lambda x: orden_personalizado.index(x) if x in orden_personalizado else 999)
        pivote_rotacion_filtrado = pivote_rotacion_filtrado.sort_values('orden').drop('orden', axis=1)
        
        df_rotacion_final = pivote_rotacion_filtrado.copy()
        columnas_campanas = [col for col in df_rotacion_final.columns if col != 'Cultivo_Estandarizado']
        df_rotacion_final['Promedio'] = df_rotacion_final[columnas_campanas].mean(axis=1)
        
        def ajustar_a_100(df_input, columna):
            df_copy = df_input.copy()
            if df_copy.empty or df_copy[columna].empty or df_copy[columna].sum() == 0:
                return df_copy
            
            total_actual = df_copy[columna].sum()
            if total_actual != 100:
                factor = 100 / total_actual
                df_copy.loc[:, columna] = (df_copy[columna] * factor).round(1)
                
                total_redondeado = df_copy[columna].sum()
                if total_redondeado != 100:
                    idx_max = df_copy[columna].idxmax()
                    df_copy.loc[idx_max, columna] = df_copy.loc[idx_max, columna] + (100 - total_redondeado)
            
            df_copy.loc[:, columna] = df_copy[columna].round(0).astype(int)
            total_entero = df_copy[columna].sum()
            if total_entero != 100:
                idx_max = df_copy[columna].idxmax()
                df_copy.loc[idx_max, columna] = df_copy.loc[idx_max, columna] + (100 - total_entero)
            
            return df_copy
        
        for col in columnas_campanas + ['Promedio']:
            df_rotacion_final = ajustar_a_100(df_rotacion_final, col)
        
        colores_cultivos = {
            'Maíz': '#0042ff', 'Soja 1ra': '#339820', 'Girasol': '#FFFF00', 'Poroto': '#f022db',
            'Algodón': '#b7b9bd', 'Maní': '#FFA500', 'Arroz': '#1d1e33', 'Sorgo GR': '#FF0000',
            'Caña de Azúcar': '#a32102', 'Caña de azúcar': '#a32102', 'Barbecho': '#646b63',
            'No Agrícola': '#e6f0c2', 'Papa': '#8A2BE2', 'Verdeo de Sorgo': '#800080',
            'Tabaco': '#D2B48C', 'CI-Maíz': '#87CEEB', 'CI-Maíz 2da': '#87CEEB',
            'CI-Soja': '#90ee90', 'CI-Soja 2da': '#90ee90', 'Soja 2da': '#90ee90'
        }
        
        color_default = '#999999'
        
        df_plot = df_rotacion_final.set_index('Cultivo_Estandarizado')
        columnas_grafico = columnas_campanas + ['Promedio']
        df_temp = df_plot[columnas_grafico]
        
        colores_ordenados = []
        for cultivo in df_temp.index:
            if cultivo in colores_cultivos:
                colores_ordenados.append(colores_cultivos[cultivo])
            else:
                colores_ordenados.append(color_default)
        
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
        
        return fig, df_rotacion_final
        
    except Exception as e:
        st.error(f"Error generando gráfico: {e}")
        return None, None

def get_download_link(df, filename, link_text):
    """Genera un enlace de descarga para un DataFrame"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{link_text}</a>'
    return href


def crear_mapa_con_tiles_engine(aoi, tiles_urls, df_resultados, cultivos_por_campana, campana_seleccionada):
    """
    Crea un mapa interactivo con tiles reales de Google Earth Engine
    
    Args:
        aoi: FeatureCollection de Earth Engine 
        tiles_urls: URLs de tiles por campaña
        df_resultados: DataFrame con resultados
        cultivos_por_campana: Diccionario de cultivos por campaña
        campana_seleccionada: Campaña a mostrar
        
    Returns:
        folium.Map: Mapa con tiles de Earth Engine
    """
    
    # Obtener centro del AOI
    try:
        aoi_bounds = aoi.geometry().bounds()
        bounds_info = aoi_bounds.getInfo()
        center_lat = (bounds_info["coordinates"][0][1] + bounds_info["coordinates"][0][3]) / 2
        center_lon = (bounds_info["coordinates"][0][0] + bounds_info["coordinates"][0][2]) / 2
    except:
        center_lat, center_lon = -34.0, -60.0
    
    # Crear mapa base
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
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
    
    # Agregar tiles de Earth Engine para la campaña seleccionada
    if campana_seleccionada in tiles_urls:
        tile_url = tiles_urls[campana_seleccionada]
        
        folium.raster_layers.TileLayer(
            tiles=tile_url,
            attr='Google Earth Engine',
            name=f'Cultivos {campana_seleccionada}',
            overlay=True,
            control=True,
            opacity=0.7
        ).add_to(m)
    
    # Agregar contorno del AOI
    try:
        aoi_geojson = aoi.getInfo()
        folium.GeoJson(
            aoi_geojson,
            name="Límite del Campo",
            style_function=lambda x: {
                "fillColor": "transparent",
                "color": "red", 
                "weight": 3,
                "fillOpacity": 0
            }
        ).add_to(m)
    except Exception as e:
        st.warning(f"No se pudo agregar contorno: {e}")
    
    # Crear leyenda oficial estilo mapas
    df_campana = df_resultados[df_resultados['Campaña'] == campana_seleccionada]
    cultivos_campana = cultivos_por_campana.get(campana_seleccionada, {})
    
    # Colores para la leyenda
    colores_cultivos = {
        'Maíz': '#0042ff', 'Soja 1ra': '#339820', 'Girasol': '#FFFF00', 'Poroto': '#f022db',
        'Algodón': '#b7b9bd', 'Maní': '#FFA500', 'Arroz': '#1d1e33', 'Sorgo GR': '#FF0000',
        'Caña de azúcar': '#a32102', 'Barbecho': '#646b63', 'No agrícola': '#e6f0c2',
        'Papa': '#8A2BE2', 'Verdeo de Sorgo': '#800080', 'Tabaco': '#D2B48C',
        'CI-Maíz 2da': '#87CEEB', 'CI-Soja 2da': '#90ee90', 'Girasol-CV': '#a32102'
    }
    
    # Crear leyenda HTML estilo oficial
    legend_html = f"""
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 280px;
                background-color: white; z-index:9999; 
                border: 2px solid #333; border-radius: 8px;
                padding: 15px; font-family: Arial, sans-serif;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);">
                
    <h3 style="margin: 0 0 15px 0; text-align: center; 
               background-color: #2E8B57; color: white; 
               padding: 8px; border-radius: 4px;">
        Campaña {campana_seleccionada}
    </h3>
    """
    
    # Agregar cultivos con área > 0 ordenados por área
    cultivos_con_area = df_campana[df_campana['Área (ha)'] > 0].sort_values('Área (ha)', ascending=False)
    
    for _, row in cultivos_con_area.iterrows():
        cultivo = row['Cultivo']
        area = row['Área (ha)']
        porcentaje = row['Porcentaje (%)']
        color = colores_cultivos.get(cultivo, '#999999')
        
        legend_html += f"""
        <div style="display: flex; align-items: center; margin: 8px 0;">
            <div style="width: 25px; height: 18px; background-color: {color}; 
                        margin-right: 10px; border: 1px solid #333;
                        border-radius: 2px;"></div>
            <span style="font-size: 13px; font-weight: bold;">
                {cultivo}: {area} ha ({porcentaje}%)
            </span>
        </div>
        """
    
    legend_html += """
    <div style="margin-top: 15px; padding-top: 10px; 
                border-top: 1px solid #ccc; font-size: 11px; 
                color: #666; text-align: center;">
        🌾 Mapa Nacional de Cultivos<br>
        Google Earth Engine
    </div>
    </div>
    """
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Control de capas
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m

def crear_visor_cultivos_interactivo(aoi, df_resultados):
    """
    Crea un visor interactivo de cultivos usando Folium
    
    Args:
        aoi: FeatureCollection de Earth Engine con el área de interés
        df_resultados: DataFrame con los resultados de análisis de cultivos
        
    Returns:
        folium.Map: Mapa interactivo con capas de cultivos
    """
    
    # Obtener el centro del AOI
    try:
        # Obtener bounds del AOI para centrar el mapa
        aoi_bounds = aoi.geometry().bounds()
        bounds_info = aoi_bounds.getInfo()
        
        # Calcular centro
        center_lat = (bounds_info["coordinates"][0][1] + bounds_info["coordinates"][0][3]) / 2
        center_lon = (bounds_info["coordinates"][0][0] + bounds_info["coordinates"][0][2]) / 2
        
    except:
        # Fallback a coordenadas por defecto (Argentina)
        center_lat, center_lon = -34.0, -60.0
    
    # Crear mapa base
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles=None  # No añadir capa base por defecto
    )
    
    # Agregar capas base
    folium.TileLayer(
        "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Satellite",
        name="Satelital",
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google Hybrid",
        name="Híbrido",
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        "OpenStreetMap",
        name="Mapa",
        control=True
    ).add_to(m)
    
    # Colores específicos por cultivo (mismos que en los gráficos)
    colores_cultivos = {
        "Maíz": "#0042ff",
        "Soja 1ra": "#339820", 
        "Girasol": "#FFFF00",
        "Girasol-CV": "#FFFF00",
        "Poroto": "#f022db",
        "Algodón": "#b7b9bd",
        "Maní": "#FFA500",
        "Arroz": "#1d1e33",
        "Sorgo GR": "#FF0000",
        "Caña de azúcar": "#a32102",
        "Caña de Azúcar": "#a32102",
        "Barbecho": "#646b63",
        "No agrícola": "#e6f0c2",
        "No Agrícola": "#e6f0c2",
        "Papa": "#8A2BE2",
        "Verdeo de Sorgo": "#800080",
        "Tabaco": "#D2B48C",
        "CI-Maíz 2da": "#87CEEB",
        "CI-Soja 2da": "#90ee90",
        "Soja 2da": "#90ee90"
    }
    
    # Crear grupos de capas por campaña
    campanas = sorted(df_resultados["Campaña"].unique())
    
    for campana in campanas:
        # Crear grupo de capa para esta campaña
        feature_group = folium.FeatureGroup(name=f"Cultivos {campana}")
        
        # Filtrar datos de esta campaña
        df_campana = df_resultados[df_resultados["Campaña"] == campana]
        
        # Agrupar por cultivo para crear áreas
        for cultivo in df_campana["Cultivo"].unique():
            df_cultivo = df_campana[df_campana["Cultivo"] == cultivo]
            
            if df_cultivo["Área (ha)"].sum() > 0:  # Solo mostrar cultivos con área > 0
                # Obtener color del cultivo
                color = colores_cultivos.get(cultivo, "#999999")
                
                # Crear polígono representativo (usaremos el AOI como base)
                try:
                    area_total = df_cultivo["Área (ha)"].sum()
                    porcentaje = df_cultivo["Porcentaje (%)"].sum()
                    
                    # Crear popup con información
                    popup_html = f"""
                    <div style="font-family: Arial; width: 200px;">
                        <h4 style="margin: 0; color: {color};">{cultivo}</h4>
                        <p style="margin: 5px 0;"><b>Campaña:</b> {campana}</p>
                        <p style="margin: 5px 0;"><b>Área:</b> {area_total:.1f} ha</p>
                        <p style="margin: 5px 0;"><b>Porcentaje:</b> {porcentaje:.1f}%</p>
                    </div>
                    """
                    
                    # Agregar marcador representativo
                    folium.CircleMarker(
                        location=[center_lat + (hash(cultivo) % 1000 - 500) * 0.001,
                                center_lon + (hash(cultivo) % 1000 - 500) * 0.001],
                        radius=max(5, min(20, area_total / 10)),
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"{cultivo}: {area_total:.1f} ha",
                        color="black",
                        weight=1,
                        fillColor=color,
                        fillOpacity=0.7
                    ).add_to(feature_group)
                    
                except Exception as e:
                    st.warning(f"Error agregando {cultivo} al mapa: {e}")
        
        # Agregar el grupo de características al mapa
        feature_group.add_to(m)
    
    # Intentar agregar el contorno del AOI
    try:
        # Obtener geometría del AOI como GeoJSON
        aoi_geojson = aoi.getInfo()
        
        # Agregar AOI como overlay
        folium.GeoJson(
            aoi_geojson,
            name="Límite del Campo",
            style_function=lambda x: {
                "fillColor": "transparent",
                "color": "red",
                "weight": 3,
                "fillOpacity": 0
            },
            tooltip="Límite del área analizada"
        ).add_to(m)
        
    except Exception as e:
        st.warning(f"No se pudo agregar el contorno del campo al mapa: {e}")
    
    # Agregar control de capas
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Agregar leyenda personalizada
    legend_html = """
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: auto; 
                background-color: white; z-index:9999; font-size:12px;
                border:2px solid grey; padding: 10px; border-radius: 5px;">
                
    <h4 style="margin-top:0;">🌾 Cultivos Detectados</h4>
    """
    
    # Agregar colores de cultivos más comunes a la leyenda
    cultivos_principales = ["Maíz", "Soja 1ra", "Girasol", "No agrícola"]
    for cultivo in cultivos_principales:
        if cultivo in colores_cultivos:
            color = colores_cultivos[cultivo]
            legend_html += f"""
            <div style="margin: 5px 0;">
                <span style="background-color: {color}; width: 15px; height: 15px; 
                           display: inline-block; margin-right: 5px; border: 1px solid black;"></span>
                <span>{cultivo}</span>
            </div>
            """
    
    legend_html += """
    <p style="margin: 10px 0 0 0; font-size: 10px; color: #666;">
        💡 Usa los controles de capas para ver diferentes años
    </p>
    </div>
    """
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def generar_codigo_earth_engine_visor(aoi):
    """
    Genera código JavaScript para Google Earth Engine Code Editor
    que permite visualizar los cultivos por campaña
    """
    
    # Obtener información del AOI para el código
    try:
        aoi_info = aoi.getInfo()
        # Simplificar para el código de ejemplo
        first_feature = aoi_info["features"][0] if aoi_info.get("features") else None
        
        if first_feature:
            coords = first_feature["geometry"]["coordinates"][0]
            # Tomar solo los primeros puntos para el ejemplo
            coords_sample = coords[:5] if len(coords) > 5 else coords
            
            coords_str = ", ".join([f"[{c[0]}, {c[1]}]" for c in coords_sample])
            
        else:
            coords_str = "[-60.0, -34.0], [-59.9, -34.0], [-59.9, -33.9], [-60.0, -33.9], [-60.0, -34.0]"
            
    except:
        coords_str = "[-60.0, -34.0], [-59.9, -34.0], [-59.9, -33.9], [-60.0, -33.9], [-60.0, -34.0]"
    
    codigo_js = f"""// ===================================================================
// VISOR DE CULTIVOS POR CAMPAÑA - GOOGLE EARTH ENGINE
// Generado automáticamente por la aplicación web
// ===================================================================

// Definir el área de interés (AOI)
var aoi = ee.FeatureCollection([
  ee.Feature(ee.Geometry.Polygon([[{coords_str}]]))
]);

// Centrar mapa en el AOI
Map.centerObject(aoi, 13);

// Agregar AOI al mapa
Map.addLayer(aoi, {{color: 'red', fillOpacity: 0}}, 'Área de Interés');

print('✓ Código generado automáticamente desde la aplicación web');
print('✓ Para ver los cultivos, activa las capas en el panel de la derecha');
"""
    
    return codigo_js

def main():
    # Inicializar session state si no existe
    if 'resultados_analisis' not in st.session_state:
        st.session_state.resultados_analisis = None
    if 'analisis_completado' not in st.session_state:
        st.session_state.analisis_completado = False
    
    with st.sidebar:
        st.header("📋 Información")
        st.write("""
        **¿Qué hace esta aplicación?**
        
        1. **Sube archivos KMZ** con polígonos de campos
        2. **Analiza cultivos** usando Google Earth Engine
        3. **Calcula rotación** por campaña (2019-2024)
        4. **Genera gráficos** profesionales
        5. **Permite descargar** resultados en CSV
        """)
        
        st.header("🎯 Cultivos detectados")
        st.write("""
        - Maíz / Soja / Girasol
        - Poroto / Algodón / Maní
        - Arroz / Sorgo / Papa
        - Caña de azúcar / Tabaco
        - Cultivos de cobertura
        - Áreas no agrícolas
        """)
    
    if 'ee_initialized' not in st.session_state:
        with st.spinner("Inicializando Google Earth Engine..."):
            st.session_state.ee_initialized = init_earth_engine()
    
    if not st.session_state.ee_initialized:
        st.error("❌ No se pudo conectar con Google Earth Engine. Verifica la configuración.")
        return
    
    st.success("✅ Google Earth Engine conectado correctamente")
    
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.subheader("📁 Sube tus archivos KMZ")
    
    uploaded_files = st.file_uploader(
        "Selecciona uno o más archivos KMZ",
        type=['kmz'],
        accept_multiple_files=True,
        help="Puedes subir múltiples archivos KMZ a la vez"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} archivo(s) subido(s)")
        
        with st.expander("Ver detalles de archivos subidos"):
            for file in uploaded_files:
                st.write(f"📄 {file.name} ({file.size:,} bytes)")
        
        # BOTÓN DE ANÁLISIS - SOLO PROCESA Y GUARDA EN SESSION STATE
        if st.button("🚀 Analizar Cultivos y Rotación", type="primary"):
            with st.spinner("🔄 Procesando análisis completo..."):
                # Procesar archivos KMZ
                todos_los_poligonos = []
                for uploaded_file in uploaded_files:
                    poligonos = procesar_kmz_uploaded(uploaded_file)
                    todos_los_poligonos.extend(poligonos)
                
                if not todos_los_poligonos:
                    st.error("❌ No se encontraron polígonos válidos en los archivos")
                    st.session_state.analisis_completado = False
                    return
                
                # Crear AOI
                aoi = crear_ee_feature_collection_web(todos_los_poligonos)
                if not aoi:
                    st.error("❌ No se pudo crear el área de interés")
                    st.session_state.analisis_completado = False
                    return
                
                # Ejecutar análisis
                resultado = analizar_cultivos_web(aoi)
                
                if len(resultado) == 4:
                    df_cultivos, area_total, tiles_urls, cultivos_por_campana = resultado
                else:
                    df_cultivos, area_total = resultado[:2]
                    tiles_urls = {}
                    cultivos_por_campana = {}
                
                if df_cultivos is not None and not df_cultivos.empty:
                    # GUARDAR TODO EN SESSION STATE
                    st.session_state.resultados_analisis = {
                        'df_cultivos': df_cultivos,
                        'area_total': area_total,
                        'tiles_urls': tiles_urls,
                        'cultivos_por_campana': cultivos_por_campana,
                        'aoi': aoi,
                        'archivo_info': f"{len(uploaded_files)} archivo(s) - {len(todos_los_poligonos)} polígonos"
                    }
                    st.session_state.analisis_completado = True
                    st.success("🎉 ¡Análisis completado exitosamente!")
                    st.rerun()  # Refrescar para mostrar resultados
                else:
                    st.error("❌ No se pudieron analizar los cultivos")
                    st.session_state.analisis_completado = False
    
    # MOSTRAR RESULTADOS PERSISTENTES - FUERA DEL BOTÓN
    if st.session_state.analisis_completado and st.session_state.resultados_analisis:
        st.markdown("---")
        st.markdown("## 📊 Resultados del Análisis")
        
        # Extraer datos de session state
        datos = st.session_state.resultados_analisis
        df_cultivos = datos['df_cultivos']
        area_total = datos['area_total']
        tiles_urls = datos['tiles_urls']
        cultivos_por_campana = datos['cultivos_por_campana']
        aoi = datos['aoi']
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Área Total", f"{area_total:.1f} ha")
        with col2:
            cultivos_detectados = df_cultivos[df_cultivos['Área (ha)'] > 0]['Cultivo'].nunique()
            st.metric("Cultivos Detectados", cultivos_detectados)
        with col3:
            area_agricola_por_campana = df_cultivos[~df_cultivos['Cultivo'].str.contains('No agrícola', na=False)].groupby('Campaña')['Área (ha)'].sum()
            area_agricola = area_agricola_por_campana.mean()
            st.metric("Área Agrícola", f"{area_agricola:.1f} ha", help="Promedio de área agrícola por campaña")
        with col4:
            porcentaje_agricola = (area_agricola / area_total * 100) if area_total > 0 else 0
            st.metric("% Agrícola", f"{porcentaje_agricola:.1f}%", help="Porcentaje promedio de área agrícola")
        
        # Generar gráfico de rotación
        fig, df_rotacion = generar_grafico_rotacion_web(df_cultivos)
        
        if fig is not None:
            st.subheader("🎨 Gráfico de Rotación de Cultivos")
            st.pyplot(fig)
            
            st.subheader("📋 Tabla de Rotación (%)")
            df_display = df_rotacion.copy()
            df_display = df_display.rename(columns={'Cultivo_Estandarizado': 'Cultivo'})
            st.dataframe(df_display, use_container_width=True)
            
            # MAPA INTERACTIVO PERSISTENTE
            st.subheader("🗺️ Mapa Interactivo de Cultivos")
            st.write("Explora los píxeles de cultivos reales de Google Earth Engine:")
            
            # Dropdown para seleccionar campaña
            campanas_disponibles = sorted(df_cultivos['Campaña'].unique())
            
            col_dropdown, col_info = st.columns([1, 2])
            with col_dropdown:
                campana_seleccionada = st.selectbox(
                    "🗓️ Seleccionar Campaña:",
                    campanas_disponibles,
                    index=len(campanas_disponibles)-1,
                    key="selector_campana_persistente"  # Key única y persistente
                )
            
            with col_info:
                # Mostrar info de la campaña seleccionada
                df_sel = df_cultivos[df_cultivos['Campaña'] == campana_seleccionada]
                cultivos_sel = len(df_sel[df_sel['Área (ha)'] > 0])
                area_agricola_sel = df_sel[~df_sel['Cultivo'].str.contains('No agrícola', na=False)]['Área (ha)'].sum()
                
                st.metric(
                    f"Campaña {campana_seleccionada}", 
                    f"{area_agricola_sel:.1f} ha agrícolas",
                    help=f"{cultivos_sel} cultivos detectados"
                )
            
            # Mostrar mapa
            try:
                if tiles_urls and campana_seleccionada in tiles_urls:
                    # Crear mapa con tiles reales de Earth Engine
                    mapa_tiles = crear_mapa_con_tiles_engine(
                        aoi, tiles_urls, df_cultivos, 
                        cultivos_por_campana, campana_seleccionada
                    )
                    
                    # Mostrar el mapa
                    map_data = st_folium(mapa_tiles, width=700, height=500, key="mapa_persistente")
                    
                    st.success("✅ **Mapa con píxeles reales de Google Earth Engine**")
                    st.info("💡 **Cómo usar el mapa:**")
                    st.write("""
                    - 🎨 **Píxeles de colores**: Cada color representa un cultivo específico
                    - 🗓️ **Cambiar campaña**: Usa el dropdown arriba para ver otras años
                    - 🔍 **Zoom**: Acerca/aleja para ver más detalle
                    - 📊 **Leyenda**: Área y porcentaje de cada cultivo (esquina inferior derecha)
                    - 🗺️ **Capas base**: Cambia entre satelital y mapa en el control de capas
                    """)
                    
                else:
                    st.warning("⚠️ No hay tiles disponibles para esta campaña")
                    # Fallback al visor anterior
                    mapa_cultivos = crear_visor_cultivos_interactivo(aoi, df_cultivos)
                    map_data = st_folium(mapa_cultivos, width=700, height=500, key="mapa_fallback")
                
            except Exception as e:
                st.error(f"Error generando el mapa con tiles: {e}")
                st.info("El análisis se completó correctamente, pero no se pudo mostrar el mapa con tiles.")
            
            # DESCARGAS PERSISTENTES
            st.markdown("---")
            st.subheader("💾 Descargar Resultados")
            st.write("Descarga los resultados del análisis en formato CSV:")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename_cultivos = f"cultivos_por_campana_{timestamp}.csv"
                download_link_cultivos = get_download_link(df_cultivos, filename_cultivos, "📊 Descargar CSV - Cultivos por Campaña")
                st.markdown(download_link_cultivos, unsafe_allow_html=True)
            
            with col2:
                filename_rotacion = f"rotacion_cultivos_{timestamp}.csv"
                download_link_rotacion = get_download_link(df_display, filename_rotacion, "🔄 Descargar CSV - Rotación de Cultivos")
                st.markdown(download_link_rotacion, unsafe_allow_html=True)
            
            with col3:
                # Generar código de Earth Engine
                codigo_ee = generar_codigo_earth_engine_visor(aoi)
                filename_codigo = f"earth_engine_visor_{timestamp}.js"
                
                # Crear enlace de descarga para el código JS
                b64_codigo = base64.b64encode(codigo_ee.encode()).decode()
                download_link_codigo = f"""
                <a href="data:text/javascript;base64,{b64_codigo}" download="{filename_codigo}">
                    <button style="
                        background-color: #ff6b35;
                        border: none;
                        color: white;
                        padding: 8px 16px;
                        text-align: center;
                        text-decoration: none;
                        display: inline-block;
                        font-size: 14px;
                        margin: 4px 2px;
                        cursor: pointer;
                        border-radius: 4px;
                    ">🗺️ Código Earth Engine</button>
                </a>
                """
                st.markdown(download_link_codigo, unsafe_allow_html=True)
                st.caption("📝 Úsalo en Google Earth Engine Code Editor")
            
            # RESUMEN FINAL PERSISTENTE
            st.subheader("📈 Resumen por Campaña")
            pivot_summary = df_cultivos.pivot_table(
                index='Cultivo', 
                columns='Campaña', 
                values='Área (ha)', 
                aggfunc='sum', 
                fill_value=0
            )
            pivot_summary['Total'] = pivot_summary.sum(axis=1)
            pivot_filtered = pivot_summary[pivot_summary['Total'] > 0].sort_values('Total', ascending=False)
            st.dataframe(pivot_filtered, use_container_width=True)
            
            # Mensaje final
            st.markdown("---")
            st.success("✅ **Todos los resultados están listos y disponibles para descarga**")
            st.info("💡 **Tip**: Los resultados permanecen visibles. Puedes cambiar la campaña en el mapa libremente.")
            
            # Botón para limpiar resultados
            if st.button("🗑️ Limpiar Resultados", help="Borra los resultados para hacer un nuevo análisis"):
                st.session_state.analisis_completado = False
                st.session_state.resultados_analisis = None
                st.rerun()
    
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        🌾 Análisis de Rotación de Cultivos | Powered by Google Earth Engine & Streamlit
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 