# UI Module - Interactive Map Interface

This module provides interactive map components for the Precision AgriAI Streamlit application, enabling coordinate capture, plot marker management, and GPS location services.

## Overview

The UI module integrates ISRO Bhuvan mapping with Streamlit using `streamlit-folium` to provide:
- Interactive map visualization with ISRO Bhuvan LISS III satellite imagery
- Click/tap coordinate capture for plot registration
- GPS location services with privacy controls
- Plot marker management with status-based color coding
- Jurisdiction heatmaps for Extension Officers
- Cluster outbreak visualization

## Components

### MapInterface Class

The `MapInterface` class provides high-level methods for rendering interactive maps in Streamlit.

#### Key Methods

##### `render_interactive_map()`
Renders an interactive map with coordinate capture capabilities.

```python
map_data = map_interface.render_interactive_map(
    center_lat=12.9716,
    center_lon=77.5946,
    zoom=12,
    plots=[...],  # Optional list of plots to display
    enable_click_capture=True,
    enable_gps=True,
    key="farmer_map"
)
```

**Returns:** Dictionary with map interaction data including:
- `last_clicked`: Last clicked coordinates `{lat, lng}`
- `center`: Current map center
- `zoom`: Current zoom level
- `bounds`: Current map bounds

##### `render_coordinate_capture_ui()`
Displays captured coordinates with validation feedback.

```python
coords = map_interface.render_coordinate_capture_ui(
    map_data,
    session_key="captured_coordinates"
)
```

**Returns:** Tuple of `(lat, lon)` if valid coordinates captured, `None` otherwise.

##### `render_gps_location_ui()`
Renders GPS location capture UI with privacy controls.

```python
gps_coords = map_interface.render_gps_location_ui(
    session_key="gps_coordinates"
)
```

**Features:**
- Privacy information disclosure
- "Use My Location" button with instructions
- "Clear Location" button for data removal
- Explicit opt-in design

##### `render_plot_marker_manager()`
Manages plot markers with status-based filtering.

```python
selected_plot_id = map_interface.render_plot_marker_manager(
    plots=[...],
    selected_plot_id="P001"
)
```

**Features:**
- Plot count by status
- Plot selection dropdown
- Status metrics display

##### `render_jurisdiction_heatmap()`
Renders jurisdiction-wide heatmap for Extension Officers.

```python
map_data = map_interface.render_jurisdiction_heatmap(
    hobli_id="KA_BLR_001",
    plots=[...],
    alerts=[...],
    center_lat=12.9716,
    center_lon=77.5946,
    key="officer_map"
)
```

**Features:**
- Clustered plot markers
- Alert heatmap overlay
- Jurisdiction boundary visualization
- Risk-based color coding

##### `render_coordinate_input_form()`
Provides manual coordinate entry with validation.

```python
coords = map_interface.render_coordinate_input_form(
    default_lat=12.9716,
    default_lon=77.5946
)
```

## Integration with MapService

The `MapInterface` class wraps `MapService` methods to provide Streamlit-specific functionality:

### MapService Interactive Methods

#### `create_interactive_map()`
Creates a Folium map with interactive features enabled.

```python
m = map_service.create_interactive_map(
    center_lat=12.9716,
    center_lon=77.5946,
    zoom=10,
    add_bhuvan_layer=True,
    enable_draw=False,
    enable_locate=True
)
```

**Features:**
- ISRO Bhuvan WMS base layer
- GPS location control (LocateControl)
- Drawing tools (optional)
- Click event handling (LatLngPopup)
- Layer control

#### `add_clustered_markers()`
Adds clustered plot markers with status-based colors.

```python
map_service.add_clustered_markers(
    map_obj=m,
    plots=[
        {"plot_id": "P001", "lat": 12.9716, "lon": 77.5946, 
         "status": "active", "crop": "Rice"}
    ],
    cluster_radius=80
)
```

**Status Colors:**
- 🟢 Green: `active` - Healthy plots
- 🔵 Blue: `analyzed` - Recently analyzed
- 🟠 Orange: `warning` - Warning level
- 🔴 Red: `alert` - Alert level
- ⚪ Gray: `inactive` - Inactive plots

#### `add_heatmap_layer()`
Adds alert heatmap visualization.

```python
map_service.add_heatmap_layer(
    map_obj=m,
    alerts=[
        {"lat": 12.9716, "lon": 77.5946, "risk_level": "high"}
    ],
    radius=15,
    blur=25
)
```

**Risk Level Intensity:**
- `low`: 0.3 (green)
- `medium`: 0.6 (yellow)
- `high`: 0.9 (orange)
- `critical`: 1.0 (red)

## Usage Examples

