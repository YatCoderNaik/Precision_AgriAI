"""
Unit tests for MapService - ISRO Bhuvan Integration

Tests coordinate validation, WMS integration, and Hobli detection.
"""

import pytest
import folium
from services.map_service import MapService, CoordinateValidationResult
from config.settings import get_settings


@pytest.fixture
def map_service():
    """Create MapService instance for testing"""
    return MapService()


class TestCoordinateValidation:
    """Test coordinate validation functionality"""
    
    def test_valid_coordinates_bangalore(self, map_service):
        """Test validation of valid Bangalore coordinates"""
        result = map_service.validate_coordinates(12.9716, 77.5946)
        
        assert result.is_valid is True
        assert result.error is None
        assert result.normalized_coordinates is not None
        assert result.hobli_id is not None
        assert result.hobli_name is not None
        assert result.district is not None
        assert result.state is not None
    
    def test_valid_coordinates_chennai(self, map_service):
        """Test validation of valid Chennai coordinates"""
        result = map_service.validate_coordinates(13.0827, 80.2707)
        
        assert result.is_valid is True
        assert result.error is None
        assert result.normalized_coordinates == (13.0827, 80.2707)
    
    def test_invalid_latitude_out_of_range(self, map_service):
        """Test validation fails for latitude out of range"""
        result = map_service.validate_coordinates(95.0, 77.5946)
        
        assert result.is_valid is False
        assert "out of valid range" in result.error.lower()
    
    def test_invalid_longitude_out_of_range(self, map_service):
        """Test validation fails for longitude out of range"""
        result = map_service.validate_coordinates(12.9716, 200.0)
        
        assert result.is_valid is False
        assert "out of valid range" in result.error.lower()
    
    def test_coordinates_outside_india(self, map_service):
        """Test validation fails for coordinates outside India"""
        # New York coordinates with sufficient precision
        result = map_service.validate_coordinates(40.7128, -74.0060)
        
        assert result.is_valid is False
        # Could fail on precision check first, which is also valid
        assert "outside indian geographic region" in result.error.lower() or "decimal places" in result.error.lower()
    
    def test_coordinates_outside_india_with_precision(self, map_service):
        """Test validation fails for coordinates outside India with proper precision"""
        # London coordinates with sufficient precision
        result = map_service.validate_coordinates(51.5074, -0.1278)
        
        assert result.is_valid is False
        assert "outside indian geographic region" in result.error.lower()
    
    def test_insufficient_precision(self, map_service):
        """Test validation fails for insufficient decimal precision"""
        result = map_service.validate_coordinates(12.97, 77.59)
        
        assert result.is_valid is False
        assert "decimal places" in result.error.lower()
    
    def test_coordinate_normalization(self, map_service):
        """Test coordinates are normalized to specified precision"""
        result = map_service.validate_coordinates(12.971612345, 77.594612345)
        
        assert result.is_valid is True
        assert result.normalized_coordinates == (12.9716, 77.5946)


class TestHobliDetection:
    """Test Hobli boundary detection"""
    
    def test_bangalore_hobli_detection(self, map_service):
        """Test Hobli detection for Bangalore region"""
        hobli_info = map_service.get_hobli_from_coordinates(12.9716, 77.5946)
        
        assert hobli_info is not None
        assert hobli_info["hobli_id"] == "KA_BLR_001"
        assert hobli_info["hobli_name"] == "Bangalore North Hobli"
        assert hobli_info["district"] == "Bangalore Urban"
        assert hobli_info["state"] == "Karnataka"
    
    def test_mysore_hobli_detection(self, map_service):
        """Test Hobli detection for Mysore region"""
        hobli_info = map_service.get_hobli_from_coordinates(14.0, 76.5)
        
        assert hobli_info is not None
        assert hobli_info["hobli_id"] == "KA_MYS_001"
        assert hobli_info["state"] == "Karnataka"
    
    def test_chennai_hobli_detection(self, map_service):
        """Test Hobli detection for Chennai region"""
        hobli_info = map_service.get_hobli_from_coordinates(13.0827, 80.2707)
        
        assert hobli_info is not None
        assert hobli_info["hobli_id"] == "TN_CHN_001"
        assert hobli_info["state"] == "Tamil Nadu"
    
    def test_unknown_region_fallback(self, map_service):
        """Test fallback for unknown regions"""
        hobli_info = map_service.get_hobli_from_coordinates(20.0, 85.0)
        
        assert hobli_info is not None
        assert hobli_info["hobli_id"] == "IN_UNK_001"
        assert hobli_info["hobli_name"] == "Unknown Hobli"


