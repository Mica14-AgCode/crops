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
        
        capas = {}
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
        
        status_text.text("Análisis completado!")
        progress_bar.progress(1.0)
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
        return pd.DataFrame(resultados_todas_campanas), area_total
        
    except Exception as e:
        st.error(f"Error en análisis de cultivos: {e}")
        return None, 0

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
    Genera código JavaScript completo para Google Earth Engine Code Editor
    que permite visualizar los cultivos por campaña con todas las funcionalidades
    """
    
    # Obtener todas las coordenadas del AOI para el código
    aoi_definition = None
    coordenadas_usuario_exitosas = False
    
    try:
        print("🔍 Extrayendo coordenadas del KMZ del usuario...")
        aoi_info = aoi.getInfo()
        features = aoi_info.get("features", [])
        
        print(f"📊 Número de features encontradas: {len(features)}")
        
        # Construir el código JavaScript para todas las features
        aoi_features_js = []
        
        for i, feature in enumerate(features):
            geom = feature.get("geometry", {})
            if geom.get("type") == "Polygon":
                coords = geom.get("coordinates", [[]])[0]  # Primer anillo
                if len(coords) >= 3:  # Mínimo 3 puntos para un polígono válido
                    coords_str = ", ".join([f"[{c[0]}, {c[1]}]" for c in coords])
                    aoi_features_js.append(f"  ee.Feature(ee.Geometry.Polygon([[{coords_str}]]))")
                    print(f"✅ Polígono {i+1}: {len(coords)} coordenadas extraídas")
                else:
                    print(f"⚠️ Polígono {i+1}: Insuficientes coordenadas ({len(coords)})")
        
        if aoi_features_js:
            aoi_definition = "var aoi = ee.FeatureCollection([\n" + ",\n".join(aoi_features_js) + "\n]);"
            coordenadas_usuario_exitosas = True
            print(f"✅ Coordenadas del usuario extraídas exitosamente: {len(aoi_features_js)} polígonos")
        else:
            print("⚠️ No se encontraron polígonos válidos en las features")
        
    except Exception as e:
        print(f"❌ Error extrayendo coordenadas del usuario: {e}")
        import traceback
        traceback.print_exc()
    
    # Si no se pudieron extraer las coordenadas del usuario, usar fallback
    if not coordenadas_usuario_exitosas:
        print("🔄 Usando coordenadas de fallback (genéricas)")
        aoi_definition = """var aoi = ee.FeatureCollection([
  ee.Feature(ee.Geometry.Polygon([[[-60.0, -34.0], [-59.9, -34.0], [-59.9, -33.9], [-60.0, -33.9], [-60.0, -34.0]]]))
]);"""
    
    # Agregar comentario informativo sobre el origen de las coordenadas
    if coordenadas_usuario_exitosas:
        coord_origin_comment = "// ✅ AOI extraído automáticamente del archivo KMZ subido por el usuario"
    else:
        coord_origin_comment = "// ⚠️ AOI de ejemplo (no se pudieron extraer coordenadas del KMZ usuario)"
    
    codigo_js = f"""// ===================================================================
// VISOR COMPLETO DE CULTIVOS POR CAMPAÑA - GOOGLE EARTH ENGINE
// Generado automáticamente por la aplicación web de rotación de cultivos
// Incluye análisis para campañas 2019-2020 hasta 2023-2024
// ===================================================================

// ===== DEFINICIÓN DEL ÁREA DE INTERÉS (AOI) =====
{coord_origin_comment}
{aoi_definition}

// ===== CONFIGURACIÓN INICIAL =====
// Centrar el mapa en el AOI
Map.centerObject(aoi, 10);

// Agregar el contorno del AOI al mapa
Map.addLayer(aoi, {{color: 'red', fillOpacity: 0, width: 2}}, 'Área de Interés');

// Calcular el área total del AOI en hectáreas
var areaTotalAOI = aoi.geometry().transform('EPSG:5345', 1).area(1).divide(10000);

// Calcular el área de cada píxel en metros cuadrados
var areaPixeles = ee.Image.pixelArea().reproject('EPSG:5345', null, 30);

// Mostrar el área total del AOI en la consola
print('Área total del AOI (hectáreas):', areaTotalAOI);

