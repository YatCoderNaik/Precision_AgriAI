"""
BrainService Live Demo

Demonstrates the complete multimodal AI analysis workflow:
1. Initialize BrainService with GEEService and SentinelService
2. Analyze a Bangalore farm location
3. Show GEE NDVI data, Sentinel imagery, and Bedrock reasoning
4. Generate farmer guidance
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from services.brain_service import BrainService
from services.gee_service import GEEService
from services.sentinel_service import SentinelService


async def main():
    """Run BrainService demo"""
    print("=" * 80)
    print("BrainService Live Demo - Multimodal AI Analysis")
    print("=" * 80)
    print()
    
    # Initialize configuration
    print("1. Initializing services...")
    settings = Settings()
    
    # Initialize services
    gee_service = GEEService(settings.gee)
    sentinel_service = SentinelService(region=settings.aws.region)
    brain_service = BrainService(
        use_mock_gee=False,  # Try real GEE first, will fallback to mock if unavailable
        region=settings.aws.region
    )
    
    print(f"   ✓ BrainService initialized (GEE mock: {brain_service.gee_service.use_mock})")
    print()
    
    # Test coordinates - Bangalore farm area
    latitude = 12.434
    longitude = 76.8333
    
    print(f"2. Analyzing plot at coordinates: ({latitude}, {longitude})")
    print()
    
    # Perform multimodal analysis
    print("3. Running multimodal analysis...")
    print("   - Fetching NDVI data from Google Earth Engine")
    print("   - Fetching satellite imagery from Sentinel-2")
    print("   - Analyzing with AWS Bedrock Claude 3 Sonnet")
    print()
    
    try:
        result = await brain_service.analyze_plot(
            lat=latitude,
            lon=longitude
        )
        
        print("=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)
        print()
        
        # GEE Data
        print("📊 NDVI Data (Google Earth Engine):")
        print(f"   NDVI Value: {result.gee_data.ndvi_float:.4f}")
        print(f"   Data Quality: {result.gee_data.quality_score:.2f}")
        print(f"   Timestamp: {result.analysis_timestamp}")
        print()
        
        # Sentinel Data
        print("🛰️  Satellite Imagery (Sentinel-2):")
        if result.sentinel_data.image_url:
            print(f"   Image URL: {result.sentinel_data.image_url[:80]}...")
            print(f"   Image Quality: {result.sentinel_data.quality_assessment}")
            print(f"   Cloud Cover: {result.sentinel_data.cloud_cover_percentage:.1f}%")
        else:
            print("   No imagery available")
        print()
        
        # Bedrock Analysis
        print("🤖 AI Analysis (AWS Bedrock):")
        print(f"   Risk Level: {result.risk_level.upper()}")
        print(f"   Confidence: {result.confidence:.2f}")
        print()
        print("   Recommendations:")
        for i, rec in enumerate(result.bedrock_reasoning.recommendations, 1):
            print(f"   {i}. {rec}")
        print()
        
        # Farmer Guidance
        print("4. Generating farmer-friendly guidance...")
        print()
        
        guidance = await brain_service.generate_farmer_guidance(
            analysis=result,
            language="English"
        )
        
        print("=" * 80)
        print("FARMER GUIDANCE")
        print("=" * 80)
        print()
        print(guidance)
        print()
        
    except ValueError as e:
        print(f"⚠️  Analysis incomplete: {e}")
        print()
        print("Note: This demo requires recent Sentinel-2 imagery for the location.")
        print("The BrainService is designed to work with both GEE and Sentinel data.")
        print("In production, you would implement fallback logic or use cached imagery.")
        print()
        print("Let's demonstrate the other features that don't require Sentinel data...")
        print()
        
        # Cluster Detection Demo
        print("=" * 80)
        print("5. Testing cluster outbreak detection...")
        print()
        
        # Create sample alerts for cluster detection
        from services.brain_service import Alert
        from datetime import datetime
        
        sample_alerts = [
            Alert(
                plot_id='plot_001',
                gee_proof={'ndvi_value': 0.15},
                risk_level='critical',
                timestamp=datetime.now()
            ),
            Alert(
                plot_id='plot_002',
                gee_proof={'ndvi_value': 0.18},
                risk_level='critical',
                timestamp=datetime.now()
            ),
            Alert(
                plot_id='plot_003',
                gee_proof={'ndvi_value': 0.22},
                risk_level='high',
                timestamp=datetime.now()
            )
        ]
        
        cluster_result = brain_service.detect_cluster_outbreak(
            hobli_alerts=sample_alerts
        )
        
        print(f"   Cluster Detected: {cluster_result.outbreak_detected}")
        print(f"   Affected Plots: {cluster_result.affected_plots}")
        print(f"   Average NDVI: {cluster_result.avg_ndvi:.3f}")
        print(f"   Severity: {cluster_result.severity}")
        print(f"   Recommended Action: {cluster_result.recommended_action}")
        print()
        
        print("=" * 80)
        print("✅ Demo completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
