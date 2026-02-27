"""
Configuration Validation Script

Validates all configuration requirements for Precision AgriAI including:
- AWS credentials and region
- Google Earth Engine credentials
- Service configurations
- DynamoDB tables
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import print_configuration_status, get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main validation function"""
    print("\nPrecision AgriAI Configuration Validation")
    print("=" * 60)
    
    # Load and validate configuration
    try:
        settings = get_settings()
        logger.info(f"Loaded configuration for environment: {settings.environment}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Print configuration status
    all_valid = print_configuration_status()
    
    # Print service configurations
    print("\nService Configurations:")
    print("-" * 60)
    print(f"AWS Region: {settings.aws.region}")
    print(f"DynamoDB Plots Table: {settings.aws.dynamodb_plots_table}")
    print(f"DynamoDB Alerts Table: {settings.aws.dynamodb_alerts_table}")
    print(f"Bedrock Model: {settings.aws.bedrock_model_id}")
    print(f"Bedrock Haiku Model: {settings.aws.bedrock_haiku_model_id}")
    print(f"S3 Audio Bucket: {settings.aws.s3_audio_bucket}")
    print(f"\nBhuvan Base URL: {settings.map_service.bhuvan_base_url}")
    print(f"India Lat Bounds: {settings.map_service.india_lat_bounds}")
    print(f"India Lon Bounds: {settings.map_service.india_lon_bounds}")
    print(f"\nGEE NDVI Collection: {settings.gee.ndvi_collection}")
    print(f"GEE Cloud Cover Threshold: {settings.gee.cloud_cover_threshold}%")
    print(f"\nSentinel S3 Bucket: {settings.sentinel.s3_bucket}")
    print(f"Sentinel Resolution: {settings.sentinel.default_resolution}")
    print(f"\nVoice Default Language: {settings.voice_service.default_language}")
    print(f"Voice Polly Voice ID: {settings.voice_service.polly_voice_id}")
    print(f"\nBrain Service Max Tokens: {settings.brain_service.max_tokens}")
    print(f"Brain Service Temperature: {settings.brain_service.temperature}")
    print(f"NDVI Threshold Critical: {settings.brain_service.ndvi_threshold_critical}")
    print(f"NDVI Threshold High: {settings.brain_service.ndvi_threshold_high}")
    print(f"NDVI Threshold Medium: {settings.brain_service.ndvi_threshold_medium}")
    print(f"\nDB Service Read Capacity: {settings.db_service.read_capacity_units}")
    print(f"DB Service Write Capacity: {settings.db_service.write_capacity_units}")
    print(f"DB Service Encryption: {settings.db_service.enable_encryption}")
    print(f"\nPerformance Max Response Time: {settings.performance.max_response_time_seconds}s")
    print(f"Performance Concurrent Fetch: {settings.performance.concurrent_fetch_enabled}")
    print(f"Performance Cache TTL: {settings.performance.cache_ttl_seconds}s")
    print("-" * 60)
    
    # Exit with appropriate code
    if all_valid:
        print("\n✓ Configuration validation passed")
        sys.exit(0)
    else:
        print("\n✗ Configuration validation failed - please fix issues above")
        sys.exit(1)


if __name__ == "__main__":
    main()
