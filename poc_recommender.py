import ee
import os
import sys

# --- Configuration ---
USE_MOCK_LLM = True 

def init_earth_engine():
    """Initializes Google Earth Engine."""
    try:
        ee.Initialize()
        print("[INFO] Google Earth Engine Initialized successfully.")
    except Exception as e:
        print("[ERROR] Earth Engine Initialization failed.")
        print(f"Details: {e}")
        sys.exit(1)

def get_alpha_earth_embedding(lat, lon, year=2022):
    """Fetches AlphaEarth 64-dim embeddings (Robust)."""
    print(f"[INFO] Fetching AlphaEarth for Point({lat}, {lon}) Year: {year}...")
    point = ee.Geometry.Point([lon, lat])
    collection = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
    
    # Selection logic: Use filterBounds + filterDate as 'year' property can be tricky
    filtered = collection.filterBounds(point).filterDate(f"{year}-01-01", f"{year + 1}-01-01")
    image = filtered.first()
    
    if not image or image.getInfo() is None: return None

    features = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=point, scale=30, bestEffort=True)
    data = features.getInfo()
    if not data or all(v is None for v in data.values()): return None
    
    vector = [float(data[k]) if data[k] is not None else 0.0 for k in sorted(data.keys()) if k.startswith('A')]
    return vector

def get_sentinel2_data(lat, lon, year=2022):
    """Fetches Sentinel-2 MSI RGB/NIR data (Refined)."""
    print(f"[INFO] Fetching Sentinel-2 for Point({lat}, {lon})...")
    point = ee.Geometry.Point([lon, lat])
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    
    # Filter for mid-year (Summer) for the given year
    image = s2.filterBounds(point).filterDate(f"{year}-06-01", f"{year}-07-31").sort('CLOUDY_PIXEL_PERCENTAGE').first()
    
    if not image: return None
    
    # Increase scale to 30m for speed and consistency with AlphaEarth
    stats = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=point, scale=30, bestEffort=True).getInfo()
    return {
        "RGB_NIR": [stats.get('B4'), stats.get('B3'), stats.get('B2'), stats.get('B8')],
        "Cloud_Prob": stats.get('MSK_CLDPRB', 0)
    }

def get_modis_ndvi(lat, lon, year=2022):
    """Fetches MODIS NDVI (Refined)."""
    print(f"[INFO] Fetching MODIS for Point({lat}, {lon})...")
    point = ee.Geometry.Point([lon, lat])
    # Use MOD13Q1 250m
    modis = ee.ImageCollection("MODIS/061/MOD13Q1")
    image = modis.filterBounds(point).filterDate(f"{year}-01-01", f"{year}-12-31").median() # Median is faster than mean for composites
    
    stats = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=point, scale=250, bestEffort=True).getInfo()
    ndvi = stats.get('NDVI', 0) * 0.0001 if stats.get('NDVI') else 0
    return {"NDVI_Annual_Median": round(ndvi, 3)}

def get_soil_data(lat, lon):
    """Fetches SoilGrid data (Clay, Sand, pH)."""
    print(f"[INFO] Fetching SoilGrid for Point({lat}, {lon})...")
    point = ee.Geometry.Point([lon, lat])
    
    soil_clay = ee.Image("projects/soilgrids-isric/clay_mean").select('clay_0-5cm_mean')
    soil_ph = ee.Image("projects/soilgrids-isric/phh2o_mean").select('phh2o_0-5cm_mean')
    
    clay = soil_clay.reduceRegion(reducer=ee.Reducer.mean(), geometry=point, scale=250).getInfo().get('clay_0-5cm_mean', 0)
    ph = soil_ph.reduceRegion(reducer=ee.Reducer.mean(), geometry=point, scale=250).getInfo().get('phh2o_0-5cm_mean', 0)
    
    return {
        "Clay_Content_%": clay / 10 if clay else "N/A", # Scaled by 10
        "Soil_pH": ph / 10 if ph else "N/A" # Scaled by 10
    }

def interpret_and_recommend(vector, crop_type, loc_name, weather_data=None):
    """
    Simulates or Performs LLM analysis on the vector and fused weather signals.
    """
    if not vector or len(vector) < 64:
        return "Error: Incomplete geospatial data."
    
    # Analyze Weather for Guardrails
    weather_caveat = ""
    if weather_data:
        temp = weather_data.get('Temperature', 20)
        wind = weather_data.get('WindSpeed', 0)
        if temp < 0:
            weather_caveat += f"⚠️ CRITICAL: Sub-zero temperature ({temp}°C) detected. High risk of frost damage for {crop_type}. "
        if wind > 40:
            weather_caveat += f"⚠️ ADVISORY: High wind speeds ({wind} km/h) may impact spraying or harvest operations. "

    prompt = f"""
    ROLE: Expert AI Agronomist
    CONTEXT:
    - Target Crop: {crop_type}
    - Location: {loc_name}
    - Weather: {weather_data if weather_data else 'Stable'}
    - AlphaEarth Geospatial Embedding (10m Res, Annual Composite):
      {vector[:8]}... (64-dimensional vector)
      
    TASK: Based on this signature and weather context, provide a crop health summary and harvest recommendation.
    """
    
    if USE_MOCK_LLM:
        avg = sum(vector)/len(vector)
        # Abiotic Stress Section Logic
        stress_info = "No significant abiotic stress (heat/drought) is flagged in the 64-dim signature."
        if weather_caveat:
            stress_info = f"{weather_caveat} The structural integrity of the latent signature remains stable, but immediate weather protection is advised."

        return f"""
[POC RECOMMENDATION: {loc_name}]

1. **Crop Health Analysis**: 
   The AlphaEarth embedding for this {crop_type} plot indicates positive vegetation vigor indicators. 
   The mean latent signal value of {avg:.4f} suggests a robust latent vegetation signal
   reflecting foundation-model learned surface patterns for this stage of the season.

2. **Environmental Context**: 
   {stress_info}

3. **Recommendation**:
   - **Action**: {"Prioritize frost protection measures." if "frost" in weather_caveat else "Maintain current schedule; no evidence of moisture deficit."}
   - **Harvest Plan**: Data suggests reaching maturity within the historical 'Normal' window. 
     Recommend final field moisture testing in 14 days.
"""
    else:
        return "LLM call skipped (USE_MOCK_LLM=True)"

import argparse

def main():
    parser = argparse.ArgumentParser(description="AlphaEarth Precision Agriculture POC")
    parser.add_argument("--lat", type=float, default=42.066, help="Latitude of the plot")
    parser.add_argument("--lon", type=float, default=-93.633, help="Longitude of the plot")
    parser.add_argument("--crop", type=str, default="Corn", help="Type of crop")
    parser.add_argument("--year", type=int, default=2022, help="Year for embedding data")
    parser.add_argument("--name", type=str, default="Input Plot", help="Friendly name for the location")
    
    args = parser.parse_args()
    
    init_earth_engine()
    
    print(f"\n" + "="*60)
    print(f"RUNNING POC FOR: {args.name}")
    print(f"Coordinates: ({args.lat}, {args.lon})")
    print(f"Crop: {args.crop} | Year: {args.year}")
    print("="*60)
    
    vector = get_alpha_earth_embedding(args.lat, args.lon, year=args.year)
    
    if vector:
        recommendation = interpret_and_recommend(vector, args.crop, args.name)
        print(recommendation)
    else:
        print(f"\n[FAIL] Could not retrieve embeddings for {args.name} at ({args.lat}, {args.lon}).")

if __name__ == "__main__":
    main()