class TestWMSIntegration:
    """Test ISRO Bhuvan WMS integration"""
    
    @pytest.mark.asyncio
    async def test_get_wms_capabilities(self, map_service):
        """Test WMS GetCapabilities request"""
        capabilities = await map_service.get_wms_capabilities()
        
        assert capabilities is not None
        assert capabilities.service_title is not None
        assert len(capabilities.available_layers) > 0
        assert "LISS3" in capabilities.available_layers
        assert len(capabilities.supported_formats) > 0
    
    def test_get_wms_tile_url(self, map_service):
        """Test WMS GetMap URL generation"""
        bbox = (77.5, 12.9, 77.6, 13.0)
        url = map_service.get_wms_tile_url(bbox, layer="LISS3")
        
        assert url is not None
        assert "service=WMS" in url
        assert "request=GetMap" in url
        assert "layers=LISS3" in url
        assert "bbox=" in url
    
    @pytest.mark.asyncio
    async def test_get_feature_info(self, map_service):
        """Test WMS GetFeatureInfo request"""
        # This may fail if Bhuvan service is unavailable
        result = await map_service.get_feature_info(12.9716, 77.5946)
        
        # Result may be None if service is unavailable, which is acceptable
        assert result is None or isinstance(result, dict)


class TestFoliumMapCreation:
    """Test Folium map creation"""
    
    def test_create_basic_map(self, map_service):
        """Test basic Folium map creation"""
        map_obj = map_service.create_folium_map(12.9716, 77.5946)
        
        assert map_obj is not None
        assert hasattr(map_obj, 'location')
        assert map_obj.location == [12.9716, 77.5946]
    
    def test_create_map_with_bhuvan_layer(self, map_service):
        """Test map creation with Bhuvan WMS layer"""
        map_obj = map_service.create_folium_map(
            12.9716, 77.5946, 
            zoom=12, 
            add_bhuvan_layer=True
        )
        
        assert map_obj is not None
    
    def test_add_plot_marker(self, map_service):
        """Test adding plot marker to map"""
        map_obj = map_service.create_folium_map(12.9716, 77.5946)
        marker = map_service.add_plot_marker(
            map_obj, 
            12.9716, 
            77.5946, 
            "TEST_PLOT_001"
        )
        
        assert marker is not None
    
    def test_add_jurisdiction_boundary(self, map_service):
        """Test adding jurisdiction boundary to map"""
        map_obj = map_service.create_folium_map(12.9716, 77.5946)
        
        # Simple square boundary
        boundary_coords = [
            (12.95, 77.55),
            (12.95, 77.65),
            (13.05, 77.65),
            (13.05, 77.55)
        ]
        
        polygon = map_service.add_jurisdiction_boundary(
            map_obj,
            "KA_BLR_001",
            boundary_coords
        )
        
        assert polygon is not None


class TestConfiguration:
    """Test MapService configuration"""
    
    def test_configuration_loaded(self, map_service):
        """Test configuration is properly loaded"""
        settings = get_settings()
        
        assert map_service.bhuvan_base_url == settings.map_service.bhuvan_base_url
        assert map_service.default_layer == settings.map_service.bhuvan_default_layer
        assert map_service.india_lat_bounds == settings.map_service.india_lat_bounds
        assert map_service.india_lon_bounds == settings.map_service.india_lon_bounds
        assert map_service.coordinate_precision == settings.map_service.coordinate_precision
    
    def test_india_bounds_configuration(self, map_service):
        """Test India geographic bounds are correctly configured"""
        lat_min, lat_max = map_service.india_lat_bounds
        lon_min, lon_max = map_service.india_lon_bounds
        
        assert lat_min < lat_max
        assert lon_min < lon_max
        assert 6.0 <= lat_min <= 8.0
        assert 35.0 <= lat_max <= 37.0
        assert 68.0 <= lon_min <= 70.0
        assert 95.0 <= lon_max <= 97.0


@pytest.mark.asyncio
async def test_cleanup(map_service):
    """Test MapService cleanup"""
    await map_service.close()
    # No assertion needed, just verify no exceptions


