# MapService - ISRO Bhuvan WMS Integration

## Overview

The MapService provides comprehensive geospatial functionality for the Precision AgriAI system, including:

- **ISRO Bhuvan WMS Integration**: Access to LISS III/IV satellite imagery and vector layers
- **Coordinate Validation**: Validates coordinates for Indian geographic regions with precision requirements
- **Hobli Detection**: Identifies administrative subdivisions (Hobli) from coordinates
- **Interactive Mapping**: Creates Folium maps with plot markers and jurisdiction boundaries
- **WMS Operations**: GetCapabilities, GetMap, and GetFeatureInfo support

## Features

### 1. Coordinate Validation

Validates coordinates against multiple criteria:

```python
from services.map_service import MapService

map_service = MapService()

# Validate coordinates
result = map_service.validate_coordinates(12.9716, 77.5946)

if result.is_valid:
    print(f"Valid coordinates: {result.normalized_coordinates}")
    print(f"Hobli: {result.hobli_name} ({result.hobli_id})")
    print(f"District: {result.district}, State: {result.state}")
else:
    print(f"Invalid: {result.error}")
```

**Validation Rules:**
- Latitude must be between -90 and 90 degrees
- Longitude must be between -180 and 180 degrees
- Coordinates must be within India's geographic bounds (6-37°N, 68-97°E)
- Minimum 4 decimal places precision required (~11m accuracy)
- Coordinates are normalized to configured precision

### 2. Hobli Boundary Detection

Detects administrative subdivision (Hobli) from coordinates:

```python
hobli_info = map_service.get_hobli_from_coordinates(12.9716, 77.5946)

print(f"Hobli ID: {hobli_info['hobli_id']}")
print(f"Hobli Name: {hobli_info['hobli_name']}")
print(f"District: {hobli_info['district']}")
print(f"State: {hobli_info['state']}")
```

**Supported Regions:**
- Karnataka: Bangalore, Mysore, Belgaum
- Tamil Nadu: Chennai, Coimbatore
- Andhra Pradesh: Vijayawada
- Fallback for other regions

**Note:** Current implementation uses coordinate-based mapping. In production, this should query actual Hobli boundary data from ISRO Bhuvan Vector layers or a spatial database.

### 3. WMS Integration

#### GetCapabilities

Fetch available WMS layers and capabilities:

```python
capabilities = await map_service.get_wms_capabilities()

print(f"Service: {capabilities.service_title}")
print(f"Layers: {capabilities.available_layers}")
print(f"Formats: {capabilities.supported_formats}")
```

**Available Layers:**
- LISS3: Linear Imaging Self-Scanning Sensor III (23.5m resolution)
- LISS4: Linear Imaging Self-Scanning Sensor IV (5.8m resolution)
- CARTOSAT: High-resolution cartographic satellite imagery
- VECTOR: Administrative boundaries and vector data
- ADMIN_BOUNDARY: Administrative subdivision boundaries

#### GetMap

Generate WMS tile URLs for map rendering:

```python
# Define bounding box (minx, miny, maxx, maxy)
bbox = (77.5, 12.9, 77.6, 13.0)

# Generate tile URL
url = map_service.get_wms_tile_url(
    bbox=bbox,
    width=256,
    height=256,
    layer="LISS3",
    format="image/png"
)
```

#### GetFeatureInfo

Query feature information at specific coordinates:

```python
feature_info = await map_service.get_feature_info(
    lat=12.9716,
    lon=77.5946,
    layer="ADMIN_BOUNDARY"
)
```

### 4. Folium Map Creation

Create interactive maps with ISRO Bhuvan layers:

