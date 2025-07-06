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
import re
import requests
import zipfile
from io import BytesIO

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
    /* Ocultar elementos de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Logo VISU - DISEÑO ELEGANTE QUE YA FUNCIONA */
    .visu-logo-container {
        text-align: center;
        margin: 20px 0 30px 0;
        padding: 20px;
    }
    
    .minimal-container {
        display: inline-block;
        position: relative;
    }
    
    .visu-minimal {
        font-size: 60px;
        font-weight: 300;
        letter-spacing: 15px;
        color: #C0C0C0;
        margin-bottom: 10px;
        margin-left: 15px; /* Compensar el letter-spacing */
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    .eye-underline {
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, transparent 0%, #00D2BE 20%, #00D2BE 80%, transparent 100%);
        position: relative;
    }
    
    .eye-dot {
        width: 15px;
        height: 15px;
        background: #00D2BE;
        border-radius: 50%;
        position: absolute;
        top: -6px;
        left: 50%;
        transform: translateX(-50%);
        box-shadow: 0 0 20px #00D2BE;
    }
    
    .tagline {
        font-size: 16px;
        color: #C0C0C0;
        letter-spacing: 2px;
        margin-top: 15px;
        font-weight: 300;
    }
    
    /* Responsive design para móviles */
    @media (max-width: 768px) {
        .visu-minimal {
            font-size: 45px;
            letter-spacing: 10px;
            margin-left: 10px;
        }
        
        .tagline {
            font-size: 14px;
            letter-spacing: 1px;
        }
        
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
        
        /* MEJORAR FILE UPLOADER EN MÓVIL - FORZADO NEGRO */
        [data-testid="stFileUploader"] {
            background: linear-gradient(135deg, #2a2a2a, #1a1a1a) !important;
            border: 3px dashed #00D2BE !important;
            border-radius: 15px !important;
            padding: 20px !important;
            text-align: center !important;
        }
        
        [data-testid="stFileUploader"] label {
            font-size: 18px !important;
            font-weight: bold !important;
            color: #00D2BE !important;
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
    
    /* MEJORAR FILE UPLOADER EN GENERAL - FORZADO NEGRO */
    [data-testid="stFileUploader"] {
        background: linear-gradient(135deg, #2a2a2a, #1a1a1a) !important;
        border: 3px dashed #00D2BE !important;
        border-radius: 15px !important;
        padding: 25px !important;
        text-align: center !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stFileUploader"]:hover {
        background: linear-gradient(135deg, #3a3a3a, #2a2a2a) !important;
        border-color: #00B8A8 !important;
        transform: scale(1.02) !important;
    }
    
    [data-testid="stFileUploader"] label {
        font-size: 20px !important;
        font-weight: bold !important;
        color: #00D2BE !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3) !important;
    }
    
    /* FORZAR TODOS LOS ELEMENTOS DEL FILE UPLOADER */
    [data-testid="stFileUploader"] * {
        background-color: transparent !important;
        color: #ffffff !important;
    }
    
    [data-testid="stFileUploader"] div {
        background-color: transparent !important;
        color: #ffffff !important;
    }
    
    [data-testid="stFileUploader"] section {
        background-color: transparent !important;
        color: #ffffff !important;
    }
    
    [data-testid="stFileUploader"] small {
        color: #cccccc !important;
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

# AVISOS ELIMINADOS - MOVIDOS AL MAIN()

# Inicialización de Earth Engine
@st.cache_resource
def init_earth_engine():
    """Inicializa Google Earth Engine con Service Account"""
    try:
        proyecto_id = "carbide-kayak-459911-n3"
        
        # Intentar autenticación con Service Account - SILENCIOSA
        if "google_credentials" in st.secrets:
            # Producción: usar Service Account desde Streamlit Secrets
            credentials = st.secrets["google_credentials"]
            ee.Initialize(ee.ServiceAccountCredentials(
                email=credentials["client_email"],
                key_data=json.dumps(dict(credentials))
            ), project=proyecto_id)
            
        elif 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            # Desarrollo: usar Service Account desde archivo local
            credentials_path = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
            ee.Initialize(ee.ServiceAccountCredentials(
                email=None,
                key_file=credentials_path
            ), project=proyecto_id)
            
        else:
            # Fallback: autenticación interactiva para desarrollo
            ee.Authenticate()
            ee.Initialize(project=proyecto_id)
        
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
        
        # 🎨 PALETA OFICIAL SINCRONIZADA - Earth Engine + Gráfico
        paleta_oficial = [
            '646b63',  # 0: Sin datos / barbecho
            '646b63',  # 1-5: Reservados
            'ffffff',  # 6: Trigo
            'ff6347',  # 7-9: Reservados  
            '0042ff',  # 10: Maíz - AZUL
            '339820',  # 11: Soja 1ra - VERDE
            'ffff00',  # 12: Girasol - AMARILLO
            'f022db',  # 13: Poroto - ROSA/FUCSIA
            'a32102',  # 14: Caña de azúcar - ROJO OSCURO
            'b7b9bd',  # 15: Algodón - GRIS CLARO
            'ffa500',  # 16: Maní - NARANJA
            '1d1e33',  # 17: Arroz - AZUL OSCURO
            'ff0000',  # 18: Sorgo GR - ROJO
            'a32102',  # 19: ⚠️ CORREGIDO: Girasol-CV/Caña → ROJO OSCURO (era amarillo)
            '646b63',  # 20: Barbecho - GRIS OSCURO
            'e6f0c2',  # 21: No agrícola - BEIGE CLARO
            'e6f0c2',  # 22: No agrícola - BEIGE CLARO
            'ff6347',  # 23-25: Reservados
            '8a2be2',  # 26: Papa - VIOLETA
            'ff6347',  # 27: Reservado
            '800080',  # 28: Verdeo de Sorgo - MORADO
            'ff6347',  # 29: Reservado
            'd2b48c',  # 30: Tabaco - MARRÓN CLARO
            '87ceeb',  # 31: CI-Maíz 2da - AZUL CLARO/CELESTE
            '90ee90'   # 32: CI-Soja 2da - VERDE CLARO/FLUOR
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
                
                # 🎨 FORZAR MÉTODO RGB QUE SÍ FUNCIONA
                try:
                    # 🔧 MÉTODO PRINCIPAL NO APLICA COLORES CORRECTAMENTE
                    # Aunque "funciona", los colores son incorrectos
                    raise Exception("🎯 FORZANDO método RGB que genera colores EXACTOS")
                except Exception as e:
                    # 🎨 MÉTODO RGB PARA COLORES EXACTOS
                    try:
                        
                        # 🎯 CREAR IMAGEN RGB CON COLORES GARANTIZADOS
                        # Convertir paleta hex a RGB
                        def hex_to_rgb(hex_color):
                            hex_color = hex_color.lstrip('#')
                            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                        
                        # 🎯 CREAR IMAGEN TRANSPARENTE (sin píxeles negros)
                        # Crear máscara de cultivos válidos
                        mascara_cultivos = capa_combinada.gt(0)  # Solo píxeles con cultivos
                        
                        # Mapeo ID → Color RGB exacto
                        colores_rgb_exactos = {
                            10: hex_to_rgb('#0042ff'),  # Maíz - Azul
                            11: hex_to_rgb('#339820'),  # Soja 1ra - Verde
                            12: hex_to_rgb('#FFFF00'),  # Girasol - Amarillo
                            13: hex_to_rgb('#f022db'),  # Poroto - Rosa
                            14: hex_to_rgb('#a32102'),  # Caña de azúcar - Rojo oscuro
                            15: hex_to_rgb('#b7b9bd'),  # Algodón - Gris claro
                            16: hex_to_rgb('#FFA500'),  # Maní - Naranja
                            17: hex_to_rgb('#1d1e33'),  # Arroz - Azul oscuro
                            18: hex_to_rgb('#FF0000'),  # Sorgo GR - Rojo
                            19: hex_to_rgb('#a32102'),  # Girasol-CV/Caña - Rojo oscuro
                            21: hex_to_rgb('#e6f0c2'),  # No agrícola - Beige
                            22: hex_to_rgb('#e6f0c2'),  # No agrícola - Beige
                            26: hex_to_rgb('#8A2BE2'),  # Papa - Violeta
                            28: hex_to_rgb('#800080'),  # Verdeo Sorgo - Morado
                            30: hex_to_rgb('#D2B48C'),  # Tabaco - Marrón claro
                            31: hex_to_rgb('#87CEEB'),  # CI-Maíz 2da - Azul claro
                            32: hex_to_rgb('#90ee90')   # CI-Soja 2da - Verde claro
                        }
                        
                        # Mapeo de colores optimizado
                        
                        # 🔧 CREAR IMAGEN RGB SIMPLIFICADA Y EFICIENTE
                        # Usar el método visualization con parámetros RGB específicos
                        imagen_rgb = capa_combinada.visualize(
                            min=0, 
                            max=32, 
                            palette=[f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}" for rgb in [
                                hex_to_rgb('646b63'),  # 0
                                hex_to_rgb('646b63'),  # 1
                                hex_to_rgb('646b63'),  # 2
                                hex_to_rgb('646b63'),  # 3
                                hex_to_rgb('646b63'),  # 4
                                hex_to_rgb('646b63'),  # 5
                                hex_to_rgb('ffffff'),  # 6
                                hex_to_rgb('ff6347'),  # 7
                                hex_to_rgb('ff6347'),  # 8
                                hex_to_rgb('ff6347'),  # 9
                                hex_to_rgb('0042ff'),  # 10 - Maíz
                                hex_to_rgb('339820'),  # 11 - Soja 1ra
                                hex_to_rgb('FFFF00'),  # 12 - Girasol
                                hex_to_rgb('f022db'),  # 13 - Poroto
                                hex_to_rgb('a32102'),  # 14 - Caña
                                hex_to_rgb('b7b9bd'),  # 15 - Algodón
                                hex_to_rgb('FFA500'),  # 16 - Maní
                                hex_to_rgb('1d1e33'),  # 17 - Arroz
                                hex_to_rgb('FF0000'),  # 18 - Sorgo
                                hex_to_rgb('a32102'),  # 19 - Girasol-CV/Caña
                                hex_to_rgb('646b63'),  # 20
                                hex_to_rgb('e6f0c2'),  # 21 - No agrícola
                                hex_to_rgb('e6f0c2'),  # 22 - No agrícola
                                hex_to_rgb('ff6347'),  # 23
                                hex_to_rgb('ff6347'),  # 24
                                hex_to_rgb('ff6347'),  # 25
                                hex_to_rgb('8A2BE2'),  # 26 - Papa
                                hex_to_rgb('ff6347'),  # 27
                                hex_to_rgb('800080'),  # 28 - Verdeo Sorgo
                                hex_to_rgb('ff6347'),  # 29
                                hex_to_rgb('D2B48C'),  # 30 - Tabaco
                                hex_to_rgb('87CEEB'),  # 31 - CI-Maíz
                                hex_to_rgb('90ee90')   # 32 - CI-Soja
                            ]]
                        )
                        
                        # Generar tiles de la imagen RGB personalizada
                        simple_map_id = imagen_rgb.getMapId({})
                        
                        if 'tile_fetcher' in simple_map_id:
                            tiles_urls[campana] = simple_map_id['tile_fetcher'].url_format
                        elif 'urlTemplate' in simple_map_id:
                            tiles_urls[campana] = simple_map_id['urlTemplate']
                            
                    except Exception as e2:
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
            # Cultivos con ID fijo en todas las campañas
            "Maíz": "#0042ff",           # ID 10 - Azul
            "Soja 1ra": "#339820",       # ID 11 - Verde  
            "Girasol": "#FFFF00",        # ID 12 - Amarillo
            "Poroto": "#f022db",         # ID 13 - Rosa/Fucsia
            "Algodón": "#b7b9bd",        # ID 15 - Gris claro
            "Maní": "#FFA500",           # ID 16 - Naranja
            "Arroz": "#1d1e33",          # ID 17 - Azul oscuro
            "Sorgo GR": "#FF0000",       # ID 18 - Rojo
            "Barbecho": "#646b63",       # ID 21 - Gris oscuro
            "No agrícola": "#e6f0c2",    # ID 22 - Beige claro
            "No Agrícola": "#e6f0c2",    # ID 22 - Beige claro
            "Papa": "#8A2BE2",           # ID 26 - Violeta
            "Verdeo de Sorgo": "#800080", # ID 28 - Morado
            "Tabaco": "#D2B48C",         # ID 30 - Marrón claro
            "CI-Maíz 2da": "#87CEEB",    # ID 31 - Azul claro/celeste
            "CI-Soja 2da": "#90ee90",    # ID 32 - Verde claro/fluor
            "Soja 2da": "#90ee90",       # ID 32 - Verde claro/fluor
            
            # Cultivos que CAMBIAN de ID según campaña - TODOS usan ID 19 → color #a32102
            "Girasol-CV": "#a32102",     # ID 19 en campañas 19-20, 20-21 - Rojo oscuro
            "Caña de azúcar": "#a32102", # ID 19 en campañas 21-22, 22-23, 23-24 - Rojo oscuro
            "Caña de Azúcar": "#a32102", # ID 19 en campañas 21-22, 22-23, 23-24 - Rojo oscuro
            
            # Variantes de nombres que pueden aparecer
            "CI-Maíz": "#87CEEB",        # Variante de CI-Maíz 2da
            "C inv - Maíz 2da": "#87CEEB", # Variante de CI-Maíz 2da
            "CI-Soja": "#90ee90",        # Variante de CI-Soja 2da
            "C inv - Soja 2da": "#90ee90"  # Variante de CI-Soja 2da
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

def generar_kmz_desde_cuit(poligonos_data, nombre_archivo="campos"):
    """Genera un archivo KMZ desde datos de polígonos de CUIT"""
    try:
        # Crear contenido KML
        kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>Campos - {nombre_archivo}</name>
  <Style id="campoStyle">
    <LineStyle>
      <color>ff0000ff</color>
      <width>3</width>
    </LineStyle>
    <PolyStyle>
      <color>7f0000ff</color>
    </PolyStyle>
  </Style>
"""
        
        for i, campo in enumerate(poligonos_data):
            coords = campo.get('coords', [])
            if coords:
                kml_content += f"""
  <Placemark>
    <name>Campo {i+1}: {campo.get('titular', 'Sin titular')}</name>
    <description>
      Localidad: {campo.get('localidad', 'Sin información')}
      Superficie: {campo.get('superficie', 0):.1f} ha
    </description>
    <styleUrl>#campoStyle</styleUrl>
    <Polygon>
      <outerBoundaryIs>
        <LinearRing>
          <coordinates>
"""
                for coord in coords:
                    kml_content += f"{coord[0]},{coord[1]},0\n"
                
                kml_content += """
          </coordinates>
        </LinearRing>
      </outerBoundaryIs>
    </Polygon>
  </Placemark>
"""
        
        kml_content += "</Document></kml>"
        
        # Crear KMZ (ZIP con el KML)
        kmz_buffer = BytesIO()
        with zipfile.ZipFile(kmz_buffer, 'w', zipfile.ZIP_DEFLATED) as kmz:
            kmz.writestr("doc.kml", kml_content)
        
        kmz_buffer.seek(0)
        return kmz_buffer
        
    except Exception as e:
        st.error(f"Error generando KMZ: {e}")
        return None


def crear_mapa_con_tiles_engine(aoi, tiles_urls, df_resultados, cultivos_por_campana, campana_seleccionada):
    """
    Crea un mapa interactivo con tiles reales de Google Earth Engine
    Versión simplificada y robusta
    """
    
    # Centro por defecto (Argentina)
    center_lat, center_lon = -34.0, -60.0
    zoom_level = 14
    
    # Intentar obtener centro del AOI de forma segura
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
                    
                    # Zoom basado en el rango de coordenadas
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
        pass  # Usar valores por defecto
    
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
    
    # Agregar tiles de Earth Engine CON BARRA DESLIZANTE DE TRANSPARENCIA
    if campana_seleccionada in tiles_urls and tiles_urls[campana_seleccionada]:
        try:
            # 🎯 ORDEN CORRECTO: 100% → 70% → 50% → 30% (de mayor a menor transparencia)
            # ✅ SOLO 50% ACTIVO POR DEFECTO
            
            # 1. OPACO 100% (primero en la lista, NO activo)
            folium.raster_layers.TileLayer(
                tiles=tiles_urls[campana_seleccionada],
                attr='Google Earth Engine',
                name=f'🌾 Cultivos {campana_seleccionada} (100%)',
                overlay=True,  # ✅ ARREGLADO: Ahora puede coexistir con satelital
                control=True,
                opacity=1.0
            ).add_to(m)
            
            # 2. MEDIO 70% (NO activo)
            folium.raster_layers.TileLayer(
                tiles=tiles_urls[campana_seleccionada],
                attr='Google Earth Engine',
                name=f'🌾 Cultivos {campana_seleccionada} (70%)',
                overlay=True,  # ✅ ARREGLADO: Ahora puede coexistir con satelital
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
                overlay=True,  # ✅ ARREGLADO: Ahora puede coexistir con satelital
                control=True,
                opacity=0.3
            ).add_to(m)
            
            # Agregar barra de transparencia ULTRA VISIBLE
            transparency_control = """
            <div id="transparency-control" style="
                position: fixed !important; 
                bottom: 30px !important; 
                left: 30px !important; 
                background: rgba(255, 255, 255, 0.98) !important; 
                padding: 20px !important; 
                border-radius: 15px !important;
                box-shadow: 0 8px 25px rgba(0,0,0,0.5) !important;
                z-index: 99999 !important; 
                font-family: Arial, sans-serif !important;
                min-width: 250px !important;
                border: 3px solid #2E8B57 !important;
                backdrop-filter: blur(5px) !important;">
                
                <div style="margin-bottom: 12px !important; font-weight: bold !important; 
                           color: #2E8B57 !important; text-align: center !important; 
                           font-size: 14px !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.1) !important;">
                    🎨 Control de Transparencia
                </div>
                
                <div style="display: flex !important; align-items: center !important; gap: 15px !important;">
                    <span style="font-size: 14px !important; color: #666 !important;">👁️</span>
                    <input type="range" id="opacity-slider" min="0" max="100" value="70" 
                           style="flex: 1 !important; height: 8px !important; border-radius: 10px !important; 
                                  background: linear-gradient(to right, #ff6b6b, #4ecdc4, #45b7d1) !important;
                                  outline: none !important; cursor: pointer !important;
                                  -webkit-appearance: none !important; appearance: none !important;">
                    <span style="font-size: 14px !important; color: #666 !important;">🌾</span>
                </div>
                
                <div style="text-align: center !important; margin-top: 8px !important; 
                           font-size: 13px !important; color: #2E8B57 !important; font-weight: bold !important;">
                    <span id="opacity-value">70%</span> Opacidad
                </div>
                
                <div style="text-align: center !important; margin-top: 5px !important; 
                           font-size: 10px !important; color: #888 !important;">
                    Desliza para ajustar transparencia
                </div>
            </div>
            
            <style>
            #opacity-slider::-webkit-slider-thumb {
                appearance: none !important;
                width: 25px !important;
                height: 25px !important;
                border-radius: 50% !important;
                background: #2E8B57 !important;
                cursor: pointer !important;
                border: 3px solid white !important;
                box-shadow: 0 3px 8px rgba(0,0,0,0.3) !important;
            }
            
            #opacity-slider::-moz-range-thumb {
                width: 25px !important;
                height: 25px !important;
                border-radius: 50% !important;
                background: #2E8B57 !important;
                cursor: pointer !important;
                border: 3px solid white !important;
                box-shadow: 0 3px 8px rgba(0,0,0,0.3) !important;
            }
            </style>
            
            <script>
            // Función de transparencia mejorada
            setTimeout(function() {
                var slider = document.getElementById('opacity-slider');
                var valueDisplay = document.getElementById('opacity-value');
                
                console.log('Inicializando control de transparencia...');
                
                if (slider && valueDisplay) {
                    slider.addEventListener('input', function() {
                        var opacity = this.value / 100;
                        valueDisplay.textContent = this.value + '%';
                        
                        console.log('Cambiando opacidad a:', opacity);
                        
                        // Método 1: Buscar por atribución Earth Engine
                        if (window.map && window.map._layers) {
                            Object.values(window.map._layers).forEach(function(layer) {
                                if (layer.options && 
                                    (layer.options.attribution === 'Google Earth Engine' ||
                                     layer.options.name && layer.options.name.includes('Cultivos'))) {
                                    if (layer.setOpacity) {
                                        layer.setOpacity(opacity);
                                        console.log('Opacidad aplicada a:', layer.options.name);
                                    }
                                }
                            });
                        }
                        
                        // Método 2: Buscar por clase CSS
                        var leafletLayers = document.querySelectorAll('.leaflet-tile-pane .leaflet-layer');
                        leafletLayers.forEach(function(layer, index) {
                            if (index > 0) { // Saltar capa base
                                layer.style.opacity = opacity;
                            }
                        });
                    });
                    
                    console.log('Control de transparencia configurado correctamente');
                } else {
                    console.log('Error: No se encontraron elementos de control');
                }
            }, 2000);
            </script>
            """
            m.get_root().html.add_child(folium.Element(transparency_control))
            
        except Exception as e:
            pass  # Si falla, continuar sin tiles
    
    # 🔥 CONTORNO ELIMINADO TEMPORALMENTE - SE AGREGA AL FINAL DEL MAPA
    
    # Crear leyenda con información de cultivos
    legend_added = False
    
    try:
        df_campana = df_resultados[df_resultados['Campaña'] == campana_seleccionada]
        
        if not df_campana.empty:
            # Colores para la leyenda - EXACTOS de la paleta oficial JavaScript
            colores_cultivos = {
                # Cultivos con ID fijo en todas las campañas
                "Maíz": "#0042ff",           # ID 10 - Azul
                "Soja 1ra": "#339820",       # ID 11 - Verde  
                "Girasol": "#FFFF00",        # ID 12 - Amarillo
                "Poroto": "#f022db",         # ID 13 - Rosa/Fucsia
                "Algodón": "#b7b9bd",        # ID 15 - Gris claro
                "Maní": "#FFA500",           # ID 16 - Naranja
                "Arroz": "#1d1e33",          # ID 17 - Azul oscuro
                "Sorgo GR": "#FF0000",       # ID 18 - Rojo
                "Barbecho": "#646b63",       # ID 21 - Gris oscuro
                "No agrícola": "#e6f0c2",    # ID 22 - Beige claro
                "No Agrícola": "#e6f0c2",    # ID 22 - Beige claro
                "Papa": "#8A2BE2",           # ID 26 - Violeta
                "Verdeo de Sorgo": "#800080", # ID 28 - Morado
                "Tabaco": "#D2B48C",         # ID 30 - Marrón claro
                "CI-Maíz 2da": "#87CEEB",    # ID 31 - Azul claro/celeste
                "CI-Soja 2da": "#90ee90",    # ID 32 - Verde claro/fluor
                "Soja 2da": "#90ee90",       # ID 32 - Verde claro/fluor
                
                # Cultivos que CAMBIAN de ID según campaña - TODOS usan ID 19 → color #a32102
                "Girasol-CV": "#a32102",     # ID 19 en campañas 19-20, 20-21 - Rojo oscuro
                "Caña de azúcar": "#a32102", # ID 19 en campañas 21-22, 22-23, 23-24 - Rojo oscuro
                "Caña de Azúcar": "#a32102", # ID 19 en campañas 21-22, 22-23, 23-24 - Rojo oscuro
                
                # Variantes de nombres que pueden aparecer
                "CI-Maíz": "#87CEEB",        # Variante de CI-Maíz 2da
                "C inv - Maíz 2da": "#87CEEB", # Variante de CI-Maíz 2da
                "CI-Soja": "#90ee90",        # Variante de CI-Soja 2da
                "C inv - Soja 2da": "#90ee90"  # Variante de CI-Soja 2da
            }
            
            # Calcular área total
            try:
                area_total_campana = float(df_campana['Área (ha)'].sum())
            except:
                area_total_campana = 0
            
            # Crear leyenda HTML MEJORADA con CSS más fuerte
            legend_html = f"""
            <div id="legend-cultivos" style="position: fixed !important; 
                        top: 10px !important; right: 10px !important; 
                        width: 300px !important; min-width: 300px !important;
                        background-color: rgba(255, 255, 255, 0.98) !important; 
                        z-index: 9999 !important; 
                        border: 3px solid #2E8B57 !important; 
                        border-radius: 10px !important;
                        padding: 15px !important; 
                        font-family: Arial, sans-serif !important;
                        box-shadow: 0 8px 16px rgba(0,0,0,0.7) !important;
                        max-height: 85vh !important; 
                        overflow-y: auto !important;
                        backdrop-filter: blur(2px) !important;">
                        
            <h4 style="margin: 0 0 12px 0 !important; text-align: center !important; 
                       background: linear-gradient(135deg, #2E8B57, #3CB371) !important; 
                       color: white !important; 
                       padding: 10px !important; border-radius: 6px !important; 
                       font-size: 15px !important; font-weight: bold !important;
                       text-shadow: 1px 1px 2px rgba(0,0,0,0.3) !important;">
                🌾 Cultivos - Campaña {campana_seleccionada}
            </h4>
            
            <div style="margin-bottom: 15px !important; padding: 8px !important; 
                        background: linear-gradient(135deg, #f0f8ff, #e6f3ff) !important; 
                        border-radius: 6px !important; text-align: center !important; 
                        font-weight: bold !important; font-size: 13px !important;
                        border: 1px solid #4682B4 !important;">
                📊 Área Total: {area_total_campana:,.0f} hectáreas
            </div>
            """
            
            # Filtrar cultivos con área > 0 y ordenar
            try:
                cultivos_con_area = df_campana[df_campana['Área (ha)'] > 0].sort_values('Área (ha)', ascending=False)
                
                # Agregar cada cultivo a la leyenda
                for idx, (_, row) in enumerate(cultivos_con_area.iterrows()):
                    try:
                        cultivo = str(row['Cultivo'])
                        area = float(row['Área (ha)'])
                        porcentaje = float(row['Porcentaje (%)'])
                        color = colores_cultivos.get(cultivo, '#999999')
                        
                        bg_color = '#f9f9f9' if idx % 2 == 0 else '#ffffff'
                        
                        legend_html += f"""
                        <div style="display: flex !important; align-items: center !important; 
                                    margin: 8px 0 !important; padding: 8px !important; 
                                    background-color: {bg_color} !important;
                                    border-radius: 6px !important; 
                                    border-left: 4px solid {color} !important;
                                    border: 1px solid #e0e0e0 !important;
                                    transition: all 0.2s ease !important;">
                            <div style="width: 24px !important; height: 18px !important; 
                                        background-color: {color} !important; 
                                        margin-right: 10px !important; 
                                        border: 2px solid #333 !important;
                                        border-radius: 3px !important; 
                                        flex-shrink: 0 !important;
                                        box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;"></div>
                            <div style="flex-grow: 1 !important; font-size: 12px !important;">
                                <div style="font-weight: bold !important; color: #2c3e50 !important; 
                                            line-height: 1.3 !important; margin-bottom: 2px !important;">
                                    {cultivo}
                                </div>
                                <div style="color: #5a6c7d !important; line-height: 1.2 !important;
                                            font-size: 11px !important; font-weight: 500 !important;">
                                    🌾 {area:,.0f} ha • {porcentaje:.1f}%
                                </div>
                            </div>
                        </div>
                        """
                    except:
                        continue  # Saltar cultivos problemáticos
            except:
                # Si no hay cultivos, mostrar mensaje
                legend_html += """
                <div style="text-align: center; color: #666; padding: 10px;">
                    No hay cultivos detectados<br>para esta campaña
                </div>
                """
            
            # Pie de la leyenda con explicación de colores
            legend_html += """
            <div style="margin-top: 15px !important; padding: 10px !important; 
                        border-top: 2px solid #2E8B57 !important; 
                        background: linear-gradient(135deg, #f8f9fa, #e9ecef) !important;
                        border-radius: 6px !important; font-size: 10px !important; 
                        color: #495057 !important; text-align: center !important;">
                
                <div style="margin-bottom: 8px !important; font-weight: bold !important; 
                            color: #2E8B57 !important; font-size: 11px !important;">
                    📡 Google Earth Engine • 🛰️ Mapa Nacional de Cultivos
                </div>
                
                <div style="font-size: 9px !important; color: #6c757d !important; 
                            line-height: 1.3 !important; font-style: italic !important;">
                    ⚠️ Los colores en el mapa pueden diferir de esta leyenda.<br>
                    Los colores exactos están en el gráfico de rotación ⬇️
                </div>
                
                <div style="margin-top: 8px !important; font-size: 9px !important; 
                            color: #495057 !important; font-weight: 500 !important;">
                    💡 Usa el control de capas para cambiar transparencia
                </div>
            </div>
            </div>
            """
            
            # Agregar leyenda al mapa usando método más directo
            # Usar marco (iframe) para asegurar que la leyenda se muestre
            legend_element = folium.Element(legend_html)
            m.get_root().html.add_child(legend_element)
            
            # JavaScript adicional para asegurar visibilidad
            visibility_script = """
            <script>
            // Asegurar que la leyenda sea visible después de cargar el mapa
            setTimeout(function() {
                var legend = document.getElementById('legend-cultivos');
                if (legend) {
                    legend.style.display = 'block';
                    legend.style.position = 'fixed';
                    legend.style.top = '10px';
                    legend.style.right = '10px';
                    legend.style.zIndex = '9999';
                    legend.style.backgroundColor = 'rgba(255, 255, 255, 0.98)';
                    console.log('Leyenda forzada a ser visible');
                } else {
                    console.log('Leyenda no encontrada');
                }
            }, 1000);
            </script>
            """
            m.get_root().html.add_child(folium.Element(visibility_script))
            legend_added = True
        
    except Exception as e:
        legend_added = False
    
    # Si no se pudo agregar la leyenda completa, agregar una básica
    if not legend_added:
        try:
            basic_legend = f"""
            <div style="position: fixed !important; top: 10px !important; right: 10px !important; 
                        width: 280px !important; background-color: rgba(255, 255, 255, 0.98) !important; 
                        z-index: 9999 !important; border: 3px solid #dc3545 !important; 
                        border-radius: 10px !important; padding: 15px !important; 
                        font-family: Arial, sans-serif !important; 
                        box-shadow: 0 8px 16px rgba(0,0,0,0.7) !important;">
                        
                <h4 style="margin: 0 0 12px 0 !important; text-align: center !important; 
                           background: linear-gradient(135deg, #dc3545, #c82333) !important; 
                           color: white !important; padding: 10px !important; 
                           border-radius: 6px !important; font-size: 15px !important;">
                    ⚠️ Campaña {campana_seleccionada}
                </h4>
                
                <div style="margin-bottom: 15px !important; padding: 10px !important; 
                            background: linear-gradient(135deg, #fff3cd, #ffeaa7) !important; 
                            border-radius: 6px !important; text-align: center !important; 
                            font-weight: bold !important; font-size: 13px !important;
                            border: 1px solid #ffc107 !important; color: #856404 !important;">
                    🔄 Cargando información de cultivos...
                </div>
                
                <div style="text-align: center !important; color: #495057 !important; 
                            padding: 15px !important; font-size: 12px !important; 
                            line-height: 1.4 !important;">
                    Los datos de cultivos están<br>
                    disponibles en el análisis.<br><br>
                    📊 Consulta el gráfico de rotación<br>
                    para ver los colores exactos.
                </div>
                
                <div style="margin-top: 15px !important; padding: 10px !important; 
                            border-top: 2px solid #dc3545 !important; font-size: 10px !important; 
                            color: #6c757d !important; text-align: center !important;
                            background: linear-gradient(135deg, #f8f9fa, #e9ecef) !important;
                            border-radius: 6px !important;">
                    📡 Google Earth Engine • 🛰️ Mapa Nacional de Cultivos
                </div>
            </div>
            """
            m.get_root().html.add_child(folium.Element(basic_legend))
        except Exception as e:
            st.warning(f"Error creando leyenda de respaldo: {e}")
            pass
    
    # 🔥 MÉTODO COMPLETAMENTE NUEVO: HTML DIRECTO SUPERPUESTO
    try:
        aoi_geojson = aoi.getInfo()
        if aoi_geojson and 'features' in aoi_geojson:
            # Obtener las coordenadas del polígono
            feature = aoi_geojson['features'][0]
            if 'geometry' in feature and 'coordinates' in feature['geometry']:
                coords = feature['geometry']['coordinates'][0]
                
                # Convertir coordenadas a puntos para el mapa
                coord_strings = []
                for coord in coords:
                    coord_strings.append(f"{coord[1]},{coord[0]}")  # lat,lon para Leaflet
                
                # Crear coordenadas para JavaScript
                coords_js = str(coords).replace("'", '"')
                
                # Crear HTML superpuesto con JavaScript directo
                contorno_html = f"""
                <script>
                // MÉTODO JAVASCRIPT DIRECTO PARA DIBUJAR LÍMITES - EJECUTA DESPUÉS DE CARGAR EL MAPA
                setTimeout(function() {{
                    // Buscar el mapa en el window global
                    var mapObj = null;
                    for (var key in window) {{
                        if (key.startsWith('map_') && window[key] && window[key]._container) {{
                            mapObj = window[key];
                            break;
                        }}
                    }}
                    
                    if (mapObj) {{
                        console.log('🎯 Mapa encontrado, agregando contorno...');
                        
                        // Coordenadas del polígono (lat, lon)
                        var coords = {coords_js};
                        
                        // Convertir coordenadas de [lon, lat] a [lat, lon] para Leaflet
                        var leafletCoords = coords.map(function(coord) {{
                            return [coord[1], coord[0]];  // Intercambiar lon,lat a lat,lon
                        }});
                        
                        // CREAR POLÍGONO SÚPER VISIBLE
                        var polygon = L.polygon(leafletCoords, {{
                            color: '#FF0000',        // Rojo brillante
                            weight: 15,              // Súper grueso
                            opacity: 1.0,            // Completamente opaco
                            fillColor: '#FFFF00',    // Amarillo brillante
                            fillOpacity: 0.3,        // Semi-transparente
                            dashArray: '20, 10'      // Punteado visible
                        }});
                        
                        // Agregar al mapa
                        polygon.addTo(mapObj);
                        
                        // AGREGAR MARCADORES GIGANTES EN LAS ESQUINAS
                        for (var i = 0; i < leafletCoords.length; i += Math.max(1, Math.floor(leafletCoords.length/4))) {{
                            if (i < leafletCoords.length) {{
                                var marker = L.circleMarker(leafletCoords[i], {{
                                    radius: 20,
                                    color: '#FF0000',
                                    fillColor: '#FFFF00',
                                    fillOpacity: 1.0,
                                    weight: 8
                                }});
                                marker.addTo(mapObj);
                                marker.bindPopup('🔴 LÍMITE DEL CAMPO - PUNTO ' + (i+1));
                            }}
                        }}
                        
                        console.log('✅ CONTORNO AGREGADO CON JAVASCRIPT DIRECTO - ' + leafletCoords.length + ' puntos');
                    }} else {{
                        console.log('❌ No se encontró el mapa en window');
                        console.log('Keys en window:', Object.keys(window).filter(k => k.includes('map')));
                    }}
                }}, 3000);  // Esperar 3 segundos para asegurar que el mapa esté listo
                </script>
                """
                
                # Agregar el HTML al mapa
                m.get_root().html.add_child(folium.Element(contorno_html))
                
                # MÉTODO ADICIONAL: Marcadores enormes como fallback
                for i in [0, len(coords)//4, len(coords)//2, 3*len(coords)//4]:
                    if i < len(coords):
                        coord = coords[i]
                        folium.Marker(
                            location=[coord[1], coord[0]],
                            popup=f"🔴 LÍMITE CAMPO - PUNTO {i+1}",
                            icon=folium.Icon(color='red', icon='exclamation-sign', prefix='fa')
                        ).add_to(m)
                        
    except Exception as e:
        # Método de emergencia con marcadores gigantes
        try:
            bounds = aoi.geometry().bounds().getInfo()
            if bounds and 'coordinates' in bounds:
                coords = bounds['coordinates'][0]
                
                # Marcadores gigantes en todas las esquinas
                for i, coord in enumerate(coords[::max(1, len(coords)//4)]):
                    folium.Marker(
                        location=[coord[1], coord[0]],
                        popup=f"🚨 LÍMITE CAMPO EMERGENCIA {i+1}",
                        icon=folium.Icon(color='red', icon='warning', prefix='fa')
                    ).add_to(m)
                
        except:
            pass
    
    # Control de capas
    try:
        folium.LayerControl(collapsed=False).add_to(m)
    except:
        pass
    
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
    
    # Colores EXACTOS por nombre de cultivo (basado en tu JavaScript)
    colores_cultivos = {
        # Cultivos con ID fijo en todas las campañas
        "Maíz": "#0042ff",           # ID 10 - Azul
        "Soja 1ra": "#339820",       # ID 11 - Verde  
        "Girasol": "#FFFF00",        # ID 12 - Amarillo
        "Poroto": "#f022db",         # ID 13 - Rosa/Fucsia
        "Algodón": "#b7b9bd",        # ID 15 - Gris claro
        "Maní": "#FFA500",           # ID 16 - Naranja
        "Arroz": "#1d1e33",          # ID 17 - Azul oscuro
        "Sorgo GR": "#FF0000",       # ID 18 - Rojo
        "Barbecho": "#646b63",       # ID 21 - Gris oscuro
        "No agrícola": "#e6f0c2",    # ID 22 - Beige claro
        "No Agrícola": "#e6f0c2",    # ID 22 - Beige claro
        "Papa": "#8A2BE2",           # ID 26 - Violeta
        "Verdeo de Sorgo": "#800080", # ID 28 - Morado
        "Tabaco": "#D2B48C",         # ID 30 - Marrón claro
        "CI-Maíz 2da": "#87CEEB",    # ID 31 - Azul claro/celeste
        "CI-Soja 2da": "#90ee90",    # ID 32 - Verde claro/fluor
        "Soja 2da": "#90ee90",       # ID 32 - Verde claro/fluor
        
        # Cultivos que CAMBIAN de ID según campaña - TODOS usan ID 19 → color #a32102
        "Girasol-CV": "#a32102",     # ID 19 en campañas 19-20, 20-21 - Rojo oscuro
        "Caña de azúcar": "#a32102", # ID 19 en campañas 21-22, 22-23, 23-24 - Rojo oscuro
        "Caña de Azúcar": "#a32102", # ID 19 en campañas 21-22, 22-23, 23-24 - Rojo oscuro
        
        # Variantes de nombres que pueden aparecer
        "CI-Maíz": "#87CEEB",        # Variante de CI-Maíz 2da
        "C inv - Maíz 2da": "#87CEEB", # Variante de CI-Maíz 2da
        "CI-Soja": "#90ee90",        # Variante de CI-Soja 2da
        "C inv - Soja 2da": "#90ee90"  # Variante de CI-Soja 2da
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
    
    # 🔥 CONTORNO FALLBACK ELIMINADO (YA HAY UNO ARRIBA)
    
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

# =====================================================================
# FUNCIONES PARA CONSULTA POR CUIT
# =====================================================================

# Configuraciones para API SENASA
API_BASE_URL = "https://aps.senasa.gob.ar/restapiprod/servicios/renspa"
TIEMPO_ESPERA = 0.5

def normalizar_cuit(cuit):
    """Normaliza un CUIT a formato XX-XXXXXXXX-X"""
    cuit_limpio = cuit.replace("-", "")
    
    if len(cuit_limpio) != 11:
        raise ValueError(f"CUIT inválido: {cuit}. Debe tener 11 dígitos.")
    
    return f"{cuit_limpio[:2]}-{cuit_limpio[2:10]}-{cuit_limpio[10]}"

def obtener_datos_por_cuit(cuit):
    """Obtiene todos los campos asociados a un CUIT"""
    try:
        url_base = f"{API_BASE_URL}/consultaPorCuit"
        
        todos_campos = []
        offset = 0
        limit = 10
        has_more = True
        
        while has_more:
            url = f"{url_base}?cuit={cuit}&offset={offset}"
            
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                resultado = response.json()
                
                if 'items' in resultado and resultado['items']:
                    todos_campos.extend(resultado['items'])
                    has_more = resultado.get('hasMore', False)
                    offset += limit
                else:
                    has_more = False
            
            except Exception as e:
                has_more = False
                
            time.sleep(TIEMPO_ESPERA)
        
        return todos_campos
    
    except Exception as e:
        return []

def consultar_campo_detalle(renspa):
    """Consulta los detalles de un campo específico para obtener el polígono"""
    try:
        url = f"{API_BASE_URL}/consultaPorNumero?numero={renspa}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        return None

def extraer_coordenadas_senasa(poligono_str):
    """Extrae coordenadas de un string de polígono de SENASA"""
    if not poligono_str or not isinstance(poligono_str, str):
        return None
    
    coord_pattern = r'\(([-\d\.]+),([-\d\.]+)\)'
    coord_pairs = re.findall(coord_pattern, poligono_str)
    
    if not coord_pairs:
        return None
    
    coords_geojson = []
    for lat_str, lon_str in coord_pairs:
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            coords_geojson.append([lon, lat])
        except ValueError:
            continue
    
    if len(coords_geojson) >= 3:
        if coords_geojson[0] != coords_geojson[-1]:
            coords_geojson.append(coords_geojson[0])
        
        return coords_geojson
    
    return None

def procesar_campos_cuit(cuit, solo_activos=True):
    """Procesa campos de un CUIT y extrae polígonos para análisis"""
    try:
        cuit_normalizado = normalizar_cuit(cuit)
        campos = obtener_datos_por_cuit(cuit_normalizado)
        
        if not campos:
            return []
        
        # Filtrar según la opción seleccionada
        if solo_activos:
            campos_a_procesar = [c for c in campos if c.get('fecha_baja') is None]
        else:
            campos_a_procesar = campos
        
        # Procesar polígonos
        poligonos_data = []
        
        for i, campo in enumerate(campos_a_procesar):
            renspa = campo['renspa']
            
            # Primero intentar con los datos que ya tenemos
            coords = None
            if 'poligono' in campo and campo['poligono']:
                coords = extraer_coordenadas_senasa(campo['poligono'])
            
            # Si no tenemos polígono, consultar detalle
            if not coords:
                resultado_detalle = consultar_campo_detalle(renspa)
                if resultado_detalle and 'items' in resultado_detalle and resultado_detalle['items']:
                    item_detalle = resultado_detalle['items'][0]
                    if 'poligono' in item_detalle and item_detalle['poligono']:
                        coords = extraer_coordenadas_senasa(item_detalle['poligono'])
                
                time.sleep(TIEMPO_ESPERA)
            
            if coords:
                poligono_data = {
                    'nombre': f"Campo_{i+1}_{campo.get('titular', 'Sin_titular')}",
                    'coords': coords,
                    'numero': i + 1,
                    'archivo_origen': f'CUIT_{cuit_normalizado}',
                    'kml_origen': f'Campo_{renspa}',
                    'titular': campo.get('titular', ''),
                    'localidad': campo.get('localidad', ''),
                    'superficie': campo.get('superficie', 0),
                    'renspa': renspa
                }
                poligonos_data.append(poligono_data)
        
        return poligonos_data
    
    except Exception as e:
        st.error(f"Error procesando CUIT {cuit}: {e}")
        return []

def analizar_gsw_ano(geometry, ano, gsw):
    """
    Analiza un año específico con JRC Global Surface Water
    VERSIÓN SIMPLIFICADA Y ROBUSTA
    """
    try:
        # Filtrar GSW por año
        year_img = gsw.filter(ee.Filter.eq('year', ano)).first()
        
        # Verificar si hay imagen
        if not year_img:
            return {
                'area_inundada': 0,
                'porcentaje': 0,
                'sensor': 'JRC GSW (sin datos)',
                'imagenes': 0
            }
        
        # Crear máscara para áreas con agua (valor 2 = agua permanente, valor 1 = estacional)
        water_mask = year_img.eq(2).Or(year_img.eq(1))
        
        # Calcular área total del AOI
        area_total = geometry.area(maxError=1).divide(10000).getInfo()
        
        # Calcular área inundada usando pixelArea
        area_inundada_img = water_mask.multiply(ee.Image.pixelArea()).divide(10000)
        
        # Usar reduceRegion con parámetros conservadores
        area_stats = area_inundada_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=30,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        
        # Extraer área inundada de manera robusta
        area_ha = 0
        if area_stats:
            # Buscar el valor en las posibles keys
            for key in ['constant', 'sum', 'b1', 'classification']:
                if key in area_stats and area_stats[key] is not None:
                    area_ha = max(area_ha, area_stats[key])
        
        # Calcular porcentaje
        porcentaje = (area_ha / area_total * 100) if area_total > 0 else 0
        
        return {
            'area_inundada': area_ha,
            'porcentaje': porcentaje,
            'sensor': 'JRC GSW',
            'imagenes': 1
        }
        
    except Exception as e:
        return {
            'area_inundada': 0,
            'porcentaje': 0,
            'sensor': 'JRC GSW (error)',
            'imagenes': 0
        }

def analizar_sentinel2_ndwi_ano(geometry, ano):
    """
    Analiza un año específico con Sentinel-2 NDWI
    VERSIÓN SIMPLIFICADA Y ROBUSTA
    """
    try:
        # Definir fechas
        fecha_inicio = f"{ano}-01-01"
        if ano == 2025:
            fecha_fin = "2025-04-30"  # Solo hasta abril 2025
        else:
            fecha_fin = f"{ano}-12-31"
        
        # Intentar primero con colección armonizada
        s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterDate(fecha_inicio, fecha_fin) \
            .filterBounds(geometry) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))
        
        # Contar imágenes
        num_imagenes = s2_collection.size().getInfo()
        
        # Si no hay suficientes imágenes, intentar con colección principal
        if num_imagenes == 0:
            s2_collection = ee.ImageCollection('COPERNICUS/S2_SR') \
                .filterDate(fecha_inicio, fecha_fin) \
                .filterBounds(geometry) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))
            
            num_imagenes = s2_collection.size().getInfo()
        
        if num_imagenes == 0:
            return {
                'area_inundada': 0,
                'porcentaje': 0,
                'sensor': 'Sentinel-2 (sin datos)',
                'imagenes': 0
            }
        
        # Función para calcular NDWI simplificada
        def add_ndwi(image):
            # Calcular NDWI: (Green - NIR) / (Green + NIR)
            ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI')
            
            # Máscara de nubes básica
            try:
                cloud_mask = image.select('QA60').bitwiseAnd(1 << 10).eq(0)
            except:
                cloud_mask = ee.Image(1)  # Sin máscara si falla
            
            return image.addBands(ndwi).updateMask(cloud_mask)
        
        # Aplicar función a la colección
        s2_ndwi = s2_collection.map(add_ndwi)
        
        # Calcular composición anual (mediana para ser más conservador)
        ndwi_median = s2_ndwi.select('NDWI').median()
        
        # Crear máscara de agua usando umbral científico
        water_mask = ndwi_median.gt(0.2)  # Umbral más conservador
        
        # Calcular área total del AOI
        area_total = geometry.area(maxError=1).divide(10000).getInfo()
        
        # Calcular área inundada
        area_inundada_img = water_mask.multiply(ee.Image.pixelArea()).divide(10000)
        
        area_stats = area_inundada_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=20,  # Resolución más conservadora
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        
        # Extraer área inundada de manera robusta
        area_ha = 0
        if area_stats:
            for key in ['NDWI', 'constant', 'sum', 'b1']:
                if key in area_stats and area_stats[key] is not None:
                    area_ha = max(area_ha, area_stats[key])
        
        # Calcular porcentaje
        porcentaje = (area_ha / area_total * 100) if area_total > 0 else 0
        
        return {
            'area_inundada': area_ha,
            'porcentaje': porcentaje,
            'sensor': 'Sentinel-2 NDWI',
            'imagenes': num_imagenes
        }
        
    except Exception as e:
        return {
            'area_inundada': 0,
            'porcentaje': 0,
            'sensor': 'Sentinel-2 (error)',
            'imagenes': 0
        }

def analizar_riesgo_hidrico_web(aoi, anos_analisis, umbral_inundacion):
    """
    Analiza riesgo de inundación usando METODOLOGÍA CIENTÍFICA COMPLETA:
    - JRC Global Surface Water (GSW) 1984-2019: Estándar mundial
    - Sentinel-2 NDWI > 0.2 (2020-2025): Umbral científico validado
    - Análisis temporal completo: 1984-2025 (41 años)
    - Detección de lagos/lagunas permanentes vs inundaciones temporales
    """
    try:
        # Obtener geometría del AOI
        if hasattr(aoi, 'geometry'):
            geometry = aoi.geometry()
        else:
            geometry = aoi
        
        st.markdown("### 🔬 **Metodología Científica Completa (GSW + Sentinel-2)**")
        st.markdown("**📊 JRC Global Surface Water (1984-2019) + Sentinel-2 NDWI (2020-2025)**")
        
        # Calcular área del AOI
        area_aoi = geometry.area(maxError=1).divide(10000).getInfo()  # en hectáreas
        
        st.markdown(f"📏 Área total del polígono: {area_aoi:.1f} ha")
        
        # Ajustar años de análisis para usar toda la serie temporal disponible
        ano_inicio = max(1984, anos_analisis[0])  # GSW empieza en 1984
        ano_fin = min(2025, anos_analisis[1])     # Datos hasta 2025
        
        anos_completos = list(range(ano_inicio, ano_fin + 1))
        st.markdown(f"📅 Analizando {len(anos_completos)} años: {ano_inicio}-{ano_fin}")
        
        # Diccionario para almacenar resultados
        resultados_por_ano = {}
        tiles_inundacion = {}  # Para mapas interactivos
        
        # FASE 1: ANÁLISIS CON JRC GLOBAL SURFACE WATER (1984-2019)
        st.markdown("### 🌍 **Fase 1: JRC Global Surface Water (1984-2019)**")
        
        # Cargar dataset GSW - ACTUALIZADO A LA NUEVA VERSIÓN  
        gsw = ee.ImageCollection("JRC/GSW1_4/YearlyHistory")
        
        # DEBUG: Mostrar años que van a GSW vs Sentinel-2
        anos_gsw = [ano for ano in anos_completos if ano <= 2019]
        anos_s2 = [ano for ano in anos_completos if ano >= 2020]
        
        if anos_gsw:
            st.info(f"🌍 **Años con GSW**: {len(anos_gsw)} años ({min(anos_gsw)}-{max(anos_gsw)})")
        if anos_s2:
            st.info(f"🛰️ **Años con Sentinel-2**: {len(anos_s2)} años ({min(anos_s2)}-{max(anos_s2)})")
        
        # Analizar cada año con GSW
        for ano in anos_completos:
            if ano <= 2019:  # Solo GSW hasta 2019
                st.markdown(f"🔍 Analizando año {ano} con **JRC GSW**...")
                resultado = analizar_gsw_ano(geometry, ano, gsw)
                if resultado and resultado['area_inundada'] > 0:
                    resultados_por_ano[ano] = resultado
                    # Crear tiles para visualización
                    tiles_inundacion[ano] = crear_tiles_gsw_ano(geometry, ano, gsw)
                    # DEBUG: Mostrar valores obtenidos
                    st.markdown(f"   📊 **GSW {ano}**: {resultado['area_inundada']:.1f} ha ({resultado['porcentaje']:.1f}%)")
                else:
                    resultados_por_ano[ano] = {
                        'area_inundada': 0,
                        'porcentaje': 0,
                        'sensor': 'GSW (sin datos)',
                        'imagenes': 0
                    }
                    st.markdown(f"   ⚪ **GSW {ano}**: Sin datos")
        
        # FASE 2: ANÁLISIS CON SENTINEL-2 NDWI (2020-2025)
        st.markdown("### 🛰️ **Fase 2: Sentinel-2 NDWI (2020-2025)**")
        
        # Analizar cada año con Sentinel-2
        for ano in anos_completos:
            if ano >= 2020:  # Solo Sentinel-2 desde 2020
                st.markdown(f"🔍 Analizando año {ano} con **Sentinel-2 NDWI**...")
                resultado = analizar_sentinel2_ndwi_ano(geometry, ano)
                if resultado and resultado['area_inundada'] > 0:
                    resultados_por_ano[ano] = resultado
                    # Crear tiles para visualización
                    tiles_inundacion[ano] = crear_tiles_sentinel2_ano(geometry, ano)
                    # DEBUG: Mostrar valores obtenidos
                    st.markdown(f"   📊 **S2 {ano}**: {resultado['area_inundada']:.1f} ha ({resultado['porcentaje']:.1f}%) - {resultado['imagenes']} imágenes")
                else:
                    resultados_por_ano[ano] = {
                        'area_inundada': 0,
                        'porcentaje': 0,
                        'sensor': 'Sentinel-2 (sin datos)',
                        'imagenes': 0
                    }
                    st.markdown(f"   ⚪ **S2 {ano}**: Sin datos")
        
        # Procesar resultados y calcular estadísticas
        if resultados_por_ano:
            # Crear DataFrame para análisis
            df_inundacion = pd.DataFrame([
                {
                    'Año': ano,
                    'Área Total (ha)': area_aoi,
                    'Área Inundada (ha)': datos['area_inundada'],
                    'Porcentaje Inundación': datos['porcentaje'],
                    'Sensor': datos['sensor'],
                    'Imágenes': datos['imagenes']
                }
                for ano, datos in resultados_por_ano.items()
            ])
            
            # Calcular estadísticas
            areas_inundadas = [r['area_inundada'] for r in resultados_por_ano.values() if r['area_inundada'] > 0]
            porcentajes = [r['porcentaje'] for r in resultados_por_ano.values() if r['porcentaje'] > 0]
            
            # Detectar lagos y lagunas permanentes (GSW)
            lagos_detectados = []
            anos_con_agua = len([ano for ano, datos in resultados_por_ano.items() if datos['area_inundada'] > 0])
            frecuencia_agua = anos_con_agua / len(anos_completos) * 100
            
            # Clasificar agua permanente vs temporal
            if frecuencia_agua > 70:  # Agua en >70% de los años = lago/laguna
                lagos_detectados.append({
                    'tipo': 'Lagos/Lagunas Permanentes',
                    'frecuencia': frecuencia_agua,
                    'area_promedio': np.mean(areas_inundadas) if areas_inundadas else 0
                })
            
            if areas_inundadas:
                riesgo_promedio = np.mean(porcentajes)
                riesgo_maximo = np.max(porcentajes)
                eventos_significativos = len([p for p in porcentajes if p >= umbral_inundacion])
                probabilidad_evento = eventos_significativos / len(anos_completos) * 100
                
                # Clasificar riesgo
                if riesgo_promedio < 5:
                    categoria_riesgo = "Bajo"
                elif riesgo_promedio < 15:
                    categoria_riesgo = "Medio"
                elif riesgo_promedio < 30:
                    categoria_riesgo = "Alto"
                else:
                    categoria_riesgo = "Muy Alto"
                
                st.success(f"🎉 **Análisis completado**: {len(resultados_por_ano)} años analizados")
                st.info(f"📊 **Riesgo promedio**: {riesgo_promedio:.1f}% - Categoría: {categoria_riesgo}")
                
                # Mostrar información de lagos/lagunas
                if lagos_detectados:
                    st.info(f"🏞️ **Lagos/Lagunas detectados**: Agua presente en {frecuencia_agua:.1f}% de los años")
                
                # CREAR MAPA BÁSICO SIEMPRE (aunque no haya eventos significativos)
                mapa_riesgo = crear_mapa_riesgo_hidrico(geometry, resultados_por_ano, [])
                
                return {
                    'df_inundacion': df_inundacion,
                    'area_total_ha': area_aoi,
                    'riesgo_promedio': riesgo_promedio,
                    'riesgo_maximo': riesgo_maximo,
                    'categoria_riesgo': categoria_riesgo,
                    'probabilidad_evento': probabilidad_evento,
                    'años_analizados': len(anos_completos),
                    'años_con_datos': len(resultados_por_ano),
                    'resultados_por_año': resultados_por_ano,
                    'eventos_significativos': eventos_significativos,
                    'mapa_riesgo': mapa_riesgo,
                    'tiles_inundacion': tiles_inundacion,  # ✅ NUEVO: Tiles por año
                    'lagos_detectados': lagos_detectados,  # ✅ NUEVO: Lagos/lagunas
                    'frecuencia_agua': frecuencia_agua,    # ✅ NUEVO: % años con agua
                    'metodologia': 'GSW_SENTINEL2'         # ✅ NUEVO: Identificar metodología
                }
            else:
                st.info("ℹ️ **No se detectaron inundaciones significativas** en el período analizado")
                
                # CREAR MAPA BÁSICO INCLUSO SIN EVENTOS SIGNIFICATIVOS
                mapa_riesgo = crear_mapa_riesgo_hidrico(geometry, resultados_por_ano, [])
                
                return {
                    'df_inundacion': df_inundacion,
                    'area_total_ha': area_aoi,
                    'riesgo_promedio': 0,
                    'riesgo_maximo': 0,
                    'categoria_riesgo': "Sin riesgo",
                    'probabilidad_evento': 0,
                    'años_analizados': len(anos_completos),
                    'años_con_datos': len(resultados_por_ano),
                    'resultados_por_año': resultados_por_ano,
                    'eventos_significativos': 0,
                    'mapa_riesgo': mapa_riesgo,
                    'tiles_inundacion': tiles_inundacion,
                    'lagos_detectados': [],
                    'frecuencia_agua': 0,
                    'metodologia': 'GSW_SENTINEL2'
                }
        else:
            st.warning("⚠️ **No se pudieron procesar los datos** para ningún año")
            return None
        
    except Exception as e:
        st.error(f"❌ Error en análisis: {str(e)}")
        return None

def crear_tiles_gsw_ano(geometry, ano, gsw):
    """
    Crea tiles azules para visualización de inundación GSW por año
    """
    try:
        # Filtrar GSW por año
        year_img = gsw.filter(ee.Filter.eq('year', ano)).first()
        
        if not year_img:
            return None
        
        # Crear máscara para áreas con agua (valor 2 = agua permanente, valor 1 = estacional)
        water_mask = year_img.eq(2).Or(year_img.eq(1))
        
        # Crear imagen azul para visualización
        imagen_azul = water_mask.selfMask().visualize(**{
            'palette': ['#0077be'],  # Azul para agua
            'min': 0,
            'max': 1
        })
        
        # Generar tiles
        map_id = imagen_azul.getMapId()
        
        if 'tile_fetcher' in map_id:
            return map_id['tile_fetcher'].url_format
        elif 'urlTemplate' in map_id:
            return map_id['urlTemplate']
        else:
            return None
            
    except Exception as e:
        print(f"Error creando tiles GSW {ano}: {str(e)}")
        return None

def crear_tiles_sentinel2_ano(geometry, ano):
    """
    Crea tiles azules para visualización de inundación Sentinel-2 por año
    """
    try:
        # Definir fechas
        fecha_inicio = f"{ano}-01-01"
        if ano == 2025:
            fecha_fin = "2025-04-30"  # Solo hasta abril 2025
        else:
            fecha_fin = f"{ano}-12-31"
        
        # Colección Sentinel-2
        s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterDate(fecha_inicio, fecha_fin) \
            .filterBounds(geometry) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))
        
        if s2_collection.size().getInfo() == 0:
            s2_collection = ee.ImageCollection('COPERNICUS/S2_SR') \
                .filterDate(fecha_inicio, fecha_fin) \
                .filterBounds(geometry) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))
        
        if s2_collection.size().getInfo() == 0:
            return None
        
        # Función para calcular NDWI
        def add_ndwi(image):
            ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI')
            try:
                cloud_mask = image.select('QA60').bitwiseAnd(1 << 10).eq(0)
            except:
                cloud_mask = ee.Image(1)
            return image.addBands(ndwi).updateMask(cloud_mask)
        
        # Aplicar función a la colección
        s2_ndwi = s2_collection.map(add_ndwi)
        
        # Calcular composición anual (mediana)
        ndwi_median = s2_ndwi.select('NDWI').median()
        
        # Crear máscara de agua
        water_mask = ndwi_median.gt(0.2)
        
        # Crear imagen azul para visualización
        imagen_azul = water_mask.selfMask().visualize(**{
            'palette': ['#0077be'],  # Azul para agua
            'min': 0,
            'max': 1
        })
        
        # Generar tiles
        map_id = imagen_azul.getMapId()
        
        if 'tile_fetcher' in map_id:
            return map_id['tile_fetcher'].url_format
        elif 'urlTemplate' in map_id:
            return map_id['urlTemplate']
        else:
            return None
            
    except Exception as e:
        print(f"Error creando tiles Sentinel-2 {ano}: {str(e)}")
        return None
def obtener_datos_inundacion_año(geometry, fecha_inicio, fecha_fin):
    """
    Obtiene datos de inundación para un año específico
    Combina datos de Sentinel-1 (radar para detección de agua)
    """
    try:
        # Colección de Sentinel-1 (radar, detecta agua)
        s1_collection = ee.ImageCollection("COPERNICUS/S1_GRD") \
            .filterBounds(geometry) \
            .filterDate(fecha_inicio, fecha_fin) \
            .filter(ee.Filter.eq('instrumentMode', 'IW')) \
            .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
        
        if s1_collection.size().getInfo() > 0:
            # Procesar imágenes Sentinel-1
            s1_agua = s1_collection.map(lambda img: procesar_sentinel1_agua(img))
            
            # Obtener máscara de agua más frecuente
            agua_frecuencia = s1_agua.mean()
            umbral_agua = 0.3  # 30% de frecuencia mínima
            
            mascara_agua = agua_frecuencia.gt(umbral_agua)
            
            # Calcular área inundada
            stats = mascara_agua.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=30,
                maxPixels=1e9
            )
            
            pixeles_agua = stats.getInfo().get('agua', 0)
            area_inundada_ha = pixeles_agua * 30 * 30 / 10000  # Convertir a hectáreas
            
            # Contar eventos (imágenes con agua detectada)
            frecuencia_eventos = s1_collection.size().getInfo()
            
            return {
                'area_inundada_ha': area_inundada_ha,
                'frecuencia_eventos': frecuencia_eventos,
                'duracion_maxima': frecuencia_eventos * 12  # Estimación basada en revisitas
            }
        else:
            return None
            
    except Exception as e:
        print(f"Error obteniendo datos de inundación: {str(e)}")
        return None

def procesar_sentinel1_agua(imagen):
    """
    Procesa imagen Sentinel-1 para detectar agua
    """
    try:
        # Usar banda VH (mejor para detección de agua)
        vh = imagen.select('VH')
        
        # Umbral para detectar agua (valores bajos indican agua)
        umbral_agua = -18  # dB
        
        # Crear máscara de agua
        mascara_agua = vh.lt(umbral_agua)
        
        # Aplicar filtro para reducir ruido
        mascara_agua = mascara_agua.focal_median(2)
        
        return mascara_agua.rename('agua')
        
    except Exception as e:
        print(f"Error procesando Sentinel-1: {str(e)}")
        return imagen.select('VH').multiply(0)

def analizar_gsw_ano(geometry, ano, gsw):
    """
    Analiza un año específico con JRC Global Surface Water
    VERSIÓN SIMPLIFICADA Y ROBUSTA
    """
    try:
        # Filtrar GSW por año
        year_img = gsw.filter(ee.Filter.eq('year', ano)).first()
        
        # Verificar si hay imagen
        if not year_img:
            return {
                'area_inundada': 0,
                'porcentaje': 0,
                'sensor': 'JRC GSW (sin datos)',
                'imagenes': 0
            }
        
        # Crear máscara para áreas con agua (valor 2 = agua permanente, valor 1 = estacional)
        water_mask = year_img.eq(2).Or(year_img.eq(1))
        
        # Calcular área total del AOI
        area_total = geometry.area(maxError=1).divide(10000).getInfo()
        
        # Calcular área inundada usando pixelArea
        area_inundada_img = water_mask.multiply(ee.Image.pixelArea()).divide(10000)
        
        # Usar reduceRegion con parámetros conservadores
        area_stats = area_inundada_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=30,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        
        # Extraer área inundada de manera robusta
        area_ha = 0
        if area_stats:
            # Buscar el valor en las posibles keys
            for key in ['constant', 'sum', 'b1', 'classification']:
                if key in area_stats and area_stats[key] is not None:
                    area_ha = max(area_ha, area_stats[key])
        
        # Calcular porcentaje
        porcentaje = (area_ha / area_total * 100) if area_total > 0 else 0
        
        return {
            'area_inundada': area_ha,
            'porcentaje': porcentaje,
            'sensor': 'JRC GSW',
            'imagenes': 1
        }
        
    except Exception as e:
        return {
            'area_inundada': 0,
            'porcentaje': 0,
            'sensor': 'JRC GSW (error)',
            'imagenes': 0
        }

def analizar_sentinel2_ndwi_ano(geometry, ano):
    """
    Analiza un año específico con Sentinel-2 NDWI
    VERSIÓN SIMPLIFICADA Y ROBUSTA
    """
    try:
        # Definir fechas
        fecha_inicio = f"{ano}-01-01"
        if ano == 2025:
            fecha_fin = "2025-04-30"  # Solo hasta abril 2025
        else:
            fecha_fin = f"{ano}-12-31"
        
        # Intentar primero con colección armonizada
        s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterDate(fecha_inicio, fecha_fin) \
            .filterBounds(geometry) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))
        
        # Contar imágenes
        num_imagenes = s2_collection.size().getInfo()
        
        # Si no hay suficientes imágenes, intentar con colección principal
        if num_imagenes == 0:
            s2_collection = ee.ImageCollection('COPERNICUS/S2_SR') \
                .filterDate(fecha_inicio, fecha_fin) \
                .filterBounds(geometry) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))
            
            num_imagenes = s2_collection.size().getInfo()
        
        if num_imagenes == 0:
            return {
                'area_inundada': 0,
                'porcentaje': 0,
                'sensor': 'Sentinel-2 (sin datos)',
                'imagenes': 0
            }
        
        # Función para calcular NDWI simplificada
        def add_ndwi(image):
            # Calcular NDWI: (Green - NIR) / (Green + NIR)
            ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI')
            
            # Máscara de nubes básica
            try:
                cloud_mask = image.select('QA60').bitwiseAnd(1 << 10).eq(0)
            except:
                cloud_mask = ee.Image(1)  # Sin máscara si falla
            
            return image.addBands(ndwi).updateMask(cloud_mask)
        
        # Aplicar función a la colección
        s2_ndwi = s2_collection.map(add_ndwi)
        
        # Calcular composición anual (mediana para ser más conservador)
        ndwi_median = s2_ndwi.select('NDWI').median()
        
        # Crear máscara de agua usando umbral científico
        water_mask = ndwi_median.gt(0.2)  # Umbral más conservador
        
        # Calcular área total del AOI
        area_total = geometry.area(maxError=1).divide(10000).getInfo()
        
        # Calcular área inundada
        area_inundada_img = water_mask.multiply(ee.Image.pixelArea()).divide(10000)
        
        area_stats = area_inundada_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=20,  # Resolución más conservadora
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        
        # Extraer área inundada de manera robusta
        area_ha = 0
        if area_stats:
            for key in ['NDWI', 'constant', 'sum', 'b1']:
                if key in area_stats and area_stats[key] is not None:
                    area_ha = max(area_ha, area_stats[key])
        
        # Calcular porcentaje
        porcentaje = (area_ha / area_total * 100) if area_total > 0 else 0
        
        return {
            'area_inundada': area_ha,
            'porcentaje': porcentaje,
            'sensor': 'Sentinel-2 NDWI',
            'imagenes': num_imagenes
        }
        
    except Exception as e:
        return {
            'area_inundada': 0,
            'porcentaje': 0,
            'sensor': 'Sentinel-2 (error)',
            'imagenes': 0
        }

def crear_mapa_riesgo_hidrico(geometry, resultados_por_año, eventos_inundacion):
    """
    Crea un mapa interactivo de riesgo hídrico
    """
    try:
        # Obtener centroide de la geometría
        centroide = geometry.centroid().getInfo()['coordinates']
        
        # Crear mapa base
        mapa = folium.Map(
            location=[centroide[1], centroide[0]],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Añadir polígono del campo
        if hasattr(geometry, 'getInfo'):
            coords = geometry.getInfo()['coordinates'][0]
            folium.Polygon(
                locations=[[coord[1], coord[0]] for coord in coords],
                popup="Área de Análisis",
                color='blue',
                fillColor='lightblue',
                fillOpacity=0.3,
                weight=2
            ).add_to(mapa)
        
        # Añadir marcadores de eventos significativos
        for evento in eventos_inundacion:
            color = 'red' if evento['severidad'] == 'Alta' else 'orange' if evento['severidad'] == 'Media' else 'yellow'
            
            folium.CircleMarker(
                location=[centroide[1], centroide[0]],
                radius=evento['porcentaje'] / 5,  # Tamaño proporcional al porcentaje
                popup=f"Año {evento['año']}: {evento['porcentaje']:.1f}% inundado",
                color=color,
                fillColor=color,
                fillOpacity=0.7
            ).add_to(mapa)
        
        return mapa
        
    except Exception as e:
        print(f"Error creando mapa de riesgo: {str(e)}")
        return None

def main():
    # Logo VISU con tagline correcto - DISEÑO ELEGANTE QUE YA FUNCIONA
    st.markdown("""
    <div class="visu-logo-container">
        <div class="minimal-container">
            <div class="visu-minimal">VISU</div>
            <div class="eye-underline">
                <div class="eye-dot"></div>
            </div>
            <div class="tagline">VISUALIZE WITH SUPERPOWERS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Inicializar session state si no existe
    if 'resultados_analisis' not in st.session_state:
        st.session_state.resultados_analisis = None
    if 'analisis_completado' not in st.session_state:
        st.session_state.analisis_completado = False
    if 'tab_activa' not in st.session_state:
        st.session_state.tab_activa = 0
    
    if 'ee_initialized' not in st.session_state:
        with st.spinner("Inicializando Google Earth Engine..."):
            st.session_state.ee_initialized = init_earth_engine()
    
    if not st.session_state.ee_initialized:
        st.error("❌ No se pudo conectar con Google Earth Engine. Verifica la configuración.")
        return
    
    # CREAR PESTAÑAS CON ESTADO PERSISTENTE
    tabs = st.tabs(["📁 Análisis desde KMZ", "🔍 Análisis por CUIT"])
    
    with tabs[0]:
        mostrar_analisis_kmz()
                # RESULTADOS SE MUESTRAN DENTRO DE LAS SUB-PESTAÑAS
        
    with tabs[1]:
        mostrar_analisis_cuit()
        # MOSTRAR RESULTADOS DENTRO DE LA PESTAÑA CUIT
        if st.session_state.analisis_completado and st.session_state.resultados_analisis:
            if st.session_state.resultados_analisis.get('fuente') == 'CUIT':
                mostrar_resultados_analisis()
    
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        🌾 Análisis de Rotación de Cultivos | Powered by Google Earth Engine & Streamlit
    </div>
    """, unsafe_allow_html=True)

def mostrar_analisis_kmz():
    """Muestra la interfaz para análisis desde archivos KMZ"""
    
    # SUB-PESTAÑAS PARA TIPOS DE ANÁLISIS
    sub_tabs = st.tabs(["🌾 Cultivos y Rotación", "🌊 Riesgo Hídrico"])
    
    with sub_tabs[0]:
        mostrar_analisis_cultivos_kmz()
    
            # MOSTRAR RESULTADOS DE CULTIVOS DENTRO DE LA SUB-PESTAÑA
        if st.session_state.analisis_completado and st.session_state.resultados_analisis:
            if st.session_state.resultados_analisis.get('fuente') == 'KMZ':
                tipo_analisis = st.session_state.resultados_analisis.get('tipo_analisis', 'cultivos')
                if tipo_analisis == 'cultivos':
                    mostrar_resultados_analisis()
    
    with sub_tabs[1]:
        mostrar_analisis_inundacion_kmz()
        # MOSTRAR RESULTADOS DE INUNDACIÓN DENTRO DE LA SUB-PESTAÑA
        if st.session_state.analisis_completado and st.session_state.resultados_analisis:
            if st.session_state.resultados_analisis.get('fuente') == 'KMZ':
                tipo_analisis = st.session_state.resultados_analisis.get('tipo_analisis', 'cultivos')
                if tipo_analisis == 'inundacion':
                    mostrar_resultados_inundacion()

def mostrar_analisis_cultivos_kmz():
    """Análisis de cultivos desde archivos KMZ"""
    
    # 🔥 ÁREA DE UPLOAD - FORZADO CON !IMPORTANT PARA QUE FUNCIONE
    st.markdown("""
    <div style="background: linear-gradient(135deg, #2a2a2a, #1a1a1a) !important; 
                padding: 25px !important; border-radius: 15px !important; margin: 20px 0 !important; 
                border: 2px solid #00D2BE !important; text-align: center !important;">
        <h3 style="color: #00D2BE !important; margin: 0 0 15px 0 !important; font-weight: bold !important;">
            📁 Carga de Archivos KMZ
        </h3>
        <p style="color: #ffffff !important; margin: 0 !important; font-size: 1.1rem !important;">
            Selecciona uno o más archivos KMZ para analizar cultivos y rotación
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "🌾 Selecciona tus archivos KMZ",
        type=['kmz'],
        accept_multiple_files=True,
        help="💡 Puedes subir múltiples archivos KMZ para analizar cultivos y rotación. ⚠️ En móviles puede no funcionar - usa computadora para mejores resultados.",
        key="kmz_uploader_cultivos"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} archivo(s) subido(s) correctamente")
        
        with st.expander("📋 Ver detalles de archivos subidos"):
            for file in uploaded_files:
                file_size_mb = file.size / (1024 * 1024)
                st.write(f"📄 **{file.name}** - {file_size_mb:.2f} MB ({file.size:,} bytes)")
        
        # BOTÓN DE ANÁLISIS - SOLO PROCESA Y GUARDA EN SESSION STATE
        if st.button("🚀 Analizar Cultivos y Rotación", type="primary", key="btn_analizar_cultivos_kmz"):
            with st.spinner("🔄 Procesando análisis completo..."):
                # Procesar archivos KMZ
                todos_los_poligonos = []
                nombres_archivos = []
                
                for uploaded_file in uploaded_files:
                    poligonos = procesar_kmz_uploaded(uploaded_file)
                    todos_los_poligonos.extend(poligonos)
                    # Extraer nombre sin extensión para usar en descargas
                    nombre_limpio = uploaded_file.name.replace('.kmz', '').replace('.KMZ', '')
                    # Limpiar caracteres especiales para nombre de archivo
                    nombre_limpio = re.sub(r'[^\w\s-]', '', nombre_limpio).strip()
                    nombre_limpio = re.sub(r'[-\s]+', '_', nombre_limpio)
                    nombres_archivos.append(nombre_limpio)
                
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
                        'tipo_analisis': 'cultivos',
                        'df_cultivos': df_cultivos,
                        'area_total': area_total,
                        'tiles_urls': tiles_urls,
                        'cultivos_por_campana': cultivos_por_campana,
                        'aoi': aoi,
                        'archivo_info': f"{len(uploaded_files)} archivo(s) - {len(todos_los_poligonos)} polígonos",
                        'nombres_archivos': nombres_archivos,  # Guardar nombres para descargas
                        'fuente': 'KMZ'  # Identificar fuente
                    }
                    st.session_state.analisis_completado = True
                    st.success("🎉 ¡Análisis completado exitosamente!")
                    # SIN RERUN para mantener la pestaña activa
                    st.info("📋 Los resultados aparecerán abajo.")
                    
                    # Mostrar resumen rápido en la misma pestaña
                    st.markdown("### 📊 Resumen Rápido")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Área Total", f"{area_total:,.1f} ha")
                    with col2:
                        cultivos_detectados = df_cultivos[df_cultivos['Área (ha)'] > 0]['Cultivo'].nunique()
                        st.metric("Cultivos", f"{cultivos_detectados:,}")
                    with col3:
                        st.metric("Archivo", f"{len(uploaded_files)} KMZ")
                else:
                    st.error("❌ No se pudieron analizar los cultivos")
                    st.session_state.analisis_completado = False

def mostrar_analisis_inundacion_kmz():
    """Análisis de riesgo hídrico desde archivos KMZ"""
    
    # 🔥 ÁREA DE UPLOAD PARA INUNDACIÓN
    st.markdown("""
    <div style="background: linear-gradient(135deg, #2a2a2a, #1a1a1a) !important; 
                padding: 25px !important; border-radius: 15px !important; margin: 20px 0 !important; 
                border: 2px solid #00D2BE !important; text-align: center !important;">
        <h3 style="color: #00D2BE !important; margin: 0 0 15px 0 !important; font-weight: bold !important;">
            🌊 Análisis de Riesgo Hídrico
        </h3>
        <p style="color: #ffffff !important; margin: 0 !important; font-size: 1.1rem !important;">
            Analiza el riesgo de inundación basado en datos históricos 1984-2025
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files_inund = st.file_uploader(
        "🌊 Selecciona tus archivos KMZ",
        type=['kmz'],
        accept_multiple_files=True,
        help="💡 Archivos KMZ para análisis de riesgo hídrico. El análisis incluye frecuencia de inundación, áreas afectadas y mapas de riesgo.",
        key="kmz_uploader_inundacion"
    )
    
    if uploaded_files_inund:
        st.success(f"✅ {len(uploaded_files_inund)} archivo(s) subido(s) para análisis hídrico")
        
        with st.expander("📋 Ver detalles de archivos subidos"):
            for file in uploaded_files_inund:
                file_size_mb = file.size / (1024 * 1024)
                st.write(f"📄 **{file.name}** - {file_size_mb:.2f} MB ({file.size:,} bytes)")
        
        # Configuración del análisis
        st.markdown("### ⚙️ Configuración del Análisis")
        col1, col2 = st.columns(2)
        
        with col1:
            anos_analisis = st.slider(
                "📅 Años de análisis:",
                min_value=1984,
                max_value=2025,
                value=(1984, 2025),
                help="Rango de años para análisis histórico (1984-2025). GSW: 1984-2019, Sentinel-2: 2020-2025"
            )
        
        with col2:
            umbral_inundacion = st.slider(
                "🌊 Umbral de inundación (%):",
                min_value=5,
                max_value=50,
                value=20,
                help="Porcentaje mínimo de área inundada para considerar evento significativo"
            )
        
        # BOTÓN DE ANÁLISIS DE INUNDACIÓN
        if st.button("🌊 Analizar Riesgo Hídrico", type="primary", key="btn_analizar_inundacion_kmz"):
            # 🚨 LIMPIAR RESULTADOS ANTERIORES PARA EVITAR CACHE DE FUNCIÓN ANTIGUA
            st.session_state.analisis_completado = False
            st.session_state.resultados_analisis = None
            
            with st.spinner("🔄 Analizando riesgo hídrico (esto puede tardar varios minutos)..."):
                # Procesar archivos KMZ
                todos_los_poligonos = []
                nombres_archivos = []
                
                for uploaded_file in uploaded_files_inund:
                    poligonos = procesar_kmz_uploaded(uploaded_file)
                    todos_los_poligonos.extend(poligonos)
                    nombre_limpio = uploaded_file.name.replace('.kmz', '').replace('.KMZ', '')
                    nombre_limpio = re.sub(r'[^\w\s-]', '', nombre_limpio).strip()
                    nombre_limpio = re.sub(r'[-\s]+', '_', nombre_limpio)
                    nombres_archivos.append(nombre_limpio)
                
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
                
                # Ejecutar análisis de inundación
                resultado_inundacion = analizar_riesgo_hidrico_web(aoi, anos_analisis, umbral_inundacion)
                
                if resultado_inundacion:
                    # GUARDAR RESULTADOS DE INUNDACIÓN
                    st.session_state.resultados_analisis = {
                        'tipo_analisis': 'inundacion',
                        'resultado_inundacion': resultado_inundacion,
                        'aoi': aoi,
                        'archivo_info': f"{len(uploaded_files_inund)} archivo(s) - {len(todos_los_poligonos)} polígonos",
                        'nombres_archivos': nombres_archivos,
                        'fuente': 'KMZ',
                        'config_analisis': {
                            'anos_analisis': anos_analisis,
                            'umbral_inundacion': umbral_inundacion
                        }
                    }
                    st.session_state.analisis_completado = True
                    st.success("🎉 ¡Análisis de riesgo hídrico completado!")
                    st.info("📋 Los resultados aparecerán abajo.")
                    
                    # Mostrar resumen rápido
                    st.markdown("### 📊 Resumen Rápido - Riesgo Hídrico")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Área Total", f"{resultado_inundacion.get('area_total_ha', 0):,.1f} ha")
                    with col2:
                        st.metric("Años Analizados", f"{anos_analisis[1] - anos_analisis[0] + 1} años")
                    with col3:
                        st.metric("Riesgo Promedio", f"{resultado_inundacion.get('riesgo_promedio', 0):.1f}%")
                else:
                    st.error("❌ No se pudo analizar el riesgo hídrico")
                    st.session_state.analisis_completado = False

def mostrar_analisis_cuit():
    """Muestra la interfaz para análisis por CUIT"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #2a2a2a, #1a1a1a) !important; 
                padding: 25px !important; border-radius: 15px !important; margin: 20px 0 !important; 
                border: 2px solid #00D2BE !important; text-align: center !important;">
        <h3 style="color: #00D2BE !important; margin: 0 0 15px 0 !important; font-weight: bold !important;">
            🔍 Análisis por CUIT
        </h3>
        <p style="color: #ffffff !important; margin: 0 !important; font-size: 1.1rem !important;">
            Consulta automática de coordenadas para obtener polígonos y analizar cultivos
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Input para CUIT
    cuit_input = st.text_input(
        "🏢 Ingresá el CUIT del productor:",
        placeholder="30-12345678-9",
        key="cuit_input",
        help="💡 Consulta automática de coordenadas de campos registrados"
    )
    
    # Opción para elegir entre campos activos o históricos
    solo_activos = st.radio(
        "¿Qué campos querés analizar?",
        ["Solo campos activos", "Todos los campos (incluye históricos)"],
        key="tipo_campos_cuit",
        horizontal=True
    ) == "Solo campos activos"
    
    # NUEVA OPCIÓN: Análisis individual o general
    st.markdown("---")
    tipo_analisis = st.radio(
        "¿Cómo querés analizar los cultivos?",
        ["🌾 Análisis General (todos los campos juntos)", "🎯 Análisis Individual (campo por campo)"],
        key="tipo_analisis_cuit",
        horizontal=True,
        help="General: Un solo análisis con todos los campos como AOI único. Individual: Análisis separado por cada campo."
    )
    
    if st.button("🚀 Analizar Cultivos por CUIT", type="primary", key="btn_analizar_cuit"):
        if cuit_input:
            try:
                with st.spinner("🔄 Analizando polígonos y coordenadas..."):
                    # Procesar campos del CUIT
                    poligonos_data = procesar_campos_cuit(cuit_input, solo_activos)
                    
                    if not poligonos_data:
                        st.error("❌ No se encontraron campos válidos para este CUIT")
                        return
                    
                    # Mostrar información de campos encontrados
                    st.success(f"✅ Se encontraron {len(poligonos_data)} campos con coordenadas")
                    
                    # Mostrar detalles de los campos
                    with st.expander("📋 Ver detalles de campos encontrados"):
                        for i, campo in enumerate(poligonos_data):
                            st.write(f"""
                            **Campo {i+1}**: {campo.get('titular', 'Sin titular')}  
                            **Localidad**: {campo.get('localidad', 'Sin información')}  
                            **Superficie**: {campo.get('superficie', 0):.1f} ha
                            """)
                    
                    # ANÁLISIS SEGÚN TIPO ELEGIDO
                    if "Individual" in tipo_analisis:
                        # 🎯 ANÁLISIS INDIVIDUAL POR CAMPO
                        with st.spinner("🔄 Ejecutando análisis individual por campo..."):
                            resultados_individuales = []
                            campo_mas_grande = None
                            max_superficie = 0
                            
                            for i, campo_data in enumerate(poligonos_data):
                                st.write(f"🔄 Analizando Campo {i+1}: {campo_data.get('titular', 'Sin titular')}...")
                                
                                # Crear AOI individual para este campo
                                aoi_individual = crear_ee_feature_collection_web([campo_data])
                                
                                if aoi_individual:
                                    # Análisis individual
                                    resultado = analizar_cultivos_web(aoi_individual)
                                    
                                    if len(resultado) >= 2:
                                        df_cultivos_ind, area_total_ind = resultado[:2]
                                        tiles_urls_ind = resultado[2] if len(resultado) > 2 else {}
                                        cultivos_por_campana_ind = resultado[3] if len(resultado) > 3 else {}
                                        
                                        if df_cultivos_ind is not None and not df_cultivos_ind.empty:
                                            # Agregar información del campo al dataframe
                                            df_cultivos_ind['campo_nombre'] = campo_data.get('titular', f'Campo_{i+1}')
                                            df_cultivos_ind['campo_numero'] = i + 1
                                            df_cultivos_ind['campo_localidad'] = campo_data.get('localidad', 'Sin información')
                                            df_cultivos_ind['campo_superficie_total'] = campo_data.get('superficie', 0)
                                            
                                            resultado_campo = {
                                                'campo_numero': i + 1,
                                                'campo_nombre': campo_data.get('titular', f'Campo_{i+1}'),
                                                'campo_localidad': campo_data.get('localidad', 'Sin información'),
                                                'campo_superficie': campo_data.get('superficie', 0),
                                                'df_cultivos': df_cultivos_ind,
                                                'area_total': area_total_ind,
                                                'tiles_urls': tiles_urls_ind,
                                                'cultivos_por_campana': cultivos_por_campana_ind,
                                                'aoi': aoi_individual,
                                                'coords': campo_data.get('coords', [])
                                            }
                                            resultados_individuales.append(resultado_campo)
                                            
                                            # Encontrar campo más grande
                                            if campo_data.get('superficie', 0) > max_superficie:
                                                max_superficie = campo_data.get('superficie', 0)
                                                campo_mas_grande = resultado_campo
                            
                            if resultados_individuales:
                                # GUARDAR RESULTADOS INDIVIDUALES EN SESSION STATE
                                st.session_state.resultados_analisis = {
                                    'tipo': 'individual',
                                    'resultados_individuales': resultados_individuales,
                                    'campo_principal': campo_mas_grande,
                                    'total_campos': len(resultados_individuales),
                                    'superficie_total': sum(r['campo_superficie'] for r in resultados_individuales),
                                    'fuente': 'CUIT_INDIVIDUAL',
                                    'cuit_info': {
                                        'cuit': cuit_input,
                                        'campos_encontrados': len(poligonos_data),
                                        'solo_activos': solo_activos
                                    },
                                    'nombres_archivos': [f"CUIT_{normalizar_cuit(cuit_input).replace('-', '')}_individual"]
                                }
                                st.session_state.analisis_completado = True
                                st.success("🎉 ¡Análisis individual completado exitosamente!")
                                st.info("📋 Los resultados de cada campo aparecerán abajo.")
                                
                                # Mostrar resumen rápido
                                st.markdown("### 📊 Resumen por Campo")
                                for resultado in resultados_individuales:
                                    with st.expander(f"🏡 {resultado['campo_nombre']} - {resultado['campo_superficie']:.1f} ha", expanded=False):
                                        col1, col2, col3 = st.columns(3)
                                        with col1:
                                            st.metric("Área Total", f"{resultado['area_total']:,.1f} ha")
                                        with col2:
                                            cultivos_detectados = resultado['df_cultivos'][resultado['df_cultivos']['Área (ha)'] > 0]['Cultivo'].nunique()
                                            st.metric("Cultivos", f"{cultivos_detectados:,}")
                                        with col3:
                                            st.metric("Localidad", resultado['campo_localidad'])
                            else:
                                st.error("❌ No se pudieron analizar los campos individualmente")
                                st.session_state.analisis_completado = False
                    
                    else:
                        # 🌾 ANÁLISIS GENERAL (ORIGINAL)
                        # Crear AOI
                        aoi = crear_ee_feature_collection_web(poligonos_data)
                        if not aoi:
                            st.error("❌ No se pudo crear el área de interés")
                            return
                        
                        # Ejecutar análisis
                        with st.spinner("🔄 Ejecutando análisis general de cultivos..."):
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
                                    'tipo': 'general',
                                    'df_cultivos': df_cultivos,
                                    'area_total': area_total,
                                    'tiles_urls': tiles_urls,
                                    'cultivos_por_campana': cultivos_por_campana,
                                    'aoi': aoi,
                                    'archivo_info': f"CUIT: {cuit_input} - {len(poligonos_data)} campos",
                                    'nombres_archivos': [f"CUIT_{normalizar_cuit(cuit_input).replace('-', '')}"],
                                    'fuente': 'CUIT',  # Identificar fuente
                                    'cuit_info': {
                                        'cuit': cuit_input,
                                        'campos_encontrados': len(poligonos_data),
                                        'solo_activos': solo_activos
                                    },
                                    'poligonos_data': poligonos_data  # Para generar KMZ
                                }
                                st.session_state.analisis_completado = True
                                st.success("🎉 ¡Análisis completado exitosamente!")
                                # SIN RERUN para mantener la pestaña activa
                                st.info("📋 Los resultados aparecerán abajo. Podés cambiar de pestaña para verlos en detalle.")
                                
                                # Mostrar resumen rápido en la misma pestaña
                                st.markdown("### 📊 Resumen Rápido")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Área Total", f"{area_total:,.1f} ha")
                                with col2:
                                    cultivos_detectados = df_cultivos[df_cultivos['Área (ha)'] > 0]['Cultivo'].nunique()
                                    st.metric("Cultivos", f"{cultivos_detectados:,}")
                                with col3:
                                    st.metric("Campos", f"{len(poligonos_data)} encontrados")
                            else:
                                st.error("❌ No se pudieron analizar los cultivos")
                                st.session_state.analisis_completado = False
                            
            except ValueError as e:
                st.error("❌ CUIT inválido. Verificá el formato (XX-XXXXXXXX-X)")
            except Exception as e:
                st.error(f"❌ Error procesando CUIT: {e}")
        else:
            st.warning("⚠️ Por favor, ingresá un CUIT válido")

def mostrar_resultados_analisis():
    """Muestra los resultados del análisis completo"""
    st.markdown("---")
    st.markdown("## 📊 Resultados del Análisis")
    
    # Extraer datos de session state
    datos = st.session_state.resultados_analisis
    tipo_analisis = datos.get('tipo', 'general')
    fuente = datos.get('fuente', 'Desconocida')
    
    # ANÁLISIS INDIVIDUAL POR CAMPO
    if tipo_analisis == 'individual':
        resultados_individuales = datos['resultados_individuales']
        campo_principal = datos.get('campo_principal')
        
        # Mostrar información de la fuente
        cuit_info = datos.get('cuit_info', {})
        st.info(f"📋 **Análisis Individual**: CUIT {cuit_info.get('cuit', 'N/A')} - {datos['total_campos']} campos analizados")
        
        # Métricas generales
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Campos Analizados", f"{datos['total_campos']:,}")
        with col2:
            st.metric("Superficie Total", f"{datos['superficie_total']:,.1f} ha")
        with col3:
            if campo_principal:
                st.metric("Campo Más Grande", f"{campo_principal['campo_superficie']:,.1f} ha")
            else:
                st.metric("Campo Más Grande", "N/A")
        with col4:
            superficie_promedio = datos['superficie_total'] / datos['total_campos'] if datos['total_campos'] > 0 else 0
            st.metric("Superficie Promedio", f"{superficie_promedio:,.1f} ha")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # SELECTOR DE CAMPO INDIVIDUAL
        st.subheader("🎯 Seleccionar Campo para Análisis Detallado")
        
        # Crear opciones para el selectbox
        opciones_campos = [f"🏡 Campo {r['campo_numero']}: {r['campo_nombre']} ({r['campo_superficie']:.1f} ha)" 
                          for r in resultados_individuales]
        
        # Si hay campo principal, ponerlo como default
        default_index = 0
        if campo_principal:
            for i, r in enumerate(resultados_individuales):
                if r['campo_numero'] == campo_principal['campo_numero']:
                    default_index = i
                    break
        
        campo_seleccionado_idx = st.selectbox(
            "Elegir campo:",
            range(len(opciones_campos)),
            format_func=lambda x: opciones_campos[x],
            index=default_index,
            key="selector_campo_individual"
        )
        
        # Obtener datos del campo seleccionado
        resultado_campo = resultados_individuales[campo_seleccionado_idx]
        df_cultivos = resultado_campo['df_cultivos']
        area_total = resultado_campo['area_total']
        tiles_urls = resultado_campo['tiles_urls']
        cultivos_por_campana = resultado_campo['cultivos_por_campana']
        aoi = resultado_campo['aoi']
        
        # Mostrar info del campo seleccionado
        st.info(f"📍 **Campo**: {resultado_campo['campo_nombre']} | **Localidad**: {resultado_campo['campo_localidad']} | **Superficie**: {resultado_campo['campo_superficie']:.1f} ha")
        
    # ANÁLISIS GENERAL (ORIGINAL)
    else:
        df_cultivos = datos['df_cultivos']
        area_total = datos['area_total']
        tiles_urls = datos['tiles_urls']
        cultivos_por_campana = datos['cultivos_por_campana']
        aoi = datos['aoi']
        
        # Mostrar información de la fuente
        if fuente == 'CUIT':
            cuit_info = datos.get('cuit_info', {})
            st.info(f"📋 **Análisis General**: CUIT {cuit_info.get('cuit', 'N/A')} - {cuit_info.get('campos_encontrados', 0)} campos unidos")
        else:
            st.info(f"📋 **Fuente**: {datos.get('archivo_info', 'Archivos KMZ')}")
    
    # MÉTRICAS DEL ANÁLISIS SELECCIONADO
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Área Analizada", f"{area_total:,.1f} ha")
    with col2:
        cultivos_detectados = df_cultivos[df_cultivos['Área (ha)'] > 0]['Cultivo'].nunique()
        st.metric("Cultivos Detectados", f"{cultivos_detectados:,}")
    with col3:
        area_agricola_por_campana = df_cultivos[~df_cultivos['Cultivo'].str.contains('No agrícola', na=False)].groupby('Campaña')['Área (ha)'].sum()
        area_agricola = area_agricola_por_campana.mean()
        st.metric("Área Agrícola", f"{area_agricola:,.1f} ha", help="Promedio de área agrícola por campaña")
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
            key="selector_campana_persistente"
        )
    
    with col_info:
        # Mostrar info de la campaña seleccionada
        df_sel = df_cultivos[df_cultivos['Campaña'] == campana_seleccionada]
        cultivos_sel = len(df_sel[df_sel['Área (ha)'] > 0])
        area_agricola_sel = df_sel[~df_sel['Cultivo'].str.contains('No agrícola', na=False)]['Área (ha)'].sum()
        
        st.metric(
            f"Campaña {campana_seleccionada}", 
            f"{area_agricola_sel:,.1f} ha agrícolas",
            help=f"{cultivos_sel:,} cultivos detectados"
        )
    
    # Mostrar mapa
    try:
        if tiles_urls and campana_seleccionada in tiles_urls:
            # Crear mapa con tiles reales de Earth Engine
            mapa_tiles = crear_mapa_con_tiles_engine(
                aoi, tiles_urls, df_cultivos, 
                cultivos_por_campana, campana_seleccionada
            )
            
            # Mostrar el mapa - Altura fija responsiva
            map_data = st_folium(mapa_tiles, width=None, height=500, key="mapa_persistente")
            
            st.success("✅ **Mapa con píxeles reales de Google Earth Engine**")
            
            # Ayuda responsive para usar el mapa CON EXPLICACIÓN DE COLORES
            with st.expander("💡 Cómo usar el mapa", expanded=False):
                st.markdown("""
                **🎨 Píxeles de colores**: Cada color representa un cultivo específico  
                **🗓️ Cambiar campaña**: Usa el dropdown arriba para ver otros años  
                **🔍 Zoom**: Toca dos veces o usa los controles para acercar/alejar  
                **🗺️ Capas**: Usa el control de capas (esquina superior derecha) para cambiar vista satelital/mapa  
                **📊 Leyenda**: Área y porcentaje de cada cultivo (esquina superior derecha del mapa)
                **🎛️ Transparencia**: Usa la barra deslizante (esquina inferior izquierda) para ajustar transparencia
                """)
            
        else:
            st.warning("⚠️ No hay tiles disponibles para esta campaña")
            # Fallback al visor anterior
            mapa_cultivos = crear_visor_cultivos_interactivo(aoi, df_cultivos)
            map_data = st_folium(mapa_cultivos, width=None, height=500, key="mapa_fallback")
    
    except Exception as e:
        st.error(f"Error generando el mapa: {e}")
        st.info("El análisis se completó correctamente, pero no se pudo mostrar el mapa con tiles.")
    
    # DESCARGAS MEJORADAS CON KMZ PARA CUIT
    st.markdown("---")
    st.subheader("💾 Descargar Resultados")
    st.write("Descarga los resultados del análisis en diferentes formatos:")
    
    # Crear nombre base para archivos
    nombres_archivos = datos.get('nombres_archivos', ['analisis'])
    nombre_base = '_'.join(nombres_archivos) if nombres_archivos else 'analisis'
    # Limitar longitud del nombre
    if len(nombre_base) > 50:
        nombre_base = nombre_base[:50]
    
    # CSVs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_hectareas = f"{nombre_base}_hectareas_{timestamp}.csv"
        download_link_hectareas = get_download_link(df_cultivos, filename_hectareas, "📊 CSV - Hectáreas")
        st.markdown(download_link_hectareas, unsafe_allow_html=True)
        st.caption("📄 Cultivo, Campaña, Área")
    
    with col2:
        filename_porcentajes = f"{nombre_base}_porcentajes_{timestamp}.csv"
        download_link_porcentajes = get_download_link(df_display, filename_porcentajes, "🔄 CSV - Rotación")
        st.markdown(download_link_porcentajes, unsafe_allow_html=True)
        st.caption("📄 Porcentajes por campaña")
    
    # KMZ para análisis por CUIT
    with col3:
        if fuente in ['CUIT', 'CUIT_INDIVIDUAL'] and 'poligonos_data' in datos:
            filename_kmz = f"{nombre_base}_campos_{timestamp}.kmz"
            kmz_buffer = generar_kmz_desde_cuit(datos['poligonos_data'], nombre_base)
            if kmz_buffer:
                st.download_button(
                    label="🗺️ KMZ - Campos",
                    data=kmz_buffer,
                    file_name=filename_kmz,
                    mime="application/vnd.google-earth.kmz"
                )
                st.caption("📄 Coordenadas de campos")
        elif tipo_analisis == 'individual':
            # Para análisis individual, generar KMZ del campo actual
            filename_kmz = f"{nombre_base}_campo_{resultado_campo['campo_numero']}_{timestamp}.kmz"
            campo_individual = [resultado_campo]  # Convertir a lista
            kmz_buffer = generar_kmz_desde_cuit([{
                'coords': resultado_campo['coords'],
                'titular': resultado_campo['campo_nombre'],
                'localidad': resultado_campo['campo_localidad'],
                'superficie': resultado_campo['campo_superficie']
            }], f"campo_{resultado_campo['campo_numero']}")
            if kmz_buffer:
                st.download_button(
                    label="🏡 KMZ - Campo",
                    data=kmz_buffer,
                    file_name=filename_kmz,
                    mime="application/vnd.google-earth.kmz"
                )
                st.caption("📄 Campo seleccionado")
    
    # RESUMEN FINAL PERSISTENTE
    st.subheader("📈 Resumen por Campaña")
    pivot_summary = df_cultivos.pivot_table(
        index='Cultivo', 
        columns='Campaña', 
        values='Área (ha)', 
        aggfunc='sum', 
        fill_value=0
    )
    pivot_summary['Promedio'] = pivot_summary.mean(axis=1).round(1)
    pivot_filtered = pivot_summary[pivot_summary['Promedio'] > 0].sort_values('Promedio', ascending=False)
    st.dataframe(pivot_filtered, use_container_width=True)
    
    # Mensaje final
    st.markdown("---")
    st.success("✅ **Todos los resultados están listos y disponibles para descarga**")
    
    # Botón para limpiar resultados
    if st.button("🗑️ Limpiar Resultados", help="Borra los resultados para hacer un nuevo análisis"):
        st.session_state.analisis_completado = False
        st.session_state.resultados_analisis = None
        # NO usar st.rerun() para evitar salto de pestañas

def mostrar_resultados_inundacion():
    """Muestra los resultados del análisis de inundación"""
    st.markdown("---")
    st.markdown("## 🌊 Resultados del Análisis de Riesgo Hídrico")
    
    # Extraer datos de session state
    datos = st.session_state.resultados_analisis
    resultado_inundacion = datos['resultado_inundacion']
    config_analisis = datos.get('config_analisis', {})
    
    # Mostrar información del análisis
    st.info(f"📋 **Análisis de Riesgo Hídrico**: {datos.get('archivo_info', 'Archivos KMZ')}")
    
    # MÉTRICAS PRINCIPALES
    st.markdown("### 📊 Métricas de Riesgo")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Área Analizada", 
            f"{resultado_inundacion['area_total_ha']:,.1f} ha"
        )
    
    with col2:
        st.metric(
            "Riesgo Promedio", 
            f"{resultado_inundacion['riesgo_promedio']:.1f}%",
            help="Porcentaje promedio de área inundada por año"
        )
    
    with col3:
        categoria = resultado_inundacion['categoria_riesgo']
        color_categoria = {
            'Bajo': 'normal',
            'Medio': 'inverse',
            'Alto': 'off', 
            'Muy Alto': 'off'
        }.get(categoria, 'normal')
        
        st.metric(
            "Categoría de Riesgo", 
            categoria,
            help=f"Clasificación basada en riesgo promedio de {resultado_inundacion['riesgo_promedio']:.1f}%"
        )
    
    with col4:
        st.metric(
            "Probabilidad de Evento", 
            f"{resultado_inundacion['probabilidad_evento']:.1f}%",
            help=f"Probabilidad de evento significativo (>{config_analisis.get('umbral_inundacion', 20)}%)"
        )
    
    # ANÁLISIS TEMPORAL
    st.markdown("### 📅 Análisis Temporal")
    
    if 'df_inundacion' in resultado_inundacion:
        df_inundacion = resultado_inundacion['df_inundacion']
        
        # Gráfico de evolución temporal
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Gráfico de barras con colores según severidad
        colors = ['red' if x > 40 else 'orange' if x > 20 else 'lightblue' for x in df_inundacion['Porcentaje Inundación']]
        
        ax.bar(df_inundacion['Año'], df_inundacion['Porcentaje Inundación'], color=colors, alpha=0.7)
        ax.axhline(y=config_analisis.get('umbral_inundacion', 20), color='red', linestyle='--', alpha=0.5, label='Umbral de Riesgo')
        ax.set_xlabel('Año')
        ax.set_ylabel('Porcentaje de Área Inundada (%)')
        ax.set_title('Evolución del Riesgo de Inundación por Año')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
        
        # Tabla de resultados por año
        st.markdown("### 📋 Detalle por Año")
        st.dataframe(df_inundacion, use_container_width=True)
    
    # EVENTOS SIGNIFICATIVOS
    if resultado_inundacion['eventos_significativos']:
        st.markdown("### ⚠️ Eventos Significativos")
        
        for evento in resultado_inundacion['eventos_significativos']:
            severity_color = {
                'Alta': '🔴',
                'Media': '🟠', 
                'Baja': '🟡'
            }.get(evento['severidad'], '🔵')
            
            st.warning(f"{severity_color} **Año {evento['año']}**: {evento['porcentaje']:.1f}% inundado ({evento['area_ha']:.1f} ha) - Severidad: {evento['severidad']}")
    else:
        st.success("✅ **No se detectaron eventos significativos de inundación** en el período analizado")
    
    # MAPA DE RIESGO
    if 'mapa_riesgo' in resultado_inundacion and resultado_inundacion['mapa_riesgo']:
        st.markdown("### 🗺️ Mapa de Riesgo Hídrico")
        st.write("Visualización de eventos de inundación en el área analizada:")
        
        # Mostrar el mapa
        map_data = st_folium(resultado_inundacion['mapa_riesgo'], width=None, height=500, key="mapa_riesgo_hidrico")
        
        # Explicación del mapa
        with st.expander("💡 Cómo interpretar el mapa"):
            st.markdown("""
            **🔴 Círculos rojos**: Eventos de alta severidad (>40% inundado)  
            **🟠 Círculos naranjas**: Eventos de severidad media (20-40% inundado)  
            **🟡 Círculos amarillos**: Eventos de baja severidad (<20% inundado)  
            **📏 Tamaño del círculo**: Proporcional al porcentaje de área inundada  
            **🔵 Polígono azul**: Área total analizada
            """)
    
    # RECOMENDACIONES
    st.markdown("### 💡 Recomendaciones")
    
    riesgo_promedio = resultado_inundacion['riesgo_promedio']
    
    if riesgo_promedio < 10:
        st.success("""
        **✅ Riesgo Bajo**: El área presenta bajo riesgo de inundación
        - Monitoreo preventivo cada 2-3 años
        - Mantenimiento básico de drenajes
        - Cultivos sin restricciones especiales
        """)
    elif riesgo_promedio < 25:
        st.warning("""
        **⚠️ Riesgo Medio**: Requiere atención y medidas preventivas
        - Monitoreo anual durante época de lluvias
        - Mejoras en sistema de drenaje
        - Considerar cultivos resistentes a encharcamiento
        - Seguro agrícola recomendado
        """)
    elif riesgo_promedio < 50:
        st.error("""
        **🚨 Riesgo Alto**: Implementar medidas de mitigación urgentes
        - Monitoreo continuo con sensores
        - Infraestructura de drenaje robusta
        - Cultivos adaptados a condiciones hídricas variables
        - Seguro agrícola obligatorio
        - Planes de contingencia para eventos extremos
        """)
    else:
        st.error("""
        **💀 Riesgo Muy Alto**: Área crítica - considerar cambio de uso
        - Evaluación técnica especializada
        - Posible no aptitud para agricultura tradicional
        - Considerar actividades ganaderas o forestales
        - Seguro agrícola con cobertura especial
        - Monitoreo meteorológico avanzado
        """)
    
    # DESCARGAS
    st.markdown("---")
    st.markdown("### 💾 Descargar Resultados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'df_inundacion' in resultado_inundacion:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analisis_inundacion_{timestamp}.csv"
            csv_data = resultado_inundacion['df_inundacion'].to_csv(index=False)
            
            st.download_button(
                label="📊 Descargar CSV - Análisis de Inundación",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                help="Datos detallados del análisis de riesgo hídrico"
            )
    
    with col2:
        # Crear resumen ejecutivo
        resumen = f"""
ANÁLISIS DE RIESGO HÍDRICO
=========================

Área Analizada: {resultado_inundacion['area_total_ha']:,.1f} ha
Años Analizados: {resultado_inundacion['años_analizados']}
Período: {config_analisis.get('anos_analisis', (2005, 2025))}

MÉTRICAS DE RIESGO:
- Riesgo Promedio: {resultado_inundacion['riesgo_promedio']:.1f}%
- Riesgo Máximo: {resultado_inundacion['riesgo_maximo']:.1f}%
- Categoría: {resultado_inundacion['categoria_riesgo']}
- Probabilidad de Evento: {resultado_inundacion['probabilidad_evento']:.1f}%

EVENTOS SIGNIFICATIVOS: {len(resultado_inundacion['eventos_significativos'])}

Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        st.download_button(
            label="📄 Descargar Reporte Ejecutivo",
            data=resumen,
            file_name=f"reporte_riesgo_hidrico_{timestamp}.txt",
            mime="text/plain",
            help="Resumen ejecutivo del análisis de riesgo hídrico"
        )
    
    # Botón para limpiar resultados
    st.markdown("---")
    if st.button("🗑️ Limpiar Resultados", help="Borra los resultados para hacer un nuevo análisis", key="limpiar_inundacion"):
        st.session_state.analisis_completado = False
        st.session_state.resultados_analisis = None

if __name__ == "__main__":
    main()