// ===== DEFINICIÓN DE PALETAS Y NOMBRES DE CULTIVOS =====

// Paleta de colores unificada para todos los cultivos
var nuevaPaleta = [
  '#ffffff', // 0: Blanco (no usado)
  '#ffffff', // 1: Blanco (no usado)
  '#ffffff', // 2: Blanco (no usado)
  '#ffffff', // 3: Blanco (no usado)
  '#ffffff', // 4: Blanco (no usado)
  '#ffffff', // 5: Blanco (no usado)
  '#ffffff', // 6: Blanco (no usado)
  '#ffffff', // 7: Blanco (no usado)
  '#ffffff', // 8: Blanco (no usado)
  '#ffffff', // 9: Blanco (no usado)
  '#0042ff', // 10: Maíz (Azul)
  '#339820', // 11: Soja 1ra (Verde)
  '#FFFF00', // 12: Girasol (Amarillo)
  '#f022db', // 13: Poroto
  '#ffffff', // 14: No usado (Caña de Azúcar ahora es ID 19)
  '#b7b9bd', // 15: Algodón
  '#FFA500', // 16: Maní (Naranja)
  '#1d1e33', // 17: Arroz
  '#FF0000', // 18: Sorgo GR (Rojo)
  '#a32102', // 19: Caña de Azúcar / Girasol-CV (Rojo oscuro)
  '#ffffff', // 20: No usado
  '#646b63', // 21: Barbecho
  '#e6f0c2', // 22: No agrícola
  '#612517', // 23: No usado
  '#94d200', // 24: No usado
  '#ffffff', // 25: No usado
  '#8A2BE2', // 26: Papa (Violeta)
  '#ffffff', // 27: No usado
  '#800080', // 28: Verdeo de Sorgo (Morado)
  '#ffffff', // 29: No usado
  '#D2B48C', // 30: Tabaco (Marrón claro)
  '#87CEEB', // 31: CI-Maíz 2da (Azul claro/celeste)
  '#90ee90'  // 32: CI-Soja 2da (Verde claro/fluor)
];

// Valor máximo para la paleta
var maxValor = 32;

// Función para calcular áreas y porcentajes con leyenda
var calcularAreas = function(capa, cultivos, titulo, posicionLeyenda) {{
  var areasCultivos = [];

  // Calcular áreas y porcentajes
  Object.keys(cultivos).forEach(function(cultivoId) {{
    var nombre = cultivos[cultivoId];
    var color = nuevaPaleta[cultivoId];

    // Si el nombre es "XXX", omitir de la leyenda
    if (nombre === 'XXX') {{
      return; // Salir de esta iteración
    }}

    // Crear máscara para el cultivo
    var mascaraCultivo = capa.eq(Number(cultivoId));

    // Calcular área del cultivo
    var areaCultivo = areaPixeles.multiply(mascaraCultivo).reduceRegion({{
      reducer: ee.Reducer.sum(),
      geometry: aoi.geometry(),
      scale: 30, // Resolución de 30 metros
      maxPixels: 1e13
    }}).get('area');

    // Convertir a hectáreas y redondear a entero
    areaCultivo = ee.Number(areaCultivo).divide(10000).round();

    // Calcular porcentaje respecto al AOI
    var porcentajeCultivo = areaCultivo.divide(areaTotalAOI).multiply(100).round();

    // Añadir a las listas
    areasCultivos.push({{
      'Cultivo': nombre,
      'Área (ha)': areaCultivo,
      'Porcentaje (%)': porcentajeCultivo,
      'Color': color
    }});
  }});

  // Evaluar las áreas y crear la leyenda
  ee.List(areasCultivos).evaluate(function(result) {{
    // Ordenar las áreas de mayor a menor
    result.sort(function(a, b) {{
      return b['Área (ha)'] - a['Área (ha)'];
    }});

    // Crear la leyenda
    var legend = ui.Panel({{
      style: {{
        position: posicionLeyenda,
        padding: '8px 15px',
        backgroundColor: 'white',
        border: '1px solid #ccc'
      }}
    }});

    var legendTitle = ui.Label({{
      value: titulo,
      style: {{
        fontWeight: 'bold',
        fontSize: '18px',
        margin: '0 0 4px 0',
        padding: '0'
      }}
    }});
    legend.add(legendTitle);

    // Añadir cada cultivo y su área a la leyenda (solo si el área es >= 1 Ha)
    result.forEach(function(item) {{
      var nombre = item['Cultivo'];
      var area = item['Área (ha)'];
      var porcentaje = item['Porcentaje (%)'];
      var color = item['Color'];

      if (area >= 1) {{ // Solo agregar a la leyenda si el área es >= 1 Ha
        var legendItem = ui.Panel({{
          widgets: [
            ui.Label({{
              style: {{backgroundColor: color, padding: '8px', margin: '0 0 4px 0'}}
            }}),
            ui.Label({{
              value: nombre + ' ' + (area || 0) + ' Ha (' + (porcentaje || 0) + '%)',
              style: {{margin: '0 0 0 8px'}}
            }})
          ],
          layout: ui.Panel.Layout.flow('horizontal')
        }});

        legend.add(legendItem);
      }}
    }});

    // Añadir la leyenda al mapa
    Map.add(legend);
  }});
}};