```python
# Create base map
map_obj = map_service.create_folium_map(
    center_lat=12.9716,
    center_lon=77.5946,
    zoom=12,
    add_bhuvan_layer=True
)

# Add plot marker
map_service.add_plot_marker(
    map_obj,
    lat=12.9716,
    lon=77.5946,
    plot_id="PLOT_001",
    popup_text="Test Plot",
    color="green",
    draggable=True
)

# Add jurisdiction boundary
boundary_coords = [
    (12.95, 77.55),
    (12.95, 77.65),
    (13.05, 77.65),
    (13.05, 77.55)
]

map_service.add_jurisdiction_boundary(
    map_obj,
    hobli_id="KA_BLR_001",
    boundary_coords=boundary_coords,
    color="blue"
)

# Save map
map_obj.save("output_map.html")
```

## Configuration

MapService configuration is managed through `config/settings.py`:

```python
class MapServiceConfig(BaseModel):
    bhuvan_base_url: str = "https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms"
    bhuvan_default_layer: str = "LISS3"
    india_lat_bounds: tuple[float, float] = (6.0, 37.0)
    india_lon_bounds: tuple[float, float] = (68.0, 97.0)
    coordinate_precision: int = 4
```

**Environment Variables:**
- `MAP_SERVICE__BHUVAN_BASE_URL`: Override Bhuvan WMS endpoint
- `MAP_SERVICE__BHUVAN_DEFAULT_LAYER`: Default layer name
- `MAP_SERVICE__COORDINATE_PRECISION`: Decimal places for coordinates

## API Reference

### MapService Class

#### `__init__()`
Initialize MapService with configuration from settings.

#### `validate_coordinates(lat: float, lon: float) -> CoordinateValidationResult`
Validate coordinates for Indian geographic regions.

**Returns:**
- `is_valid`: Boolean indicating validation success
- `error`: Error message if validation fails
- `normalized_coordinates`: Tuple of (lat, lon) rounded to precision
- `hobli_id`, `hobli_name`, `district`, `state`: Administrative information

#### `get_hobli_from_coordinates(lat: float, lon: float) -> Optional[Dict[str, str]]`
Detect Hobli administrative subdivision from coordinates.

**Returns:** Dictionary with `hobli_id`, `hobli_name`, `district`, `state`

#### `async get_wms_capabilities() -> WMSCapabilities`
Fetch WMS service capabilities.

**Returns:** WMSCapabilities with service information and available layers

#### `get_wms_tile_url(bbox, width, height, layer, format, crs) -> str`
Generate WMS GetMap URL for tile rendering.

**Parameters:**
- `bbox`: Bounding box (minx, miny, maxx, maxy)
- `width`, `height`: Image dimensions in pixels
- `layer`: WMS layer name
- `format`: Image format (image/png, image/jpeg)
- `crs`: Coordinate reference system (EPSG:4326, EPSG:3857)

#### `async get_feature_info(lat, lon, layer, info_format) -> Optional[Dict]`
Query feature information at coordinates using WMS GetFeatureInfo.

#### `create_folium_map(center_lat, center_lon, zoom, add_bhuvan_layer) -> folium.Map`
Create Folium map with optional ISRO Bhuvan base layer.

#### `add_plot_marker(map_obj, lat, lon, plot_id, popup_text, color, draggable) -> folium.Marker`
Add plot marker to Folium map.

#### `add_jurisdiction_boundary(map_obj, hobli_id, boundary_coords, color, fill_opacity) -> folium.Polygon`
Add Hobli jurisdiction boundary polygon to map.

#### `async close()`
Close HTTP client connections.

## Data Models

### CoordinateValidationResult
```python
class CoordinateValidationResult(BaseModel):
    is_valid: bool
    error: Optional[str] = None
    normalized_coordinates: Optional[Tuple[float, float]] = None
    hobli_id: Optional[str] = None
    hobli_name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
```

### WMSCapabilities
```python
class WMSCapabilities(BaseModel):
    service_title: str
    service_abstract: Optional[str] = None
    available_layers: List[str]
    supported_formats: List[str]
    supported_crs: List[str]
```

### HobliInfo
```python
class HobliInfo(BaseModel):
    hobli_id: str
    hobli_name: str
    district: str
    state: str
    coordinates: Tuple[float, float]
```

## Testing

