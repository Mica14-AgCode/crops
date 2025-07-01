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
    """
    Función principal que analiza cultivos con Google Earth Engine
    Versión limpia sin mensajes técnicos para el usuario final
    """
    try:
        # Calcular área total del AOI en hectáreas
        area_total_aoi = aoi.geometry().transform('EPSG:5345', 1).area(1).divide(10000)
        area_total = area_total_aoi.getInfo()
        
        # Configurar contenedores persistentes para mostrar información esencial
        container_progreso = st.container()
        container_resultados = st.container()
        
        with container_progreso:
            progress_bar = st.progress(0.0)
            status_text = st.empty()
        
        # Paleta de colores oficial para visualización
        paleta_oficial = [
            '646b63',  # 0: Sin datos / barbecho
            '646b63',  # 1-5: Reservados
            'ffffff',  # 6: Trigo
            'ff6347',  # 7-9: Reservados  
            '0042ff',  # 10: Maíz
            '339820',  # 11: Soja 1ra
            'ffff00',  # 12: Girasol
            'f022db',  # 13: Poroto
            'a32102',  # 14: Caña de azúcar
            'b7b9bd',  # 15: Algodón
            'ffa500',  # 16: Maní
            '1d1e33',  # 17: Arroz
            'ff0000',  # 18: Sorgo GR
            'ffff00',  # 19: Girasol-CV
            '646b63',  # 20: Barbecho
            'e6f0c2',  # 21: No agrícola
            'e6f0c2',  # 22: No agrícola
            'ff6347',  # 23-25: Reservados
            '8a2be2',  # 26: Papa
            'ff6347',  # 27: Reservado
            '800080',  # 28: Verdeo de Sorgo
            'ff6347',  # 29: Reservado
            'd2b48c',  # 30: Tabaco
            '87ceeb',  # 31: CI-Maíz 2da
            '90ee90'   # 32: CI-Soja 2da
        ]
        
        status_text.text("⚡ Cargando capas de cultivos...")
        progress_bar.progress(0.1)
        
        # Cargar capas de todas las campañas
        capas = {}
        tiles_urls = {}
        campanas = ['19-20', '20-21', '21-22', '22-23', '23-24']
        
        # Mapear campañas a assets
        asset_map = {
            '19-20': {'inv': 'inv19', 'ver': 'ver20'},
            '20-21': {'inv': 'inv20', 'ver': 'ver21'},
            '21-22': {'inv': 'inv21', 'ver': 'ver22'},
            '22-23': {'inv': 'inv22', 'ver': 'ver23'},
            '23-24': {'inv': 'inv23', 'ver': 'ver24'}
        }
        
        for i, campana in enumerate(campanas):
            try:
                inv_name = asset_map[campana]['inv']
                ver_name = asset_map[campana]['ver']
                
                inv_asset = ee.Image(f'projects/carbide-kayak-459911-n3/assets/{inv_name}')
                ver_asset = ee.Image(f'projects/carbide-kayak-459911-n3/assets/{ver_name}')
                
                inv_asset_projected = inv_asset.reproject('EPSG:5345', None, 30)
                ver_asset_projected = ver_asset.reproject('EPSG:5345', None, 30)
                
                inv_aoi = inv_asset_projected.clip(aoi.geometry())
                ver_aoi = ver_asset_projected.clip(aoi.geometry())
                
                # Crear expresión combinada según campaña
                if campana == '19-20':
                    capa_combinada = ee.Image().expression(
                        '(verano == 10 && (invierno == 0 || invierno == 6)) ? 31 : ' +
                        '(verano == 11 && (invierno == 0 || invierno == 6)) ? 32 : ' +
                        '(verano == 10) ? 10 : ' + '(verano == 11) ? 11 : ' +
                        '(verano == 14) ? 14 : ' + '(verano == 19) ? 19 : ' + 'verano',
                        {'verano': ver_aoi, 'invierno': inv_aoi}
                    )
                elif campana == '20-21':
                    capa_combinada = ee.Image().expression(
                        '(verano == 10 && (invierno == 0 || invierno == 16 || invierno == 24)) ? 31 : ' +
                        '(verano == 11 && (invierno == 0 || invierno == 16 || invierno == 24)) ? 32 : ' +
                        '(verano == 10) ? 10 : ' + '(verano == 11) ? 11 : ' +
                        '(verano == 14) ? 14 : ' + '(verano == 19) ? 19 : ' + '(verano == 26) ? 26 : ' + 'verano',
                        {'verano': ver_aoi, 'invierno': inv_aoi}
                    )
                else:
                    capa_combinada = ee.Image().expression(
                        '(verano == 10 && (invierno == 6 || invierno == 16 || invierno == 24)) ? 31 : ' +
                        '(verano == 11 && (invierno == 6 || invierno == 16 || invierno == 24)) ? 32 : ' +
                        '(verano == 10) ? 10 : ' + '(verano == 11) ? 11 : ' +
                        '(invierno == 19 || verano == 14) ? 14 : ' + '(verano == 19) ? 19 : ' +
                        '(verano == 26) ? 26 : ' + 'verano',
                        {'verano': ver_aoi, 'invierno': inv_aoi}
                    )
                
                capas[campana] = capa_combinada
                
                # Generar tiles para visualización
                try:
                    vis_params = {'min': 0, 'max': 32, 'palette': paleta_oficial}
                    map_id = capa_combinada.getMapId(vis_params)
                    
                    # Acceso correcto a tiles
                    if 'tile_fetcher' in map_id and hasattr(map_id['tile_fetcher'], 'url_format'):
                        tiles_urls[campana] = map_id['tile_fetcher'].url_format
                    elif 'urlTemplate' in map_id:
                        tiles_urls[campana] = map_id['urlTemplate']
                        
                except:
                    # Método alternativo silencioso
                    try:
                        vis_image = capa_combinada.visualize(**vis_params)
                        simple_map_id = vis_image.getMapId({})
                        if 'tile_fetcher' in simple_map_id:
                            tiles_urls[campana] = simple_map_id['tile_fetcher'].url_format
                    except:
                        pass
                
            except:
                continue
            
            progress_bar.progress(0.1 + (i + 1) / len(campanas) * 0.3)
        
        status_text.text("📊 Calculando áreas por cultivo...")
        progress_bar.progress(0.4)
        
        # Configuración de cultivos por campaña
        cultivos_por_campana = {
            '19-20': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 14: 'Caña de azúcar', 15: 'Algodón', 16: 'Maní', 17: 'Arroz', 18: 'Sorgo GR', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '20-21': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 14: 'Caña de azúcar', 15: 'Algodón', 16: 'Maní', 17: 'Arroz', 18: 'Sorgo GR', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 26: 'Papa', 28: 'Verdeo de Sorgo', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '21-22': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 14: 'Caña de azúcar', 15: 'Algodón', 16: 'Maní', 17: 'Arroz', 18: 'Sorgo GR', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 26: 'Papa', 28: 'Verdeo de Sorgo', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '22-23': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 14: 'Caña de azúcar', 15: 'Algodón', 16: 'Maní', 17: 'Arroz', 18: 'Sorgo GR', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 26: 'Papa', 28: 'Verdeo de Sorgo', 30: 'Tabaco', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'},
            '23-24': {10: 'Maíz', 11: 'Soja 1ra', 12: 'Girasol', 13: 'Poroto', 14: 'Caña de azúcar', 15: 'Algodón', 16: 'Maní', 17: 'Arroz', 18: 'Sorgo GR', 19: 'Girasol-CV', 21: 'No agrícola', 22: 'No agrícola', 26: 'Papa', 28: 'Verdeo de Sorgo', 30: 'Tabaco', 31: 'CI-Maíz 2da', 32: 'CI-Soja 2da'}
        }
        
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
                            
                        except:
                            continue
                    
                    progress_bar.progress(0.4 + (j + 1) / len(campanas) * 0.5)
                    
                except:
                    continue
        
        status_text.text("✅ Análisis completado!")
        progress_bar.progress(1.0)
        
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
    Versión limpia para usuarios finales
    """
    
    # MEJORAR: Obtener centro y bounds del AOI de forma más precisa
    try:
        # ARREGLO: Agregar maxError para evitar el error de bounds
        aoi_bounds = aoi.geometry().bounds(maxError=1)
        bounds_info = aoi_bounds.getInfo()
        
        # Extraer coordenadas de bounds [lon_min, lat_min, lon_max, lat_max]
        coords = bounds_info["coordinates"][0]
        lon_min = min([c[0] for c in coords])
        lon_max = max([c[0] for c in coords])
        lat_min = min([c[1] for c in coords])
        lat_max = max([c[1] for c in coords])
        
        # Centro más preciso
        center_lat = (lat_min + lat_max) / 2
        center_lon = (lon_min + lon_max) / 2
        
        # Calcular zoom apropiado basado en el tamaño del AOI
        lat_diff = lat_max - lat_min
        lon_diff = lon_max - lon_min
        max_diff = max(lat_diff, lon_diff)
        
        # Zoom dinámico basado en el tamaño
        if max_diff < 0.01:  # Muy pequeño
            zoom_level = 16
        elif max_diff < 0.02:  # Pequeño
            zoom_level = 15
        elif max_diff < 0.05:  # Mediano
            zoom_level = 14
        elif max_diff < 0.1:   # Grande
            zoom_level = 13
        else:  # Muy grande
            zoom_level = 12
            
    except Exception as e:
        # MÉTODO ALTERNATIVO: Usar centroide del AOI
        try:
            centroide = aoi.geometry().centroid(maxError=1)
            centroide_coords = centroide.getInfo()['coordinates']
            center_lon, center_lat = centroide_coords[0], centroide_coords[1]
            zoom_level = 15  # Zoom medio como respaldo
            bounds_info = None
        except:
            center_lat, center_lon = -34.0, -60.0
            zoom_level = 14
            bounds_info = None
    
    # Crear mapa base con mejor centrado
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
        
        # MEJORAR: Ajustar el mapa automáticamente a los bounds del AOI
        if bounds_info:
            try:
                coords = bounds_info["coordinates"][0]
                lats = [c[1] for c in coords]
                lons = [c[0] for c in coords]
                
                # Fit bounds con padding
                m.fit_bounds(
                    [[min(lats), min(lons)], [max(lats), max(lons)]],
                    padding=[20, 20]
                )
            except:
                pass
            
    except:
        pass
    
    # LEYENDA ARREGLADA Y VISIBLE
    df_campana = df_resultados[df_resultados['Campaña'] == campana_seleccionada]
    
    # Colores para la leyenda (mismos que en Earth Engine)
    colores_cultivos = {
        'Maíz': '#0042ff', 'Soja 1ra': '#339820', 'Girasol': '#FFFF00', 'Poroto': '#f022db',
        'Algodón': '#b7b9bd', 'Maní': '#FFA500', 'Arroz': '#1d1e33', 'Sorgo GR': '#FF0000',
        'Caña de azúcar': '#a32102', 'Barbecho': '#646b63', 'No agrícola': '#e6f0c2',
        'Papa': '#8A2BE2', 'Verdeo de Sorgo': '#800080', 'Tabaco': '#D2B48C',
        'CI-Maíz 2da': '#87CEEB', 'CI-Soja 2da': '#90ee90', 'Girasol-CV': '#FFFF00'
    }
    
    # Calcular área total de la campaña
    area_total_campana = df_campana['Área (ha)'].sum()
    
    # LEYENDA COMPLETAMENTE REDISEÑADA - MAS VISIBLE
    legend_html = f"""
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 280px;
                background-color: rgba(255, 255, 255, 0.95); 
                z-index: 1000; 
                border: 2px solid #2E8B57; 
                border-radius: 8px;
                padding: 12px; 
                font-family: Arial, sans-serif;
                box-shadow: 0 4px 8px rgba(0,0,0,0.5);
                max-height: 80vh; 
                overflow-y: auto;">
                
    <h4 style="margin: 0 0 10px 0; text-align: center; 
               background-color: #2E8B57; color: white; 
               padding: 8px; border-radius: 4px; font-size: 14px;">
        🌾 Campaña {campana_seleccionada}
    </h4>
    
    <div style="margin-bottom: 12px; padding: 6px; background-color: #f0f8ff; 
                border-radius: 4px; text-align: center; font-weight: bold; font-size: 12px;">
        Total: {area_total_campana:.0f} hectáreas
    </div>
    """
    
    # Filtrar y ordenar cultivos con área > 0
    cultivos_con_area = df_campana[df_campana['Área (ha)'] > 0].sort_values('Área (ha)', ascending=False)
    
    # Agregar cada cultivo a la leyenda
    for idx, (_, row) in enumerate(cultivos_con_area.iterrows()):
        cultivo = row['Cultivo']
        area = row['Área (ha)']
        porcentaje = row['Porcentaje (%)']
        color = colores_cultivos.get(cultivo, '#999999')
        
        legend_html += f"""
        <div style="display: flex; align-items: center; margin: 6px 0; 
                    padding: 6px; background-color: {'#f9f9f9' if idx % 2 == 0 else '#ffffff'};
                    border-radius: 4px; border-left: 3px solid {color};">
            <div style="width: 20px; height: 15px; background-color: {color}; 
                        margin-right: 8px; border: 1px solid #333;
                        border-radius: 2px; flex-shrink: 0;"></div>
            <div style="flex-grow: 1; font-size: 11px;">
                <div style="font-weight: bold; color: #333; line-height: 1.2;">
                    {cultivo}
                </div>
                <div style="color: #666; line-height: 1.2;">
                    {area:.0f} ha ({porcentaje:.1f}%)
                </div>
            </div>
        </div>
        """
    
    # Pie de la leyenda más compacto
    legend_html += """
    <div style="margin-top: 10px; padding-top: 8px; 
                border-top: 1px solid #2E8B57; font-size: 10px; 
                color: #666; text-align: center;">
        📡 Google Earth Engine<br>
        🛰️ Mapa Nacional de Cultivos
    </div>
    </div>
    """
    
    # AGREGAR LA LEYENDA AL MAPA
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Control de capas
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m

def crear_visor_cultivos_interactivo(aoi, df_resultados):
    """Crea un mapa interactivo de cultivos como fallback"""
    
    # Calcular centro del mapa usando bounds del AOI
    try:
        aoi_geojson = aoi.getInfo()
        bounds_info = aoi.geometry().bounds().getInfo()
        
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
                    
                except:
                    pass
        
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
        
    except:
        pass
    
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

def main():
    # CSS Responsive para móviles
    st.markdown("""
    <style>
    /* Responsive design para móviles */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        .stSelectbox > div > div {
            font-size: 14px;
        }
        
        .metric-container {
            text-align: center !important;
        }
        
        .stColumns > div {
            padding: 0.5rem !important;
        }
        
        /* Hacer botones más grandes en móvil */
        .stButton > button {
            width: 100% !important;
            padding: 0.75rem !important;
            font-size: 16px !important;
        }
        
        /* Mejorar tablas en móvil */
        .dataframe {
            font-size: 12px !important;
        }
        
        /* Sidebar responsive */
        .css-1d391kg {
            padding-top: 1rem !important;
        }
    }
    
    /* Estilo general mejorado */
    .upload-section {
        background-color: #f0f8ff;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #0066cc;
        margin: 1rem 0;
    }
    
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #e9ecef;
    }
    
    /* Mejorar apariencia de métricas */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Centrar contenido en móviles */
    @media (max-width: 480px) {
        h1, h2, h3 {
            text-align: center !important;
        }
        
        .stSelectbox {
            margin-bottom: 1rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
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
        
        # Métricas principales - Responsive
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)
        
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
            
            # Dropdown para seleccionar campaña - Responsive
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
                    
                    # Mostrar el mapa - Responsive height
                    altura_mapa = 400 if st.container().width < 768 else 500
                    map_data = st_folium(mapa_tiles, width=None, height=altura_mapa, key="mapa_persistente")
                    
                    st.success("✅ **Mapa con píxeles reales de Google Earth Engine**")
                    
                    # Ayuda responsive para usar el mapa
                    with st.expander("💡 Cómo usar el mapa", expanded=False):
                        st.markdown("""
                        **🎨 Píxeles de colores**: Cada color representa un cultivo específico  
                        **🗓️ Cambiar campaña**: Usa el dropdown arriba para ver otros años  
                        **🔍 Zoom**: Toca dos veces o usa los controles para acercar/alejar  
                        **🗺️ Capas**: Usa el control de capas (esquina superior derecha) para cambiar vista satelital/mapa  
                        **📊 Leyenda**: Área y porcentaje de cada cultivo (esquina superior derecha del mapa)
                        """)
                    
                else:
                    st.warning("⚠️ No hay tiles disponibles para esta campaña")
                    # Fallback al visor anterior
                    mapa_cultivos = crear_visor_cultivos_interactivo(aoi, df_cultivos)
                    altura_mapa = 400 if st.container().width < 768 else 500
                    map_data = st_folium(mapa_cultivos, width=None, height=altura_mapa, key="mapa_fallback")
                
            except Exception as e:
                st.error(f"Error generando el mapa: {e}")
                st.info("El análisis se completó correctamente, pero no se pudo mostrar el mapa con tiles.")
            
            # DESCARGAS LIMPIAS Y CLARAS
            st.markdown("---")
            st.subheader("💾 Descargar Resultados")
            st.write("Descarga los resultados del análisis en formato CSV:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename_hectareas = f"cultivos_hectareas_{timestamp}.csv"
                download_link_hectareas = get_download_link(df_cultivos, filename_hectareas, "📊 Descargar CSV - Hectáreas por Cultivo")
                st.markdown(download_link_hectareas, unsafe_allow_html=True)
                st.caption("📄 Contiene: Cultivo, Campaña, Área en hectáreas")
            
            with col2:
                filename_porcentajes = f"cultivos_porcentajes_{timestamp}.csv"
                download_link_porcentajes = get_download_link(df_display, filename_porcentajes, "🔄 Descargar CSV - Porcentajes de Rotación")
                st.markdown(download_link_porcentajes, unsafe_allow_html=True)
                st.caption("📄 Contiene: Rotación en porcentajes por campaña")
            
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