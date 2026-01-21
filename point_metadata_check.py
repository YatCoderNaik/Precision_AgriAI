import ee
try:
    ee.Initialize()
    asset_id = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
    col = ee.ImageCollection(asset_id)
    
    # Filter by a point first
    point = ee.Geometry.Point([-93.633, 42.066])
    filtered = col.filterBounds(point)
    
    size = filtered.size().getInfo()
    print(f"Number of images at this point: {size}")
    
    if size > 0:
        # List properties of these images
        images = filtered.toList(size).getInfo()
        for i, img_info in enumerate(images):
            props = img_info.get('properties', {})
            year = props.get('year', 'N/A')
            date = props.get('system:time_start', 'N/A')
            print(f"Image {i}: ID={img_info['id']}, Year={year}, system:time_start={date}")
    else:
        print("No images found at this specific point.")
        
except Exception as e:
    print(f"Error: {e}")