Run unit tests:

```bash
pytest tests/unit/test_map_service.py -v
```

Run demo:

```bash
python examples/map_service_demo.py
```

**Test Coverage:**
- Coordinate validation (valid/invalid cases)
- Hobli detection for different regions
- WMS integration (GetCapabilities, GetMap, GetFeatureInfo)
- Folium map creation with markers and boundaries
- Configuration loading

## Integration with Other Services

### DbService Integration
```python
# Store validated coordinates in DynamoDB
result = map_service.validate_coordinates(lat, lon)
if result.is_valid:
    db_service.register_plot(
        user_id="user_123",
        plot_data={
            "coordinates": result.normalized_coordinates,
            "hobli_id": result.hobli_id,
            "district": result.district,
            "state": result.state
        }
    )
```

### BrainService Integration
```python
# Validate coordinates before analysis
result = map_service.validate_coordinates(lat, lon)
if result.is_valid:
    analysis = await brain_service.analyze_plot(*result.normalized_coordinates)
```

### Streamlit UI Integration
```python
import streamlit as st
from streamlit_folium import st_folium

# Create map
map_obj = map_service.create_folium_map(12.9716, 77.5946)

# Display in Streamlit
st_folium(map_obj, width=700, height=500)
```

## Production Considerations

### 1. Hobli Boundary Data
Current implementation uses coordinate-based mapping. For production:

- Load actual Hobli boundary data from spatial database (PostGIS)
- Use ISRO Bhuvan Vector layers for administrative boundaries
- Implement point-in-polygon spatial queries
- Cache boundary data for performance

### 2. WMS Service Reliability
ISRO Bhuvan WMS may have:

- Rate limiting
- Authentication requirements
- CORS restrictions
- Availability issues

**Recommendations:**
- Implement WMS proxy through backend
- Add retry logic with exponential backoff
- Cache WMS tiles locally
- Provide fallback to OpenStreetMap

### 3. Performance Optimization
- Cache WMS GetCapabilities responses
- Implement tile caching for frequently accessed areas
- Use connection pooling for HTTP requests
- Add request timeout handling

### 4. Security
- Validate all user inputs
- Sanitize coordinates before WMS requests
- Implement rate limiting for API calls
- Add authentication for sensitive operations

## Requirements Validation

This implementation validates the following requirements:

- **Requirement 11.1**: Map interface with ISRO Bhuvan integration ✓
- **Requirement 11.2**: Coordinate capture and validation ✓
- **Requirement 11.3**: GPS location services support ✓
- **Requirement 11.4**: Interactive map with plot markers ✓
- **Requirement 11.5**: Hobli boundary detection ✓
- **Requirement 11.6**: Jurisdiction-based mapping ✓

## Known Limitations

1. **Hobli Detection**: Uses coordinate-based mapping instead of actual boundary data
2. **WMS Redirects**: Bhuvan WMS may return 302 redirects requiring follow_redirects=True
3. **Offline Support**: Requires internet connectivity for WMS operations
4. **Coverage**: Hobli mapping currently covers major regions, not all of India

## Future Enhancements

1. **Real Hobli Boundaries**: Integrate actual Hobli boundary shapefiles
2. **Offline Maps**: Cache tiles for offline operation
3. **GPS Integration**: Add real-time GPS tracking
4. **Advanced Queries**: Support complex spatial queries (nearest plots, cluster detection)
5. **3D Visualization**: Add terrain and elevation data
6. **Time Series**: Support historical satellite imagery comparison

## References

- [ISRO Bhuvan Portal](https://bhuvan.nrsc.gov.in/)
- [WMS Specification](https://www.ogc.org/standards/wms)
- [Folium Documentation](https://python-visualization.github.io/folium/)
- [Shapely Documentation](https://shapely.readthedocs.io/)

## Support

For issues or questions:
- Check test cases in `tests/unit/test_map_service.py`
- Run demo script: `python examples/map_service_demo.py`
- Review configuration in `config/settings.py`