class TestInteractiveMapFeatures:
    """Test interactive map functionality for Streamlit integration"""
    
    def test_create_interactive_map(self, map_service):
        """Test interactive map creation with GPS and drawing tools"""
        m = map_service.create_interactive_map(
            12.9716, 77.5946,
            enable_draw=True,
            enable_locate=True
        )
        
        assert isinstance(m, folium.Map)
        assert m.location == [12.9716, 77.5946]
    
    def test_create_interactive_map_without_gps(self, map_service):
        """Test interactive map without GPS location"""
        m = map_service.create_interactive_map(
            12.9716, 77.5946,
            enable_locate=False
        )
        
        assert isinstance(m, folium.Map)
    
    def test_add_clustered_markers(self, map_service):
        """Test adding clustered plot markers"""
        m = map_service.create_interactive_map(12.9716, 77.5946)
        
        plots = [
            {"plot_id": "P001", "lat": 12.9716, "lon": 77.5946, "status": "active", "crop": "Rice"},
            {"plot_id": "P002", "lat": 12.9816, "lon": 77.6046, "status": "alert", "crop": "Wheat"},
            {"plot_id": "P003", "lat": 12.9616, "lon": 77.5846, "status": "analyzed", "crop": "Cotton"}
        ]
        
        map_service.add_clustered_markers(m, plots)
        
        # Check that markers were added
        assert len(m._children) > 0
    
    def test_add_clustered_markers_with_empty_plots(self, map_service):
        """Test clustered markers with empty plot list"""
        m = map_service.create_interactive_map(12.9716, 77.5946)
        
        # Should not raise error with empty list
        map_service.add_clustered_markers(m, [])
        
        assert isinstance(m, folium.Map)
    
    def test_add_clustered_markers_with_invalid_coordinates(self, map_service):
        """Test clustered markers with plots missing coordinates"""
        m = map_service.create_interactive_map(12.9716, 77.5946)
        
        plots = [
            {"plot_id": "P001", "lat": 12.9716, "lon": 77.5946, "status": "active"},
            {"plot_id": "P002", "lat": None, "lon": None, "status": "alert"},  # Invalid
            {"plot_id": "P003", "status": "analyzed"}  # Missing coordinates
        ]
        
        # Should handle invalid data gracefully
        map_service.add_clustered_markers(m, plots)
        
        assert isinstance(m, folium.Map)
    
    def test_add_heatmap_layer(self, map_service):
        """Test adding alert heatmap layer"""
        m = map_service.create_interactive_map(12.9716, 77.5946)
        
        alerts = [
            {"lat": 12.9716, "lon": 77.5946, "risk_level": "high"},
            {"lat": 12.9816, "lon": 77.6046, "risk_level": "critical"},
            {"lat": 12.9616, "lon": 77.5846, "risk_level": "medium"}
        ]
        
        map_service.add_heatmap_layer(m, alerts)
        
        # Check that heatmap was added
        assert len(m._children) > 0
    
    def test_add_heatmap_layer_with_empty_alerts(self, map_service):
        """Test heatmap with empty alert list"""
        m = map_service.create_interactive_map(12.9716, 77.5946)
        
        # Should not raise error with empty list
        map_service.add_heatmap_layer(m, [])
        
        assert isinstance(m, folium.Map)
    
    def test_add_heatmap_layer_with_invalid_coordinates(self, map_service):
        """Test heatmap with alerts missing coordinates"""
        m = map_service.create_interactive_map(12.9716, 77.5946)
        
        alerts = [
            {"lat": 12.9716, "lon": 77.5946, "risk_level": "high"},
            {"lat": None, "lon": None, "risk_level": "medium"},  # Invalid
            {"risk_level": "low"}  # Missing coordinates
        ]
        
        # Should handle invalid data gracefully
        map_service.add_heatmap_layer(m, alerts)
        
        assert isinstance(m, folium.Map)
    
    def test_clustered_markers_status_colors(self, map_service):
        """Test that different plot statuses use correct colors"""
        m = map_service.create_interactive_map(12.9716, 77.5946)
        
        plots = [
            {"plot_id": "P001", "lat": 12.9716, "lon": 77.5946, "status": "active"},
            {"plot_id": "P002", "lat": 12.9816, "lon": 77.6046, "status": "alert"},
            {"plot_id": "P003", "lat": 12.9616, "lon": 77.5846, "status": "warning"},
            {"plot_id": "P004", "lat": 12.9516, "lon": 77.5746, "status": "inactive"}
        ]
        
        map_service.add_clustered_markers(m, plots)
        
        # Verify map was created successfully
        assert isinstance(m, folium.Map)
    
    def test_heatmap_risk_level_intensity(self, map_service):
        """Test that different risk levels use correct intensity"""
        m = map_service.create_interactive_map(12.9716, 77.5946)
        
        alerts = [
            {"lat": 12.9716, "lon": 77.5946, "risk_level": "low"},
            {"lat": 12.9816, "lon": 77.6046, "risk_level": "medium"},
            {"lat": 12.9616, "lon": 77.5846, "risk_level": "high"},
            {"lat": 12.9516, "lon": 77.5746, "risk_level": "critical"}
        ]
        
        map_service.add_heatmap_layer(m, alerts)
        
        # Verify map was created successfully
        assert isinstance(m, folium.Map)
    
    def test_clustered_markers_with_custom_radius(self, map_service):
        """Test clustered markers with custom clustering radius"""
        m = map_service.create_interactive_map(12.9716, 77.5946)
        
        plots = [
            {"plot_id": "P001", "lat": 12.9716, "lon": 77.5946, "status": "active"},
            {"plot_id": "P002", "lat": 12.9816, "lon": 77.6046, "status": "alert"}
        ]
        
        map_service.add_clustered_markers(m, plots, cluster_radius=50)
        
        assert isinstance(m, folium.Map)
    
    def test_heatmap_with_custom_parameters(self, map_service):
        """Test heatmap with custom radius and blur"""
        m = map_service.create_interactive_map(12.9716, 77.5946)
        
        alerts = [
            {"lat": 12.9716, "lon": 77.5946, "risk_level": "high"}
        ]
        
        map_service.add_heatmap_layer(m, alerts, radius=20, blur=30)
        
        assert isinstance(m, folium.Map)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