### Farmer View - Coordinate Capture

```python
from ui.map_interface import MapInterface
from services.map_service import MapService

# Initialize services
map_service = MapService()
map_interface = MapInterface(map_service)

# Render interactive map
map_data = map_interface.render_interactive_map(
    center_lat=12.9716,
    center_lon=77.5946,
    zoom=12,
    enable_click_capture=True,
    enable_gps=True,
    key="farmer_map"
)

# Capture coordinates
coords = map_interface.render_coordinate_capture_ui(
    map_data,
    session_key="farmer_coordinates"
)

if coords:
    st.success(f"Coordinates captured: {coords}")
```

### Officer View - Jurisdiction Heatmap

```python
# Get plots and alerts for jurisdiction
plots = db_service.get_hobli_plots("KA_BLR_001")
alerts = db_service.get_recent_alerts("KA_BLR_001", hours=24)

# Render jurisdiction heatmap
map_data = map_interface.render_jurisdiction_heatmap(
    hobli_id="KA_BLR_001",
    plots=plots,
    alerts=alerts,
    center_lat=13.0827,
    center_lon=77.5946,
    key="officer_map"
)
```

### Admin View - Plot Registration

```python
# Render map for coordinate selection
map_data = map_interface.render_interactive_map(
    center_lat=12.9716,
    center_lon=77.5946,
    zoom=10,
    enable_click_capture=True,
    key="admin_map"
)

# Capture and validate coordinates
coords = map_interface.render_coordinate_capture_ui(
    map_data,
    session_key="admin_coordinates"
)

if coords:
    # Validate coordinates
    validation = map_service.validate_coordinates(coords[0], coords[1])
    
    if validation.is_valid:
        # Register plot
        plot_data = {
            "coordinates": coords,
            "hobli_id": validation.hobli_id,
            "hobli_name": validation.hobli_name
        }
```

## Privacy Controls

The GPS location services implement privacy-first design:

1. **Explicit Opt-In**: Users must explicitly click "Use My Location"
2. **Browser Permission**: Browser prompts for location access permission
3. **Clear Instructions**: Step-by-step guidance for GPS usage
4. **Data Removal**: "Clear Location" button removes stored GPS data
5. **Privacy Disclosure**: Expandable privacy information panel

### Privacy Information Displayed

```
GPS Location Privacy:
- Location data is used only for plot registration
- Your location is not stored permanently without your consent
- You can clear location data at any time
- Location access requires your explicit permission
```

## Coordinate Validation

All captured coordinates are validated using `MapService.validate_coordinates()`:

1. **Range Validation**: Lat/Lon within valid ranges
2. **Precision Check**: Minimum 4 decimal places
3. **Geographic Bounds**: Within Indian geographic region
4. **Hobli Detection**: Automatic jurisdiction identification

### Validation Feedback

- ✅ **Valid**: Green success message with Hobli information
- ❌ **Invalid**: Red error message with specific reason
- 📍 **Hobli Info**: District, State, and Hobli name displayed

## Session State Management

The map interface uses Streamlit session state to persist data:

- `farmer_coordinates`: Captured coordinates in Farmer View
- `farmer_gps`: GPS coordinates in Farmer View
- `admin_coordinates`: Captured coordinates in Admin View
- `admin_gps`: GPS coordinates in Admin View
- `selected_hobli`: Selected jurisdiction in Officer View

## Testing

Unit tests are provided in `tests/unit/test_map_service.py`:

```bash
# Run all map service tests
pytest tests/unit/test_map_service.py -v

# Run only interactive map tests
pytest tests/unit/test_map_service.py::TestInteractiveMapFeatures -v
```

**Test Coverage:**
- Interactive map creation
- Clustered marker management
- Heatmap layer visualization
- Empty data handling
- Invalid coordinate handling
- Custom parameters

## Dependencies

- `streamlit>=1.28.0`: Web application framework
- `streamlit-folium>=0.15.0`: Folium integration for Streamlit
- `folium>=0.15.0`: Interactive map visualization
- `folium.plugins`: MarkerCluster, HeatMap, LocateControl, Draw

## Requirements Validated

This implementation validates the following requirements:

- **11.1**: Interactive map with ISRO Bhuvan base layers
- **11.2**: Click/tap coordinate capture
- **11.3**: Plot marker management with status colors
- **11.4**: GPS location services
- **11.5**: Privacy controls for location access
- **11.6**: Coordinate validation and Hobli detection

## Future Enhancements

- Real-time plot marker updates via WebSocket
- Offline map caching for rural connectivity
- Custom marker icons for different crop types
- Drawing tools for plot boundary definition
- Multi-plot selection for batch operations
- Export map as image/PDF for reports
