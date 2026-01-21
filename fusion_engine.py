import requests
from poc_recommender import (
    get_alpha_earth_embedding, 
    get_sentinel2_data, 
    get_modis_ndvi, 
    get_soil_data,
    init_earth_engine
)

def get_weather_data(lat, lon):
    """Fetches real-time weather from Open-Meteo (Free)."""
    print(f"[INFO] Fetching Weather for Point({lat}, {lon})...")
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=precipitation_probability"
    try:
        response = requests.get(url)
        data = response.json()
        current = data.get('current_weather', {})
        return {
            "Temperature": current.get('temperature'),
            "WindSpeed": current.get('windspeed'),
            "WeatherCode": current.get('weathercode')
        }
    except Exception as e:
        print(f"[ERROR] Weather fetch failed: {e}")
        return None

def fuse_signals(lat, lon, crop, year=2022):
    """Orchestrates multi-source fetch and fuses them into a semantic context."""
    init_earth_engine()
    
    results = {}
    
    # GEE Core
    results['AlphaEarth'] = get_alpha_earth_embedding(lat, lon, year)
    results['Sentinel2'] = get_sentinel2_data(lat, lon, year)
    results['MODIS'] = get_modis_ndvi(lat, lon, year)
    results['Soil'] = get_soil_data(lat, lon)
    
    # External APIs
    results['Weather'] = get_weather_data(lat, lon)
    
    # Semantic Fusion Logic
    # We turn these raw signals into a "Context String" for the LLM
    fusion_context = f"FIELD REPORT FUSION: {crop} at ({lat}, {lon})\n"
    
    if results['Soil']:
        s = results['Soil']
        fusion_context += f"- SOIL: pH {s.get('Soil_pH')}, Clay {s.get('Clay_Content_%')}% (Source: SoilGrid)\n"
    
    if results['MODIS']:
        m = results['MODIS']
        fusion_context += f"- VEGETATION HISTORY: Annual NDVI Median {m.get('NDVI_Annual_Median')} (Source: MODIS)\n"
        
    if results['Weather']:
        w = results['Weather']
        fusion_context += f"- CURRENT WEATHER: Temp {w.get('Temperature')}°C, Wind {w.get('WindSpeed')}km/h\n"
        
    if results['Sentinel2']:
        s2 = results['Sentinel2']
        rgb_nir = s2.get('RGB_NIR', [0,0,0,0])
        fusion_context += f"- OPTICAL SCAN: NIR {rgb_nir[3]}, Cloud Prob {s2.get('Cloud_Prob')}% (Source: Sentinel-2)\n"
        
    if results['AlphaEarth']:
        ae = results['AlphaEarth']
        avg_ae = sum(ae)/len(ae) if ae else 0
        fusion_context += f"- ALPHA EARTH SIGNATURE: 64-dim latent average {avg_ae:.4f} (Source: DeepMind Foundation Model)\n"

    return fusion_context, results

if __name__ == "__main__":
    # Internal Test
    lat, lon = 42.066, -93.633
    context, raw = fuse_signals(lat, lon, "Corn")
    print("\n" + "="*50)
    print("FUSED CONTEXT FOR LLM:")
    print(context)
    print("="*50)