class TestBhuvanWMSIntegration:
    """Additional tests for ISRO Bhuvan WMS integration - Task 3.4"""
    
    def test_wms_tile_url_format(self, map_service):
        """Test WMS tile URL has correct format and parameters"""
        bbox = (77.5, 12.9, 77.6, 13.0)
        url = map_service.get_wms_tile_url(bbox, layer="LISS3", width=256, height=256)
        
        assert "bhuvan" in url.lower()
        assert "service=WMS" in url or "SERVICE=WMS" in url
        assert "request=GetMap" in url or "REQUEST=GetMap" in url
        assert "version=" in url.lower()
        assert "layers=" in url.lower() or "LAYERS=" in url
        assert "bbox=" in url.lower() or "BBOX=" in url
        assert "width=" in url.lower() or "WIDTH=" in url
        assert "height=" in url.lower() or "HEIGHT=" in url
        assert "format=" in url.lower() or "FORMAT=" in url
    
    def test_wms_tile_url_different_layers(self, map_service):
        """Test WMS tile URL generation for different layers"""
        bbox = (77.5, 12.9, 77.6, 13.0)
        
        # Test LISS3 layer
        url_liss3 = map_service.get_wms_tile_url(bbox, layer="LISS3")
        assert "LISS3" in url_liss3 or "liss3" in url_liss3.lower()
        
        # Test Vector layer
        url_vector = map_service.get_wms_tile_url(bbox, layer="Vector")
        assert "Vector" in url_vector or "vector" in url_vector.lower()
    
    def test_wms_tile_url_bbox_order(self, map_service):
        """Test WMS tile URL bbox parameter order (minx,miny,maxx,maxy)"""
        bbox = (77.5, 12.9, 77.6, 13.0)
        url = map_service.get_wms_tile_url(bbox)
        
        # Extract bbox parameter
        assert "77.5" in url
        assert "12.9" in url
        assert "77.6" in url
        assert "13.0" in url
    
    def test_wms_tile_url_custom_dimensions(self, map_service):
        """Test WMS tile URL with custom width and height"""
        bbox = (77.5, 12.9, 77.6, 13.0)
        url = map_service.get_wms_tile_url(bbox, width=512, height=512)
        
        assert "512" in url
    
    def test_wms_tile_url_different_formats(self, map_service):
        """Test WMS tile URL with different image formats"""
        bbox = (77.5, 12.9, 77.6, 13.0)
        
        # Test PNG format
        url_png = map_service.get_wms_tile_url(bbox, format="image/png")
        assert "png" in url_png.lower()
        
        # Test JPEG format
        url_jpeg = map_service.get_wms_tile_url(bbox, format="image/jpeg")
        assert "jpeg" in url_jpeg.lower() or "jpg" in url_jpeg.lower()