// ===== CAMPAÑA 2019-2020 =====
print('Procesando campaña 2019-2020...');

// Cargar las capas de cultivos
var inv19 = ee.Image('projects/carbide-kayak-459911-n3/assets/inv19');
var ver20 = ee.Image('projects/carbide-kayak-459911-n3/assets/ver20');

// Recortar las capas al AOI
var inv19_aoi = inv19.clip(aoi);
var ver20_aoi = ver20.clip(aoi);

// Crear capa combinada para 2019-2020
var nuevaCapa1920 = ee.Image().expression(
  '(verano == 10 && (invierno == 0 || invierno == 6)) ? 31 : ' + // CI-Maíz
  '(verano == 11 && (invierno == 0 || invierno == 6)) ? 32 : ' + // CI-Soja
  '(verano == 10) ? 10 : ' + // Maíz
  '(verano == 11) ? 11 : ' + // Soja 1ra
  '(verano == 14) ? 19 : ' + // Caña de azúcar (reasignar ID 14 a 19)
  '(verano == 19) ? 19 : ' + // Girasol-CV (19)
  'verano', // Para otros cultivos
  {{
    'verano': ver20_aoi,
    'invierno': inv19_aoi
  }}
);

// Nombres de cultivos para 2019-2020
var nombresNuevaCapa1920 = {{
  10: 'Maíz',
  11: 'Soja 1ra',
  12: 'Girasol',
  13: 'Poroto',
  15: 'Algodón',
  16: 'Maní',
  17: 'Arroz',
  18: 'Sorgo GR',
  19: 'Girasol-CV',
  21: 'Barbecho',
  22: 'No agrícola',
  31: 'CI-Maíz 2da',
  32: 'CI-Soja 2da'
}};

// Visualizar la capa 2019-2020
Map.addLayer(nuevaCapa1920, {{min: 0, max: maxValor, palette: nuevaPaleta, opacity: 0.5}}, 'Cultivos 2019/2020', false);

// ===== CAMPAÑA 2020-2021 =====
print('Procesando campaña 2020-2021...');

var inv20 = ee.Image('projects/carbide-kayak-459911-n3/assets/inv20');
var ver21 = ee.Image('projects/carbide-kayak-459911-n3/assets/ver21');

var inv20_aoi = inv20.clip(aoi);
var ver21_aoi = ver21.clip(aoi);

var nuevaCapa2021 = ee.Image().expression(
  '(verano == 10 && (invierno == 0 || invierno == 16 || invierno == 24)) ? 31 : ' + // CI-Maíz
  '(verano == 11 && (invierno == 0 || invierno == 16 || invierno == 24)) ? 32 : ' + // CI-Soja
  '(verano == 10) ? 10 : ' + // Maíz
  '(verano == 11) ? 11 : ' + // Soja 1ra
  '(verano == 14) ? 19 : ' + // Caña de azúcar (reasignar ID 14 a 19)
  '(verano == 19 || verano == 26) ? verano : ' + // Girasol-CV (19) y Papa (26)
  'verano', // Para otros cultivos
  {{
    'verano': ver21_aoi,
    'invierno': inv20_aoi
  }}
);

