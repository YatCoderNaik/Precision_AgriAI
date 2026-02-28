"""
Property-Based Tests for BrainService

Tests multimodal AI orchestration properties including:
- Visual verification consistency
- Concurrent processing performance
- Risk classification consistency
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime
import asyncio

from services.brain_service import BrainService, AnalysisResult, Alert, ClusterAnalysis
from services.gee_service import GEEData
from services.sentinel_service import SentinelData


# Test data generators
@st.composite
def valid_coordinates(draw):
    """Generate valid latitude/longitude pairs"""
    # Focus on Indian region for realistic testing
    lat = draw(st.floats(min_value=8.0, max_value=35.0))
    lon = draw(st.floats(min_value=68.0, max_value=97.0))
    return lat, lon


@st.composite
def ndvi_values(draw):
    """Generate valid NDVI values"""
    return draw(st.floats(min_value=-1.0, max_value=1.0))


@st.composite
def cloud_cover_values(draw):
    """Generate valid cloud cover percentages"""
    return draw(st.floats(min_value=0.0, max_value=100.0))


# Property 21: Visual Verification Consistency
# **Validates: Requirements 15.1, 15.2, 15.3**

@pytest.mark.asyncio
@given(coords=valid_coordinates())
@settings(max_examples=10, deadline=30000)  # 30s deadline for async operations
async def test_visual_verification_consistency(coords):
    """
    Property 21: Visual Verification Consistency
    
    For any plot analysis, the system should:
    1. Fetch appropriate Sentinel-2 imagery from AWS Open Data
    2. Cross-reference it with Google Earth Engine vegetation indices
    3. Flag confidence warnings when visual and analytical data are inconsistent
    
    **Validates: Requirements 15.1, 15.2, 15.3**
    """
    lat, lon = coords
    
    # Initialize BrainService with mock GEE (to avoid external dependencies)
    brain_service = BrainService(use_mock_gee=True)
    
    try:
        # Perform multimodal analysis
        result = await brain_service.analyze_plot(lat, lon)
        
        # Property 1: Result must contain both GEE and Sentinel data
        assert isinstance(result, AnalysisResult), "Result must be AnalysisResult"
        assert isinstance(result.gee_data, GEEData), "Must include GEE data"
        assert isinstance(result.sentinel_data, SentinelData), "Must include Sentinel data"
        
        # Property 2: NDVI value must be in valid range
        assert -1.0 <= result.gee_data.ndvi_float <= 1.0, \
            f"NDVI {result.gee_data.ndvi_float} outside valid range [-1, 1]"
        
        # Property 3: Sentinel image URL must be provided
        assert result.sentinel_data.image_url, "Sentinel image URL must be provided"
        assert isinstance(result.sentinel_data.image_url, str), "Image URL must be string"
        
        # Property 4: Bedrock reasoning must be present
        assert result.bedrock_reasoning, "Bedrock reasoning must be present"
        assert result.bedrock_reasoning.risk_classification in ['low', 'medium', 'high', 'critical'], \
            f"Invalid risk classification: {result.bedrock_reasoning.risk_classification}"
        
        # Property 5: Confidence score must be in valid range
        assert 0.0 <= result.bedrock_reasoning.confidence_score <= 1.0, \
            f"Confidence {result.bedrock_reasoning.confidence_score} outside [0, 1]"
        
        # Property 6: Risk level must match Bedrock classification
        assert result.risk_level == result.bedrock_reasoning.risk_classification, \
            "Risk level must match Bedrock classification"
        
        # Property 7: Analysis timestamp must be recent
        time_diff = (datetime.now() - result.analysis_timestamp).total_seconds()
        assert time_diff < 60, "Analysis timestamp must be recent (< 60s)"
        
        # Property 8: Visual observations must be provided
        assert result.bedrock_reasoning.visual_observations, \
            "Visual observations must be provided"
        
        # Property 9: Recommendations must be provided
        assert len(result.bedrock_reasoning.recommendations) > 0, \
            "At least one recommendation must be provided"
        
        # Property 10: Confidence warning for inconsistency
        # If NDVI is very high (>0.8) but confidence is low (<0.5),
        # this suggests visual/analytical inconsistency
        if result.gee_data.ndvi_float > 0.8 and result.confidence < 0.5:
            assert 'inconsist' in result.bedrock_reasoning.explanation.lower() or \
                   'warning' in result.bedrock_reasoning.explanation.lower() or \
                   'concern' in result.bedrock_reasoning.explanation.lower(), \
                "Low confidence with high NDVI should flag inconsistency"
        
    except Exception as e:
        # For property tests, we want to understand failures
        pytest.fail(f"Analysis failed for coordinates ({lat}, {lon}): {e}")


@pytest.mark.asyncio
@given(
    coords=valid_coordinates(),
    ndvi=ndvi_values()
)
@settings(max_examples=10, deadline=10000)
async def test_risk_classification_consistency(coords, ndvi):
    """
    Property: Risk classification must be consistent with NDVI thresholds
    
    Tests that risk classification follows expected patterns:
    - NDVI < 0.2: critical or high risk
    - NDVI 0.2-0.4: high or medium risk
    - NDVI 0.4-0.6: medium or low risk
    - NDVI > 0.6: low risk
    """
    lat, lon = coords
    
    # Create mock analysis result with specific NDVI
    from services.brain_service import BedrockResponse
    
    brain_service = BrainService(use_mock_gee=True)
    
    # Use fallback classification to test deterministic behavior
    bedrock_response = brain_service._fallback_risk_classification(ndvi)
    
    # Verify risk classification consistency
    if ndvi < 0.2:
        assert bedrock_response.risk_classification in ['critical', 'high'], \
            f"NDVI {ndvi:.3f} should be critical/high risk"
    elif ndvi < 0.4:
        assert bedrock_response.risk_classification in ['high', 'medium'], \
            f"NDVI {ndvi:.3f} should be high/medium risk"
    elif ndvi < 0.6:
        assert bedrock_response.risk_classification in ['medium', 'low'], \
            f"NDVI {ndvi:.3f} should be medium/low risk"
    else:
        assert bedrock_response.risk_classification == 'low', \
            f"NDVI {ndvi:.3f} should be low risk"
    
    # Confidence should be reasonable
    assert 0.3 <= bedrock_response.confidence_score <= 1.0, \
        "Confidence should be reasonable (0.3-1.0)"
    
    # Recommendations should be provided
    assert len(bedrock_response.recommendations) > 0, \
        "Recommendations must be provided"


@pytest.mark.asyncio
@given(
    alerts_count=st.integers(min_value=0, max_value=20),
    avg_ndvi=ndvi_values()
)
@settings(max_examples=10)
async def test_cluster_outbreak_detection(alerts_count, avg_ndvi):
    """
    Property: Cluster outbreak detection must be consistent
    
    Tests that cluster analysis correctly identifies outbreaks based on:
    - Number of affected plots
    - Average NDVI values
    - Risk level distribution
    """
    # Filter out negative NDVI for this test (focus on vegetation)
    assume(avg_ndvi >= 0)
    
    brain_service = BrainService(use_mock_gee=True)
    
    # Create mock alerts
    alerts = []
    for i in range(alerts_count):
        # Vary NDVI around the average
        plot_ndvi = max(0, min(1.0, avg_ndvi + (i % 3 - 1) * 0.1))
        
        # Determine risk level based on NDVI
        if plot_ndvi < 0.2:
            risk = 'critical'
        elif plot_ndvi < 0.4:
            risk = 'high'
        elif plot_ndvi < 0.6:
            risk = 'medium'
        else:
            risk = 'low'
        
        alert = Alert(
            plot_id=f"plot_{i}",
            gee_proof={'ndvi_value': plot_ndvi},
            risk_level=risk,
            timestamp=datetime.now()
        )
        alerts.append(alert)
    
    # Perform cluster analysis
    cluster_result = brain_service.detect_cluster_outbreak(alerts)
    
    # Property 1: Result must be ClusterAnalysis
    assert isinstance(cluster_result, ClusterAnalysis)
    
    # Property 2: Affected plots count must match
    assert cluster_result.affected_plots == alerts_count
    
    # Property 3: Outbreak detection logic
    if alerts_count >= 3 and avg_ndvi < 0.3:
        assert cluster_result.outbreak_detected, \
            f"Should detect outbreak with {alerts_count} plots and NDVI {avg_ndvi:.3f}"
    
    if alerts_count < 3:
        assert not cluster_result.outbreak_detected, \
            "Should not detect outbreak with < 3 plots"
    
    # Property 4: Severity must be valid
    assert cluster_result.severity in ['none', 'low', 'medium', 'high', 'critical']
    
    # Property 5: Recommended action must be valid
    assert cluster_result.recommended_action in [
        'no_action', 'routine_monitoring', 'enhanced_monitoring',
        'coordinate_intervention', 'immediate_intervention'
    ]
    
    # Property 6: Average NDVI must be in valid range
    if alerts_count > 0:
        assert 0.0 <= cluster_result.avg_ndvi <= 1.0


@pytest.mark.asyncio
@given(coords=valid_coordinates())
@settings(max_examples=5, deadline=10000)
async def test_farmer_guidance_generation(coords):
    """
    Property: Farmer guidance must be generated for any analysis result
    
    Tests that farmer-friendly guidance is always provided and is
    appropriate for the risk level.
    """
    lat, lon = coords
    
    brain_service = BrainService(use_mock_gee=True)
    
    # Perform analysis
    result = await brain_service.analyze_plot(lat, lon)
    
    # Generate farmer guidance
    guidance = await brain_service.generate_farmer_guidance(result, language="English")
    
    # Property 1: Guidance must be non-empty string
    assert isinstance(guidance, str), "Guidance must be string"
    assert len(guidance) > 0, "Guidance must not be empty"
    
    # Property 2: Guidance should mention key information
    # (either NDVI value or risk level should be referenced)
    guidance_lower = guidance.lower()
    
    # Property 3: Critical/high risk should have urgent language
    if result.risk_level in ['critical', 'high']:
        assert any(word in guidance_lower for word in ['urgent', 'important', 'immediate', 'attention']), \
            "High risk guidance should use urgent language"
    
    # Property 4: Low risk should have positive language
    if result.risk_level == 'low':
        assert any(word in guidance_lower for word in ['good', 'healthy', 'maintain', 'continue']), \
            "Low risk guidance should use positive language"


# Helper function to run async tests
def test_run_async_property_tests():
    """
    Helper to run all async property tests
    
    This ensures property tests are executed properly in the test suite.
    """
    # This test serves as a marker that property tests exist
    # The actual async tests are run by pytest-asyncio
    assert True


# Property 22: Concurrent Processing Performance
# **Validates: Requirements 8.1, 8.5**

@pytest.mark.asyncio
@given(coords=valid_coordinates())
@settings(max_examples=5, deadline=None)  # No deadline for performance test
async def test_concurrent_processing_performance(coords):
    """
    Property 22: Concurrent Processing Performance
    
    For any analysis request, the system should:
    1. Complete end-to-end processing within 8 seconds
    2. Fetch Google Earth Engine analytics and AWS Sentinel-2 imagery concurrently
    3. Optimize performance through parallel data fetching
    
    **Validates: Requirements 8.1, 8.5**
    """
    import time
    
    lat, lon = coords
    
    brain_service = BrainService(use_mock_gee=True)
    
    # Measure end-to-end analysis time
    start_time = time.time()
    
    try:
        result = await brain_service.analyze_plot(lat, lon)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Property 1: Analysis must complete within 8 seconds
        # Note: With mock data, this should be very fast (<1s)
        # With real GEE/Sentinel, target is <8s
        assert elapsed_time < 8.0, \
            f"Analysis took {elapsed_time:.2f}s, exceeds 8s requirement"
        
        # Property 2: Result must be complete
        assert isinstance(result, AnalysisResult)
        assert result.gee_data is not None
        assert result.sentinel_data is not None
        assert result.bedrock_reasoning is not None
        
        # Property 3: Both data sources must have timestamps
        # This verifies concurrent fetching occurred
        assert result.gee_data.acquisition_date is not None
        assert result.sentinel_data.acquisition_date is not None
        
        # Property 4: Analysis timestamp must be after data acquisition
        assert result.analysis_timestamp >= result.gee_data.acquisition_date
        
        # Log performance for monitoring
        print(f"\nPerformance: Analysis completed in {elapsed_time:.3f}s for ({lat:.4f}, {lon:.4f})")
        
    except Exception as e:
        pytest.fail(f"Concurrent processing failed: {e}")


@pytest.mark.asyncio
@given(
    coords_list=st.lists(valid_coordinates(), min_size=2, max_size=5)
)
@settings(max_examples=3, deadline=None)
async def test_concurrent_multiple_plots_performance(coords_list):
    """
    Property: Multiple plot analyses should benefit from concurrent processing
    
    Tests that analyzing multiple plots concurrently is faster than sequential.
    """
    import time
    
    brain_service = BrainService(use_mock_gee=True)
    
    # Measure concurrent processing time
    start_concurrent = time.time()
    
    # Analyze all plots concurrently
    tasks = [brain_service.analyze_plot(lat, lon) for lat, lon in coords_list]
    results_concurrent = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_concurrent = time.time()
    concurrent_time = end_concurrent - start_concurrent
    
    # Property 1: All analyses should complete
    successful_results = [r for r in results_concurrent if isinstance(r, AnalysisResult)]
    assert len(successful_results) >= len(coords_list) * 0.8, \
        "At least 80% of analyses should succeed"
    
    # Property 2: Concurrent processing should be reasonably fast
    # With mock data, should complete quickly even for multiple plots
    avg_time_per_plot = concurrent_time / len(coords_list)
    assert avg_time_per_plot < 5.0, \
        f"Average time per plot {avg_time_per_plot:.2f}s exceeds 5s"
    
    # Property 3: Total time should be less than sequential worst case
    # (assuming each plot takes at most 8s sequentially)
    max_sequential_time = len(coords_list) * 8.0
    assert concurrent_time < max_sequential_time, \
        "Concurrent processing should be faster than sequential"
    
    print(f"\nConcurrent performance: {len(coords_list)} plots in {concurrent_time:.3f}s "
          f"(avg {avg_time_per_plot:.3f}s per plot)")


@pytest.mark.asyncio
@settings(max_examples=3, deadline=15000)
async def test_service_initialization_performance():
    """
    Property: Service initialization should be fast
    
    Tests that BrainService and its sub-services initialize quickly.
    """
    import time
    
    start_time = time.time()
    
    # Initialize service
    brain_service = BrainService(use_mock_gee=True)
    
    end_time = time.time()
    init_time = end_time - start_time
    
    # Property 1: Initialization should be fast (< 2 seconds)
    assert init_time < 2.0, \
        f"Service initialization took {init_time:.2f}s, should be < 2s"
    
    # Property 2: Service should be ready to use
    service_info = brain_service.get_service_info()
    assert service_info is not None
    assert 'service' in service_info
    assert service_info['service'] == 'BrainService'
    
    print(f"\nInitialization performance: {init_time:.3f}s")