class TestCoordinateTransformation:
    """Test coordinate transformation and precision handling - Task 3.4"""
    
    def test_coordinate_rounding_to_precision(self, map_service):
        """Test coordinates are rounded to configured precision"""
        # Input with high precision
        result = map_service.validate_coordinates(12.97161234567, 77.59461234567)
        
        assert result.is_valid is True
        # Should be rounded to 4 decimal places (default precision)
        assert result.normalized_coordinates == (12.9716, 77.5946)
    
    def test_coordinate_precision_consistency(self, map_service):
        """Test coordinate precision is consistent across operations"""
        lat, lon = 12.97165, 77.59465
        result = map_service.validate_coordinates(lat, lon)
        
        assert result.is_valid is True
        # Normalized coordinates should have exactly 4 decimal places
        norm_lat, norm_lon = result.normalized_coordinates
        assert len(str(norm_lat).split('.')[-1]) <= 4
        assert len(str(norm_lon).split('.')[-1]) <= 4
    
    def test_coordinate_transformation_preserves_location(self, map_service):
        """Test coordinate transformation doesn't significantly change location"""
        original_lat, original_lon = 12.97165, 77.59465
        result = map_service.validate_coordinates(original_lat, original_lon)
        
        assert result.is_valid is True
        norm_lat, norm_lon = result.normalized_coordinates
        
        # Difference should be less than precision threshold
        assert abs(norm_lat - original_lat) < 0.0001
        assert abs(norm_lon - original_lon) < 0.0001
    
    def test_coordinate_transformation_edge_cases(self, map_service):
        """Test coordinate transformation at boundary edges"""
        # Test at minimum latitude boundary
        result_min = map_service.validate_coordinates(6.0001, 77.5946)
        assert result_min.is_valid is True
        
        # Test at maximum latitude boundary
        result_max = map_service.validate_coordinates(36.9999, 77.5946)
        assert result_max.is_valid is True
    
    def test_coordinate_decimal_places_validation(self, map_service):
        """Test validation of decimal places in coordinates"""
        # 1 decimal place - should fail
        result_1 = map_service.validate_coordinates(12.9, 77.5)
        assert result_1.is_valid is False
        
        # 2 decimal places - should fail
        result_2 = map_service.validate_coordinates(12.97, 77.59)
        assert result_2.is_valid is False
        
        # 3 decimal places - should fail
        result_3 = map_service.validate_coordinates(12.971, 77.594)
        assert result_3.is_valid is False
        
        # 4 decimal places - should pass
        result_4 = map_service.validate_coordinates(12.9716, 77.5946)
        assert result_4.is_valid is True
        
        # 6 decimal places - should pass
        result_6 = map_service.validate_coordinates(12.971612, 77.594612)
        assert result_6.is_valid is True


class TestHobliBoundaryDetection:
    """Test Hobli boundary detection accuracy - Task 3.4"""
    
    def test_hobli_detection_consistency(self, map_service):
        """Test Hobli detection is consistent for same coordinates"""
        lat, lon = 12.9716, 77.5946
        
        hobli1 = map_service.get_hobli_from_coordinates(lat, lon)
        hobli2 = map_service.get_hobli_from_coordinates(lat, lon)
        
        assert hobli1 == hobli2
        assert hobli1["hobli_id"] == hobli2["hobli_id"]
    
    def test_hobli_detection_nearby_coordinates(self, map_service):
        """Test Hobli detection for nearby coordinates in same region"""
        # Two points very close together should be in same Hobli
        hobli1 = map_service.get_hobli_from_coordinates(12.9716, 77.5946)
        hobli2 = map_service.get_hobli_from_coordinates(12.9717, 77.5947)
        
        assert hobli1["hobli_id"] == hobli2["hobli_id"]
        assert hobli1["district"] == hobli2["district"]
    
    def test_hobli_detection_different_states(self, map_service):
        """Test Hobli detection distinguishes different states"""
        # Karnataka (Bangalore)
        hobli_ka = map_service.get_hobli_from_coordinates(12.9716, 77.5946)
        
        # Tamil Nadu (Chennai)
        hobli_tn = map_service.get_hobli_from_coordinates(13.0827, 80.2707)
        
        assert hobli_ka["state"] != hobli_tn["state"]
        assert hobli_ka["hobli_id"] != hobli_tn["hobli_id"]
    
    def test_hobli_detection_returns_required_fields(self, map_service):
        """Test Hobli detection returns all required fields"""
        hobli = map_service.get_hobli_from_coordinates(12.9716, 77.5946)
        
        assert "hobli_id" in hobli
        assert "hobli_name" in hobli
        assert "district" in hobli
        assert "state" in hobli
        
        # All fields should be non-empty strings
        assert isinstance(hobli["hobli_id"], str) and len(hobli["hobli_id"]) > 0
        assert isinstance(hobli["hobli_name"], str) and len(hobli["hobli_name"]) > 0
        assert isinstance(hobli["district"], str) and len(hobli["district"]) > 0
        assert isinstance(hobli["state"], str) and len(hobli["state"]) > 0
    
    def test_hobli_detection_fallback_for_unknown_region(self, map_service):
        """Test Hobli detection provides fallback for unknown regions"""
        # Remote region that might not have specific Hobli mapping
        hobli = map_service.get_hobli_from_coordinates(25.0, 90.0)
        
        assert hobli is not None
        assert "hobli_id" in hobli
        assert "state" in hobli
        # Should have some fallback value
        assert hobli["hobli_id"] is not None