var nombresNuevaCapa2021 = {{
  10: 'Maíz',
  11: 'Soja 1ra',
  12: 'Girasol',
  13: 'Poroto',
  15: 'Algodón',
  16: 'Maní',
  17: 'Arroz',
  18: 'Sorgo GR',
  19: 'Girasol-CV',
  21: 'Barbecho',
  22: 'No agrícola',
  26: 'Papa',
  28: 'Verdeo de Sorgo',
  31: 'CI-Maíz 2da',
  32: 'CI-Soja 2da'
}};

Map.addLayer(nuevaCapa2021, {{min: 0, max: maxValor, palette: nuevaPaleta, opacity: 0.5}}, 'Cultivos 2020/2021', false);

// ===== CAMPAÑA 2021-2022 =====
print('Procesando campaña 2021-2022...');

var inv21 = ee.Image('projects/carbide-kayak-459911-n3/assets/inv21');
var ver22 = ee.Image('projects/carbide-kayak-459911-n3/assets/ver22');

var inv21_aoi = inv21.clip(aoi);
var ver22_aoi = ver22.clip(aoi);

var nuevaCapa2122 = ee.Image().expression(
  '(verano == 10 && (invierno == 6 || invierno == 16 || invierno == 24)) ? 31 : ' + // CI-Maíz
  '(verano == 11 && (invierno == 6 || invierno == 16 || invierno == 24)) ? 32 : ' + // CI-Soja
  '(verano == 10) ? 10 : ' + // Maíz
  '(verano == 11) ? 11 : ' + // Soja 1ra
  '(verano == 14) ? 19 : ' + // Caña de azúcar (reasignar ID 14 a 19)
  '(verano == 19 || verano == 26) ? verano : ' + // Caña (19) y Papa (26)
  'verano', // Para otros cultivos
  {{
    'verano': ver22_aoi,
    'invierno': inv21_aoi
  }}
);

var nombresNuevaCapa2122 = {{
  10: 'Maíz',
  11: 'Soja 1ra',
  12: 'Girasol',
  13: 'Poroto',
  15: 'Algodón',
  16: 'Maní',
  17: 'Arroz',
  18: 'Sorgo GR',
  19: 'Caña de Azúcar',
  21: 'Barbecho',
  22: 'No agrícola',
  26: 'Papa',
  28: 'Verdeo de Sorgo',
  31: 'CI-Maíz 2da',
  32: 'CI-Soja 2da'
}};

Map.addLayer(nuevaCapa2122, {{min: 0, max: maxValor, palette: nuevaPaleta, opacity: 0.5}}, 'Cultivos 2021/2022', false);

// ===== CAMPAÑA 2022-2023 =====
print('Procesando campaña 2022-2023...');

var inv22 = ee.Image('projects/carbide-kayak-459911-n3/assets/inv22');
var ver23 = ee.Image('projects/carbide-kayak-459911-n3/assets/ver23');

var inv22_aoi = inv22.clip(aoi);
var ver23_aoi = ver23.clip(aoi);

var nuevaCapa2223 = ee.Image().expression(
  '(verano == 10 && (invierno == 6 || invierno == 16 || invierno == 24)) ? 31 : ' + // CI-Maíz
  '(verano == 11 && (invierno == 6 || invierno == 16 || invierno == 24)) ? 32 : ' + // CI-Soja
  '(verano == 10) ? 10 : ' + // Maíz
  '(verano == 11) ? 11 : ' + // Soja 1ra
  '(verano == 14) ? 19 : ' + // Caña de azúcar (reasignar ID 14 a 19)
  '(verano == 19 || verano == 26) ? verano : ' + // Caña (19) y Papa (26)
  'verano', // Para otros cultivos
  {{
    'verano': ver23_aoi,
    'invierno': inv22_aoi
  }}
);

var nombresNuevaCapa2223 = {{
  10: 'Maíz',
  11: 'Soja 1ra',
  12: 'Girasol',
  13: 'Poroto',
  15: 'Algodón',
  16: 'Maní',
  17: 'Arroz',
  18: 'Sorgo GR',
  19: 'Caña de Azúcar',
  21: 'Barbecho',
  22: 'No agrícola',
  26: 'Papa',
  28: 'Verdeo de Sorgo',
  30: 'Tabaco',
  31: 'CI-Maíz 2da',
  32: 'CI-Soja 2da'
}};

