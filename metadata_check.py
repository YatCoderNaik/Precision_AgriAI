import ee
try:
    ee.Initialize()
    asset_id = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
    col = ee.ImageCollection(asset_id)
    img = col.first()
    info = img.getInfo()
    print("Properties of the first image:")
    for k, v in info.get('properties', {}).items():
        print(f"  {k}: {v}")
    
    # Try to see if there is a 'year' property
    years = col.aggregate_array('year').distinct().getInfo()
    print(f"Unique 'year' values in collection: {years}")
    
except Exception as e:
    print(f"Error: {e}")