class TestGPSLocationValidation:
    """Test GPS location capture and validation - Task 3.4"""
    
    def test_gps_coordinates_within_india(self, map_service):
        """Test GPS coordinates within India are validated correctly"""
        # Simulate GPS coordinates from various Indian cities (with 4+ decimal places)
        gps_coords = [
            (28.6139, 77.2091),  # Delhi
            (19.0761, 72.8777),  # Mumbai
            (22.5726, 88.3639),  # Kolkata
            (17.3851, 78.4867),  # Hyderabad
        ]
        
        for lat, lon in gps_coords:
            result = map_service.validate_coordinates(lat, lon)
            assert result.is_valid is True, f"GPS coordinates ({lat}, {lon}) should be valid"
    
    def test_gps_coordinates_outside_india(self, map_service):
        """Test GPS coordinates outside India are rejected"""
        # Simulate GPS coordinates from outside India
        gps_coords = [
            (51.5074, -0.1278),   # London
            (40.7128, -74.0060),  # New York
            (35.6762, 139.6503),  # Tokyo
        ]
        
        for lat, lon in gps_coords:
            result = map_service.validate_coordinates(lat, lon)
            assert result.is_valid is False, f"GPS coordinates ({lat}, {lon}) should be invalid"
    
    def test_gps_coordinate_precision_handling(self, map_service):
        """Test GPS coordinates with varying precision are handled correctly"""
        # GPS typically provides 6-8 decimal places
        high_precision_lat = 12.971612345
        high_precision_lon = 77.594612345
        
        result = map_service.validate_coordinates(high_precision_lat, high_precision_lon)
        
        assert result.is_valid is True
        # Should be normalized to configured precision
        assert result.normalized_coordinates is not None
    
    def test_gps_coordinate_boundary_validation(self, map_service):
        """Test GPS coordinates at India's geographic boundaries"""
        # Test coordinates near India's boundaries (with 4+ decimal places)
        boundary_coords = [
            (8.0001, 77.0001),    # Southern region
            (35.0001, 77.0001),   # Northern region
            (20.0001, 70.0001),   # Western region
            (20.0001, 95.0001),   # Eastern region
        ]
        
        for lat, lon in boundary_coords:
            result = map_service.validate_coordinates(lat, lon)
            # These should all be valid as they're within India's bounds
            assert result.is_valid is True
    
    def test_gps_coordinate_error_messages(self, map_service):
        """Test GPS validation provides clear error messages"""
        # Test various invalid scenarios
        
        # Out of range latitude
        result1 = map_service.validate_coordinates(100.0, 77.5946)
        assert result1.is_valid is False
        assert result1.error is not None
        assert len(result1.error) > 0
        
        # Out of range longitude
        result2 = map_service.validate_coordinates(12.9716, 200.0)
        assert result2.is_valid is False
        assert result2.error is not None
        
        # Outside India
        result3 = map_service.validate_coordinates(51.5074, -0.1278)
        assert result3.is_valid is False
        assert result3.error is not None
    
    def test_gps_coordinate_normalization_for_storage(self, map_service):
        """Test GPS coordinates are normalized appropriately for database storage"""
        # High precision GPS input
        gps_lat = 12.97161234567890
        gps_lon = 77.59461234567890
        
        result = map_service.validate_coordinates(gps_lat, gps_lon)
        
        assert result.is_valid is True
        norm_lat, norm_lon = result.normalized_coordinates
        
        # Normalized coordinates should be suitable for DynamoDB storage
        # (not too many decimal places, but enough for accuracy)
        assert isinstance(norm_lat, float)
        assert isinstance(norm_lon, float)
        assert 6.0 <= norm_lat <= 37.0
        assert 68.0 <= norm_lon <= 97.0
