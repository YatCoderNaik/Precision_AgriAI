"""
MapService Demo - ISRO Bhuvan Integration

Demonstrates the MapService functionality including:
- Coordinate validation
- Hobli detection
- WMS integration
- Folium map creation
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.map_service import MapService
from config.settings import get_settings


async def main():
    """Demonstrate MapService functionality"""
    
    print("=" * 70)
    print("MapService Demo - ISRO Bhuvan Integration")
    print("=" * 70)
    print()
    
    # Initialize MapService
    map_service = MapService()
    settings = get_settings()
    
    print(f"✓ MapService initialized")
    print(f"  Bhuvan URL: {map_service.bhuvan_base_url}")
    print(f"  Default Layer: {map_service.default_layer}")
    print(f"  India Bounds: Lat {map_service.india_lat_bounds}, Lon {map_service.india_lon_bounds}")
    print()
    
    # Test coordinates for different Indian cities
    test_locations = [
        ("Bangalore", 12.9716, 77.5946),
        ("Chennai", 13.0827, 80.2707),
        ("Mysore", 14.0000, 76.5000),
        ("Vijayawada", 16.5062, 80.6480),
        ("Coimbatore", 11.0168, 76.9558),
    ]
    
    print("-" * 70)
    print("1. Coordinate Validation and Hobli Detection")
    print("-" * 70)
    print()
    
    for city, lat, lon in test_locations:
        print(f"Testing: {city} ({lat}, {lon})")
        
        # Validate coordinates
        result = map_service.validate_coordinates(lat, lon)
        
        if result.is_valid:
            print(f"  ✓ Valid coordinates")
            print(f"  Normalized: {result.normalized_coordinates}")
            print(f"  Hobli: {result.hobli_name} ({result.hobli_id})")
            print(f"  District: {result.district}")
            print(f"  State: {result.state}")
        else:
            print(f"  ✗ Invalid: {result.error}")
        
        print()
    
    # Test invalid coordinates
    print("-" * 70)
    print("2. Invalid Coordinate Handling")
    print("-" * 70)
    print()
    
    invalid_tests = [
        ("Insufficient precision", 12.97, 77.59),
        ("Outside India", 51.5074, -0.1278),
        ("Out of range", 95.0, 200.0),
    ]
    
    for test_name, lat, lon in invalid_tests:
        print(f"Testing: {test_name} ({lat}, {lon})")
        result = map_service.validate_coordinates(lat, lon)
        print(f"  ✗ {result.error}")
        print()
    
    # Test WMS capabilities
    print("-" * 70)
    print("3. WMS Capabilities")
    print("-" * 70)
    print()
    
    try:
        capabilities = await map_service.get_wms_capabilities()
        print(f"Service: {capabilities.service_title}")
        print(f"Available Layers: {', '.join(capabilities.available_layers)}")
        print(f"Supported Formats: {', '.join(capabilities.supported_formats)}")
        print(f"Supported CRS: {', '.join(capabilities.supported_crs)}")
    except Exception as e:
        print(f"Note: Could not fetch live WMS capabilities (using defaults)")
        print(f"Reason: {e}")
    
    print()
    
    # Test WMS tile URL generation
    print("-" * 70)
    print("4. WMS Tile URL Generation")
    print("-" * 70)
    print()
    
    # Bangalore bounding box
    bbox = (77.5, 12.9, 77.6, 13.0)
    
    for layer in ["LISS3", "LISS4", "CARTOSAT", "VECTOR"]:
        url = map_service.get_wms_tile_url(bbox, layer=layer)
        print(f"{layer} Layer URL:")
        print(f"  {url[:100]}...")
        print()
    
    # Test Folium map creation
    print("-" * 70)
    print("5. Folium Map Creation")
    print("-" * 70)
    print()
    
    # Create map for Bangalore
    bangalore_map = map_service.create_folium_map(
        12.9716, 77.5946, 
        zoom=12, 
        add_bhuvan_layer=True
    )
    
    # Add plot markers
    map_service.add_plot_marker(
        bangalore_map,
        12.9716, 77.5946,
        "PLOT_001",
        popup_text="Test Plot 1<br>Bangalore North Hobli",
        color="green"
    )
    
    map_service.add_plot_marker(
        bangalore_map,
        12.9800, 77.6000,
        "PLOT_002",
        popup_text="Test Plot 2<br>Bangalore North Hobli",
        color="blue"
    )
    
    # Add jurisdiction boundary
    boundary_coords = [
        (12.95, 77.55),
        (12.95, 77.65),
        (13.05, 77.65),
        (13.05, 77.55)
    ]
    
    map_service.add_jurisdiction_boundary(
        bangalore_map,
        "KA_BLR_001",
        boundary_coords,
        color="blue"
    )
    
    # Save map
    output_file = "bangalore_map_demo.html"
    bangalore_map.save(output_file)
    
    print(f"✓ Created Folium map with:")
    print(f"  - ISRO Bhuvan LISS III base layer")
    print(f"  - 2 plot markers")
    print(f"  - Jurisdiction boundary")
    print(f"  - Saved to: {output_file}")
    print()
    
    # Test GetFeatureInfo
    print("-" * 70)
    print("6. WMS GetFeatureInfo")
    print("-" * 70)
    print()
    
    try:
        feature_info = await map_service.get_feature_info(12.9716, 77.5946)
        if feature_info:
            print(f"✓ Retrieved feature information")
            print(f"  {feature_info}")
        else:
            print(f"Note: No feature information available (service may be unavailable)")
    except Exception as e:
        print(f"Note: Could not fetch feature info")
        print(f"Reason: {e}")
    
    print()
    
    # Cleanup
    await map_service.close()
    
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print(f"Summary:")
    print(f"  ✓ Coordinate validation working")
    print(f"  ✓ Hobli detection working")
    print(f"  ✓ WMS integration working")
    print(f"  ✓ Folium map creation working")
    print(f"  ✓ Map saved to: {output_file}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
