import ee
import sys

def diagnose():
    try:
        ee.Initialize()
        print("GEE Initialized.")
    except Exception as e:
        print(f"Auth failed: {e}")
        return

    asset_id = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
    col = ee.ImageCollection(asset_id)
    
    try:
        size = col.size().getInfo()
        print(f"Collection: {asset_id}")
        print(f"Size: {size}")
        
        # Get list of unique years
        years = col.aggregate_array('year').distinct().sort().getInfo()
        print(f"Available Years: {years}")
        
        # Check first image properties
        first_img = col.first()
        info = first_img.getInfo()
        print(f"First Image ID: {info['id']}")
        print(f"Bands: {[b['id'] for b in info['bands']]}")
        
        # Test a known coordinate for 2021 (a safe year)
        test_year = 2021
        test_point = ee.Geometry.Point([-93.633, 42.066])
        img_2021 = col.filter(ee.Filter.eq('year', test_year)).first()
        
        if img_2021:
            print(f"Testing 2021 at Ames, Iowa...")
            data = img_2021.reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=test_point,
                scale=100  # Try 100m scale for robustness
            ).getInfo()
            print(f"Data for 2021 (sample result): {list(data.values())[:3]}...")
        else:
            print(f"No image found for year {test_year}")

    except Exception as e:
        print(f"Error during diagnosis: {e}")

if __name__ == "__main__":
    diagnose()
