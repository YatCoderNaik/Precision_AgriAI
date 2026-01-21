import ee
try:
    ee.Initialize()
    asset_id = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
    col = ee.ImageCollection(asset_id)
    print(f"Collection: {asset_id}")
    print(f"Size: {col.size().getInfo()}")
    
    # Try to get one image
    img = col.first()
    if img:
        print(f"First image ID: {img.id().getInfo()}")
        print(f"Bands: {img.bandNames().getInfo()[:5]}...")
    else:
        print("No images found in collection.")
except Exception as e:
    print(f"Error: {e}")