Map.addLayer(nuevaCapa2223, {{min: 0, max: maxValor, palette: nuevaPaleta, opacity: 0.5}}, 'Cultivos 2022/2023', false);

// ===== CAMPAÑA 2023-2024 =====
print('Procesando campaña 2023-2024...');

var inv23 = ee.Image('projects/carbide-kayak-459911-n3/assets/inv23');
var ver24 = ee.Image('projects/carbide-kayak-459911-n3/assets/ver24');

var inv23_aoi = inv23.clip(aoi);
var ver24_aoi = ver24.clip(aoi);

var nuevaCapa2324 = ee.Image().expression(
  '(verano == 10 && (invierno == 6 || invierno == 16 || invierno == 24)) ? 31 : ' + // CI-Maíz
  '(verano == 11 && (invierno == 6 || invierno == 16 || invierno == 24)) ? 32 : ' + // CI-Soja
  '(verano == 10) ? 10 : ' + // Maíz
  '(verano == 11) ? 11 : ' + // Soja 1ra
  '(verano == 14) ? 19 : ' + // Caña de azúcar (reasignar ID 14 a 19)
  '(verano == 19 || verano == 26) ? verano : ' + // Caña (19) y Papa (26)
  'verano', // Para otros cultivos
  {{
    'verano': ver24_aoi,
    'invierno': inv23_aoi
  }}
);

var nombresNuevaCapa2324 = {{
  10: 'Maíz',
  11: 'Soja 1ra',
  12: 'Girasol',
  13: 'Poroto',
  15: 'Algodón',
  16: 'Maní',
  17: 'Arroz',
  18: 'Sorgo GR',
  19: 'Caña de Azúcar',
  21: 'Barbecho',
  22: 'No agrícola',
  26: 'Papa',
  28: 'Verdeo de Sorgo',
  30: 'Tabaco',
  31: 'CI-Maíz 2da',
  32: 'CI-Soja 2da'
}};

Map.addLayer(nuevaCapa2324, {{min: 0, max: maxValor, palette: nuevaPaleta, opacity: 0.5}}, 'Cultivos 2023/2024', true);

// ===== ANÁLISIS DE ÁREAS PARA LA ÚLTIMA CAMPAÑA =====
// Calcular áreas y porcentajes para la campaña 2023-2024 (la más reciente)
calcularAreas(nuevaCapa2324, nombresNuevaCapa2324, 'Campaña 23-24', 'bottom-right');

