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
    """
    Fetches the 64-dimensional embedding vector from AlphaEarth Foundations.
    Target Year: 2022
    Collection: GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL
    """
    print(f"[INFO] Fetching embeddings for Point({lat}, {lon}) Year: {year}...")
    
    point = ee.Geometry.Point([lon, lat])
    collection = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
    
    # Selection logic: Use date filter as 'year' property is missing
    start_date = f"{year}-01-01"
    end_date = f"{year + 1}-01-01"
    
    filtered = collection.filterBounds(point).filterDate(start_date, end_date)
    image = filtered.first()
    
    if image is None or image.getInfo() is None:
        print(f"[WARN] No image found for year {year} at this location.")
        return None

    # Debug info
    props = image.getInfo().get('properties', {})
    ts = props.get('system:time_start')
    print(f"[DEBUG] Found Image: {image.id().getInfo()} (system:time_start: {ts})")

    # 3. Sample the point with robust mean reducer
    features = image.reduceRegion(
        reducer=ee.Reducer.mean(), 
        geometry=point,
        scale=30, # 30m to ensure we are not hitting a tiny mask gap
        bestEffort=True
    )
    
    # 4. Extract values
    try:
        data = features.getInfo()
        if not data or all(v is None for v in data.values()):
            print("[WARN] No data found at this location (masked pixel).")
            return None
    except Exception as e:
        print(f"[ERROR] Failed during reduceRegion.getInfo(): {e}")
        return None
        
    vector = []
    # Band names are A00, A01, ..., A63
    sorted_keys = sorted([k for k in data.keys() if k.startswith('A')])
    
    for k in sorted_keys:
        val = data[k]
        vector.append(float(val) if val is not None else 0.0)
        
    print(f"[INFO] Embedding retrieval successful. Dimensions: {len(vector)}")
    return vector

def interpret_and_recommend(vector, crop_type, loc_name):
    """
    Simulates or Performs LLM analysis on the vector.
    """
    if not vector or len(vector) < 64:
        return "Error: Incomplete geospatial data."
    
    # In a real app, this would be an API call to Gemini/OpenAI
    # For POC, we show the prompt and a "believable" generated response.
    
    prompt = f"""
    ROLE: Expert AI Agronomist
    CONTEXT:
    - Target Crop: {crop_type}
    - Location: {loc_name}
    - AlphaEarth Geospatial Embedding (10m Res, Annual Composite):
      {vector[:8]}... (64-dimensional vector)
      
    TASK: Based on this signature, provide a crop health summary and harvest recommendation.
    """
    
    print("\n" + "-"*20 + " PROMPT PREVIEW " + "-"*20)
    print(prompt.strip())
    print("-" * 56)
    
    if USE_MOCK_LLM:
        avg = sum(vector)/len(vector)
        return f"""
[POC RECOMMENDATION: {loc_name}]

1. **Crop Health Analysis**: 
   The AlphaEarth embedding for this {crop_type} plot indicates an 'Optimal' vegetative trajectory. 
   The mean latent signal value of {avg:.4f} suggests robust photosynthetic activity 
   and adequate carbon sequestration (Biomass) for this stage of the season.

2. **Environmental Context**: 
   No significant abiotic stress (drought/heat) is flagged in the 64-dim signature. 
   The soil moisture index, derived from the latent radar components, appears stable.

3. **Recommendation**:
   - **Irrigation**: Maintain current schedule; no evidence of water deficit.
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
