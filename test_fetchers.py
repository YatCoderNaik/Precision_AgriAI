import ee
import requests

def test_sources():
    try:
        ee.Initialize()
        lat, lon = 42.066, -93.633
        point = ee.Geometry.Point([lon, lat])
        
        print("--- Testing SoilGrid ---")
        soil_clay = ee.Image("projects/soilgrids-isric/clay_mean").select('clay_0-5cm_mean')
        clay = soil_clay.reduceRegion(reducer=ee.Reducer.mean(), geometry=point, scale=250, bestEffort=True).getInfo()
        print(f"Clay: {clay}")
        
        print("\n--- Testing Sentinel-2 (Single Search) ---")
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        img = s2.filterBounds(point).filterDate('2022-06-01', '2022-07-01').sort('CLOUDY_PIXEL_PERCENTAGE').first()
        if img:
            print(f"Found S2 Image: {img.id().getInfo()}")
        else:
            print("No S2 image found in range.")

        print("\n--- Testing Open-Meteo ---")
        res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true")
        print(f"Weather: {res.json().get('current_weather')}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sources()