// ===== INSTRUCCIONES Y INFORMACIÓN =====
print('===================================================================');
print('🌾 VISOR COMPLETO DE CULTIVOS - TODAS LAS CAMPAÑAS DISPONIBLES');
print('===================================================================');
print('');
print('✅ Capas cargadas exitosamente:');
print('   • Cultivos 2019/2020');
print('   • Cultivos 2020/2021');
print('   • Cultivos 2021/2022');
print('   • Cultivos 2022/2023');
print('   • Cultivos 2023/2024 (activada por defecto)');
print('');
print('🎛️ INSTRUCCIONES DE USO:');
print('   1. Usa el panel "Layers" (arriba a la derecha) para activar/desactivar capas');
print('   2. Solo una campaña visible a la vez para mejor visualización');
print('   3. La leyenda muestra los cultivos de la campaña 2023-2024');
print('   4. Usa el zoom para explorar áreas específicas');
print('');
print('🎨 CÓDIGO DE COLORES:');
print('   • Azul: Maíz');
print('   • Verde: Soja 1ra');  
print('   • Amarillo: Girasol');
print('   • Celeste: CI-Maíz 2da (Cultivo de Invierno + Maíz)');
print('   • Verde claro: CI-Soja 2da (Cultivo de Invierno + Soja)');
print('   • Beige: No agrícola');
print('   • Otros colores: Ver leyenda en pantalla');
print('');
print('📊 ÁREA TOTAL ANALIZADA:', areaTotalAOI, 'hectáreas');
print('');
print('🔗 Código generado automáticamente desde:');
print('   rotacion.streamlit.app');
print('===================================================================');
"""
    
    return codigo_js

def main():
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
        
        if st.button("🚀 Analizar Cultivos y Rotación", type="primary"):
            with st.spinner("Procesando archivos KMZ..."):
                todos_los_poligonos = []
                for uploaded_file in uploaded_files:
                    poligonos = procesar_kmz_uploaded(uploaded_file)
                    todos_los_poligonos.extend(poligonos)
                
                if not todos_los_poligonos:
                    st.error("❌ No se encontraron polígonos válidos en los archivos")
                    return
                
                st.info(f"📊 {len(todos_los_poligonos)} polígonos extraídos de {len(uploaded_files)} archivo(s)")
                
                aoi = crear_ee_feature_collection_web(todos_los_poligonos)
                
                if not aoi:
                    st.error("❌ No se pudo crear el área de interés")
                    return
                
                df_cultivos, area_total = analizar_cultivos_web(aoi)
                
                # Asegurar que siempre tengamos datos válidos para mostrar
                if df_cultivos is not None and not df_cultivos.empty:
                    st.markdown('<div class="results-section">', unsafe_allow_html=True)
                    st.subheader("📊 Resultados del Análisis")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Área Total", f"{area_total:.1f} ha")
                    with col2:
                        cultivos_detectados = df_cultivos[df_cultivos['Área (ha)'] > 0]['Cultivo'].nunique()
                        st.metric("Cultivos Detectados", cultivos_detectados)
                    with col3:
                        # CORRECCIÓN: Calcular área agrícola PROMEDIO por campaña
                        area_agricola_por_campana = df_cultivos[~df_cultivos['Cultivo'].str.contains('No agrícola', na=False)].groupby('Campaña')['Área (ha)'].sum()
                        area_agricola = area_agricola_por_campana.mean()
                        st.metric("Área Agrícola", f"{area_agricola:.1f} ha", help="Promedio de área agrícola por campaña")
                    with col4:
                        porcentaje_agricola = (area_agricola / area_total * 100) if area_total > 0 else 0
                        st.metric("% Agrícola", f"{porcentaje_agricola:.1f}%", help="Porcentaje promedio de área agrícola")
                    
                    fig, df_rotacion = generar_grafico_rotacion_web(df_cultivos)
                    
                    if fig is not None:
                        st.subheader("🎨 Gráfico de Rotación de Cultivos")
                        st.pyplot(fig)
                        
                        st.subheader("📋 Tabla de Rotación (%)")
                        df_display = df_rotacion.copy()
                        df_display = df_display.rename(columns={'Cultivo_Estandarizado': 'Cultivo'})
                        st.dataframe(df_display, use_container_width=True)
                        
                        
                        # ===== VISOR INTERACTIVO DE CULTIVOS =====
                        st.subheader("🗺️ Visor Interactivo de Cultivos")
                        st.write("Explora los cultivos detectados en cada campaña usando el mapa interactivo:")
                        
                        try:
                            # Crear visor de cultivos
                            mapa_cultivos = crear_visor_cultivos_interactivo(aoi, df_cultivos)
                            
                            # Mostrar el mapa usando streamlit-folium
                            map_data = st_folium(mapa_cultivos, width=700, height=500)
                            
                            st.info("💡 **Cómo usar el visor:**")
                            st.write("""
                            - 🔘 **Capas base**: Cambia entre vista satelital, híbrida o mapa
                            - 📅 **Cultivos por año**: Activa/desactiva las campañas en el control de capas
                            - 🖱️ **Click en marcadores**: Ver detalles de área y porcentaje por cultivo
                            - 🌾 **Colores**: Cada cultivo tiene su color específico (ver leyenda)
                            """)
                            
                        except Exception as e:
                            st.error(f"Error generando el visor de mapas: {e}")
                            st.info("El análisis de cultivos se completó exitosamente, pero no se pudo generar el mapa interactivo.")
                        st.subheader("💾 Descargar Resultados")
                        
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
                            st.caption("Úsalo en Google Earth Engine Code Editor")
                        
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
                        
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                else:
                    st.error("❌ No se pudieron analizar los cultivos")
                    st.warning("Verifica que el archivo KMZ contenga polígonos válidos")
                    st.info("Puedes intentar con otro archivo KMZ o verificar que el formato sea correcto")
    
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        🌾 Análisis de Rotación de Cultivos | Powered by Google Earth Engine & Streamlit
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 