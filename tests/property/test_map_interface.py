"""
Property-Based Tests for Map Interface Consistency

Property 17: Map Interface Consistency
Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.6

This module tests that the map interface maintains consistency across:
- Coordinate validation and transformation
- Interactive map rendering with various configurations
- Plot marker management and clustering
- GPS location services and privacy controls
- Hobli boundary detection and jurisdiction mapping
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.strategies import composite
from decimal import Decimal
from typing import Dict, Any, List, Tuple
import folium
from services.map_service import MapService, CoordinateValidationResult
from config.settings import Settings


# ============================================================================
# Strategy Definitions
# ============================================================================

@composite
def valid_indian_coordinates(draw):
    """Generate valid coordinates within Indian geographic bounds with required precision"""
    # India's approximate bounds: lat 6-37°N, lon 68-97°E
    # Generate coordinates that will have at least 4 decimal places when converted to string
    # We need to ensure the 4th decimal place is non-zero to guarantee 4 decimal places in string form
    
    lat_whole = draw(st.integers(min_value=6, max_value=36))
    # Generate 4 decimal digits, ensuring at least one of the last digits is non-zero
    lat_decimal = draw(st.integers(min_value=1000, max_value=9999)) / 10000.0
    lat = lat_whole + lat_decimal
    
    lon_whole = draw(st.integers(min_value=68, max_value=96))
    lon_decimal = draw(st.integers(min_value=1000, max_value=9999)) / 10000.0
    lon = lon_whole + lon_decimal
    
    # Round to 6 decimals for consistency
    lat = round(lat, 6)
    lon = round(lon, 6)
    
    return (lat, lon)


@composite
def invalid_coordinates(draw):
    """Generate invalid coordinates outside Indian bounds"""
    choice = draw(st.integers(min_value=0, max_value=3))
    
    if choice == 0:
        # Latitude too low
        lat = draw(st.floats(min_value=-90.0, max_value=5.9, allow_nan=False, allow_infinity=False))
        lon = draw(st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False))
    elif choice == 1:
        # Latitude too high
        lat = draw(st.floats(min_value=37.1, max_value=90.0, allow_nan=False, allow_infinity=False))
        lon = draw(st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False))
    elif choice == 2:
        # Longitude too low
        lat = draw(st.floats(min_value=6.0, max_value=37.0, allow_nan=False, allow_infinity=False))
        lon = draw(st.floats(min_value=-180.0, max_value=67.9, allow_nan=False, allow_infinity=False))
    else:
        # Longitude too high
        lat = draw(st.floats(min_value=6.0, max_value=37.0, allow_nan=False, allow_infinity=False))
        lon = draw(st.floats(min_value=97.1, max_value=180.0, allow_nan=False, allow_infinity=False))
    
    return (lat, lon)


@composite
def plot_data(draw):
    """Generate plot data for marker testing"""
    lat, lon = draw(valid_indian_coordinates())
    plot_id = draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    crop = draw(st.sampled_from(['Rice', 'Wheat', 'Cotton', 'Sugarcane', 'Maize']))
    status = draw(st.sampled_from(['active', 'monitoring', 'alert', 'critical', 'inactive']))
    
    return {
        'plot_id': plot_id,
        'latitude': lat,
        'longitude': lon,
        'crop': crop,
        'status': status,
        'farmer_name': f"Farmer_{plot_id[:5]}"
    }


@composite
def plot_list(draw, min_size=1, max_size=20):
    """Generate a list of plots"""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    plots = [draw(plot_data()) for _ in range(size)]
    return plots


# ============================================================================
# Property 17: Map Interface Consistency
# ============================================================================

class TestMapInterfaceConsistency:
    """
    Property 17: Map Interface Consistency
    
    Tests that the map interface maintains consistency across all operations:
    - Coordinate validation is deterministic and reversible
    - Map rendering produces valid Folium objects
    - Plot markers are correctly positioned and styled
    - Interactive features work consistently
    """
    
    @given(coords=valid_indian_coordinates())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coordinate_validation_consistency(self, coords, map_service):
        """
        Property: Valid coordinates always validate successfully
        Requirement 11.5: Coordinate validation for Indian regions
        """
        lat, lon = coords
        
        # Validate coordinates
        validation = map_service.validate_coordinates(lat, lon)
        
        # Property: Valid Indian coordinates should always pass validation
        assert validation.is_valid, f"Valid coordinates ({lat}, {lon}) failed validation: {validation.error}"
        assert validation.normalized_coordinates is not None
        # MapService rounds to 4 decimal places, so compare rounded values
        assert validation.normalized_coordinates[0] == round(lat, 4)
        assert validation.normalized_coordinates[1] == round(lon, 4)
        assert validation.state is not None
        assert validation.district is not None
    
    @given(coords=invalid_coordinates())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_coordinate_rejection(self, coords, map_service):
        """
        Property: Invalid coordinates always fail validation
        Requirement 11.5: Coordinate validation rejects out-of-bounds coordinates
        """
        lat, lon = coords
        
        # Validate coordinates
        validation = map_service.validate_coordinates(lat, lon)
        
        # Property: Invalid coordinates should always fail validation
        assert not validation.is_valid, f"Invalid coordinates ({lat}, {lon}) passed validation"
        assert validation.error is not None
        assert "outside Indian geographic bounds" in validation.error
    
    @given(coords=valid_indian_coordinates(), zoom=st.integers(min_value=1, max_value=18))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_map_creation_consistency(self, coords, zoom, map_service):
        """
        Property: Map creation always produces valid Folium map objects
        Requirement 11.1: Interactive map rendering with ISRO Bhuvan layers
        """
        lat, lon = coords
        
        # Create interactive map
        m = map_service.create_interactive_map(
            center_lat=lat,
            center_lon=lon,
            zoom=zoom,
            add_bhuvan_layer=True
        )
        
        # Property: Map object should be valid Folium Map
        assert isinstance(m, folium.Map)
        assert m.location == [lat, lon]
        assert m.options['zoom'] == zoom
        
        # Property: Map should have Bhuvan layer
        html = m._repr_html_()
        assert 'bhuvan' in html.lower() or 'wms' in html.lower()
    
    @given(plots=plot_list(min_size=1, max_size=10))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_plot_marker_consistency(self, plots, map_service):
        """
        Property: Plot markers are correctly positioned and styled
        Requirement 11.3: Plot marker management with status-based styling
        """
        # Create base map
        m = map_service.create_interactive_map()
        
        # Add plot markers
        map_service.add_clustered_markers(m, plots)
        
        # Property: Map should contain markers for all plots
        html = m._repr_html_()
        
        # Check that plot IDs appear in the map HTML
        for plot in plots:
            assert plot['plot_id'] in html, f"Plot {plot['plot_id']} not found in map"
    
    @given(
        coords1=valid_indian_coordinates(),
        coords2=valid_indian_coordinates()
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coordinate_validation_determinism(self, coords1, coords2, map_service):
        """
        Property: Coordinate validation is deterministic
        Requirement 11.5: Consistent coordinate validation behavior
        """
        lat1, lon1 = coords1
        lat2, lon2 = coords2
        
        # Validate same coordinates multiple times
        validation1a = map_service.validate_coordinates(lat1, lon1)
        validation1b = map_service.validate_coordinates(lat1, lon1)
        
        # Property: Same coordinates should produce identical validation results
        assert validation1a.is_valid == validation1b.is_valid
        if validation1a.normalized_coordinates and validation1b.normalized_coordinates:
            assert validation1a.normalized_coordinates[0] == validation1b.normalized_coordinates[0]
            assert validation1a.normalized_coordinates[1] == validation1b.normalized_coordinates[1]
        assert validation1a.state == validation1b.state
        assert validation1a.district == validation1b.district
        
        # If coordinates are different, validation results may differ
        if (lat1, lon1) != (lat2, lon2):
            validation2 = map_service.validate_coordinates(lat2, lon2)
            # Both should be valid (since both are from valid_indian_coordinates)
            assert validation1a.is_valid
            assert validation2.is_valid
    
    @given(
        center_coords=valid_indian_coordinates(),
        plots=plot_list(min_size=5, max_size=15)
    )
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_marker_clustering_consistency(self, center_coords, plots, map_service):
        """
        Property: Marker clustering works consistently with various plot counts
        Requirement 11.3: Clustered markers for performance
        """
        lat, lon = center_coords
        
        # Create map with clustering
        m = map_service.create_interactive_map(center_lat=lat, center_lon=lon)
        map_service.add_clustered_markers(m, plots, cluster_radius=50)
        
        # Property: Map should contain MarkerCluster
        html = m._repr_html_()
        assert 'MarkerCluster' in html or 'marker' in html.lower()
        
        # Property: All plots should be represented
        for plot in plots:
            assert plot['plot_id'] in html
    
    @given(coords=valid_indian_coordinates())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_hobli_detection_consistency(self, coords, map_service):
        """
        Property: Hobli detection is consistent for same coordinates
        Requirement 11.6: Hobli boundary detection from coordinates
        """
        lat, lon = coords
        
        # Detect Hobli multiple times
        hobli1 = map_service.detect_hobli_from_coordinates(lat, lon)
        hobli2 = map_service.detect_hobli_from_coordinates(lat, lon)
        
        # Property: Same coordinates should produce same Hobli detection
        assert hobli1 == hobli2, f"Hobli detection inconsistent: {hobli1} != {hobli2}"
        
        # Property: Hobli ID should be non-empty string if detected
        if hobli1:
            assert isinstance(hobli1, str)
            assert len(hobli1) > 0
    
    @given(
        coords=valid_indian_coordinates(),
        add_bhuvan=st.booleans(),
        enable_draw=st.booleans(),
        enable_locate=st.booleans()
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_map_configuration_consistency(self, coords, add_bhuvan, enable_draw, enable_locate, map_service):
        """
        Property: Map configuration options work consistently
        Requirement 11.1, 11.2: Interactive map with configurable features
        """
        lat, lon = coords
        
        # Create map with various configurations
        m = map_service.create_interactive_map(
            center_lat=lat,
            center_lon=lon,
            add_bhuvan_layer=add_bhuvan,
            enable_draw=enable_draw,
            enable_locate=enable_locate
        )
        
        # Property: Map should always be valid Folium Map
        assert isinstance(m, folium.Map)
        assert m.location == [lat, lon]
        
        # Property: Configuration should be reflected in map
        html = m._repr_html_()
        
        if add_bhuvan:
            assert 'bhuvan' in html.lower() or 'wms' in html.lower()
        
        if enable_draw:
            assert 'draw' in html.lower() or 'Draw' in html
        
        if enable_locate:
            assert 'locate' in html.lower() or 'Locate' in html
    
    @given(
        plots=plot_list(min_size=3, max_size=10),
        status_filter=st.sampled_from(['active', 'monitoring', 'alert', 'critical', 'inactive', None])
    )
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_status_based_marker_styling(self, plots, status_filter, map_service):
        """
        Property: Marker styling is consistent with plot status
        Requirement 11.3: Status-based color coding for plot markers
        """
        # Filter plots by status if specified
        if status_filter:
            filtered_plots = [p for p in plots if p['status'] == status_filter]
        else:
            filtered_plots = plots
        
        if not filtered_plots:
            assume(False)  # Skip if no plots match filter
        
        # Create map with markers
        m = map_service.create_interactive_map()
        map_service.add_clustered_markers(m, filtered_plots)
        
        # Property: Map should contain all filtered plots
        html = m._repr_html_()
        for plot in filtered_plots:
            assert plot['plot_id'] in html
            
            # Property: Status should be reflected in marker (color or icon)
            # The status appears in the popup content
            assert plot['status'] in html.lower()
